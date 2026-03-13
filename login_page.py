import streamlit as st
import cv2
import time

from face_auth import register_face, recognize_face
from eye_blink_detector import EyeBlinkDetector
from blink_input import BlinkInput

def login_page():
    st.title("EyeSpeak Login System")
    
    # Initialize session state for persistent objects
    if "detector" not in st.session_state:
        st.session_state.detector = EyeBlinkDetector()
    if "blink_input" not in st.session_state:
        st.session_state.blink_input = BlinkInput()
    if "do_register" not in st.session_state:
        st.session_state.do_register = False

    mode = st.radio("Select Mode", ["Login", "Register"])
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        run = st.toggle("Start Camera", key="login_cam_toggle")
        video_placeholder = st.empty()
        
    with col2:
        username_display = st.empty()
        message_placeholder = st.empty()
        
        if mode == "Register":
            # Use text_input for the username, but update it from blink_input
            reg_username = st.text_input("Username (or blink it)", value=st.session_state.blink_input.text)
            if st.button("Register Face"):
                st.session_state.do_register = True
        
        if st.button("Clear Blink Text"):
            st.session_state.blink_input.text = ""
            st.rerun()

    if run:
        cap = cv2.VideoCapture(0)
        try:
            while run:
                ret, frame = cap.read()
                if not ret:
                    st.error("Camera error")
                    break
                
                frame = cv2.flip(frame, 1)
                
                # Process blink events
                blink_event, _, frame, _ = st.session_state.detector.process_frame(frame)
                if blink_event:
                    st.session_state.blink_input.process_blink(blink_event)
                st.session_state.blink_input.update()
                
                # Update UI
                username_display.write(f"**Detected Username:** {st.session_state.blink_input.text}")
                video_placeholder.image(frame, channels="BGR")
                
                # Logic for Login
                if mode == "Login":
                    user = recognize_face(frame)
                    if user:
                        st.session_state.user = user
                        message_placeholder.success(f"Welcome {user}!")
                        time.sleep(1)
                        cap.release()
                        st.rerun()
                
                # Logic for Registration
                if mode == "Register" and st.session_state.do_register:
                    target_user = reg_username if reg_username else st.session_state.blink_input.text
                    if not target_user.strip():
                        message_placeholder.error("Please provide a username first.")
                    else:
                        success, msg = register_face(frame, target_user)
                        if success:
                            message_placeholder.success(msg)
                        else:
                            message_placeholder.error(msg)
                    st.session_state.do_register = False
                
                time.sleep(0.01)
        finally:
            cap.release()
    else:
        st.info("Toggle 'Start Camera' to begin login or registration.")
