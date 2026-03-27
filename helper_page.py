import streamlit as st
import pickle
import os
import time

HELPERS_DB = "helpers_db.pkl"
MESSAGES_DB = "messages_db.pkl"

def load_helpers():
    if os.path.exists(HELPERS_DB):
        with open(HELPERS_DB, "rb") as f:
            return pickle.load(f)
    return {}

def save_helpers(db):
    with open(HELPERS_DB, "wb") as f:
        pickle.dump(db, f)

def load_messages():
    if os.path.exists(MESSAGES_DB):
        with open(MESSAGES_DB, "rb") as f:
            return pickle.load(f)
    return []

def save_messages(msgs):
    with open(MESSAGES_DB, "wb") as f:
        pickle.dump(msgs, f)

def helper_page():
    st.title("👨‍⚕️ Helper Dashboard")
    
    if "helper_user" not in st.session_state:
        # Helper Login/Register
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.subheader("Login")
            email = st.text_input("Email", key="helper_login_email")
            if st.button("Login"):
                db = load_helpers()
                if email in db:
                    st.session_state.helper_user = db[email]
                    st.success(f"Logged in as {db[email]['name']}")
                    st.rerun()
                else:
                    st.error("Email not found. Please register.")
                    
        with tab2:
            st.subheader("Register")
            new_name = st.text_input("Helper Name")
            new_email = st.text_input("Helper Email")
            new_phone = st.text_input("Helper Phone")
            
            st.info("⚠️ Enter the EXACT username the patient used during face registration.")
            target_patient = st.text_input("Patient Username to Link")
            
            if st.button("Register Helper"):
                if new_email and new_name and target_patient:
                    db = load_helpers()
                    db[new_email] = {
                        "name": new_name,
                        "email": new_email,
                        "phone": new_phone,
                        "patient": target_patient.strip()
                    }
                    save_helpers(db)
                    st.success(f"Helper {new_name} linked to Patient {target_patient}!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields.")
        st.stop()

    # Logged in Helper View
    helper_info = st.session_state.helper_user
    st.sidebar.write(f"Logged in as: **{helper_info['name']}**")
    st.sidebar.write(f"Linking to Patient: **{helper_info['patient']}**")
    
    if st.sidebar.button("Logout"):
        del st.session_state.helper_user
        st.rerun()

    st.header(f"Messages from {helper_info['patient']}")
    
    msgs = load_messages()
    # Case-insensitive matching
    target_patient = helper_info["patient"].strip().lower()
    patient_msgs = [m for m in msgs if m["patient"].strip().lower() == target_patient]
    
    if not patient_msgs:
        st.info(f"No messages from your patient ({helper_info['patient']}) yet.")
    else:
        for m in reversed(patient_msgs):
            with st.chat_message("user"):
                st.write(m["message"])
                st.caption(f"Sent at: {m['time']}")

    if st.button("🔄 Refresh Messages"):
        st.rerun()

    if st.button("🗑️ Clear My Patient's Messages"):
        all_msgs = load_messages()
        # Keep only messages that are NOT from this patient
        remaining_msgs = [m for m in all_msgs if m["patient"].strip().lower() != target_patient]
        save_messages(remaining_msgs)
        st.success("Inbox cleared!")
        st.rerun()
