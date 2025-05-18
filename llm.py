import cv2
import numpy as np
import base64
import threading
import asyncio
import speech_recognition as sr
import pyttsx3
import requests
import time
from io import BytesIO
from PIL import Image
from together import Together

# Initialize Together API
client = Together(api_key="tgp_v1_Dscj56nKLZN1nqvz6ynSy71CfFXw2IW-LYXI8Z85-nQ")

# ESP32-CAM IP address
ESP_CAM_URL = "http://192.168.239.173/capture"

# Initialize text-to-speech engine
engine = pyttsx3.init()

# Initialize speech recognizer
recognizer = sr.Recognizer()

# Debug flag
DEBUG = True
mode = None  # "a" or "b"
running = True


def debug_print(message):
    """Print debug messages if DEBUG is True"""
    if DEBUG:
        print(f"[DEBUG] {message}")


def speak_text_sync(text):
    """Synchronous version of speak_text for simple operations"""
    debug_print(f"Speaking (sync): {text}")
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        debug_print(f"Error in speak_text_sync: {e}")


async def speak_text(text, max_retries=1):
    """Convert text to speech asynchronously with retry mechanism"""
    debug_print(f"Speaking: {text}")

    for attempt in range(max_retries + 1):
        def _speak():
            try:
                engine.say(text)
                engine.runAndWait()
                return True
            except Exception as e:
                debug_print(f"Error in _speak: {e}")
                return False

        try:
            # Run in a separate thread with a timeout
            success = await asyncio.wait_for(asyncio.to_thread(_speak), timeout=5.0)
            if success:
                return  # Successfully spoke the text
        except asyncio.TimeoutError:
            debug_print("Text-to-speech timed out")
            print(f"⚠️ Text-to-speech timed out (attempt {attempt + 1}/{max_retries + 1})")
            # Force the TTS engine to reset
            try:
                engine.stop()
            except:
                pass

            # Only try to reinitialize on non-final attempts
            if attempt < max_retries:
                global engine
                try:
                    engine = pyttsx3.init()
                except:
                    debug_print("Failed to reinitialize speech engine")
        except Exception as e:
            debug_print(f"Error in speak_text: {e}")
            print(f"⚠️ Speech error: {e}")

    # If we got here, all attempts failed
    raise Exception("Text-to-speech failed after all attempts")


