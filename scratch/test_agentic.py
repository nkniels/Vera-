import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vera import get_vera

def test():
    vera = get_vera()
    print("--- Test 1: Order ID in initial message ---")
    state = {}
    res = vera.process_message('where is my order TEST-ORD-001', state)
    print(f"Vera: {res['response']}")
    
    print("\n--- Test 2: Invalid/Unknown Order ID ---")
    state = {}
    res = vera.process_message('where is my order VSC-9999', state)
    print(f"Vera: {res['response']}")

if __name__ == '__main__':
    test()
