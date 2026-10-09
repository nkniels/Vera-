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
                'action': 'product_catalogue'
            },
            'Q2': {
                'keywords': ['how much', 'price', 'cost', 'afford', 'expensive', 'cheap'],
                'action': 'query_knowledge'
            },
            'Q3': {
                'keywords': ['what should i use', 'skin type', 'recommend', 'suggest', 'best for my skin', 'what is good for', 'skin quiz', 'skincare quiz', 'take the quiz', 'quiz', 'quiz results'],
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
            },
            'HEALTH_SAFETY': {
                'keywords': [
                    'pregnant', 'pregnancy', 'breastfeeding', 'nursing',
                    'medical condition', 'allergic', 'allergy', 'safe to use',
                    'safe for', 'safe during', 'skin reaction', 'rash', 'irritation',
                    'safe for pregnancy', 'safe while', 'doctor', 'pharmacist',
                    'is it safe', 'can i use', 'suitable for pregnant'
                ],
                'action': 'health_safety'
            },
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

If a customer asks anything outside this scope, do NOT answer the question. Instead, politely let them know that you're Vera, Verdant Skin Co.'s customer support assistant, and that you can only help with topics related to Verdant Skin Co. — such as products, orders, shipping, returns, skincare advice, and brand information. Gently guide them back to how you can assist.

Only use ESCALATE_VERA in your response if the customer is genuinely angry, distressed, or has an issue that truly cannot be resolved with information alone.

