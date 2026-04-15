import streamlit as st
import cv2
import time
import numpy as np
from gtts import gTTS
import os
import pygame
from helper_page import helper_page, load_helpers, load_messages, save_messages
from notification_utils import send_email_notification, send_sms_notification, send_whatsapp_notification

# Streamlit Page Config MUST be the first command
st.set_page_config(page_title="EyeSpeak - Morse Eye Communication", layout="wide")

from login_page import login_page
from eye_blink_detector import EyeBlinkDetector
from morse_translator import get_char_from_sequence, MORSE_CODE_DICT

# Predefined suggestions for common phrases
SUGGESTIONS = [
    "Hello", "Hi", "Good morning", "Good afternoon", "Good evening", "How are you?", "I am fine", "Nice to meet you", 
    "Goodbye", "See you later", "Thank you very much", "You are welcome", "Please", "Excuse me", "Sorry",
    "I want to eat", "I want to drink water", "I want to sleep", "I want to go to the bathroom",
    "I need help", "Please help me", "I need medicine", "I am in pain", "I feel sick",
    "I am tired", "I am hungry", "I am thirsty", "Yes", "No", "Maybe", "Ok", "Wait"
]

CONTROL_COMMANDS = {
    "...---...": "TOGGLE_CAMERA",   # SOS
    ".-.-.": "READ_TEXT",          # AR
    "-.-.-": "CLEAR_TEXT",         # Custom
    "----": "RESET_ALL",           # Custom
    ".--.": "SEND_TO_HELPER"       # P (for Push/Post)
}

def get_suggestions(text):
    if not text:
        return []
    text = text.lower()
    return [s for s in SUGGESTIONS if s.lower().startswith(text) and s.lower() != text]

# Role Selection
if "role" not in st.session_state:
    st.title("Welcome to EyeSpeak")
    role = st.radio("Select your role:", ["Patient", "Helper"])
    if st.button("Continue"):
        st.session_state.role = role
        st.rerun()
    st.stop()

# Helper Logic
if st.session_state.role == "Helper":
    helper_page()
    st.stop()

# Patient Login
if "user" not in st.session_state:
    login_page()
    st.stop()

# Patient Main Page Logic
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

