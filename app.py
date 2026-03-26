import streamlit as st
import cv2
import time
import numpy as np
from gtts import gTTS
import os
import pygame

# Streamlit Page Config MUST be the first command
st.set_page_config(page_title="EyeSpeak - Morse Eye Communication", layout="wide")

from login_page import login_page
from eye_blink_detector import EyeBlinkDetector
from morse_translator import get_char_from_sequence, MORSE_CODE_DICT

# Predefined suggestions for common phrases
SUGGESTIONS = [
    # Greetings & Social
    "Hello", "Hi", "Good morning", "Good afternoon", "Good evening", "How are you?", "I am fine", "Nice to meet you", 
    "Goodbye", "See you later", "Thank you very much", "You are welcome", "Please", "Excuse me", "Sorry",
    "What is your name?", "My name is...", "Have a nice day", "I love you", "Happy birthday",
    
    # Needs & Requests
    "I want to eat", "I want to drink water", "I want to drink tea", "I want to drink coffee", "I want to drink juice",
    "I want to sleep", "I want to go to the bathroom", "I want to go to the toilet", "I want to go out", 
    "I want to stay here", "I want to see my family", "I want to see a doctor", "I want to read a book", 
    "I want to listen to music", "I want to watch TV", "I want to use the computer", "I want to talk to you",
    "I want to sit down", "I want to lie down", "I want to stand up", "I want to walk",
    
    # Emergency & Health
    "I need help", "Please help me", "I need medicine", "I am in pain", "I feel sick", "I feel cold", "I feel hot", 
    "I cannot breathe well", "Call an ambulance", "Call my family", "I have a headache", "I feel dizzy",
    "I need my inhaler", "I need my insulin", "I am bleeding", "It hurts here",
    
    # Feelings & Status
    "I am tired", "I am hungry", "I am thirsty", "I am happy", "I am sad", "I am bored", "I am finished", 
    "I am ready", "I am not ready", "Yes", "No", "Maybe", "I don't know", "I understand", "I don't understand",
    "I am angry", "I am scared", "I am surprised", "I am confused", "I am comfortable", "I am uncomfortable",
    
    # Questions
    "What time is it?", "What is happening?", "Who is there?", "Where are we?", "Why?", "How?", "Can you help me?",
    "Can I have some water?", "Can I eat now?", "Is it morning?", "Is it night?", "Who are you?",
    
    # Actions & Environment
    "Please open the window", "Please close the window", "Please turn off the lights", "Please turn on the lights", 
    "Please open the door", "Please close the door", "Please adjust my pillow", "Please move me", 
    "Please give me my glasses", "Please give me the phone", "Please turn up the volume", "Please turn down the volume",
    "Please scratch my back", "Please clean my face", "Please brush my hair", "Please change the channel",
    
    # Short Responses
    "Ok", "Alright", "Wait", "Later", "Now", "Never", "Always", "Sometimes", "More", "Less", "Too much", "Enough"
]

CONTROL_COMMANDS = {
    "...---...": "TOGGLE_CAMERA",   # SOS
    ".-.-.": "READ_TEXT",          # AR
    "-.-.-": "CLEAR_TEXT",         # Custom
    "----": "RESET_ALL"            # Custom
}


def get_suggestions(text):
    if not text:
        return []
    text = text.lower()
    return [s for s in SUGGESTIONS if s.lower().startswith(text) and s.lower() != text]

# Session State Initialization
if 'translated_text' not in st.session_state:
    st.session_state.translated_text = ""
if 'current_morse' not in st.session_state:
    st.session_state.current_morse = ""
if 'last_blink_time' not in st.session_state:
    st.session_state.last_blink_time = time.time()
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
    st.session_state.auto_start_time = time.time()
if 'last_suggestions' not in st.session_state:
    st.session_state.last_suggestions = []

# If the user is not logged in -> show login system
if "user" not in st.session_state:
    login_page()
    st.stop()

# ⏳ Auto-start camera after short delay (only on main page)
if not st.session_state.is_running:
    elapsed = time.time() - st.session_state.auto_start_time
    if elapsed > 1.5:
        st.session_state.is_running = True
        st.toast("Camera started automatically 🎥")
        st.rerun()
    else:
        st.info(f"System ready. Starting camera in {max(0, 1.5 - elapsed):.1f}s...")
        time.sleep(max(0, 1.5 - elapsed))
        st.session_state.is_running = True
        st.toast("Camera started automatically 🎥")
        st.rerun()

