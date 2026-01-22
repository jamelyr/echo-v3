
import asyncio
import llm_client
import sys

# Force the test to run in the same environment context
import os
os.environ["WYGIWYH_URL"] = "http://localhost:8000"

async def test_finance():
    print("🧪 Testing One-Shot Finance Reflex...")
    
    # Test 1: Expense
    query = "Spent 420 rs on lunch at Bagatelle"
    print(f"\n👤 User: '{query}'")
    print("⏳ Processing...")
    
    start_time = asyncio.get_event_loop().time()
    response = await llm_client.process_input(query)
    end_time = asyncio.get_event_loop().time()
    
    print(f"🤖 Echo: {response}")
    print(f"⚡ Time taken: {end_time - start_time:.2f}s")
    
    # Test 2: Income
    query_2 = "Received 2500 for freelance work"
    print(f"\n👤 User: '{query_2}'")
    print("⏳ Processing...")
    
    start_time = asyncio.get_event_loop().time()
    response_2 = await llm_client.process_input(query_2)
    end_time = asyncio.get_event_loop().time()
    
    print(f"🤖 Echo: {response_2}")
    print(f"⚡ Time taken: {end_time - start_time:.2f}s")

if __name__ == "__main__":
    try:
        asyncio.run(test_finance())
    except KeyboardInterrupt:
        pass
