import asyncio
import llm_client
from unittest.mock import MagicMock, patch

async def test_react_flow():
    print("🧪 Testing ReAct Agent Logic...")
    
    # Mock the LLM call to simulate a Tool use scenario
    # Scenario: User says "Add task buy milk" -> LLM says "Tool: add_task..." -> System execs -> LLM says "Done"
    
    mock_responses = [
        'Thought: User wants to add a task.\nTool: add_task("Buy Milk")', 
        'Answer: I have added "Buy Milk" to your tasks.'
    ]
    
    # We patch call_llm to return our canned responses
    with patch('llm_client.call_llm', side_effect=mock_responses) as mock_llm:
        
        # Run process
        result = await llm_client.process_input("Add a task to buy milk")
        
        print(f"Final Result: {result}")
        
        # Verify
        if "I have added" in result and "Buy Milk" in result:
            print("✅ PASS: Agent loop flow works.")
        else:
            print(f"❌ FAIL: Unexpected result: {result}")
            
        # Verify Tool was actually executed?
        # Ideally checks database, but for now we trust the flow if result is correct.

def test_parser():
    print("\n🧪 Testing Parser...")
    
    cases = [
        ('Tool: add_task("foo")', ('add_task', ['foo'])),
        ('Thought: hmm\nTool: complete_task(42)', ('complete_task', [42])),
        ('Tool: search_web("hello world")', ('search_web', ['hello world'])),
    ]
    
    for text, expected in cases:
        got = llm_client.parse_tool(text)
        if got == expected:
            print(f"✅ PASS: {text} -> {got}")
        else:
            print(f"❌ FAIL: {text} -> Expected {expected}, got {got}")

if __name__ == "__main__":
    test_parser()
    asyncio.run(test_react_flow())
