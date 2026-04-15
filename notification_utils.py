import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Optional: Twilio for SMS and WhatsApp
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

# Load environment variables from .env file
load_dotenv()

# Email Configuration
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

def send_email_notification(to_email, helper_name, patient_name, message, time_sent):
    """
    Sends an email notification to the helper.
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return False, "Email credentials not configured in .env"

    try:
        subject = f"New Message from Patient: {patient_name}"
        body = f"""Hello {helper_name},

You have received a new message from your patient ({patient_name}):

"{message}"

Time: {time_sent}

Please check the EyeSpeak app for more details.
"""
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, f"Email failed: {str(e)}"

def send_sms_notification(to_phone, patient_name, message):
    """
    Sends an SMS notification via Twilio (if configured).
    """
    if not TWILIO_AVAILABLE:
        return False, "Twilio library not installed"
    
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        return False, "Twilio credentials not configured in .env"

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        short_msg = (message[:100] + '..') if len(message) > 100 else message
        sms_body = f"EyeSpeak: New message from {patient_name}: {short_msg}"
        
        client.messages.create(
            body=sms_body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        return True, "SMS sent successfully"
    except Exception as e:
        return False, f"SMS failed: {str(e)}"

def send_whatsapp_notification(to_phone, helper_name, patient_name, message, time_sent):
    """
    Sends a WhatsApp notification via Twilio WhatsApp Sandbox.
    """
    if not TWILIO_AVAILABLE:
        return False, "Twilio library not installed"
    
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN]):
        return False, "Twilio credentials not configured in .env"

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Ensure phone number is in correct format for Twilio WhatsApp
        # It should start with + followed by country code
        clean_phone = to_phone.strip()
        if not clean_phone.startswith("+"):
            # Assume a default prefix or warn if needed. Morocco is +212 as per user input example.
            # But we'll just prepend + if it's missing, though user should provide full format.
            clean_phone = "+" + clean_phone

        whatsapp_body = f"Hello {helper_name},\n\nNew message from your patient ({patient_name}):\n\n\"{message}\"\n\nTime: {time_sent}"
        
        msg = client.messages.create(
            body=whatsapp_body,
            from_="whatsapp:+14155238886", # Twilio Sandbox Number
            to=f"whatsapp:{clean_phone}"
        )
        return True, f"WhatsApp sent: {msg.sid}"
    except Exception as e:
        return False, f"WhatsApp failed: {str(e)}"
