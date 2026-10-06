import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from integrations.airtable import get_airtable

load_dotenv()

# ------------------------------------------------------------------
# Intern 4's Google Form — field entry IDs (extracted Oct 2026)
# Form: Verdant Skin Co. Return/Refund Request Form
# POST URL: https://docs.google.com/forms/d/e/
#           1FAIpQLSfPZ0m3DxE0s0ICrwpzwIR9By1BlpfYCaV2VrA_Z5JwGyztvQ/formResponse
# ------------------------------------------------------------------
GOOGLE_FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSfPZ0m3DxE0s0ICrwpzwIR9By1BlpfYCaV2VrA_Z5JwGyztvQ/formResponse"
)

# Field mapping  (label → entry ID)
FORM_FIELDS = {
    "name":          "entry.2005620554",
    "email":         "entry.1045781291",
    "order_number":  "entry.1065046570",
    "phone":         "entry.1166974658",
    "action":        "entry.319484113",   # "Request a refund" | "Return product"
    "reason":        "entry.505576032",   # "Wrong item received" | "Changed my mind" | "Damaged item"
}

# Map Vera's internal reason labels → Google Form option text
REASON_MAP = {
    "Wrong item received": "Wrong item received",
    "Changed my mind":     "Changed my mind",
    "Damaged item":        "Damaged item",
}


class ReturnsService:
    def __init__(self):
        self.airtable = get_airtable()

    def _submit_google_form(self, customer_name: str, order_number: str,
                             reason: str, email: str) -> bool:
        """
        Silently POST to Intern 4's Google Form.
        This triggers her existing Make.com workflow automatically.
        """
        # Determine action — if reason implies damage/wrong item → refund, else return
        action = "Return product"
        if reason in ("Wrong item received", "Damaged item"):
            action = "Request a refund"

        form_reason = REASON_MAP.get(reason, "Damaged item")

        payload = {
            FORM_FIELDS["name"]:         customer_name,
            FORM_FIELDS["email"]:        email,
            FORM_FIELDS["order_number"]: order_number,
            FORM_FIELDS["action"]:       action,
            FORM_FIELDS["reason"]:       form_reason,
        }

        try:
            # Google Forms expects a form-encoded POST, not JSON
            response = requests.post(
                GOOGLE_FORM_URL,
                data=payload,
                timeout=10,
                allow_redirects=True,
                headers={"Referer": GOOGLE_FORM_URL.replace("formResponse", "viewform")}
            )
            # Google Forms returns 200 on success (even after redirect)
            print(f"Google Form submitted for order {order_number} — status: {response.status_code}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error submitting Google Form: {e}")
            return False

    def submit_return_request(self, customer_name: str, order_number: str,
                               reason: str, email: str) -> bool:
        """
        Full returns pipeline:
        1. Submit Intern 4's Google Form → triggers her Make.com workflow
        2. Write a backup record to Airtable Returns & Refunds table
        Returns True if at least one path succeeded.
        """
        form_ok = self._submit_google_form(customer_name, order_number, reason, email)

        # Airtable write — always attempted as backup / audit trail
        airtable_ok = False
        try:
            airtable_data = {
                "Customer Name":   customer_name,
                "Email":           email,
                "Order Number":    order_number,
                "Reason":          reason,
                "Submission Date": datetime.now().strftime('%Y-%m-%d'),
                "Status":          "Pending",   # Make.com will update this
            }
            self.airtable.write_conversation("Returns & Refunds", airtable_data)
            print(f"Return request written to Airtable: {order_number}")
            airtable_ok = True
        except Exception as e:
            print(f"Error writing return to Airtable: {e}")

        return form_ok or airtable_ok


# Singleton instance
_returns_instance = None

def get_returns_service():
    global _returns_instance
    if _returns_instance is None:
        _returns_instance = ReturnsService()
    return _returns_instance