async def listen_for_speech(timeout=5):
    """Listen for speech input with improved timeout handling"""
    debug_print("Listening for speech...")
    print("🎤 Listening...")

    def _listen():
        try:
            with sr.Microphone() as source:
                debug_print("Adjusting for ambient noise...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)  # Reduced to make it more responsive
                debug_print("Listening for audio...")
                print("👂 Listening...", end="", flush=True)

                # Use a longer phrase_time_limit to catch longer sentences
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                print(" Done!")
                debug_print("Audio captured, recognizing...")
                return recognizer.recognize_google(audio)
        except sr.WaitTimeoutError:
            debug_print("Listen timeout - no speech detected")
            return "timeout"
        except sr.UnknownValueError:
            debug_print("Could not understand audio")
            return "unknown"
        except sr.RequestError as e:
            debug_print(f"Speech service error: {e}")
            return "error"
        except Exception as e:
            debug_print(f"Unexpected error in speech recognition: {e}")
            return "error"

    try:
        # Run with a timeout
        result = await asyncio.wait_for(asyncio.to_thread(_listen), timeout=timeout + 5)
        debug_print(f"Recognition result: '{result}'")
        return result
    except asyncio.TimeoutError:
        debug_print("Speech recognition timed out")
        print("⏱️ Speech recognition timed out")
        return "timeout"
    except Exception as e:
        debug_print(f"Error in listen_for_speech: {e}")
        return "error"


async def get_esp_cam_frame():
    """Get a frame from the ESP32-CAM"""
    debug_print("Attempting to get frame from ESP32-CAM...")
    try:
        # Use a synchronous request with a timeout
        def _get_frame():
            return requests.get(ESP_CAM_URL, timeout=5)

        response = await asyncio.to_thread(_get_frame)

        if response.status_code == 200:
            img_array = np.array(bytearray(response.content), dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            debug_print("Successfully got frame from ESP32-CAM")
            return frame
        else:
            debug_print(f"Failed to get image, status code: {response.status_code}")
            return None
    except Exception as e:
        debug_print(f"Error getting frame from ESP32-CAM: {e}")
        return None


async def get_webcam_frame():
    """Get a frame from the default webcam"""
    debug_print("Attempting to get frame from webcam...")
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                debug_print("Successfully got frame from webcam")
                return frame
        debug_print("Failed to get frame from webcam")
        return None
    except Exception as e:
        debug_print(f"Error getting frame from webcam: {e}")
        return None


# Default to ESP32-CAM
get_frame = get_esp_cam_frame


def encode_frame_to_base64(frame):
    debug_print("Encoding frame to base64")
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img)
    buffered = BytesIO()
    pil_img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{img_str}"


def get_depth_map(frame):
    debug_print("Computing depth map")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    depth_map = np.clip(gray * 1.5, 0, 255).astype(np.uint8)
    return depth_map


def detect_obstacle(depth_map):
    threshold = 120
    mask = cv2.inRange(depth_map, 0, threshold)
    result = np.sum(mask) > 5000
    debug_print(f"Obstacle detection result: {result}")
    return result


async def get_description(frame, prompt="Describe the scene"):
    debug_print(f"Getting AI description with prompt: '{prompt}'")
    img_b64 = encode_frame_to_base64(frame)

    async def _get_response():
        try:
            return client.chat.completions.create(
                model="meta-llama/Llama-Vision-Free",
                messages=[
                    {
                        "role": "system",
                        "content": "You are assisting a visually impaired individual. Provide clear and helpful answers."
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
        except Exception as e:
            debug_print(f"Error in API call: {e}")
            return None

    try:
        response = await asyncio.wait_for(asyncio.to_thread(_get_response), timeout=30.0)
        if response:
            result = response.choices[0].message.content.strip()
            debug_print(f"Got description: '{result[:50]}...'")
            return result
        else:
            return "I couldn't analyze the image. Please try again."
    except asyncio.TimeoutError:
        debug_print("AI description timed out")
        return "The image analysis timed out. Please try again."
    except Exception as e:
        debug_print(f"Error in get_description: {e}")
        return "Error analyzing the image. Please try again."


async def navigation_mode():
    global running, mode
    debug_print("Starting navigation mode")
    while running and mode == 'a':
        frame = await get_frame()
        if frame is None:
            message = "Cannot connect to camera. Please check the connection."
            print("❌ " + message)
            await speak_text(message)
            await asyncio.sleep(5)
            continue

        depth_map = get_depth_map(frame)
        if detect_obstacle(depth_map):
            desc = await get_description(frame, prompt="What is the obstacle?")
            short = desc.split('.')[0]
            message = f"⚠ Stop! Obstacle ahead: {short}"
            print(message)
            await speak_text(message)

        cv2.imshow("Camera Feed", frame)
        cv2.imshow("Depth Map", depth_map)

        # Non-blocking key check
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            debug_print("Quit key pressed in navigation mode")
            running = False
            break
        elif key == ord('b'):
            debug_print("Switching to interactive mode")
            mode = 'b'
            break

        await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging


async def interactive_mode():
    global running, mode
    debug_print("Starting interactive mode")
    while running and mode == 'b':
        frame = await get_frame()
        if frame is None:
            message = "Cannot connect to camera. Please check the connection."
            print("❌ " + message)
            await speak_text(message)
            await asyncio.sleep(5)
            continue

        cv2.imshow("Camera Feed", frame)
        cv2.waitKey(1)  # Update the image window

        # Ask the user what they want to know
        print("🎤 Waiting for your question...")
        try:
            await speak_text("What would you like to know about what I see?")
        except:
            print("⚠️ Text-to-speech failed. Please type your question.")

        # Give user more time to respond and handle timeouts better
        question = await listen_for_speech(timeout=15)  # Increased timeout

        if question in ["timeout", "unknown", "error"]:
            print("🔊 No speech detected or unclear audio")
            try:
                await speak_text("I didn't hear anything. Please try again or press A to switch to navigation mode.")
            except:
                print("I didn't hear anything. Please try again or press A to switch to navigation mode.")

            # Check for keyboard input after timeout
            for _ in range(30):  # Give 3 seconds to press a key
                key = cv2.waitKey(100) & 0xFF
                if key == ord('a'):
                    print("Switching to navigation mode")
                    mode = 'a'
                    return
                elif key == ord('q'):
                    running = False
                    return

            continue

        print(f"🔎 You asked: {question}")

        if question.lower() in ["exit", "stop", "quit"]:
            print("Exiting interactive mode")
            try:
                await speak_text("Exiting interactive mode")
            except:
                pass
            break
        elif "navigate" in question.lower():
            print("Switching to navigation mode")
            try:
                await speak_text("Switching to navigation mode")
            except:
                pass
            mode = 'a'
            break

        desc = await get_description(frame, prompt=question)
        print(f"📝 Answer: {desc}")
        try:
            await speak_text(desc)
        except:
            print("⚠️ Text-to-speech failed. See the text answer above.")

        await asyncio.sleep(0.5)  # Small delay between interactions


async def run_system():
    """Main system loop that handles mode switching"""
    global mode, running

    # Create windows for keyboard input
    cv2.namedWindow("Camera Feed", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Controls", 300, 100)
    control_img = np.zeros((100, 300, 3), dtype=np.uint8)
    cv2.putText(control_img, "Press A, B, or Q", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imshow("Controls", control_img)

    print("\n==== SYSTEM STARTED ====")
    print("A: Navigation Mode  |  B: Interactive Mode  |  Q: Quit")

    # Start with no mode selected, waiting for user input
    mode = None

    try:
        await speak_text("System ready. Press A for navigation mode, B for interactive mode, or Q to quit.")
    except:
        print("Text-to-speech timed out. Continuing...")

    # Wait for mode selection before proceeding
    while running and mode is None:
        key = cv2.waitKey(100) & 0xFF
        if key == ord('a'):
            mode = 'a'
            print("\nSelected: Navigation Mode")
            try:
                await speak_text("Entering navigation mode")
            except:
                print("Text-to-speech timed out")
        elif key == ord('b'):
            mode = 'b'
            print("\nSelected: Interactive Mode")
            try:
                await speak_text("Entering interactive mode")
            except:
                print("Text-to-speech timed out")
        elif key == ord('q'):
            running = False
            print("\nQuitting system...")
            try:
                await speak_text("Shutting down")
            except:
                print("Text-to-speech timed out")
            break

        # Print a waiting message periodically (every 2 seconds)
        if mode is None and int(time.time()) % 2 == 0:
            print("Waiting for mode selection (A, B, or Q)...", end="\r")

        await asyncio.sleep(0.1)  # Prevent CPU hogging

    # Now run the selected mode
    while running:
        if mode == 'a':
            print("\n🚶 NAVIGATION MODE 🚶")
            await navigation_mode()
        elif mode == 'b':
            print("\n🧠 INTERACTIVE MODE 🧠")
            await interactive_mode()
        else:
            # Check for key presses to set mode
            key = cv2.waitKey(100) & 0xFF
            if key == ord('a'):
                mode = 'a'
                try:
                    await speak_text("Entering navigation mode")
                except:
                    print("Text-to-speech timed out")
            elif key == ord('b'):
                mode = 'b'
                try:
                    await speak_text("Entering interactive mode")
                except:
                    print("Text-to-speech timed out")
            elif key == ord('q'):
                running = False
                try:
                    await speak_text("Shutting down")
                except:
                    print("Text-to-speech timed out")
                break

        # Always check for keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            running = False
            break

        await asyncio.sleep(0.1)  # Prevent CPU hogging


# Main async function with improved error handling
async def main():
    global get_frame, mode  # Correctly declare globals before use

    try:
        # Create a dummy window during initialization
        cv2.namedWindow("Initializing...", cv2.WINDOW_NORMAL)
        init_img = np.zeros((200, 400, 3), dtype=np.uint8)
        cv2.putText(init_img, "System Initializing...", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.imshow("Initializing...", init_img)
        cv2.waitKey(1)  # Update the display

        # Test connection to ESP32-CAM
        print("Testing connection to ESP32-CAM...")
        test_frame = await get_esp_cam_frame()
        if test_frame is None:
            print("⚠️ Cannot connect to ESP32-CAM. Please check the IP address and connection.")
            print("IP address: " + ESP_CAM_URL)
            print("Trying alternative...")

            # Try default webcam as fallback
            print("Attempting to use default webcam instead...")
            try:
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        print("✅ Connected to default webcam successfully!")
                        print("Continuing with default webcam since ESP32-CAM is not available.")
                        # Use webcam function instead
                        get_frame = get_webcam_frame
                    else:
                        print("❌ Could not access default webcam either.")
                        return
                else:
                    print("❌ Could not open default webcam.")
                    return
            except Exception as e:
                print(f"Error accessing webcam: {e}")
                return
        else:
            print("✅ Connected to ESP32-CAM successfully!")
            # Use ESP32-CAM function
            get_frame = get_esp_cam_frame

        # Test speech recognition
        print("Testing speech recognition...")
        try:
            speak_text_sync("Testing microphone. Please say something.")
        except:
            print("⚠️ Initial speech test failed. Continuing anyway.")

        try:
            test_speech = await listen_for_speech(timeout=5)
            if test_speech in ["timeout", "unknown", "error"]:
                print("⚠️ Speech recognition test failed. Continuing with keyboard controls only.")
            else:
                print(f"✅ Speech recognition test successful. Heard: '{test_speech}'")
        except:
            print("⚠️ Speech recognition test failed. Continuing with keyboard controls only.")

        try:
            speak_text_sync("Camera connected successfully. Starting system.")
        except:
            print("Camera connected successfully. Starting system.")

        cv2.destroyWindow("Initializing...")

        # Start the main system - initially not in any mode, waiting for user selection
        print("\n⭐ Starting main system loop...")
        mode = None  # Start with no mode selected, wait for user input
        await run_system()

    except Exception as e:
        print(f"Unexpected error in main: {e}")
    finally:
        print("\n⏹️ System shutting down...")
        try:
            await speak_text("System shutting down")
        except:
            pass
        cv2.destroyAllWindows()
        print("System shut down")


# Use asyncio to run the main function
if __name__ == "__main__":
    # Modern way to create and run an event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by keyboard")
    except Exception as e:
        print(f"Unexpected error: {e}")