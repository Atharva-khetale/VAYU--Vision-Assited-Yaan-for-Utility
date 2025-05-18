# 🤖 VAYU – The Interactive Robotic Guide

VAYU is not just a robot — it's an intelligent, voice-enabled tour companion designed to revolutionize the way visitors explore museums, zoos, and theme parks. Powered by real-time interaction, VAYU leads visitors to points of interest, narrates engaging facts, answers questions, and adds a dash of personality with jokes, suggestions, and stories.

## 🌟 Key Features

- 🎙️ **Voice Interface** – Ask questions, get guided explanations in real-time.
- 🗺️ **Autonomous Navigation** – VAYU leads visitors along predefined or dynamic routes.
- 📚 **Exhibit Information Delivery** – Real-time narration of exhibits, facts, and trivia.
- 🧠 **AI-Powered Q&A** – Responds intelligently to visitor queries.
- 🌍 **Multilingual Support** – Offers interaction in multiple languages.
- 🧒 **Interactive Mode for Kids** – Includes riddles, fun facts, and friendly banter.
- 🤪 **Entertainment Mode** – Tells jokes, gives advice, and shares random thoughts to keep visitors engaged.

## 🧩 Tech Stack

| Component         | Description                                           |
|------------------|-------------------------------------------------------|
| **ESP32/ESP-CAM**| For camera vision and lightweight control             |
| **Bluetooth / Wi-Fi Module** | For connectivity with user devices         |
| **Speech Recognition Module** | Voice command input                      |
| **Text-to-Speech (TTS)** | For VAYU's responses                          |
| **OpenCV**        | For face recognition, object detection                |
| **Servo & DC Motors** | For movement and directional control             |
| Arduino UNO      | For controlling motors and SERVO
| **Custom Framework (Python/C++)** | Core logic and interaction flow        |

## 🔧 Modules

- **Navigation Module** – Uses sensors and map data to guide users.
- **Voice Interaction Module** – Converts speech to text and responds intelligently.
- **Knowledge Engine** – Contains data about exhibits or attractions.
- **Entertainment Module** – Fun features like jokes, proverbs, and interactive games.
- **Emotion Detection** *(Optional)* – Detects visitor expressions and adapts responses.

## 🛠️ Installation

> ⚠️ This project uses hardware components. Simulation may be limited in environments like Wokwi.

### Requirements
- ESP32 or compatible microcontroller
- TFT LCD display module
- Servo motors
- DHT sensor (optional for ambient data)
- Wi-Fi connection or Bluetooth setup
- Python 3.x (for AI backend, if connected)
- OpenCV, SpeechRecognition, pyttsx3 (on server side)

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/Atharva-khetale/VAYU--Vision-Assited-Yaan-for-Utility.git
   cd VAYU--Vision-Assited-Yaan-for-Utility
