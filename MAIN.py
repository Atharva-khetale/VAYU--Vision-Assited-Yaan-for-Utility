import cv2
import numpy as np
import base64
import threading
import time
import requests
from io import BytesIO
from PIL import Image
from together import Together
import socket
import urllib.request
import queue
import os
import platform

# Initialize Together API
client = Together(api_key="tgp_v1_Dscj56nKLZN1nqvz6ynSy71CfFXw2IW-LYXI8Z85-nQ")

# ESP32-CAM configuration
ESP_CAM_IP = "192.168.239.173"  # Replace with your ESP32-CAM IP address
ESP_CAM_URL = f"http://{ESP_CAM_IP}"

# Variable to switch between local webcam and ESP32-CAM
use_esp_cam = True

# Connection timeout for ESP32-CAM (seconds)
TIMEOUT = 10

# Speech synthesis setup - using platform-specific commands
system_platform = platform.system()

# Speech queue to avoid blocking the main thread
speech_queue = queue.Queue()
is_speaking = False


def speak_windows(text):
    """TTS for Windows using PowerShell"""
    os.system(
        f'powershell -command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text}\')"')


def speak_mac(text):
    """TTS for macOS using say command"""
    os.system(f'say "{text}"')


def speak_linux(text):
    """TTS for Linux using espeak"""
    os.system(f'espeak "{text}"')


def speech_worker():
    """Thread worker to handle text-to-speech conversion"""
    global is_speaking
    while True:
        text = speech_queue.get()
        if text is None:  # Sentinel to stop the thread
            break
        is_speaking = True

        # Use platform-specific speech function
        if system_platform == "Windows":
            speak_windows(text)
        elif system_platform == "Darwin":  # macOS
            speak_mac(text)
        else:  # Linux or other systems
            speak_linux(text)

        is_speaking = False
        speech_queue.task_done()


# Start speech worker thread
speech_thread = threading.Thread(target=speech_worker, daemon=True)
speech_thread.start()


def speak(text):
    """Add text to speech queue and print"""
    speech_queue.put(text)
    print(f"🔊 {text}")  # Print with speaker emoji to indicate speech


def connect_to_stream():
    """Create connection to ESP32-CAM stream"""
    try:
        stream = urllib.request.urlopen(ESP_CAM_URL, timeout=TIMEOUT)
        bytes_buffer = bytes()
        return stream, bytes_buffer
    except Exception as e:
        speak(f"Failed to connect to ESP32-CAM: {e}")
        return None, None


def read_from_esp_cam(stream, bytes_buffer):
    """Read frame from ESP32-CAM stream"""
    if stream is None:
        return False, None

    try:
        bytes_buffer += stream.read(1024)
        a = bytes_buffer.find(b'\xff\xd8')  # JPEG start
        b = bytes_buffer.find(b'\xff\xd9')  # JPEG end

        if a != -1 and b != -1:
            jpg = bytes_buffer[a:b + 2]
            bytes_buffer = bytes_buffer[b + 2:]
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            return True, frame
        return False, None
    except Exception as e:
        speak(f"Error reading from ESP32-CAM: {e}")
        return False, None


# Initialize video capture
cap = cv2.VideoCapture(0)  # Fallback to local webcam

# ESP32-CAM stream variables
esp_stream = None
bytes_buffer = bytes()

mode = None  # "a" or "b"
running = True
last_obstacle_time = 0  # To avoid too frequent obstacle announcements


def encode_frame_to_base64(frame):
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img)
    buffered = BytesIO()
    pil_img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{img_str}"


def get_depth_map(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    depth_map = np.clip(gray * 1.5, 0, 255).astype(np.uint8)
    return depth_map


def detect_obstacle(depth_map):
    threshold = 120
    mask = cv2.inRange(depth_map, 0, threshold)
    return np.sum(mask) > 5000  # Heuristic: sufficient number of close pixels


def get_description(frame, prompt="Describe the scene"):
    img_b64 = encode_frame_to_base64(frame)
    speak("Processing image. Please wait...")

    response = client.chat.completions.create(
        model="meta-llama/Llama-Vision-Free",
        messages=[
            {
                "role": "system",
                "content": "You are assisting a visually impaired individual. Provide clear, concise and helpful answers."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": img_b64}}
                ]
            }
        ]
    )
    return response.choices[0].message.content.strip()


def get_frame():
    """Get frame from either ESP32-CAM or local webcam"""
    global esp_stream, bytes_buffer

    if use_esp_cam:
        if esp_stream is None:
            esp_stream, bytes_buffer = connect_to_stream()

        ret, frame = read_from_esp_cam(esp_stream, bytes_buffer)

        # If ESP32-CAM fails, try to reconnect once
        if not ret:
            speak("Attempting to reconnect to ESP32-CAM...")
            esp_stream, bytes_buffer = connect_to_stream()
            ret, frame = read_from_esp_cam(esp_stream, bytes_buffer)

            # If still fails, fall back to local webcam
            if not ret:
                speak("Falling back to local webcam")
                if cap.isOpened():
                    ret, frame = cap.read()
                else:
                    ret = False
    else:
        # Use local webcam
        ret, frame = cap.read()

    return ret, frame


