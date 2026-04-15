import streamlit as st
import cv2
import time

from face_auth import register_face, recognize_face
from eye_blink_detector import EyeBlinkDetector
from blink_input import BlinkInput
from morse_translator import MORSE_CODE_DICT

def login_page():
    st.title("EyeSpeak Login")

    # Initialize persistent objects in session state
    if "detector" not in st.session_state:
        st.session_state.detector = EyeBlinkDetector()
    if "blink_input" not in st.session_state:
        st.session_state.blink_input = BlinkInput()
    if "login_mode" not in st.session_state:
        st.session_state.login_mode = "login"

    # Sidebar: Morse Code Guide
    with st.sidebar:
        st.title("📖 Morse Code Guide")
        st.info("Blink dots (.) and dashes (-) to type.")
        
        st.subheader("🎮 Blink Controls")
        st.markdown("""
        - **REGISTER** → `..-` (U)  
        - **CONFIRM** → `.-.-` (AR)  
        """)

        st.divider()
        st.subheader("📝 Morse Dictionary")
        
        # Display full Morse code dictionary in a cleaner way (same as in app.py)
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

    # UI Elements setup
    video_placeholder = st.empty()
    status_placeholder = st.empty()
    message_placeholder = st.empty()
    info_placeholder = st.empty()

    cap = cv2.VideoCapture(0)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                st.error("Camera error")
                break

            frame = cv2.flip(frame, 1)

            # 1. Process eye blinks FIRST (independent of face recognition)
            blink_event, _, frame, _ = st.session_state.detector.process_frame(frame)
            if blink_event:
                st.session_state.blink_input.process_blink(blink_event)
            st.session_state.blink_input.update()

            # 2. Update live video stream
            video_placeholder.image(frame, channels="BGR")

            # 3. Get current Morse and translated text
            current_text = st.session_state.blink_input.text.strip().upper()
            current_morse = st.session_state.blink_input.current_morse
            
            # ---------------- LOGIN MODE ----------------
            if st.session_state.login_mode == "login":
                status_placeholder.subheader("🔍 Scanning for Face...")
                info_placeholder.info(f"💡 Blink `..-` (U) to **REGISTER**\n\nCurrent Morse: `{current_morse}`")

                # Check for Registration trigger (U) FIRST
                if current_text.endswith("U"):
                    st.session_state.login_mode = "register"
                    st.session_state.blink_input.text = ""
                    message_placeholder.empty()
                    st.toast("Switching to Registration Mode...")
                    # We continue to let the loop update UI in the next iteration
                else:
                    # Attempt recognition if not switching modes
                    result = recognize_face(frame)
                    if isinstance(result, str) and result not in ["NO_DB", "NO_FACE"]:
                        # result is the username
                        message_placeholder.success(f"✅ Hello {result}!")
                        st.session_state.user = result
                        time.sleep(1.5)
                        cap.release()
                        st.rerun()
                    elif result == "NO_DB":
                        message_placeholder.warning("⚠️ Database empty. Please register.")
                    elif result == "NO_FACE":
                        message_placeholder.info("🔍 Please look at the camera...")
                    else:
                        message_placeholder.warning("⚠️ Face not recognized")

            # ---------------- REGISTER MODE ----------------
            elif st.session_state.login_mode == "register":
                status_placeholder.subheader("📝 Registration Mode")
                message_placeholder.info(f"Detected Name: **{current_text}**")
                info_placeholder.write(f"Blink your name, then blink `.-.-` (AR) to confirm.\n\nCurrent Morse: `{current_morse}`")

                if current_text.endswith("AR"):
                    username = current_text.replace("AR", "").strip()
                    if not username:
                        message_placeholder.error("❌ Name cannot be empty")
                        st.session_state.blink_input.text = ""
                    else:
                        message_placeholder.info(f"💾 Saving face for {username}...")
                        success, msg = register_face(frame, username)
                        if success:
                            message_placeholder.success(f"✅ User {username} registered!")
                            st.session_state.user = username
                            time.sleep(2)
                            cap.release()
                            st.rerun()
                        else:
                            message_placeholder.error(f"❌ {msg}")
                            st.session_state.blink_input.text = ""

            time.sleep(0.01)
    finally:
        cap.release()