# Auto-start camera after 1.5s
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

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; }
    .morse-code { font-family: monospace; font-size: 24px; font-weight: bold; color: #1e88e5; }
    .translated-text { font-size: 32px; color: #2e7d32; border: 2px solid #2e7d32; padding: 10px; border-radius: 5px; margin-top: 10px; }
    .suggestion-pill { background-color: #2e3b4e; color: #ffffff; padding: 10px 15px; border-radius: 20px; margin: 5px; display: inline-block; border: 1px solid #4a90e2; font-size: 0.9em; }
    .suggestion-morse { color: #f1c40f; font-weight: bold; margin-right: 8px; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title(" Morse Code Guide")
    st.write(f"Patient ID: **{st.session_state.user}**")
    
    # 🔗 Link check
    helpers = load_helpers()
    my_helper = None
    for h_email, h_data in helpers.items():
        if h_data["patient"].strip().lower() == st.session_state.user.strip().lower():
            my_helper = h_data
            break
    
    if my_helper:
        st.success(f"🔗 Linked to: **{my_helper['name']}**")
    else:
        st.warning("⚠️ No helper linked yet.\n\nAsk your helper to register with your Patient ID.")

    st.info("Blink dots (.) and dashes (-) to type.")
    
    st.subheader("🎮 Blink Controls")
    st.markdown("- **Start/Stop Camera** → `...---...` (SOS)\n- **Read Text 🔊** → `.-.-.`\n- **Clear Text 🧹** → `-.-.-`\n- **Send to Helper 📩** → `.--.` (P)\n- **Reset All 🔄** → `----`")
    
    st.divider()
    st.subheader("📖 Morse Dictionary")
    
    # Display full Morse code dictionary in a cleaner way
    items = list(MORSE_CODE_DICT.items())
    # Sort items: letters first, then numbers
    letters = [i for i in items if i[0].isalpha() and len(i[0]) == 1]
    numbers = [i for i in items if i[0].isdigit()]
    
    cols = st.columns(2)
    with cols[0]:
        for char, code in letters[:len(letters)//2]:
            st.write(f"**{char}**: `{code}`")
    with cols[1]:
        for char, code in letters[len(letters)//2:]:
            st.write(f"**{char}**: `{code}`")
            
    st.write("---")
    cols_num = st.columns(2)
    with cols_num[0]:
        for char, code in numbers[:5]:
            st.write(f"**{char}**: `{code}`")
    with cols_num[1]:
        for char, code in numbers[5:]:
            st.write(f"**{char}**: `{code}`")

    st.divider()
    
    if st.button("Logout"):
        del st.session_state.user
        del st.session_state.role
        st.rerun()

st.title("EyeSpeak – Communication Assistance")
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
    st.subheader("Suggestions:")
    suggestions_container = st.empty()
    
    if st.button(" Read Text (TTS)"):
        if st.session_state.translated_text:
            tts = gTTS(text=st.session_state.translated_text, lang='en')
            tts.save("temp_voice.mp3")
            st.audio("temp_voice.mp3", autoplay=True)

    if st.button(" Clear"):
        st.session_state.translated_text = ""
        st.session_state.current_morse = ""

    if st.button("📩 Send to Helper"):
        if st.session_state.translated_text:
            patient_id = st.session_state.user.strip()
            msg_content = st.session_state.translated_text
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            # 1. Save message to DB
            msgs = load_messages()
            msgs.append({
                "patient": patient_id,
                "message": msg_content,
                "time": timestamp
            })
            save_messages(msgs)
            st.success("Message saved! ✅")

            # 2. Find linked helper and send notifications
            helpers_db = load_helpers()
            linked_helper = None
            for h_email, h_data in helpers_db.items():
                if h_data["patient"].strip().lower() == patient_id.lower():
                    linked_helper = h_data
                    break
            
            if linked_helper:
                # 1. Send Email
                success, email_msg = send_email_notification(
                    linked_helper["email"],
                    linked_helper["name"],
                    patient_id,
                    msg_content,
                    timestamp
                )
                if success:
                    st.success(f"Email sent to {linked_helper['name']}! 📧")
                else:
                    st.warning(f"Email notification failed: {email_msg}")
                
                # 2. Send WhatsApp (New Feature)
                if linked_helper.get("phone"):
                    wa_success, wa_msg = send_whatsapp_notification(
                        linked_helper["phone"],
                        linked_helper["name"],
                        patient_id,
                        msg_content,
                        timestamp
                    )
                    if wa_success:
                        st.success("WhatsApp notification sent! 📱")
                    else:
                        st.warning(f"WhatsApp failed: {wa_msg}")
                
                # 3. Send SMS (Optional Legacy)
                if linked_helper.get("phone"):
                    send_sms_notification(
                        linked_helper["phone"],
                        patient_id,
                        msg_content
                    )
            else:
                st.info("No linked helper found to notify.")

# Processing Loop
if st.session_state.is_running:
    cap = cv2.VideoCapture(0)
    detector = EyeBlinkDetector()
    
    while st.session_state.is_running:
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)
        blink_event, ear, frame, landmarks = detector.process_frame(frame)
        
        video_placeholder.image(frame, channels="BGR")
        
        if blink_event:
            if blink_event == "reset":
                st.session_state.current_morse = ""
                st.session_state.translated_text = ""
            elif blink_event == "clear":
                st.session_state.current_morse = ""
                st.toast("Morse cleared! 🧹")
            else:
                st.session_state.current_morse += blink_event
                st.session_state.last_blink_time = time.time()

        now = time.time()
        elapsed = now - st.session_state.last_blink_time
        
        if st.session_state.current_morse != "" and elapsed > 2.0:
            seq = st.session_state.current_morse
            if seq in CONTROL_COMMANDS:
                cmd = CONTROL_COMMANDS[seq]
                if cmd == "TOGGLE_CAMERA": st.session_state.is_running = not st.session_state.is_running
                elif cmd == "READ_TEXT":
                    if st.session_state.translated_text:
                        tts = gTTS(text=st.session_state.translated_text, lang='en')
                        tts.save("temp_voice.mp3")
                        st.audio("temp_voice.mp3", autoplay=True)
                elif cmd == "CLEAR_TEXT": st.session_state.translated_text = ""
                elif cmd == "SEND_TO_HELPER":
                    if st.session_state.translated_text:
                        patient_id = st.session_state.user.strip()
                        msg_content = st.session_state.translated_text
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

                        # 1. Save to DB
                        msgs = load_messages()
                        msgs.append({
                            "patient": patient_id,
                            "message": msg_content,
                            "time": timestamp
                        })
                        save_messages(msgs)
                        st.toast("Message saved! ✅")

                        # 2. Notify Helper
                        helpers_db = load_helpers()
                        linked_helper = None
                        for h_email, h_data in helpers_db.items():
                            if h_data["patient"].strip().lower() == patient_id.lower():
                                linked_helper = h_data
                                break
                        
                        if linked_helper:
                            # 1. Send Email
                            send_email_notification(
                                linked_helper["email"],
                                linked_helper["name"],
                                patient_id,
                                msg_content,
                                timestamp
                            )
                            # 2. Send WhatsApp
                            if linked_helper.get("phone"):
                                send_whatsapp_notification(
                                    linked_helper["phone"],
                                    linked_helper["name"],
                                    patient_id,
                                    msg_content,
                                    timestamp
                                )
                            # 3. Send SMS
                            if linked_helper.get("phone"):
                                send_sms_notification(
                                    linked_helper["phone"],
                                    patient_id,
                                    msg_content
                                )
                            st.toast("Helper notified via WhatsApp & Email! 📩")
                        else:
                            st.toast("No linked helper found.")
                elif cmd == "RESET_ALL":
                    st.session_state.translated_text = ""
                    st.session_state.current_morse = ""
            else:
                char = get_char_from_sequence(seq)
                sugs = st.session_state.last_suggestions
                if char == '1' and len(sugs) >= 1: st.session_state.translated_text = sugs[0]
                elif char == '2' and len(sugs) >= 2: st.session_state.translated_text = sugs[1]
                elif char == '3' and len(sugs) >= 3: st.session_state.translated_text = sugs[2]
                elif char == '4' and len(sugs) >= 4: st.session_state.translated_text = sugs[4]
                elif char == '5' and len(sugs) >= 5: st.session_state.translated_text = sugs[4]
                elif char != "?": st.session_state.translated_text += char
            
            st.session_state.current_morse = ""
            st.session_state.last_blink_time = now

        elif st.session_state.translated_text != "" and not st.session_state.translated_text.endswith(" ") and elapsed > 5.0:
            st.session_state.translated_text += " "
            st.session_state.last_blink_time = now

        morse_display.markdown(f'<div class="morse-code">{st.session_state.current_morse}</div>', unsafe_allow_html=True)
        text_display.markdown(f'<div class="translated-text">{st.session_state.translated_text}</div>', unsafe_allow_html=True)
        
        new_sugs = get_suggestions(st.session_state.translated_text)
        if new_sugs:
            st.session_state.last_suggestions = new_sugs[:5]
            sug_html = ""
            for i, s in enumerate(st.session_state.last_suggestions):
                hint = MORSE_CODE_DICT.get(str(i+1), "")
                sug_html += f'<div class="suggestion-pill"><span class="suggestion-morse">{hint}</span>{s}</div>'
            suggestions_container.markdown(sug_html, unsafe_allow_html=True)
        
        time.sleep(0.01)
    cap.release()
else:
    st.info("Start the camera to begin.")
