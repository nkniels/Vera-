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
    # Date of purchase — Google Forms date fields split into 3 sub-keys
    "date_year":     "entry.839337160_year",
    "date_month":    "entry.839337160_month",
    "date_day":      "entry.839337160_day",
    "action":        "entry.319484113",   # "Request a refund" | "Return product"
    "reason":        "entry.505576032",   # "Wrong item received" | "Changed my mind" | "Damaged item"
    # Other checkboxes — both options share the same entry ID (sent twice for multi-select)
    "other":         "entry.158684246",   # "Is the item unused?" | "Is the original packaging available?"
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
                             reason: str, email: str,
                             item_unused: bool = True,
                             packaging_available: bool = True) -> bool:
        """
        Silently POST to Intern 4's Google Form.
        This triggers her existing Make.com workflow automatically.
        """
        # Determine action — if reason implies damage/wrong item → refund, else return
        action = "Return product"
        if reason in ("Wrong item received", "Damaged item"):
            action = "Request a refund"

        form_reason = REASON_MAP.get(reason, "Damaged item")

        # Use today's date for Date of purchase
        now = datetime.now()

        # Build payload as a list of tuples so repeated keys (checkboxes) work correctly
        payload = [
            (FORM_FIELDS["name"],         customer_name),
            (FORM_FIELDS["email"],        email),
            (FORM_FIELDS["order_number"], order_number),
            (FORM_FIELDS["phone"],        "N/A"),   # Required by Google Form
            # Date of purchase — Google Forms requires year/month/day as separate params
            (FORM_FIELDS["date_year"],    str(now.year)),
            (FORM_FIELDS["date_month"],   str(now.month)),
            (FORM_FIELDS["date_day"],     str(now.day)),
            (FORM_FIELDS["action"],       action),
            (FORM_FIELDS["reason"],       form_reason),
        ]

        # Other checkboxes — accurately reflect customer response
        # Google Form marks this question required (must select at least one)
        if item_unused:
            payload.append((FORM_FIELDS["other"], "Is the item unused?"))
        if packaging_available or (not item_unused and not packaging_available):
            payload.append((FORM_FIELDS["other"], "Is the original packaging available?"))

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
            print(f"Google Form submitted for order {order_number} (unused={item_unused}, pkg={packaging_available}) — status: {response.status_code}")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print(f"Error submitting Google Form: {e}")
            return False

    def submit_return_request(self, customer_name: str, order_number: str,
                               reason: str, email: str,
                               item_unused: bool = True,
                               packaging_available: bool = True) -> bool:
        """
        Full returns pipeline:
        1. Submit Intern 4's Google Form → triggers her Make.com workflow
        2. Write a backup record to Airtable Returns & Refunds table
        Returns True if at least one path succeeded.
        """
        form_ok = self._submit_google_form(
            customer_name, order_number, reason, email,
            item_unused=item_unused,
            packaging_available=packaging_available
        )

        # Airtable write — always attempted as backup / audit trail
        airtable_ok = False
        try:
            form_reason = REASON_MAP.get(reason, "Damaged item")
            action = "Return product"
            if form_reason in ("Wrong item received", "Damaged item"):
                action = "Request a refund"

            airtable_data = {
                "Customer Name":   customer_name,
                "Email":           email,
                "Order Number":    order_number,
                "Request Type":    action,
                "Reason":          form_reason,
                "Submission Date": datetime.now().strftime('%Y-%m-%d'),
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
