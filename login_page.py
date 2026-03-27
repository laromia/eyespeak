import streamlit as st
import cv2
import time

from face_auth import register_face, recognize_face
from eye_blink_detector import EyeBlinkDetector
from blink_input import BlinkInput

def login_page():
    st.title("EyeSpeak Login")

    # Initialize persistent objects in session state
    if "detector" not in st.session_state:
        st.session_state.detector = EyeBlinkDetector()
    if "blink_input" not in st.session_state:
        st.session_state.blink_input = BlinkInput()
    if "login_mode" not in st.session_state:
        st.session_state.login_mode = "login"

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

            # Process eye blinks
            blink_event, _, frame, _ = st.session_state.detector.process_frame(frame)
            if blink_event:
                st.session_state.blink_input.process_blink(blink_event)
            st.session_state.blink_input.update()

            # Update live video stream
            video_placeholder.image(frame, channels="BGR")

            # Update UI text based on mode
            current_text = st.session_state.blink_input.text.strip().upper()
            
            # ---------------- LOGIN MODE ----------------
            if st.session_state.login_mode == "login":
                status_placeholder.subheader("🔍 Scanning for Face...")
                info_placeholder.info("💡 Blink `..-` (U) to **REGISTER**")

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
                    
                    if current_text.endswith("U"):
                        st.session_state.login_mode = "register"
                        st.session_state.blink_input.text = ""
                        message_placeholder.empty()
                        st.toast("Switching to Registration Mode...")

            # ---------------- REGISTER MODE ----------------
            elif st.session_state.login_mode == "register":
                status_placeholder.subheader("📝 Registration Mode")
                message_placeholder.info(f"Detected Name: **{current_text}**")
                info_placeholder.write("Blink your name, then blink `.-.-` (AR) to confirm.")

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
