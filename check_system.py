import httpx
import time

print("🔍 Testing Echo V3 System...")

try:
    # 1. Check MLX Server
    resp = httpx.get("http://127.0.0.1:1234/v1/models", timeout=5)
    if resp.status_code == 200:
        data = resp.json()["data"]
        print(f"✅ MLX Server Online")
        print(f"   - Chat Models Found: {len(data['chat'])}")
        print(f"   - Embed Models Found: {len(data['embed'])}")
        for m in data['chat']: print(f"     • {m['name']}")
        for m in data['embed']: print(f"     • {m['name']}")
    else:
        print(f"❌ MLX Server Error: {resp.status_code}")

    # 2. Check Web Server
    resp = httpx.get("http://127.0.0.1:5001/", timeout=5)
    if resp.status_code == 200:
        print("✅ Web Server Online")
    else:
        print(f"❌ Web Server Error: {resp.status_code}")

except Exception as e:
    print(f"❌ Connection Failed: {e}")
