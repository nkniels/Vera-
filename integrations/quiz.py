import os
import urllib.parse
from dotenv import load_dotenv
from integrations.airtable import get_airtable

load_dotenv()

# Intern 6's Tally Quiz link
TALLY_QUIZ_URL = "https://tally.so/r/5BNAoZ"

class QuizService:
    def __init__(self):
        self.quiz_url = TALLY_QUIZ_URL
        try:
            self.airtable = get_airtable()
        except Exception as e:
            print(f"Warning: Airtable not available in QuizService: {e}")
            self.airtable = None

    def get_quiz_url(self, email: str = "") -> str:
        """Return the Tally quiz URL, prefilled with email if provided."""
        if email:
            encoded_email = urllib.parse.quote(email.strip())
            return f"{self.quiz_url}?email={encoded_email}"
        return self.quiz_url

    def get_lead_recommendations(self, email: str) -> dict:
        """
        Read the quiz recommendation and prefilled Shopify cart straight
        from the Leads table in Airtable based on customer email.
        """
        if not self.airtable or not email:
            return None

        record = self.airtable.get_lead_by_email("Leads", email)
        if not record or 'fields' not in record:
            return None

        fields = record['fields']
        return {
            "lead_name": fields.get("Lead Name", ""),
            "email": fields.get("Email", email),
            "primary_concern": fields.get("Primary Concern", ""),
            "secondary_concern": fields.get("Secondary Concern", ""),
            "recommended_products": fields.get("Recommended Products", ""),
            "cart_link": fields.get("Cart Link", ""),
            "rationale": fields.get("Recommendation Rationale", ""),
            "routine_steps": fields.get("Routine Steps"),
            "lead_id": fields.get("Lead ID", ""),
        }

    # Backward-compatible fallback
    def submit_quiz_answers(self, skin_concern: str, skin_type: str):
        """Deprecated: Logic is now handled via Tally quiz and Airtable Leads table."""
        return None


# Singleton instance
_quiz_instance = None

def get_quiz_service():
    global _quiz_instance
    if _quiz_instance is None:
        _quiz_instance = QuizService()
    return _quiz_instance
