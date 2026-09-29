import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class EscalationService:
    def __init__(self):
        self.gmail_address = os.getenv('GMAIL_ADDRESS')
        self.gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
        self.support_email = os.getenv('SUPPORT_EMAIL')
        
        if not all([self.gmail_address, self.gmail_app_password, self.support_email]):
            raise ValueError("Gmail credentials must be set in .env")
    
    def generate_reference_number(self):
        """Generate reference number: VER-[YYYYMMDD]-[HHMMSS]"""
        now = datetime.now()
        return f"VER-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
    
    def send_escalation_email(self, transcript: str, reference_number: str, customer_message: str):
        """Send escalation email to support team"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.gmail_address
            msg['To'] = self.support_email
            msg['Subject'] = f"ESCALATED: Vera Chatbot - {reference_number}"
            
            body = f"""
VERA CHATBOT ESCALATION
=======================

Reference Number: {reference_number}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CUSTOMER MESSAGE:
{customer_message}

FULL TRANSCRIPT:
{transcript}

This case has been escalated from the Vera chatbot. Please review and respond within 24 hours.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_app_password)
                server.send_message(msg)
            
            print(f"Escalation email sent: {reference_number}")
            return True
        except Exception as e:
            print(f"Error sending escalation email: {e}")
            return False

# Singleton instance
_escalation_instance = None

def get_escalation_service():
    global _escalation_instance
    if _escalation_instance is None:
        _escalation_instance = EscalationService()
    return _escalation_instance
