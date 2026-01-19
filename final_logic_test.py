import httpx
import asyncio

async def test_logic():
    print("🚀 Running Final Logic Verification (End-to-End)...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # --- TEST 1: NEWS ---
        print("\n[Test 1] News Integration")
        try:
            resp = await client.post("http://localhost:5001/send", data={"msg": "What is the news today?"}, cookies={"session_id": "final_test"})
            if resp.status_code == 200:
                content = resp.text
                print(f"Response Preview: {content[:150]}...")
                if "Lexpress" in content or "Defimedia" in content:
                    print("✅ PASS: News Proxy logic is working.")
                else:
                    print("❌ FAIL: News Proxy missing entries.")
            else:
                print(f"❌ Error: {resp.status_code}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")

        # --- TEST 2: TASK LIST ---
        print("\n[Test 2] Task Awareness (Semantic Router)")
        try:
            resp = await client.post("http://localhost:5001/send", data={"msg": "list all pending tasks"}, cookies={"session_id": "final_test"})
            if resp.status_code == 200:
                print("✅ PASS: Task list returned.")
                print(f"Response Preview: {resp.text[:100]}...")
            else:
                print(f"❌ Error: {resp.status_code}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")

        # --- TEST 3: CHAT ---
        print("\n[Test 3] Chat (Semantic Router Fallback)")
        try:
            resp = await client.post("http://localhost:5001/send", data={"msg": "Hello Echo!"}, cookies={"session_id": "final_test"})
            if resp.status_code == 200:
                print("✅ PASS: General chat is functional.")
                print(f"Response Preview: {resp.text[:100]}...")
            else:
                print(f"❌ Error: {resp.status_code}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_logic())
