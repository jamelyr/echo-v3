
import asyncio
import wygiwyh_client
import sys

# Force the test to run in the same environment context
import os
os.environ["WYGIWYH_URL"] = "http://localhost:8000"

async def debug_wygiwyh():
    print("🔍 Debugging WYGIWYH Connectivity...")
    client = wygiwyh_client._wygiwyh_client
    
    # 1. Check Accounts
    print("1. Fetching Accounts...")
    accounts = await client.get_accounts()
    print(f"Result: {accounts}")
    
    # 2. Check Categories
    print("\n2. Fetching Categories...")
    categories = await client._request("GET", "/categories/")
    print(f"Result: {categories}")
    
    # 3. Try Create Category
    print("\n3. Testing Category Creation...")
    new_cat = await client._request("POST", "/categories/", json={"name": "DebugCategory"})
    print(f"Result: {new_cat}")

if __name__ == "__main__":
    asyncio.run(debug_wygiwyh())
