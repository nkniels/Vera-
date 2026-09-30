from groq import Groq
import os
from dotenv import load_dotenv
from knowledge_base import get_knowledge_base
from integrations.airtable import get_airtable
from integrations.escalation import get_escalation_service
from integrations.returns import get_returns_service
from integrations.quiz import get_quiz_service

load_dotenv()

class VeraChatbot:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.kb = get_knowledge_base()
        self.airtable = get_airtable()
        self.escalation = get_escalation_service()
        self.returns = get_returns_service()
        self.quiz = get_quiz_service()
        
        # Intent definitions with trigger keywords
        self.intents = {
            'Q1_PRODUCT_CATALOGUE': {
                'keywords': ['what products', 'what do you sell', 'show me', 'product list', 'catalogue'],
                'action': 'query_knowledge'
            },
            'Q2_PRICING': {
                'keywords': ['how much', 'price', 'cost', 'afford', 'expensive', 'cheap'],
                'action': 'query_knowledge'
            },
            'Q3_PRODUCT_MATCHING': {
                'keywords': ['what should i use', 'skin type', 'recommend', 'suggest', 'best for my skin'],
                'action': 'quiz_handoff'
            },
            'Q4_INGREDIENTS': {
                'keywords': ['natural', 'clean', 'ingredients', 'chemicals', 'paraben', 'sulfate'],
                'action': 'query_knowledge'
            },
            'Q5_ORDER_STATUS': {
                'keywords': ['where is my order', 'order status', 'tracking', 'my order'],
                'action': 'query_order'
            },
            'Q6_DELIVERY_TIME': {
                'keywords': ['when will it arrive', 'how long', 'delivery', 'arrival', 'shipping to'],
                'action': 'query_delivery'
            },
            'Q7_RETURNS': {
                'keywords': ['return', 'refund', 'exchange', 'wrong item', 'damaged', 'sent wrong'],
                'action': 'returns_handoff'
            },
            'Q8_SHIPPING_DESTINATIONS': {
                'keywords': ['do you ship to', 'shipping to', 'deliver to', 'available in'],
                'action': 'query_knowledge'
            },
            'Q9_SHIPPING_TIME': {
                'keywords': ['how long does shipping take', 'shipping time', 'delivery time'],
                'action': 'query_knowledge'
            },
            'Q10_COMPLAINTS': {
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

If a customer asks anything outside this scope, you must respond with: "I'm sorry, I can only help with questions about Verdant Skin Co. products, orders, shipping, returns, and skin concerns. For other matters, I'll need to escalate this to our support team. ESCALATE_VERA"

Use the provided knowledge base context to answer questions accurately. If you don't know the answer from the context, say so honestly and offer to escalate if needed."""

    def classify_intent(self, message: str) -> str:
        """Classify customer message into one of the 10 intents"""
        message_lower = message.lower()
        
        for intent, config in self.intents.items():
            for keyword in config['keywords']:
                if keyword in message_lower:
                    return intent
        
        return 'UNKNOWN'
    
    def generate_response(self, message: str, context: str = "") -> str:
        """Generate AI response using Groq API"""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Knowledge base context:\n{context}"
                })
            
            messages.append({
                "role": "user",
                "content": message
            })
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble responding right now. Please try again or let me escalate this to our support team. ESCALATE_VERA"
    
    def handle_query_knowledge(self, message: str) -> tuple:
        """Handle intents that require knowledge base query"""
        context_results = self.kb.query(message, n_results=3)
        context = "\n\n".join(context_results) if context_results else ""
        response = self.generate_response(message, context)
        return response, None
    
    def handle_quiz_handoff(self, message: str) -> tuple:
        """Handle Q3 - Product matching with quiz handoff"""
        response = "I'd love to help you find the perfect products for your skin! Let me ask you a few questions:\n\n1. What is your main skin concern?\n2. Would you describe your skin as dry, oily, combination, or sensitive?"
        return response, 'QUIZ_COLLECTING'
    
    def handle_quiz_submission(self, skin_concern: str, skin_type: str) -> tuple:
        """Submit quiz to Intern 6 and return recommendation"""
        result = self.quiz.submit_quiz_answers(skin_concern, skin_type)
        
        if result and 'recommendation' in result:
            response = f"Based on your answers, I recommend: {result['recommendation']}"
            return response, 'Resolved'
        else:
            response = "I'm having trouble getting your personalized recommendation. Let me escalate this to our support team. ESCALATE_VERA"
            return response, 'Escalated'
    
    def handle_query_order(self, message: str) -> tuple:
        """Handle Q5 - Order status query"""
        response = "Please provide your order number so I can check the status for you."
        return response, 'ORDER_COLLECTING'
    
    def handle_order_lookup(self, order_id: str) -> tuple:
        """Look up order in Airtable"""
        order_data = self.airtable.get_order_status('Orders', order_id)
        
        if order_data:
            status = order_data.get('Order Status', 'Unknown')
            response = f"Your order {order_id} status is: {status}"
            return response, 'Resolved'
        else:
            response = "I couldn't find that order number. Let me escalate this to our support team for assistance. ESCALATE_VERA"
            return response, 'Escalated'
    
    def handle_query_delivery(self, message: str) -> tuple:
        """Handle Q6 - Delivery time query"""
        context_results = self.kb.query(message, n_results=3)
        context = "\n\n".join(context_results) if context_results else ""
        response = self.generate_response(message, context)
        return response, None
    
    def handle_returns_handoff(self, message: str) -> tuple:
        """Handle Q7 - Returns handoff"""
        response = "I can help you with your return. Please provide:\n1. Your name\n2. Order number\n3. Reason for return"
        return response, 'RETURNS_COLLECTING'
    
    def handle_returns_submission(self, customer_name: str, order_number: str, reason: str, email: str) -> tuple:
        """Submit return request to Make.com"""
        success = self.returns.submit_return_request(customer_name, order_number, reason, email)
        
        if success:
            response = "Your return request has been submitted. Our team will process it within 2 business days."
            return response, 'Resolved'
        else:
            response = "I'm having trouble submitting your return request. Let me escalate this to our support team. ESCALATE_VERA"
            return response, 'Escalated'
    
    def handle_escalation(self, message: str, transcript: str) -> tuple:
        """Handle escalation logic"""
        reference = self.escalation.generate_reference_number()
        self.escalation.send_escalation_email(transcript, reference, message)
        
        response = f"I have flagged your case to our support team. Reference: #{reference}. Someone will contact you within 24 hours."
        return response, 'Escalated'
    
    def process_message(self, message: str, conversation_state: dict = None) -> dict:
        """Main message processing function"""
        if conversation_state is None:
            conversation_state = {}
        
        intent = self.classify_intent(message)
        action = self.intents.get(intent, {}).get('action', 'escalate')
        
        response = ""
        new_state = conversation_state.copy()
        new_state['intent'] = intent
        
        # Handle conversation state flows
        if conversation_state.get('state') == 'QUIZ_COLLECTING':
            # Collect quiz answers
            if 'skin_concern' not in conversation_state:
                new_state['skin_concern'] = message
                response = "Thank you. And would you describe your skin as dry, oily, combination, or sensitive?"
                new_state['state'] = 'QUIZ_COLLECTING_TYPE'
            else:
                new_state['skin_type'] = message
                response, status = self.handle_quiz_submission(new_state['skin_concern'], new_state['skin_type'])
                new_state['state'] = status
                new_state['conversation_status'] = status
        
        elif conversation_state.get('state') == 'ORDER_COLLECTING':
            # Look up order
            response, status = self.handle_order_lookup(message)
            new_state['state'] = status
            new_state['conversation_status'] = status
            new_state['order_id'] = message
        
        elif conversation_state.get('state') == 'RETURNS_COLLECTING':
            # Collect return information
            if 'customer_name' not in conversation_state:
                new_state['customer_name'] = message
                response = "Thank you. What is your order number?"
                new_state['state'] = 'RETURNS_COLLECTING_ORDER'
            elif 'order_number' not in conversation_state:
                new_state['order_number'] = message
                response = "Got it. What is the reason for your return?"
                new_state['state'] = 'RETURNS_COLLECTING_REASON'
            elif 'reason' not in conversation_state:
                new_state['reason'] = message
                response = "Please provide your email address for the return."
                new_state['state'] = 'RETURNS_COLLECTING_EMAIL'
            else:
                new_state['email'] = message
                response, status = self.handle_returns_submission(
                    new_state['customer_name'],
                    new_state['order_number'],
                    new_state['reason'],
                    new_state['email']
                )
                new_state['state'] = status
                new_state['conversation_status'] = status
        
        else:
            # Normal intent handling
            if action == 'query_knowledge':
                response, status = self.handle_query_knowledge(message)
                new_state['conversation_status'] = 'Resolved'
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
            elif action == 'escalate' or intent == 'UNKNOWN':
                response, status = self.handle_escalation(message, conversation_state.get('transcript', ''))
                new_state['state'] = status
                new_state['conversation_status'] = status
        
        # Check for escalation keyword in response
        if 'ESCALATE_VERA' in response:
            response = response.replace('ESCALATE_VERA', '').strip()
            reference = self.escalation.generate_reference_number()
            transcript = conversation_state.get('transcript', '') + f"\nCustomer: {message}\nVera: {response}"
            self.escalation.send_escalation_email(transcript, reference, message)
            response = f"{response}\n\nI have flagged your case to our support team. Reference: #{reference}. Someone will contact you within 24 hours."
            new_state['conversation_status'] = 'ESCALATED'
            new_state['escalation_flag'] = True
        
        # Update transcript
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
