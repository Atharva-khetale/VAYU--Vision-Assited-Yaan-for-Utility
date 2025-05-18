import cv2
import numpy as np
import base64
import threading
from io import BytesIO
from PIL import Image
from together import Together

# Initialize Together API
client = Together(api_key="tgp_v1_Dscj56nKLZN1nqvz6ynSy71CfFXw2IW-LYXI8Z85-nQ")

# Capture from webcam
cap = cv2.VideoCapture(0)

mode = None  # "a" or "b"
running = True

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
    response = client.chat.completions.create(
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
    return response.choices[0].message.content.strip()

def navigation_mode():
    global running
    while running and mode == 'a':
        ret, frame = cap.read()
        if not ret:
            print("❌ Could not read from camera.")
            break
        depth_map = get_depth_map(frame)
        if detect_obstacle(depth_map):
            desc = get_description(frame, prompt="What is the obstacle?")
            short = desc.split('.')[0]
            print(f"⚠ Stop! Obstacle ahead: {short}")
        cv2.imshow("Webcam Feed", frame)
        cv2.imshow("Depth Map", depth_map)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            running = False
            break

def interactive_mode():
    global running
    while running and mode == 'b':
        ret, frame = cap.read()
        if not ret:
            print("❌ Could not read from camera.")
            break
        question = input("\n🔎 Enter your question (or 'exit' to stop interactive mode): ")
        if question.lower() == 'exit':
            break
        desc = get_description(frame, prompt=question)
        print(f"📝 Answer: {desc}")

def mode_listener():
    global mode, running
    print("🎮 Press A for Navigation Mode, B for Interactive Mode, Q to Quit")
    while running:
        key = input("👉 Choose Mode [A/B/Q]: ").lower()
        if key == 'a':
            mode = 'a'
            print("🚶 Entered Navigation Mode.")
            navigation_mode()
        elif key == 'b':
            mode = 'b'
            print("🧠 Entered Interactive Mode.")
            interactive_mode()
        elif key == 'q':
            print("👋 Quitting...")
            running = False
            break
        else:
            print("❗ Invalid input. Use A, B, or Q.")

# Start the listener
try:
    mode_listener()
finally:
    cap.release()
    cv2.destroyAllWindows()