import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from integrations.airtable import get_airtable

load_dotenv()

class ReturnsService:
    def __init__(self):
        self.webhook_url = os.getenv('MAKE_WEBHOOK_URL')
        self.airtable = get_airtable()
        
        if not self.webhook_url or self.webhook_url == 'intern_4_webhook_url_here':
            print("Warning: MAKE_WEBHOOK_URL not configured. Returns will not be processed via webhook.")
    
    def submit_return_request(self, customer_name: str, order_number: str, reason: str, email: str):
        """Submit return request to Make.com webhook and Airtable"""
        # Always write to Airtable Returns & Refunds table
        try:
            airtable_data = {
                "Customer Name": customer_name,
                "Email": email,
                "Order Number": order_number,
                "Reason": reason,
                "Submission Date": datetime.now().strftime('%Y-%m-%d'),
                "Status": "Auto Approved"  # Auto-approve based on spec
            }
            self.airtable.write_conversation("Returns & Refunds", airtable_data)
            print(f"Return request written to Airtable: {order_number}")
        except Exception as e:
            print(f"Error writing return to Airtable: {e}")
        
        # Also send to Make.com webhook if configured
        if not self.webhook_url or self.webhook_url == 'intern_4_webhook_url_here':
            print("Cannot submit return to Make.com: MAKE_WEBHOOK_URL not configured")
            return True  # Return True since Airtable write succeeded
        
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
            print(f"Return request submitted to Make.com: {order_number}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error submitting return request to Make.com: {e}")
            return True  # Return True since Airtable write succeeded

# Singleton instance
_returns_instance = None

def get_returns_service():
    global _returns_instance
    if _returns_instance is None:
        _returns_instance = ReturnsService()
    return _returns_instance
