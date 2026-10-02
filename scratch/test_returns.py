
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vera import get_vera
from integrations.returns import get_returns_service

def test():
    print('Testing returns handoff...')
    returns_service = get_returns_service()
    
    # Submitting a dummy return request to see what happens
    result = returns_service.submit_return_request(
        customer_name='TEST Customer - Return',
        order_number='TEST-ORD-001',
        reason='Item arrived damaged',
        email='testcustomer@example.com'
    )
    print(f'Test completed. Result: {result}')

if __name__ == '__main__':
    test()
