from google import genai
from google.genai import types as genai_types
import os
import random
from dotenv import load_dotenv
from knowledge_base import get_knowledge_base
from integrations.airtable import get_airtable
from integrations.escalation import get_escalation_service
from integrations.returns import get_returns_service
from integrations.quiz import get_quiz_service

load_dotenv()

class VeraChatbot:
    def __init__(self):
        # --- Gemini AI client ---
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("Warning: GEMINI_API_KEY not found in environment variables")
                self.gemini_client = None
                self.gemini_available = False
            else:
                self.gemini_client = genai.Client(api_key=api_key)
                self.gemini_available = True
        except Exception as e:
            print(f"Warning: Could not initialize Gemini client: {e}")
            self.gemini_client = None
            self.gemini_available = False

        # --- Knowledge Base (instant text search, no ChromaDB) ---
        self.kb = get_knowledge_base()

        # --- Airtable ---
        try:
            self.airtable = get_airtable()
        except Exception as e:
            print(f"Warning: Airtable not available: {e}")
            self.airtable = None

        # --- Escalation (email) ---
        try:
            self.escalation = get_escalation_service()
            self.escalation_available = True
        except Exception as e:
            print(f"Warning: Escalation service not available: {e}")
            self.escalation = None
            self.escalation_available = False

        # --- Returns (Make.com webhook) ---
        try:
            self.returns = get_returns_service()
        except Exception as e:
            print(f"Warning: Returns service not available: {e}")
            self.returns = None

        # --- Quiz (external endpoint) ---
        self.quiz = get_quiz_service()

        # --- Intent definitions with trigger keywords ---
        self.intents = {
            'GREETING': {
                'keywords': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings'],
                'action': 'greeting'
            },
            'Q1': {
                'keywords': ['what products', 'what do you sell', 'show me', 'product list', 'catalogue', 'what do you have'],
                'action': 'query_knowledge'
            },
            'Q2': {
                'keywords': ['how much', 'price', 'cost', 'afford', 'expensive', 'cheap'],
                'action': 'query_knowledge'
            },
            'Q3': {
                'keywords': ['what should i use', 'skin type', 'recommend', 'suggest', 'best for my skin', 'what is good for'],
                'action': 'quiz_handoff'
            },
            'Q4': {
                'keywords': ['natural', 'clean', 'ingredients', 'chemicals', 'paraben', 'sulfate'],
                'action': 'query_knowledge'
            },
            'Q5': {
                'keywords': ['where is my order', 'order status', 'tracking', 'my order'],
                'action': 'query_order'
            },
            'Q6': {
                'keywords': ['when will it arrive', 'delivery', 'arrival', 'shipping to'],
                'action': 'query_delivery'
            },
            'Q7': {
                'keywords': ['return', 'refund', 'exchange', 'wrong item', 'damaged', 'sent wrong'],
                'action': 'returns_handoff'
            },
            'Q8': {
                'keywords': ['do you ship to', 'deliver to', 'available in'],
                'action': 'query_knowledge'
            },
            'Q9': {
                'keywords': ['how long does shipping take', 'shipping time', 'delivery time'],
                'action': 'query_knowledge'
            },
            'Q10': {
                'keywords': ['angry', 'frustrated', 'terrible', 'damaged my skin', 'unacceptable', 'hate', 'worst'],
                'action': 'escalate'
            }
        }

        self.system_prompt = """You are Vera, a warm, empathetic, and professional customer support chatbot for Verdant Skin Co., a clean beauty brand based in Accra, Ghana.

Your tone should be:
- Warm and friendly
- Empathetic to customer concerns
- Concise and to the point
- Professional yet approachable

Your scope is limited to:
- Verdant Skin Co. products
- Orders and shipping
- Returns and refunds
- Skin concerns and product recommendations
- Brand values and ingredients

If a customer asks anything outside this scope, respond helpfully to the best of your ability. Only use ESCALATE_VERA in your response if the customer is genuinely angry, distressed, or has an issue that truly cannot be resolved with information alone.

Use the provided knowledge base context to answer questions accurately. If you don't know the answer from the context, say so honestly and offer to escalate if needed."""

    def classify_intent(self, message: str) -> str:
        """Classify customer message into one of the intents using keyword matching."""
        message_lower = message.lower()
        for intent, config in self.intents.items():
            for keyword in config['keywords']:
                if keyword in message_lower:
                    return intent
        return 'UNKNOWN'

    def generate_response(self, message: str, context: str = "") -> str:
        """Generate AI response using Gemini API."""
        if not self.gemini_available:
            return "I'm currently unable to generate AI responses. Please try again later or contact our support team directly."

        try:
            prompt = self.system_prompt

            if context:
                prompt += f"\n\nKnowledge base context:\n{context}"

            prompt += f"\n\nCustomer message: {message}"

            response = self.gemini_client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                )
            )
            return response.text
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble responding right now. Please try again shortly."

    def handle_greeting(self, message: str) -> tuple:
        """Handle greeting messages."""
        responses = [
            "Hello! I'm Vera from Verdant Skin Co. How can I help you today?",
            "Hi there! I'm here to help with any questions about our products, orders, or skincare concerns.",
            "Hey! Welcome to Verdant Skin Co. What can I assist you with today?"
        ]
        response = random.choice(responses)
        return response, 'Resolved'

    def handle_query_knowledge(self, message: str) -> tuple:
        """Handle intents that require knowledge base query."""
        context_results = self.kb.query(message, n_results=3)
        context = "\n\n".join(context_results) if context_results else ""
        response = self.generate_response(message, context)
        return response, 'Resolved'

    def handle_quiz_handoff(self, message: str) -> tuple:
        """Handle Q3 - Product matching: start quiz flow."""
        response = "I'd love to help you find the perfect products for your skin! Let me ask you a couple of quick questions.\n\nWhat is your main skin concern? (e.g. acne, dryness, dark spots, oily skin)"
        return response, 'QUIZ_COLLECTING'

    def handle_quiz_submission(self, skin_concern: str, skin_type: str) -> tuple:
        """Submit quiz to endpoint or fall back to AI recommendation."""
        result = self.quiz.submit_quiz_answers(skin_concern, skin_type)

        if result and 'recommendation' in result:
            response = f"Based on your answers, I recommend: {result['recommendation']}"
            return response, 'Resolved'
        else:
            # Quiz endpoint not configured — use AI to generate recommendation inline
            context_results = self.kb.query(f"products for {skin_type} skin {skin_concern}", n_results=3)
            context = "\n\n".join(context_results) if context_results else ""
            response = self.generate_response(
                f"Recommend Verdant Skin Co. products for a customer with {skin_type} skin whose main concern is {skin_concern}. Be specific and warm.",
                context
            )
            return response, 'Resolved'

    def handle_query_order(self, message: str) -> tuple:
        """Handle Q5 - Order status query."""
        response = "Please provide your order number so I can check the status for you."
        return response, 'ORDER_COLLECTING'

    def handle_order_lookup(self, order_id: str) -> tuple:
        """Look up order in Airtable."""
        if not self.airtable:
            return "I'm unable to look up orders right now. Please contact our support team at verdantskinco.ng@gmail.com.", 'Escalated'

        order_data = self.airtable.get_order_status('Orders', order_id)

        if order_data:
            status = order_data.get('Order Status', 'Unknown')
            response = f"Your order {order_id} status is: **{status}**. Is there anything else I can help you with?"
            return response, 'Resolved'
        else:
            response = "I couldn't find that order number. Please double-check it, or contact our support team and we'll track it down for you!"
            return response, 'Resolved'

    def handle_query_delivery(self, message: str) -> tuple:
        """Handle Q6 - Delivery time query."""
        context_results = self.kb.query(message, n_results=3)
        context = "\n\n".join(context_results) if context_results else ""
        response = self.generate_response(message, context)
        return response, 'Resolved'

    def handle_returns_handoff(self, message: str) -> tuple:
        """Handle Q7 - Returns handoff."""
        response = "I can help you with your return! Please provide the following:\n1. Your name\n2. Order number\n3. Reason for return"
        return response, 'RETURNS_COLLECTING'

    def handle_returns_submission(self, customer_name: str, order_number: str, reason: str, email: str) -> tuple:
        """Submit return request."""
        if not self.returns:
            response = "I've noted your return request. Please email verdantskinco.ng@gmail.com with your order number and reason, and our team will process it within 2 business days."
            return response, 'Resolved'

        success = self.returns.submit_return_request(customer_name, order_number, reason, email)

        if success:
            response = "Your return request has been submitted successfully! Our team will process it within 2 business days and reach out to you via email."
            return response, 'Resolved'
        else:
            response = "I'm having trouble submitting your return request. Please email verdantskinco.ng@gmail.com directly with your details."
            return response, 'Resolved'

    def handle_escalation(self, message: str, transcript: str) -> tuple:
        """Handle escalation — send email to support team."""
        if not self.escalation_available:
            response = "I'm sorry I couldn't fully help. Please reach out to our support team directly at verdantskinco.ng@gmail.com."
            return response, 'Escalated'

        reference = self.escalation.generate_reference_number()
        success = self.escalation.send_escalation_email(transcript, reference, message)

        if success:
            response = f"I've flagged your case to our support team. Reference: **#{reference}**. Someone will contact you within 24 hours."
        else:
            response = "I'm having trouble reaching our support system right now. Please email us directly at verdantskinco.ng@gmail.com and we'll get back to you within 24 hours."

        return response, 'Escalated'

    def process_message(self, message: str, conversation_state: dict = None) -> dict:
        """Main message processing function."""
        if conversation_state is None:
            conversation_state = {}

        intent = self.classify_intent(message)
        action = self.intents.get(intent, {}).get('action', 'query_knowledge')

        response = ""
        new_state = conversation_state.copy()
        new_state['intent'] = intent

        # Handle active multi-step conversation flows
        current_state = conversation_state.get('state')

        if current_state == 'QUIZ_COLLECTING':
            new_state['skin_concern'] = message
            response = "Thanks! And how would you describe your skin — dry, oily, combination, or sensitive?"
            new_state['state'] = 'QUIZ_COLLECTING_TYPE'

        elif current_state == 'QUIZ_COLLECTING_TYPE':
            new_state['skin_type'] = message
            response, status = self.handle_quiz_submission(
                conversation_state.get('skin_concern', ''), message
            )
            new_state['state'] = status
            new_state['conversation_status'] = status

        elif current_state == 'ORDER_COLLECTING':
            response, status = self.handle_order_lookup(message)
            new_state['state'] = status
            new_state['conversation_status'] = status
            new_state['order_id'] = message

        elif current_state == 'RETURNS_COLLECTING':
            new_state['customer_name'] = message
            response = "Thank you! What is your order number?"
            new_state['state'] = 'RETURNS_COLLECTING_ORDER'

        elif current_state == 'RETURNS_COLLECTING_ORDER':
            new_state['order_number'] = message
            response = "Got it. What is the reason for your return?"
            new_state['state'] = 'RETURNS_COLLECTING_REASON'

        elif current_state == 'RETURNS_COLLECTING_REASON':
            new_state['reason'] = message
            response = "Almost done! Please provide your email address so we can keep you updated."
            new_state['state'] = 'RETURNS_COLLECTING_EMAIL'

        elif current_state == 'RETURNS_COLLECTING_EMAIL':
            new_state['email'] = message
            response, status = self.handle_returns_submission(
                conversation_state.get('customer_name', ''),
                conversation_state.get('order_number', ''),
                conversation_state.get('reason', ''),
                message
            )
            new_state['state'] = status
            new_state['conversation_status'] = status

        else:
            # Normal intent routing (no active multi-step flow)
            if action == 'greeting':
                response, status = self.handle_greeting(message)
                new_state['conversation_status'] = status

            elif action == 'quiz_handoff':
                response, status = self.handle_quiz_handoff(message)
                new_state['state'] = status
                new_state['conversation_status'] = 'Pending'

            elif action == 'query_order':
                response, status = self.handle_query_order(message)
                new_state['state'] = status
                new_state['conversation_status'] = 'Pending'

            elif action == 'query_delivery':
                response, status = self.handle_query_delivery(message)
                new_state['conversation_status'] = 'Resolved'

            elif action == 'returns_handoff':
                response, status = self.handle_returns_handoff(message)
                new_state['state'] = status
                new_state['conversation_status'] = 'Pending'

            elif action == 'escalate':
                response, status = self.handle_escalation(message, conversation_state.get('transcript', ''))
                new_state['state'] = status
                new_state['conversation_status'] = status

            else:
                # query_knowledge (default for all other intents + UNKNOWN)
                response, status = self.handle_query_knowledge(message)
                new_state['conversation_status'] = 'Resolved'

        # Check for escalation keyword injected by LLM in its response
        if 'ESCALATE_VERA' in response:
            response = response.replace('ESCALATE_VERA', '').strip()
            if self.escalation_available:
                reference = self.escalation.generate_reference_number()
                transcript = conversation_state.get('transcript', '') + f"\nCustomer: {message}\nVera: {response}"
                success = self.escalation.send_escalation_email(transcript, reference, message)
                if success:
                    response += f"\n\nI've flagged your case to our support team. Reference: **#{reference}**. Someone will contact you within 24 hours."
                else:
                    response += "\n\nPlease contact our support team directly at verdantskinco.ng@gmail.com."
            else:
                response += "\n\nPlease contact our support team directly at verdantskinco.ng@gmail.com."
            new_state['conversation_status'] = 'Escalated'
            new_state['escalation_flag'] = True

        # Update running transcript for escalation context
        new_state['transcript'] = conversation_state.get('transcript', '') + f"\nCustomer: {message}\nVera: {response}"

        return {
            'response': response,
            'intent': intent,
            'state': new_state
        }


# Singleton instance
_vera_instance = None

def get_vera():
    global _vera_instance
    if _vera_instance is None:
        _vera_instance = VeraChatbot()
    return _vera_instance
