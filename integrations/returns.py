import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class ReturnsService:
    def __init__(self):
        self.webhook_url = os.getenv('MAKE_WEBHOOK_URL')
        
        if not self.webhook_url or self.webhook_url == 'intern_4_webhook_url_here':
            print("Warning: MAKE_WEBHOOK_URL not configured. Returns will not be processed.")
    
    def submit_return_request(self, customer_name: str, order_number: str, reason: str, email: str):
        """Submit return request to Make.com webhook"""
        if not self.webhook_url or self.webhook_url == 'intern_4_webhook_url_here':
            print("Cannot submit return: MAKE_WEBHOOK_URL not configured")
            return False
        
        payload = {
            "customer_name": customer_name,
            "order_number": order_number,
            "reason": reason,
            "email": email,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"Return request submitted: {order_number}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error submitting return request: {e}")
            return False

# Singleton instance
_returns_instance = None

def get_returns_service():
    global _returns_instance
    if _returns_instance is None:
        _returns_instance = ReturnsService()
    return _returns_instance