def navigation_mode():
    global running, esp_stream, last_obstacle_time
    speak("Navigation Mode activated. Processing video to detect obstacles.")

    obstacle_cooldown = 3  # seconds between obstacle announcements

    while running and mode == 'a':
        ret, frame = get_frame()

        if not ret:
            speak("Could not read from camera.")
            time.sleep(1)
            continue

        depth_map = get_depth_map(frame)

        current_time = time.time()
        if detect_obstacle(depth_map) and (current_time - last_obstacle_time > obstacle_cooldown):
            last_obstacle_time = current_time
            # Play warning sound for immediate alert
            for _ in range(3):  # Beep sound simulation with multiple alerts
                speak("Warning! Obstacle detected!")
                time.sleep(0.5)

            # Get a description of what the obstacle is
            desc = get_description(frame, prompt="What is the obstacle ahead? Answer in a short sentence.")
            short = desc.split('.')[0]
            speak(f"Obstacle appears to be: {short}")

        cv2.imshow("Camera Feed", frame)
        cv2.imshow("Depth Map", depth_map)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            running = False
            break


def interactive_mode():
    global running, esp_stream
    speak("Interactive Mode activated. You can ask questions about what the camera sees.")

    while running and mode == 'b':
        ret, frame = get_frame()

        if not ret:
            speak("Could not read from camera.")
            time.sleep(1)
            continue

        cv2.imshow("Camera Feed", frame)
        cv2.waitKey(1)  # Show frame but don't block

        speak("What would you like to know about what I can see?")
        question = input("\n🔎 Enter your question (or 'exit' to stop interactive mode): ")

        if question.lower() == 'exit':
            speak("Exiting interactive mode.")
            break

        speak(f"Analyzing the image to answer: {question}")
        desc = get_description(frame, prompt=question)
        speak(f"Answer: {desc}")


def continuous_description_mode():
    global running
    speak("Continuous description mode activated. I will describe what I see every few seconds.")

    description_interval = 10  # seconds between descriptions
    last_description_time = 0

    while running and mode == 'c':
        ret, frame = get_frame()

        if not ret:
            speak("Could not read from camera.")
            time.sleep(1)
            continue

        cv2.imshow("Camera Feed", frame)

        current_time = time.time()
        if current_time - last_description_time > description_interval:
            last_description_time = current_time
            speak("Analyzing the current scene...")
            desc = get_description(frame, prompt="Describe what's in this scene briefly but informatively.")
            speak(f"I can see: {desc}")

        if cv2.waitKey(1) & 0xFF == ord('q'):
            running = False
            break


def test_voice():
    """Test speech functionality"""
    speak("Testing speech output. If you can hear this message, speech is working correctly.")
    time.sleep(2)
    speak("Speech test complete.")


def mode_listener():
    global mode, running, use_esp_cam

    # Test speech first
    speak("Welcome Atharva Sir, How are you?")
    speak("Vision Assistant with ESP32-CAM and speech output ready.")
    speak("Available commands:")
    speak("Press A for Navigation Mode, B for Interactive Mode, Q to Quit")

    while running:
        key = input("\n👉 Choose Mode [A/B/C/E/T/Q]: ").lower()

        if key == 'a':
            mode = 'a'
            speak("Starting Navigation Mode.")
            navigation_mode()
        elif key == 'b':
            mode = 'b'
            speak("Starting Interactive Mode.")
            interactive_mode()
        elif key == 'c':
            mode = 'c'
            speak("Starting Continuous Description Mode.")
            continuous_description_mode()
        elif key == 'e':
            use_esp_cam = not use_esp_cam
            camera_type = "ESP32-CAM" if use_esp_cam else "local webcam"
            speak(f"Switched to {camera_type}")
        elif key == 't':
            speak("Running voice test.")
            test_voice()
        elif key == 'q':
            speak("Shutting down Vision Assistant. Goodbye!")
            running = False
            break
        else:
            speak("Invalid input. Please use A, B, C, E, T, or Q.")


# Start the listener
try:
    print("\n===== VISION ASSISTANT WITH SPEECH OUTPUT =====")
    print(f"Running on {system_platform} with native speech commands")
    print("================================================\n")

    if use_esp_cam:
        speak(f"Attempting to connect to ESP32-CAM at {ESP_CAM_IP}...")
        esp_stream, bytes_buffer = connect_to_stream()
        if esp_stream:
            speak("Successfully connected to ESP32-CAM!")
        else:
            speak("Could not connect to ESP32-CAM. Will use local webcam instead.")
            use_esp_cam = False

    mode_listener()

finally:
    # Clean up resources
    if cap.isOpened():
        cap.release()
    if esp_stream:
        esp_stream.close()
    cv2.destroyAllWindows()

    # Stop the speech thread
    speech_queue.put(None)
    speech_thread.join(timeout=1)
