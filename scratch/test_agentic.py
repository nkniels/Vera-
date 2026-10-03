import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vera import get_vera

def run(label, messages):
    """Run a sequence of messages through Vera, printing each turn."""
    vera = get_vera()
    print(f"\n{'='*60}")
    print(f"  {label}")
    print('='*60)
    state = {}
    for msg in messages:
        res = vera.process_message(msg, state)
        state = res['state']
        print(f"  User : {repr(msg)}")
        print(f"  Vera : {res['response']}")
        print(f"  State: {state.get('state')} | Status: {state.get('conversation_status')}")
        print()

if __name__ == '__main__':
    # 1. Happy path: order ID embedded in first message
    run("Test 1: Order ID in initial message", [
        'where is my order TEST-ORD-001',
    ])

    # 2. Happy path: Vera prompts, user provides valid ID next turn
    run("Test 2: Order ID supplied on second turn", [
        'where is my order',
        'TEST-ORD-001',
    ])

    # 3. Invalid format on collecting turn, then valid format
    run("Test 3: Invalid format then valid order ID", [
        'where is my order',
        'ABC123',
        'VSC-9999',
    ])

    # 4. Cancellation escape hatch
    run("Test 4: Cancellation escape hatch", [
        'where is my order',
        'never mind',
    ])

    # 5. Empty / whitespace message guard
    run("Test 5: Empty message guard", [
        '',
        '   ',
    ])

    # 6. Valid format but unknown order ID
    run("Test 6: Valid format but unknown order", [
        'where is my order VSC-9999',
    ])

    # 7. Cancel then restart
    run("Test 7: Cancel then restart order query", [
        'where is my order',
        'cancel',
        'where is my order VSC-0001',
    ])
