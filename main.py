from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from vera import get_vera
from integrations.airtable import get_airtable

app = FastAPI(title="Vera Chatbot - Verdant Skin Co.")

# Conversation state storage (in production, use Redis or database)
conversation_states: Dict[str, Dict] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    channel: Optional[str] = "Shopify"
    customer_id: Optional[str] = None
    order_id: Optional[str] = None
    lead_id: Optional[str] = None

class WhatsAppMessage(BaseModel):
    from_: str
    message: str
    metadata: Optional[Dict[str, Any]] = {}

class InstagramMessage(BaseModel):
    from_: str
    message: str
    metadata: Optional[Dict[str, Any]] = {}

@app.get("/health")
async def health_check():
    """Health check endpoint for UptimeRobot"""
    return {"status": "healthy", "service": "Vera Chatbot"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint for Shopify widget and direct API calls"""
    try:
        vera = get_vera()
        airtable = get_airtable()
        
        # Get or create conversation state
        session_id = request.session_id or str(hash(request.message))
        state = conversation_states.get(session_id, {})
        
        # Process message
        result = vera.process_message(request.message, state)
        
        # Update conversation state
        conversation_states[session_id] = result['state']
        
        # Write to Airtable - match exact field names from schema
        airtable_data = {
            "Channel": request.channel,
            "Customer Message": request.message,
            "Vera Response (AI Draft)": result['response'],
            "Intent / Query Type": result['intent'],
            "Conversation Status": result['state'].get('conversation_status', 'Pending'),
            "Escalation Flag": result['state'].get('escalation_flag', False),
            "Escalation Transcript": result['state'].get('transcript', '') if result['state'].get('escalation_flag') else ""
        }
        
        # Link to Customer if customer_id provided
        if request.customer_id:
            airtable_data["Customer"] = [request.customer_id]
        
        # Link to Order if order_id provided
        if request.order_id:
            airtable_data["Order"] = [request.order_id]
        
        # Link to Lead if lead_id provided
        if request.lead_id:
            airtable_data["Lead"] = [request.lead_id]
        
        airtable.write_conversation("Vera Chatbot", airtable_data)
        
        return {
            "response": result['response'],
            "intent": result['intent'],
            "session_id": session_id,
            "conversation_status": result['state'].get('conversation_status', 'IN_PROGRESS')
        }
    except Exception as e:
        print(f"Error in /chat: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """WhatsApp Cloud API webhook endpoint"""
    try:
        data = await request.json()
        
        # Extract message from WhatsApp webhook format
        # Format varies based on WhatsApp Cloud API structure
        message = ""
        from_number = ""
        
        if 'entry' in data and len(data['entry']) > 0:
            entry = data['entry'][0]
            if 'changes' in entry and len(entry['changes']) > 0:
                change = entry['changes'][0]
                if 'value' in change and 'messages' in change['value']:
                    msg = change['value']['messages'][0]
                    from_number = msg['from']
                    message = msg['text']['body']
        
        if not message:
            return {"status": "no message"}
        
        vera = get_vera()
        airtable = get_airtable()
        
        # Get conversation state
        state = conversation_states.get(from_number, {})
        
        # Process message
        result = vera.process_message(message, state)
        
        # Update conversation state
        conversation_states[from_number] = result['state']
        
        # Write to Airtable - match exact field names from schema
        airtable_data = {
            "Channel": "WhatsApp",
            "Customer Message": message,
            "Vera Response (AI Draft)": result['response'],
            "Intent / Query Type": result['intent'],
            "Conversation Status": result['state'].get('conversation_status', 'Pending'),
            "Escalation Flag": result['state'].get('escalation_flag', False),
            "Escalation Transcript": result['state'].get('transcript', '') if result['state'].get('escalation_flag') else ""
        }
        
        airtable.write_conversation("Vera Chatbot", airtable_data)
        
        # In production, you would send the response back via WhatsApp API
        # For now, return the response
        return {
            "status": "processed",
            "response": result['response'],
            "to": from_number
        }
    except Exception as e:
        print(f"Error in /whatsapp: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/instagram")
async def instagram_webhook(request: Request):
    """Instagram Graph API webhook endpoint"""
    try:
        data = await request.json()
        
        # Extract message from Instagram webhook format
        message = ""
        from_user = ""
        
        if 'entry' in data and len(data['entry']) > 0:
            entry = data['entry'][0]
            if 'messaging' in entry:
                messaging = entry['messaging'][0]
                from_user = messaging['sender']['id']
                if 'message' in messaging:
                    message = messaging['message'].get('text', '')
        
        if not message:
            return {"status": "no message"}
        
        vera = get_vera()
        airtable = get_airtable()
        
        # Get conversation state
        state = conversation_states.get(from_user, {})
        
        # Process message
        result = vera.process_message(message, state)
        
        # Update conversation state
        conversation_states[from_user] = result['state']
        
        # Write to Airtable - match exact field names from schema
        airtable_data = {
            "Channel": "Instagram DM",
            "Customer Message": message,
            "Vera Response (AI Draft)": result['response'],
            "Intent / Query Type": result['intent'],
            "Conversation Status": result['state'].get('conversation_status', 'Pending'),
            "Escalation Flag": result['state'].get('escalation_flag', False),
            "Escalation Transcript": result['state'].get('transcript', '') if result['state'].get('escalation_flag') else ""
        }
        
        airtable.write_conversation("Vera Chatbot", airtable_data)
        
        # In production, you would send the response back via Instagram API
        # For now, return the response
        return {
            "status": "processed",
            "response": result['response'],
            "to": from_user
        }
    except Exception as e:
        print(f"Error in /instagram: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/widget.js")
async def get_widget():
    """Serve the Shopify embed script"""
    widget_path = os.path.join(os.path.dirname(__file__), "widget", "widget.js")
    if os.path.exists(widget_path):
        return FileResponse(widget_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="Widget not found")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Vera Chatbot",
        "version": "1.0",
        "description": "AI-powered customer support for Verdant Skin Co."
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
