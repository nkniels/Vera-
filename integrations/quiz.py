import requests
import os
from dotenv import load_dotenv

load_dotenv()

class QuizService:
    def __init__(self):
        self.quiz_endpoint = os.getenv('QUIZ_ENDPOINT')
        
        if not self.quiz_endpoint or self.quiz_endpoint == 'intern_6_quiz_endpoint_here':
            print("Warning: QUIZ_ENDPOINT not configured. Quiz handoff will not work.")
    
    def submit_quiz_answers(self, skin_concern: str, skin_type: str):
        """Submit quiz answers to Intern 6 Quiz Agent endpoint"""
        if not self.quiz_endpoint or self.quiz_endpoint == 'intern_6_quiz_endpoint_here':
            print("Cannot submit quiz: QUIZ_ENDPOINT not configured")
            return None
        
        payload = {
            "skin_concern": skin_concern,
            "skin_type": skin_type
        }
        
        try:
            response = requests.post(self.quiz_endpoint, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            print(f"Quiz response received: {result}")
            return result
        except requests.exceptions.RequestException as e:
            print(f"Error submitting quiz: {e}")
            return None
        except Exception as e:
            print(f"Error parsing quiz response: {e}")
            return None

# Singleton instance
_quiz_instance = None

def get_quiz_service():
    global _quiz_instance
    if _quiz_instance is None:
        _quiz_instance = QuizService()
    return _quiz_instance
