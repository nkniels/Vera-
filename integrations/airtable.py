from pyairtable import Api
import os
from dotenv import load_dotenv

load_dotenv()

class AirtableIntegration:
    def __init__(self):
        self.api_key = os.getenv('AIRTABLE_PAT')  # Personal Access Token
        self.base_id = os.getenv('AIRTABLE_BASE_ID')
        
        if not self.api_key or not self.base_id:
            raise ValueError("AIRTABLE_PAT and AIRTABLE_BASE_ID must be set in .env")
        
        self.api = Api(self.api_key)
        self.base = self.api.base(self.base_id)
    
    def write_conversation(self, table_name: str, data: dict):
        """Write a conversation record to Airtable"""
        try:
            table = self.base.table(table_name)
            record = table.create(data)
            return record
        except Exception as e:
            print(f"Error writing to Airtable: {e}")
            return None
    
    def get_order_status(self, table_name: str, order_id: str):
        """Query Orders table by Order ID"""
        try:
            table = self.base.table(table_name)
            # Sanitize: strip single-quotes to prevent Airtable formula injection
            safe_order_id = order_id.replace("'", "")
            formula = f"{{Order ID}} = '{safe_order_id}'"
            records = table.all(formula=formula)
            
            if records:
                return records[0]
            return None
        except Exception as e:
            print(f"Error querying Airtable: {e}")
            return None
    
    def get_customer_record(self, table_name: str, customer_id: str):
        """Get customer record by ID"""
        try:
            table = self.base.table(table_name)
            formula = f"{{Customer ID}} = '{customer_id}'"
            records = table.all(formula=formula)
            
            if records:
                return records[0]
            return None
        except Exception as e:
            print(f"Error querying customer: {e}")
            return None
    
    def get_lead_record(self, table_name: str, lead_id: str):
        """Get lead record by ID"""
        try:
            table = self.base.table(table_name)
            formula = f"{{Lead ID}} = '{lead_id}'"
            records = table.all(formula=formula)
            
            if records:
                return records[0]
            return None
        except Exception as e:
            print(f"Error querying lead: {e}")
            return None

    def get_lead_by_email(self, table_name: str, email: str):
        """Get the latest lead record by customer Email"""
        try:
            table = self.base.table(table_name)
            safe_email = email.strip().lower().replace("'", "")
            formula = f"LOWER({{Email}}) = '{safe_email}'"
            records = table.all(formula=formula)
            if records:
                # Return the latest record
                return records[-1]
            return None
        except Exception as e:
            print(f"Error querying lead by email: {e}")
            return None

# Singleton instance
_airtable_instance = None

def get_airtable():
    global _airtable_instance
    if _airtable_instance is None:
        _airtable_instance = AirtableIntegration()
    return _airtable_instance
