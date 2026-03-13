# EyeSpeak – Web Application for Communication Assistance

EyeSpeak is an accessibility solution that allows people with speech impairments or paralysis to communicate using eye blinking and Morse code.

## Features

- **Real-time Detection**: Uses MediaPipe and OpenCV to detect blinks.
- **Morse Translation**:
  - Short blink (< 0.4s) = Dot (.)
  - Long blink (> 0.4s) = Dash (-)
- **Text-to-Speech (TTS)**: Converts translated text to voice in English.
- **Learning Module**: Allows users to practice blinking for specific letters.
- **Personalization**: Adjust sensitivity and durations via the sidebar.

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Launch the application:
   ```bash
   streamlit run app.py --server.headless true --browser.gatherUsageStats false
   ```

## Usage

1. Allow access to your webcam.
2. Adjust the "Sensitivity" slider if necessary (observe the EAR value in the video stream).
3. Blink to compose your message.
4. Wait for the configured pause for the character to be validated.
5. Use the "Read Text" button to hear the message.
