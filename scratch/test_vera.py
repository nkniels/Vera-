import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vera import get_vera

def test():
    vera = get_vera()
    print('Testing order status query for TEST-ORD-001')
    
    state = {}
    print('\nUser: where is my order')
    result1 = vera.process_message('where is my order', state)
    print(f'Vera: {result1["response"]}')
    
    state = result1['state']
    
    print('\nUser: TEST-ORD-001')
    result2 = vera.process_message('TEST-ORD-001', state)
    print(f'Vera: {result2["response"]}')
    
    print('\nState after order status:')
    print(result2['state'])

    # Let's also try sending a message using the FastAPI app to see if customer integration works
    from fastapi.testclient import TestClient
    from main import app
    
    print("\n\nTesting FastAPI /chat endpoint with Customer and Order IDs")
    client = TestClient(app)
    
    # In Airtable, linked records usually require the actual record ID (e.g., rec123456789), 
    # but the prompt says "use the existing TEST Customer - Integration and TEST-ORD-001 records".
    # I'll pass them as they are and let's see how Airtable reacts.
    payload = {
        "message": "where is my order TEST-ORD-001",
        "customer_id": "TEST Customer - Integration",
        "order_id": "TEST-ORD-001"
    }
    
    response = client.post("/chat", json=payload)
    print(response.json())

if __name__ == '__main__':
    test()
