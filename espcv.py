import cv2
import numpy as np
import time
import urllib.request
import threading
import argparse


class ESPCamProcessor:
    def __init__(self, camera_url, detect_humans=True, detect_colors=True, target_colors=None):
        """
        Initialize the ESP32-CAM video processor.

        Args:
            camera_url: URL of the ESP32-CAM stream (e.g., 'http://192.168.1.100:81/stream')
            detect_humans: Whether to perform human detection
            detect_colors: Whether to perform color detection
            target_colors: Dictionary of target colors in HSV format {'color_name': (lower_hsv, upper_hsv)}
        """
        self.camera_url = camera_url
        self.detect_humans = detect_humans
        self.detect_colors = detect_colors

        # Default target colors if none provided
        self.target_colors = target_colors or {
            'red': (np.array([0, 100, 100]), np.array([10, 255, 255])),  # Red lower range
            'red2': (np.array([160, 100, 100]), np.array([180, 255, 255])),  # Red upper range
            'green': (np.array([40, 100, 100]), np.array([80, 255, 255])),
            'blue': (np.array([100, 150, 100]), np.array([140, 255, 255]))
        }

        # For video processing
        self.frame = None
        self.processed_frame = None
        self.is_running = False

        # For detection results
        self.detected_humans = []
        self.detected_colors = {}

        # Load human detection model (HOG-based by default)
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        # For potential YOLO implementation
        self.net = None
        self.output_layers = None

        # Attempt to load YOLO if available
        self.try_load_yolo()

    def try_load_yolo(self):
        """Try to load YOLO model if available"""
        try:
            # Load YOLO
            print("Attempting to load YOLO model...")
            self.net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")

            # Get output layer names
            layer_names = self.net.getLayerNames()
            try:
                # OpenCV 4.5.4+
                unconnected_out_layers = self.net.getUnconnectedOutLayers()
                self.output_layers = [layer_names[i - 1] for i in unconnected_out_layers]
            except:
                # Older OpenCV versions
                unconnected_out_layers = self.net.getUnconnectedOutLayers()
                self.output_layers = [layer_names[i[0] - 1] for i in unconnected_out_layers]

            print("YOLO model loaded successfully!")
        except Exception as e:
            print(f"Could not load YOLO model: {e}")
            print("Falling back to HOG detector for human detection")
            self.net = None

    def start(self):
        """Start video processing threads"""
        self.is_running = True

        # Start video capture thread
        self.video_thread = threading.Thread(target=self.capture_video)
        self.video_thread.daemon = True
        self.video_thread.start()

        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_video)
        self.processing_thread.daemon = True
        self.processing_thread.start()

        # Start display thread
        self.display_thread = threading.Thread(target=self.display_video)
        self.display_thread.daemon = True
        self.display_thread.start()

        print(f"Connected to ESP32-CAM at {self.camera_url}")
        print("Press 'q' to quit, 'h' to toggle human detection, 'c' to toggle color detection")

    def capture_video(self):
        """Thread for capturing video directly from ESP32-CAM stream"""
        try:
            # Try different approaches to connect to the ESP32-CAM
            if 'stream' in self.camera_url:
                # For stream URL format (MJPEG)
                self.capture_mjpeg_stream()
            else:
                # For single JPEG URL (http://ip/capture or similar)
                self.capture_jpeg_sequence()
        except Exception as e:
            print(f"Error in video capture: {e}")
            self.is_running = False

    def capture_mjpeg_stream(self):
        """Capture from MJPEG stream URL"""
        print("Using MJPEG stream capture method")
        stream = urllib.request.urlopen(self.camera_url)
        bytes_data = b''

        while self.is_running:
            try:
                bytes_data += stream.read(1024)
                a = bytes_data.find(b'\xff\xd8')  # JPEG start
                b = bytes_data.find(b'\xff\xd9')  # JPEG end

                if a != -1 and b != -1:
                    jpg = bytes_data[a:b + 2]
                    bytes_data = bytes_data[b + 2:]

                    # Decode the JPEG data
                    self.frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            except Exception as e:
                print(f"Error reading from stream: {e}")
                time.sleep(1)
                try:
                    # Try to reconnect
                    stream = urllib.request.urlopen(self.camera_url)
                    bytes_data = b''
                except:
                    pass

    def capture_jpeg_sequence(self):
        """Capture sequence of JPEG images from URL"""
        print("Using JPEG sequence capture method")
        while self.is_running:
            try:
                # Get single image
                img_resp = urllib.request.urlopen(self.camera_url)
                img_bytes = img_resp.read()

                # Convert to OpenCV format
                self.frame = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

                # Small delay to control frame rate
                time.sleep(0.05)
            except Exception as e:
                print(f"Error capturing JPEG: {e}")
                time.sleep(1)

    def process_video(self):
        """Thread for processing video frames with OpenCV"""
        while self.is_running:
            if self.frame is not None:
                try:
                    # Make a copy of the frame for processing
                    processed = self.frame.copy()

                    # Human detection
                    if self.detect_humans:
                        self.detected_humans = self.detect_humans_in_frame(processed)

                        # Draw boxes around humans
                        for (x, y, w, h) in self.detected_humans:
                            cv2.rectangle(processed, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            cv2.putText(processed, "Human", (x, y - 5),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    # Color detection
                    if self.detect_colors:
                        self.detected_colors = self.detect_colors_in_frame(processed)

                        # Draw contours for each detected color
                        for color_name, contours in self.detected_colors.items():
                            if contours:
                                if color_name.startswith('red'):
                                    color = (0, 0, 255)  # BGR for Red
                                elif color_name == 'green':
                                    color = (0, 255, 0)  # BGR for Green
                                elif color_name == 'blue':
                                    color = (255, 0, 0)  # BGR for Blue
                                else:
                                    color = (255, 255, 0)  # Default color

                                cv2.drawContours(processed, contours, -1, color, 2)

                                # Label the largest contour for each color
                                if contours:
                                    largest_contour = max(contours, key=cv2.contourArea)
                                    M = cv2.moments(largest_contour)
                                    if M["m00"] != 0:
                                        cx = int(M["m10"] / M["m00"])
                                        cy = int(M["m01"] / M["m00"])
                                        cv2.putText(processed, color_name, (cx, cy),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    # Add processing info
                    cv2.putText(processed, f"Humans: {len(self.detected_humans)}", (10, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    color_counts = {name: len(contours) for name, contours in self.detected_colors.items() if contours}
                    y_pos = 40
                    for color_name, count in color_counts.items():
                        cv2.putText(processed, f"{color_name}: {count}", (10, y_pos),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        y_pos += 20

                    # Store the processed frame
                    self.processed_frame = processed

                except Exception as e:
                    print(f"Error processing frame: {e}")

            time.sleep(0.01)  # Small delay to prevent CPU overload

    def detect_humans_in_frame(self, frame):
        """Detect humans in the frame using HOG or YOLO"""
        if self.net is not None:
            # Use YOLO for better detection if available
            return self.detect_humans_yolo(frame)
        else:
            # Use HOG detector as fallback
            return self.detect_humans_hog(frame)

    def detect_humans_hog(self, frame):
        """Detect humans using HOG detector"""
        # Resize for faster processing
        resize_factor = 1.0
        if frame.shape[1] > 640:
            resize_factor = 640 / frame.shape[1]
            frame_resized = cv2.resize(frame, (0, 0), fx=resize_factor, fy=resize_factor)
        else:
            frame_resized = frame

        # Detect people
        boxes, weights = self.hog.detectMultiScale(
            frame_resized,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05
        )

        # Scale boxes back to original size
        if resize_factor < 1.0:
            boxes = np.array([[int(x / resize_factor), int(y / resize_factor),
                               int(w / resize_factor), int(h / resize_factor)] for (x, y, w, h) in boxes])

        return boxes

    def detect_humans_yolo(self, frame):
        """Detect humans using YOLO"""
        height, width, _ = frame.shape

        # Create blob from image
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)

        class_ids = []
        confidences = []
        boxes = []

        # Process detections
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]

                # Check if the detected object is a person (class 0 in COCO dataset)
                if class_id == 0 and confidence > 0.5:
                    # Object detected is a person with confidence > 50%
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    # Rectangle coordinates
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        # Apply non-max suppression to remove overlapping boxes
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

        result_boxes = []
        for i in range(len(boxes)):
            if i in indexes:
                result_boxes.append(boxes[i])

        return np.array(result_boxes)

    def detect_colors_in_frame(self, frame):
        """Detect specified colors in the frame"""
        # Convert to HSV color space
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        results = {}

        # Process each target color
        for color_name, (lower, upper) in self.target_colors.items():
            # Create mask for this color
            mask = cv2.inRange(hsv, lower, upper)

            # Noise removal
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            # Filter small contours
            significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 500]
            results[color_name] = significant_contours

        return results

    def display_video(self):
        """Thread for displaying the processed video"""
        while self.is_running:
            if self.processed_frame is not None:
                cv2.imshow("ESP32-CAM Processing", self.processed_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.stop()
                elif key == ord('h'):
                    self.detect_humans = not self.detect_humans
                    print(f"Human detection: {'ON' if self.detect_humans else 'OFF'}")
                elif key == ord('c'):
                    self.detect_colors = not self.detect_colors
                    print(f"Color detection: {'ON' if self.detect_colors else 'OFF'}")

            time.sleep(0.03)  # ~30 FPS display

    def stop(self):
        """Stop all processes and clean up"""
        self.is_running = False

        # Wait for threads to finish
        if hasattr(self, 'video_thread') and self.video_thread.is_alive():
            self.video_thread.join(timeout=1.0)

        if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)

        if hasattr(self, 'display_thread') and self.display_thread.is_alive():
            self.display_thread.join(timeout=1.0)

        cv2.destroyAllWindows()
        print("System stopped")


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='ESP32-CAM Video Processing')
    parser.add_argument('--url', type=str, default='http://192.168.0.110//stream',
                        help='URL of the ESP32-CAM stream')
    parser.add_argument('--no-humans', action='store_true',
                        help='Disable human detection')
    parser.add_argument('--no-colors', action='store_true',
                        help='Disable color detection')

    args = parser.parse_args()

    # Create processor instance
    processor = ESPCamProcessor(
        camera_url=args.url,
        detect_humans=not args.no_humans,
        detect_colors=not args.no_colors
    )

    # Start processing
    processor.start()

    # Keep main thread alive
    try:
        while processor.is_running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping by keyboard interrupt...")
        processor.stop()


if __name__ == "__main__":
    main()