# Initialize pygame for audio
if not pygame.mixer.get_init():
    pygame.mixer.init()

# Custom CSS for styling
st.markdown("""
<style>
    .main {
        background-color: #f0f2f6;
    }
    .stButton>button {
        width: 100%;
    }
    .morse-code {
        font-family: monospace;
        font-size: 24px;
        font-weight: bold;
        color: #1e88e5;
    }
    .translated-text {
        font-size: 32px;
        color: #2e7d32;
        border: 2px solid #2e7d32;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .suggestion-pill {
        background-color: #2e3b4e;
        color: #ffffff;
        padding: 10px 15px;
        border-radius: 20px;
        margin: 5px;
        display: inline-block;
        border: 1px solid #4a90e2;
        font-size: 0.9em;
    }
    .suggestion-morse {
        color: #f1c40f;
        font-weight: bold;
        margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar: Settings and Info
with st.sidebar:
    st.title(" Morse Code Guide")
    st.info("Blink dots (.) and dashes (-) to type.")

    blink_thresh = 0.15
    min_blink = 0.20
    short_blink = 0.4
    long_blink = 1.2
    char_pause = 2.0
    word_pause = 5.0

    st.divider()

    st.subheader("🎮 Blink Controls")
    st.markdown("""
    - **Start/Stop Camera** → `...---...` (SOS)  
    - **Read Text 🔊** → `.-.-.`  
    - **Clear Text 🧹** → `-.-.-`  
    - **Reset All 🔄** → `----`  
    """)

    st.divider()
    # Display full Morse code dictionary in a cleaner way
    cols = st.columns(2)
    items = list(MORSE_CODE_DICT.items())
    half = len(items) // 2
    
    with cols[0]:
        for char, code in items[:half]:
            if char != ' ':
                st.write(f"**{char}**: `{code}`")
                
    with cols[1]:
        for char, code in items[half:]:
            if char != ' ':
                st.write(f"**{char}**: `{code}`")

# Main App Layout
st.title("EyeSpeak – Communication Assistance")
st.write(f"Welcome back, **{st.session_state.user}**!")
st.write("Communicate by blinking: short for '.', long for '-'.")

col1, col2 = st.columns([2, 1])

with col1:
    st.header(" Video Stream")
    run_btn = st.button("Start / Stop Camera", key="run_comm")
    if run_btn:
        st.session_state.is_running = not st.session_state.is_running
    
    video_placeholder = st.empty()
    
with col2:
    st.header(" Communication")
    st.subheader("Morse Code in progress:")
    morse_display = st.empty()
    
    st.subheader("Translated Text:")
    text_display = st.empty()
    
    # Suggestions Area
    st.subheader("Suggestions:")
    suggestions_container = st.empty()
    
    if st.button(" Read Text (TTS)"):
        if st.session_state.translated_text:
            try:
                tts = gTTS(text=st.session_state.translated_text, lang='en')
                tts.save("temp_voice.mp3")
                st.audio("temp_voice.mp3", autoplay=True)
            except Exception as e:
                st.error(f"TTS Error: {e}")
                
    if st.button(" Clear"):
        st.session_state.translated_text = ""
        st.session_state.current_morse = ""


# Main processing loop
if st.session_state.is_running:
    cap = cv2.VideoCapture(0)
    detector = EyeBlinkDetector(
        blink_threshold=blink_thresh, 
        short_blink_limit=short_blink, 
        long_blink_limit=long_blink,
        min_blink_duration=min_blink
    )
    
    while st.session_state.is_running:
        ret, frame = cap.read()
        if not ret:
            st.error("Impossible d'accéder à la caméra.")
            break
            
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        blink_event, ear, frame, landmarks = detector.process_frame(frame)
        
        # Draw landmarks for debugging
        if landmarks:
            # Draw all eye landmarks
            for idx in [detector.LEFT_UPPER, detector.LEFT_LOWER, detector.RIGHT_UPPER, detector.RIGHT_LOWER]:
                lm = landmarks[idx]
                px, py = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (px, py), 2, (0, 255, 255), -1)
            
            # Draw a circle around the face to show it's detected
            cv2.putText(frame, "VISAGE DETECTE", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "VISAGE NON DETECTE", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Display EAR on frame
        cv2.putText(frame, f"EAR: {ear:.4f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if detector.is_blinking:
            cv2.putText(frame, "CLIGNEMENT!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
        # Update video
        video_placeholder.image(frame, channels="BGR")
        
        # Logic for Morse events
        if blink_event:
            if blink_event == "reset":
                st.session_state.current_morse = ""
                st.session_state.translated_text = ""
            elif blink_event == "clear":
                st.session_state.current_morse = ""
                st.toast("Code Morse effacé !", icon="🧹")
            else:
                st.session_state.current_morse += blink_event
                st.session_state.last_blink_time = time.time()
                
        # Logic for pauses (detect end of character or word)
        current_time = time.time()
        time_since_last = current_time - st.session_state.last_blink_time
        
        if st.session_state.current_morse != "":
            if time_since_last > char_pause:
                sequence = st.session_state.current_morse
                
                # Check for Control Commands first
                if sequence in CONTROL_COMMANDS:
                    command = CONTROL_COMMANDS[sequence]
                    if command == "TOGGLE_CAMERA":
                        st.session_state.is_running = not st.session_state.is_running
                        st.toast("Camera toggled 👁️")
                    elif command == "READ_TEXT":
                        if st.session_state.translated_text:
                            try:
                                tts = gTTS(text=st.session_state.translated_text, lang='en')
                                tts.save("temp_voice.mp3")
                                st.audio("temp_voice.mp3", autoplay=True)
                                st.toast("Reading text 🔊")
                            except Exception as e:
                                st.error(f"TTS Error: {e}")
                    elif command == "CLEAR_TEXT":
                        st.session_state.translated_text = ""
                        st.toast("Text cleared 🧹")
                    elif command == "RESET_ALL":
                        st.session_state.translated_text = ""
                        st.session_state.current_morse = ""
                        st.toast("Reset done 🔄")
                else:
                    # Normal character handling
                    char = get_char_from_sequence(sequence)
                    
                    # Suggestions selection (1-5)
                    suggestions = st.session_state.last_suggestions
                    if char == '1' and len(suggestions) >= 1:
                        st.session_state.translated_text = suggestions[0]
                    elif char == '2' and len(suggestions) >= 2:
                        st.session_state.translated_text = suggestions[1]
                    elif char == '3' and len(suggestions) >= 3:
                        st.session_state.translated_text = suggestions[2]
                    elif char == '4' and len(suggestions) >= 4:
                        st.session_state.translated_text = suggestions[3]
                    elif char == '5' and len(suggestions) >= 5:
                        st.session_state.translated_text = suggestions[4]
                    elif char != "?":
                        st.session_state.translated_text += char
                
                # Reset current morse after processing
                st.session_state.current_morse = ""
                st.session_state.last_blink_time = current_time
        
        elif st.session_state.translated_text != "" and not st.session_state.translated_text.endswith(" "):
            if time_since_last > word_pause:
                # Fin d'un mot (espace automatique)
                st.session_state.translated_text += " "
                st.session_state.last_blink_time = current_time
        
        # Update displays
        morse_display.markdown(f'<div class="morse-code">{st.session_state.current_morse}</div>', unsafe_allow_html=True)
        text_display.markdown(f'<div class="translated-text">{st.session_state.translated_text}</div>', unsafe_allow_html=True)
        
        # Update suggestions
        new_suggestions = get_suggestions(st.session_state.translated_text)
        if new_suggestions:
            st.session_state.last_suggestions = new_suggestions[:5]
            
        if st.session_state.last_suggestions:
            sug_html = ""
            for i, s in enumerate(st.session_state.last_suggestions):
                morse_hint = MORSE_CODE_DICT.get(str(i+1), "")
                sug_html += f'<div class="suggestion-pill"><span class="suggestion-morse">{morse_hint}</span>{s}</div>'
            suggestions_container.markdown(sug_html, unsafe_allow_html=True)
        else:
            suggestions_container.empty()
        
        # Small delay for responsiveness
        time.sleep(0.01)
        
    cap.release()
else:
    st.info("Appuyez sur 'Démarrer la Caméra' pour commencer.")
