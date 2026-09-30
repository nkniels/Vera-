# Vera Chatbot - Verdant Skin Co.

AI-powered customer support chatbot for Verdant Skin Co., built with Python, FastAPI, Groq API, ChromaDB, and Airtable.

## Features

- **Intent Classification**: Handles 10 defined customer intents (product catalogue, pricing, returns, order status, etc.)
- **RAG Knowledge Base**: ChromaDB-powered retrieval for accurate product and policy information
- **CRM Integration**: Writes conversations to Airtable for tracking and analysis
- **Returns Handoff**: Integrates with Make.com webhook for return processing
- **Quiz Agent Handoff**: Collaborates with Intern 6's Quiz Agent for product recommendations
- **Escalation System**: Gmail SMTP integration for human support escalation
- **Multi-Channel Support**: Shopify widget, WhatsApp, and Instagram DM endpoints
- **Real-time Chat**: Floating chat widget for Shopify stores

## Tech Stack

- **Backend**: Python + FastAPI
- **AI Engine**: Groq API (Llama 3.1)
- **Knowledge Base**: ChromaDB
- **CRM**: Airtable (pyairtable)
- **Email**: Gmail SMTP
- **Deployment**: Render.com

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd vera-chatbot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. Run locally:
```bash
python main.py
```

## Environment Variables

Required environment variables in `.env`:

- `GROQ_API_KEY`: Your Groq API key
- `AIRTABLE_PAT`: Your Airtable Personal Access Token (PAT)
- `AIRTABLE_BASE_ID`: Your Airtable Base ID
- `GMAIL_ADDRESS`: Gmail address for escalation emails
- `GMAIL_APP_PASSWORD`: Gmail app password for SMTP
- `SUPPORT_EMAIL`: Support team email address
- `MAKE_WEBHOOK_URL`: Make.com webhook URL for returns (placeholder)
- `QUIZ_ENDPOINT`: Quiz Agent endpoint URL (placeholder)

## API Endpoints

- `POST /chat` - Main chat endpoint for Shopify widget
- `POST /whatsapp` - WhatsApp Cloud API webhook
- `POST /instagram` - Instagram Graph API webhook
- `GET /health` - Health check for UptimeRobot
- `GET /widget.js` - Shopify embed script

## Shopify Integration

Add this script tag to your Shopify theme.liquid before `</body>`:

```html
<script src="https://your-render-url.onrender.com/widget.js"></script>
```

## Deployment

### Render.com

1. Connect your GitHub repository to Render.com
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables in Render's Environment tab
5. Deploy

### Keep Server Alive

Use UptimeRobot to ping the `/health` endpoint every 10 minutes to prevent Render free tier from sleeping.

## Project Structure

```
vera-chatbot/
├── main.py                  # FastAPI app entry point
├── vera.py                  # Core chatbot logic
├── knowledge_base.py        # ChromaDB RAG setup
├── integrations/
│   ├── airtable.py          # CRM read/write
│   ├── escalation.py        # Gmail SMTP escalation
│   ├── returns.py           # Make.com webhook handoff
│   └── quiz.py              # Quiz Agent handoff
├── knowledge/
│   └── vera_knowledge.md    # Knowledge base content
├── widget/
│   └── widget.js            # Shopify embed script
├── requirements.txt         # Dependencies
├── .env                     # Environment variables (not in git)
└── .gitignore               # Git ignore rules
```

## Intent Classification

Vera classifies messages into these intents:

- **Q1**: Product catalogue queries
- **Q2**: Pricing inquiries
- **Q3**: Product matching (triggers Quiz Agent)
- **Q4**: Ingredients/natural product questions
- **Q5**: Order status queries
- **Q6**: Delivery time inquiries
- **Q7**: Returns/Refunds (writes to Returns & Refunds table + Make.com webhook)
- **Q8**: Shipping destination questions
- **Q9**: Shipping time questions
- **Q10**: Complaints/anger (triggers escalation)

## Airtable Schema

The bot integrates with the following Airtable tables:

- **Vera Chatbot**: Logs all conversations with intent, status, and escalation flags
- **Orders**: Query order status by Order ID
- **Customers**: Link customer records to conversations
- **Leads**: Link lead records to conversations
- **Returns & Refunds**: Auto-approve return requests with status "Auto Approved"
- **Products**: Track product recommendations

## License

This project is part of the Afriment AI Automation Internship — Cohort 22.

## Credits

- **Author**: Nkouonlack Niels — Intern 5, AI Chatbot Lead
- **Client**: Verdant Skin Co., Accra, Ghana
- **Version**: 1.0 — Week 3 Build