Use the provided knowledge base context to answer questions accurately. If you don't know the answer from the context, say so honestly and offer to escalate if needed."""

    def classify_intent(self, message: str) -> str:
        """Classify customer message into one of the intents using keyword matching.
        
        Q10 (escalation) is checked first so angry/urgent messages are never
        accidentally caught by a lower-priority intent like GREETING.
        Short keywords (1-2 words) use whole-word matching to avoid false
        positives from substrings (e.g. 'hi' inside 'this').
        """
        import re
        message_lower = message.lower()

        # Priority order: Q10 first, HEALTH_SAFETY second (overrides order/returns flows),
        # then all others
        priority_order = ['Q10', 'HEALTH_SAFETY', 'Q7', 'Q5', 'Q3', 'Q6', 'Q8', 'Q9', 'Q1', 'Q2', 'Q4', 'GREETING', 'UNKNOWN']

        for intent in priority_order:
            config = self.intents.get(intent)
            if not config:
                continue
            for keyword in config['keywords']:
                # Use whole-word matching for short keywords to avoid substring hits
                if len(keyword.split()) <= 2:
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, message_lower):
                        return intent
                else:
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

    def handle_health_safety(self, message: str) -> tuple:
        """Handle health, safety, and pregnancy-related product questions.

        Does NOT make a safety determination.  Provides ingredient information
        from the knowledge base where relevant and directs the customer to a
        qualified healthcare professional.
        """
        msg_lower = message.lower()

        ingredient_note = ""
        if 'moringa' in msg_lower or 'glow serum' in msg_lower or 'serum' in msg_lower:
            ingredient_note = (
                "The Moringa Glow Serum contains Moringa Extract, "
                "which is antioxidant-rich and anti-inflammatory. "
            )
        elif 'shea' in msg_lower or 'balm' in msg_lower or 'repair' in msg_lower:
            ingredient_note = (
                "The Shea Gentle Repair Balm contains raw unrefined Shea Butter, "
                "used for deep moisturisation and barrier repair. "
            )
        elif 'cleanser' in msg_lower or 'black soap' in msg_lower:
            ingredient_note = (
                "The Black Soap Clarifying Cleanser contains traditional Ghanaian Black Soap. "
            )
        elif 'baobab' in msg_lower or 'moisture cream' in msg_lower or 'cream' in msg_lower:
            ingredient_note = (
                "The Baobab Deep Moisture Cream contains Baobab Oil, "
                "rich in vitamins A, D, E, and F. "
            )

        response = "Thank you for asking — your safety is what matters most. "
        if ingredient_note:
            response += ingredient_note
        response += (
            "All our products are 100% natural, plant-based, and free of parabens, sulphates, "
            "and artificial fragrances. However, I'm not able to make a safety determination for "
            "your specific situation. Please consult your healthcare professional, doctor, or "
            "pharmacist before use during pregnancy, breastfeeding, or if you have any medical "
            "conditions or skin sensitivities. Is there anything else I can help you with?"
        )
        return response, 'Resolved'

    def handle_product_catalogue(self, message: str) -> tuple:
        """Return a concise one-line-per-product catalogue."""
        response = (
            "Here's what we carry at Verdant Skin Co.:\n\n"
            "Black Soap Clarifying Cleanser — $15 — Best for oily or acne-prone skin\n"
            "Baobab Deep Moisture Cream — $25 — Best for dry or mature skin\n"
            "Moringa Glow Serum — $28 — Best for combination skin and dullness\n"
            "Shea Gentle Repair Balm — $20 — Best for sensitive or eczema-prone skin\n"
            "Full Routine Bundle (all 4) — $75 — Save 15%\n\n"
            "Want a personalised recommendation, more details on a product, or ingredient information? Just ask!"
        )
        return response, 'Resolved'

    def strip_markdown(self, text: str) -> str:
        """Convert common Markdown markers to plain text for the widget's textContent renderer."""
        import re
        if not text:
            return text
        # Remove bold/italic markers (**text**, *text*, __text__, _text_)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'__(.+?)__', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'\*(.+?)\*', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'_(.+?)_', r'\1', text, flags=re.DOTALL)
        # Remove heading markers (# at start of line)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Remove horizontal rules (lines of 3+ dashes, asterisks, or underscores)
        text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
        # Convert Markdown bullet markers to Unicode bullet character for readability
        text = re.sub(r'^[-*]\s+', '\u2022 ', text, flags=re.MULTILINE)
        # Collapse 3+ consecutive blank lines to 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def handle_out_of_scope(self, message: str) -> str:
        """Handle messages that fall outside Vera's scope."""
        responses = [
            "I appreciate your question! However, I'm Vera, Verdant Skin Co.'s customer support assistant, and I can only help with topics related to our brand — like products, orders, shipping, returns, and skincare advice. How can I assist you with any of those?",
            "That's a great question, but it's outside what I'm able to help with! I'm Vera, here to support you with anything related to Verdant Skin Co. — whether it's product info, order tracking, returns, or skincare recommendations. What can I help you with?",
            "I'm sorry, but that falls outside my area of expertise! I'm Vera from Verdant Skin Co., and I'm best equipped to help with our products, orders, shipping, returns, and skincare concerns. Is there anything along those lines I can assist you with?",
        ]
        return random.choice(responses)

    def _extract_email(self, text: str):
        """Extract email address from text if present, including plus-addressing."""
        import re
        match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
        return match.group(0) if match else None

    def handle_quiz_handoff(self, message: str) -> tuple:
        """Handle Q3 - Product matching: start Tally quiz flow or look up existing results."""
        email = self._extract_email(message)
        msg_lower = message.lower()

        # If user explicitly asks for existing quiz results and provided an email
        if email and any(w in msg_lower for w in ['result', 'done', 'finish', 'completed', 'already took', 'check']):
            return self.handle_quiz_results_lookup(email)

        if email:
            quiz_url = self.quiz.get_quiz_url(email)
            response = (
                f"I'd love to help you find the perfect routine for your skin! ✨\n\n"
                f"We have a personalized Skin Quiz that analyzes your skin needs and builds a custom routine with a prefilled cart just for you:\n"
                f"👉 {quiz_url}\n\n"
                f"Take a quick minute to complete it. Once you're done, simply reply **'done'** here and I'll pull up your recommendations and cart link!"
            )
            return response, 'QUIZ_WAITING_COMPLETION'

        response = (
            "I'd love to help you find the perfect skincare routine for your skin! ✨ "
            "We have a quick 1-minute Skin Quiz that creates a personalized routine and prefilled Shopify cart just for you.\n\n"
            "Could you please share your email address so I can get your quiz link ready?"
        )
        return response, 'QUIZ_COLLECTING_EMAIL'

    def handle_quiz_results_lookup(self, email: str) -> tuple:
        """Look up quiz recommendations in Airtable Leads table by email."""
        result = self.quiz.get_lead_recommendations(email)
        if result:
            lead_name = result.get('lead_name', '').strip()
            name_greeting = f" {lead_name}" if lead_name and not lead_name.startswith('TEST') else ""
            products_text = result.get('recommended_products', '').strip()
            cart_link = result.get('cart_link', '').strip()
            rationale = result.get('rationale', '').strip()

            response = f"I found your quiz results{name_greeting}! 🎉\n\n"
            if rationale:
                response += f"{rationale}\n\n"
            if products_text:
                response += "**Your Recommended Products:**\n"
                for line in products_text.split('\n'):
                    line = line.strip()
                    if line:
                        response += f"• {line}\n"
                response += "\n"
            if cart_link:
                response += (
                    f"🛒 **Your Prefilled Cart:**\n"
                    f"Your custom Shopify cart is ready to go:\n"
                    f"👉 {cart_link}\n\n"
                )
            response += "Is there anything else I can help you with today?"
            return response, 'Resolved'
        else:
            quiz_url = self.quiz.get_quiz_url(email)
            response = (
                f"I couldn't find a completed quiz submission for **{email}** in our system just yet! "
                f"It can take a few seconds to sync after submitting.\n\n"
                f"If you haven't taken it yet, here is your link:\n👉 {quiz_url}\n\n"
                f"Once you've clicked **Submit**, reply **'done'** here and I'll pull up your routine. "
                f"(Or reply with a different email if you used another one!)"
            )
            return response, 'QUIZ_WAITING_COMPLETION'

    def handle_quiz_submission(self, skin_concern: str, skin_type: str) -> tuple:
        """Fallback inline AI recommendation."""
        context_results = self.kb.query(f"products for {skin_type} skin {skin_concern}", n_results=3)
        context = "\n\n".join(context_results) if context_results else ""
        response = self.generate_response(
            f"Recommend Verdant Skin Co. products for a customer with {skin_type} skin whose main concern is {skin_concern}. Be specific and warm.",
            context
        )
        return response, 'Resolved'

    def _extract_order_id(self, text: str):
        """Extract a valid order ID from text, or None if no order ID is present."""
        import re
        text = text.strip()
        if not text:
            return None

        # 1. Match common prefixed dash order patterns, e.g. TEST-ORD-001, VSC-1234, FINAL-ORD-02
        pattern_dash = r'\b([A-Za-z]{2,}(?:-[A-Za-z0-9]+)+)\b'
        match = re.search(pattern_dash, text)
        if match:
            return match.group(1).upper()

        # 2. Match hashtag orders, e.g. #1002, #1003
        pattern_hash = r'(#\d+)'
        match = re.search(pattern_hash, text)
        if match:
            return match.group(1)

        # 3. Standalone or embedded alphanumeric token containing digits (e.g. 18926617756013, VSC1001)
        for token in text.split():
            clean_tok = token.strip('?.!,;:()[]{}"\'')
            if re.match(r'^[A-Za-z0-9#-]{3,}$', clean_tok) and any(c.isdigit() for c in clean_tok):
                return clean_tok.upper() if not clean_tok.startswith('#') else clean_tok

        return None

    def _is_privacy_preference(self, message: str) -> bool:
        """Return True if the user signals they don't want to share personal data."""
        import re
        msg = message.lower().strip()
        privacy_keywords = [
            "don't want to share", "dont want to share",
            "don't want to give", "dont want to give",
            "without sharing", "prefer not to share",
            "general question", "general policy",
            "just want to know", "just asking",
            "not comfortable sharing", "rather not share",
        ]
        for kw in privacy_keywords:
            if kw in msg:
                return True
        return False

    def _is_cancellation(self, message: str) -> bool:
        """Return True if the user wants to abandon the current flow."""
        import re
        cancel_keywords = ['cancel', 'never mind', 'nevermind', 'forget it',
                           'stop', 'quit', 'exit', 'abort', 'no thanks', 'nvm']
        msg = message.lower().strip()
        for kw in cancel_keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', msg):
                return True
        return False

    def handle_query_order(self, message: str) -> tuple:
        """Handle Q5 - Order status query dynamically."""
        order_id = self._extract_order_id(message)
        if order_id:
            return self.handle_order_lookup(order_id)

        response = (
            "I'd be happy to check on your order! Could you please share your order number? "
            "You'll find it in your confirmation email."
        )
        return response, 'ORDER_COLLECTING'

    def handle_order_lookup(self, order_id: str) -> tuple:
        """Look up order in Airtable."""

        if not self.airtable:
            return "I'm unable to look up orders right now. Please contact our support team at verdantskinco.ng@gmail.com.", 'Escalated'

        order_data = self.airtable.get_order_status('Orders', order_id)

        if order_data:
            status = order_data.get('fields', {}).get('Order Status', 'Unknown')
            response = f"Your order {order_id} status is: **{status}**. Is there anything else I can help you with?"
            return response, 'Resolved'
        else:
            # Order ID is syntactically valid but not in the CRM — escalate
            transcript = f"Customer was checking status for order {order_id} but it was not found in Airtable."
            escalation_response, _ = self.handle_escalation(f"Order {order_id} not found.", transcript)
            # Use handle_escalation's return value — it already gates success/failure wording correctly
            response = (
                f"I couldn't find order {order_id} in our system. "
                f"{escalation_response}"
            )
            return response, 'Escalated'

    def handle_query_delivery(self, message: str) -> tuple:
        """Handle Q6 - Delivery time query."""
        context_results = self.kb.query(message, n_results=3)
        context = "\n\n".join(context_results) if context_results else ""
        response = self.generate_response(message, context)
        return response, 'Resolved'

    def handle_returns_handoff(self, message: str) -> tuple:
        """Handle Q7 — return/refund intent.

        Distinguish policy queries (answer from KB) from start-a-return requests
        (collect details).  Only enter RETURNS_COLLECTING when the user signals
        they actually want to start a return.
        """
        msg_lower = message.lower()

        # Signals that the user wants to START a return (not just ask about policy)
        start_return_keywords = [
            'i want to return', 'i need to return', 'start a return',
            'process a return', 'wrong item', 'damaged item', 'sent wrong',
            'i received the wrong', 'item is damaged', 'want a refund',
            'need a refund', 'request a refund',
        ]
        wants_to_start = any(kw in msg_lower for kw in start_return_keywords)

        if wants_to_start:
            response = (
                "I can help you with your return. Please provide the following details:\n"
                "1. Your full name\n"
                "2. Your order number\n"
                "3. The reason for the return"
            )
            return response, 'RETURNS_COLLECTING'

        # General return policy question — answer from knowledge base
        policy_response = (
            "Our return and exchange policy:\n\n"
            "14-day window: You can return or exchange any item within 14 days of delivery.\n\n"
            "Condition: Items must be unused, or defective/damaged upon arrival. "
            "We are unable to accept returns for a change of mind if the product has been opened.\n\n"
            "Exclusions: Opened products that show signs of use do not qualify.\n\n"
            "Process: Contact us with your order number and reason. "
            "Our team will review and get back to you within 24 hours.\n\n"
            "Would you like to start a return? I can walk you through the process."
        )
        return policy_response, 'Resolved'

    def handle_returns_submission(self, customer_name: str, order_number: str, reason: str, email: str,
                                  item_unused: bool = True, packaging_available: bool = True) -> tuple:
        """Submit return request."""
        if not self.returns:
            response = "I've noted your return request. Please email verdantskinco.ng@gmail.com with your order number and reason, and our team will process it within 2 business days."
            return response, 'Resolved'

        success = self.returns.submit_return_request(
            customer_name, order_number, reason, email,
            item_unused=item_unused, packaging_available=packaging_available
        )

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
            response = f"I've flagged your case to our support team. Reference: #{reference}. Someone will contact you within 24 hours."
        else:
            response = "I'm having trouble reaching our support system right now. Please email us directly at verdantskinco.ng@gmail.com and we'll get back to you within 24 hours."

        return response, 'Escalated'

    def classify_return_reason(self, message: str) -> str:
        """Categorize return reason into exactly one of the Airtable Single Select options."""
        valid_options = ["Wrong item received", "Changed my mind", "Damaged item"]
        if not self.gemini_available:
            return "Damaged item" # Default fallback
            
        prompt = f"Categorize the following customer return reason into EXACTLY ONE of these three options: {', '.join(valid_options)}. Reply with ONLY the exact text of the option, nothing else.\n\nCustomer reason: {message}"
        
        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1,
                )
            )
            text = response.text.strip()
            for valid_option in valid_options:
                if valid_option.lower() in text.lower():
                    return valid_option
            return "Damaged item" # Default fallback if weird response
        except Exception as e:
            print(f"Error classifying reason: {e}")
            return "Damaged item"

    def classify_item_condition(self, message: str) -> tuple:
        """
        Classify whether the customer's return item is unused and if original packaging is available.
        Returns (item_unused: bool, packaging_available: bool).
        """
        if not self.gemini_available:
            return self._fallback_item_condition(message)

        prompt = (
            "A customer was asked two questions about an item they want to return:\n"
            "1. Is the item unused?\n"
            "2. Do you still have the original packaging?\n\n"
            f"Customer response: \"{message}\"\n\n"
            "Determine the boolean answer for each question.\n"
            "Respond ONLY with a JSON object in this exact format, with no extra text or markdown:\n"
            '{"item_unused": true, "packaging_available": true}'
        )

        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1,
                )
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:].strip()
            import json
            data = json.loads(text)
            item_unused = bool(data.get("item_unused", True))
            packaging_available = bool(data.get("packaging_available", True))
            return item_unused, packaging_available
        except Exception as e:
            print(f"Error classifying item condition with AI: {e}")
            return self._fallback_item_condition(message)

    def _fallback_item_condition(self, message: str) -> tuple:
        """Rule-based parsing fallback for item condition."""
        msg = message.lower().strip()

        if any(neg in msg for neg in ["neither", "no to both", "both no", "none", "not unused and no", "no and no"]):
            return False, False

        if any(aff in msg for aff in ["yes to both", "both yes", "both", "yes", "yeah", "yep", "sure", "correct"]) and "no" not in msg and "not" not in msg:
            return True, True

        item_unused = True
        packaging_available = True

        if "used" in msg and "unused" not in msg:
            item_unused = False
        if "opened" in msg and "unopened" not in msg:
            item_unused = False
        if "1. no" in msg or "1: no" in msg or "no to 1" in msg or "no to the first" in msg:
            item_unused = False

        if "no packaging" in msg or "lost the packaging" in msg or "threw" in msg or "discarded" in msg or "no box" in msg:
            packaging_available = False
        if "2. no" in msg or "2: no" in msg or "no to 2" in msg or "no to the second" in msg:
            packaging_available = False

        if msg == "no":
            return False, False

        return item_unused, packaging_available

    def _dispatch_intent(self, intent: str, action: str, message: str,
                         new_state: dict, conversation_state: dict) -> tuple:
        """Route a (intent, action) pair to the appropriate handler.

        Extracted so that topic-change exit paths inside collecting-state blocks
        can reach normal routing without duplicating the full elif chain.
        Returns (response_str, updated_new_state_dict).
        """
        if action == 'greeting':
            response, status = self.handle_greeting(message)
            new_state['conversation_status'] = status

        elif action == 'health_safety':
            response, status = self.handle_health_safety(message)
            new_state.pop('state', None)
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
            new_state['conversation_status'] = 'Pending' if status != 'Resolved' else 'Resolved'

        elif action == 'escalate':
            response, status = self.handle_escalation(message, conversation_state.get('transcript', ''))
            new_state['state'] = status
            new_state['conversation_status'] = status

        elif action == 'product_catalogue':
            response, status = self.handle_product_catalogue(message)
            new_state['conversation_status'] = status

        elif action == 'query_knowledge':
            response, status = self.handle_query_knowledge(message)
            new_state['conversation_status'] = 'Resolved'

        else:
            # UNKNOWN intent — out of scope
            response = self.handle_out_of_scope(message)
            new_state['conversation_status'] = 'Resolved'

        return response, new_state

    def process_message(self, message: str, conversation_state: dict = None) -> dict:
        """Main message processing function."""
        if conversation_state is None:
            conversation_state = {}

        # Guard: ignore empty or whitespace-only messages
        if not message or not message.strip():
            return {
                'response': "I didn't catch that — could you please type your message?",
                'intent': 'UNKNOWN',
                'state': conversation_state,
            }

        intent = self.classify_intent(message)
        action = self.intents.get(intent, {}).get('action', 'query_knowledge')

        response = ""
        new_state = conversation_state.copy()
        new_state['intent'] = intent

        # Handle active multi-step conversation flows
        current_state = conversation_state.get('state')

        # Universal escape hatch — lets the user bail out of any multi-step flow
        COLLECTING_STATES = {
            'QUIZ_COLLECTING_EMAIL', 'QUIZ_WAITING_COMPLETION',
            'ORDER_COLLECTING',
            'RETURNS_COLLECTING', 'RETURNS_COLLECTING_ORDER',
            'RETURNS_COLLECTING_REASON', 'RETURNS_COLLECTING_EMAIL',
            'RETURNS_COLLECTING_CONDITION',
        }
        # Sets used for topic-change detection
        RETURNS_STATES = {
            'RETURNS_COLLECTING', 'RETURNS_COLLECTING_ORDER',
            'RETURNS_COLLECTING_REASON', 'RETURNS_COLLECTING_EMAIL',
            'RETURNS_COLLECTING_CONDITION',
        }
        # Intents that should always break out of a collecting flow.
        # Q3 (quiz/recommendation) and Q7 (returns) are included so that a user
        # in ORDER_COLLECTING who says "I want to return something" exits the
        # order flow, and a user who says "take the quiz" also exits cleanly.
        NON_CONTINUATION_INTENTS = {
            'GREETING', 'Q1', 'Q2', 'Q3', 'Q4', 'Q6', 'Q7', 'Q8', 'Q9',
            'Q10', 'HEALTH_SAFETY',
        }

        if current_state in COLLECTING_STATES and self._is_cancellation(message):
            new_state.pop('state', None)
            new_state['conversation_status'] = 'Resolved'
            new_state['transcript'] = conversation_state.get('transcript', '') + f"\nCustomer: {message}\nVera: No problem! Is there anything else I can help you with?"
            return {
                'response': "No problem! Is there anything else I can help you with?",
                'intent': intent,
                'state': new_state,
            }

        # HEALTH_SAFETY always overrides any pending collecting state
        if current_state in COLLECTING_STATES and intent == 'HEALTH_SAFETY':
            new_state.pop('state', None)
            response, status = self.handle_health_safety(message)
            new_state['conversation_status'] = status
            new_state['transcript'] = conversation_state.get('transcript', '') + f"\nCustomer: {message}\nVera: {response}"
            return {
                'response': self.strip_markdown(response),
                'intent': intent,
                'state': new_state,
            }

        if current_state == 'QUIZ_COLLECTING_EMAIL':
            extracted_email = self._extract_email(message) or (message.strip() if '@' in message else None)
            if extracted_email:
                new_state['quiz_email'] = extracted_email
                new_state['email'] = extracted_email
                quiz_url = self.quiz.get_quiz_url(extracted_email)
                response = (
                    f"Thank you! Here is your personalized skin quiz link:\n"
                    f"👉 {quiz_url}\n\n"
                    f"It takes just a minute to complete. Once you submit the quiz, reply 'done' here and I'll retrieve your custom routine and prefilled cart right away!"
                )
                new_state['state'] = 'QUIZ_WAITING_COMPLETION'
                new_state['conversation_status'] = 'Pending'
            else:
                response = "Please provide a valid email address so I can generate your personalized quiz link and look up your results."
                new_state['state'] = 'QUIZ_COLLECTING_EMAIL'
                new_state['conversation_status'] = 'Pending'

        elif current_state == 'QUIZ_WAITING_COMPLETION':
            extracted_email = self._extract_email(message)
            if extracted_email:
                new_state['quiz_email'] = extracted_email
                new_state['email'] = extracted_email
                email = extracted_email
            else:
                email = conversation_state.get('quiz_email') or conversation_state.get('email', '')

            if email:
                response, status = self.handle_quiz_results_lookup(email)
                new_state['state'] = status
                new_state['conversation_status'] = status
            else:
                response = "Could you please tell me the email address you used for the quiz so I can look up your results?"
                new_state['state'] = 'QUIZ_COLLECTING_EMAIL'
                new_state['conversation_status'] = 'Pending'

        elif current_state == 'ORDER_COLLECTING':
            # Topic-change guard: if user clearly changed topic, exit and handle new intent
            if intent in NON_CONTINUATION_INTENTS:
                new_state.pop('state', None)
                new_state['conversation_status'] = 'Resolved'
                response, new_state = self._dispatch_intent(intent, action, message, new_state, conversation_state)
            else:
                # Stay in order-collecting flow — try to extract a valid order ID
                order_id = self._extract_order_id(message)
                if order_id:
                    response, status = self.handle_order_lookup(order_id)
                    new_state['state'] = status
                    new_state['conversation_status'] = status
                    new_state['order_id'] = order_id
                else:
                    response = (
                        "I wasn't able to spot an order number in that message. "
                        "Your order number is in your confirmation email — it usually looks like "
                        "a short code or number. Could you paste it here?"
                    )
                    new_state['state'] = 'ORDER_COLLECTING'
                    new_state['conversation_status'] = 'Pending'

        elif current_state == 'RETURNS_COLLECTING':
            # Privacy preference: user doesn't want to share personal data
            if self._is_privacy_preference(message):
                new_state.pop('state', None)
                response, _ = self.handle_returns_handoff('return policy')
                new_state['conversation_status'] = 'Resolved'
            # Topic-change guard: user switched to a different topic
            elif intent in NON_CONTINUATION_INTENTS:
                new_state.pop('state', None)
                response, new_state = self._dispatch_intent(intent, action, message, new_state, conversation_state)
            else:
                new_state['customer_name'] = message
                response = "Thank you! What is your order number?"
                new_state['state'] = 'RETURNS_COLLECTING_ORDER'

        elif current_state == 'RETURNS_COLLECTING_ORDER':
            # Topic-change / privacy guard
            if self._is_privacy_preference(message):
                new_state.pop('state', None)
                response, _ = self.handle_returns_handoff('return policy')
                new_state['conversation_status'] = 'Resolved'
            elif intent in NON_CONTINUATION_INTENTS:
                new_state.pop('state', None)
                response, new_state = self._dispatch_intent(intent, action, message, new_state, conversation_state)
            else:
                new_state['order_number'] = message
                response = "Got it. What is the reason for your return?"
                new_state['state'] = 'RETURNS_COLLECTING_REASON'

        elif current_state == 'RETURNS_COLLECTING_REASON':
            # Privacy preference: user doesn't want to share reason
            if self._is_privacy_preference(message):
                new_state.pop('state', None)
                response, _ = self.handle_returns_handoff('return policy')
                new_state['conversation_status'] = 'Resolved'
            # Topic-change guard
            elif intent in NON_CONTINUATION_INTENTS:
                new_state.pop('state', None)
                response, new_state = self._dispatch_intent(intent, action, message, new_state, conversation_state)
            else:
                new_state['reason'] = self.classify_return_reason(message)
                response = "Almost done! Please provide your email address so we can keep you updated."
                new_state['state'] = 'RETURNS_COLLECTING_EMAIL'

        elif current_state == 'RETURNS_COLLECTING_EMAIL':
            # Privacy / topic-change guard
            if self._is_privacy_preference(message):
                new_state.pop('state', None)
                response, _ = self.handle_returns_handoff('return policy')
                new_state['conversation_status'] = 'Resolved'
            elif intent in NON_CONTINUATION_INTENTS:
                new_state.pop('state', None)
                response, new_state = self._dispatch_intent(intent, action, message, new_state, conversation_state)
            else:
                new_state['email'] = message
                response = (
                    "Almost done! Just two quick questions to confirm your return:\n"
                    "1. Is the item unused?\n"
                    "2. Do you still have the original packaging?"
                )
                new_state['state'] = 'RETURNS_COLLECTING_CONDITION'

        elif current_state == 'RETURNS_COLLECTING_CONDITION':
            # Privacy preference or topic-change guard
            if self._is_privacy_preference(message):
                new_state.pop('state', None)
                response, _ = self.handle_returns_handoff('return policy')
                new_state['conversation_status'] = 'Resolved'
            elif intent in NON_CONTINUATION_INTENTS:
                new_state.pop('state', None)
                response, new_state = self._dispatch_intent(intent, action, message, new_state, conversation_state)
            else:
                item_unused, packaging_available = self.classify_item_condition(message)
                new_state['item_unused'] = item_unused
                new_state['packaging_available'] = packaging_available
                response, status = self.handle_returns_submission(
                    conversation_state.get('customer_name', ''),
                    conversation_state.get('order_number', ''),
                    conversation_state.get('reason', ''),
                    conversation_state.get('email', ''),
                    item_unused=item_unused,
                    packaging_available=packaging_available
                )
                new_state['state'] = status
                new_state['conversation_status'] = status

        else:
            # Normal intent routing (no active multi-step flow)
            response, new_state = self._dispatch_intent(intent, action, message, new_state, conversation_state)

        # Check for escalation keyword injected by LLM in its response
        if 'ESCALATE_VERA' in response:
            response = response.replace('ESCALATE_VERA', '').strip()
            if self.escalation_available:
                reference = self.escalation.generate_reference_number()
                transcript = conversation_state.get('transcript', '') + f"\nCustomer: {message}\nVera: {response}"
                success = self.escalation.send_escalation_email(transcript, reference, message)
                if success:
                    response += f"\n\nI've flagged your case to our support team. Reference: #{reference}. Someone will contact you within 24 hours."
                else:
                    response += "\n\nPlease contact our support team directly at verdantskinco.ng@gmail.com."
            else:
                response += "\n\nPlease contact our support team directly at verdantskinco.ng@gmail.com."
            new_state['conversation_status'] = 'Escalated'
            new_state['escalation_flag'] = True

        # Update running transcript for escalation context
        new_state['transcript'] = conversation_state.get('transcript', '') + f"\nCustomer: {message}\nVera: {response}"

        return {
            'response': self.strip_markdown(response),
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
