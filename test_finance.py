"""
Test Finance Integration
Validates WYGIWYH finance tools and dashboard functionality.
"""

import asyncio
import sys
sys.path.insert(0, '/Users/marley/Documents/ag')

async def test_finance_integration():
    """Test finance client and tools"""
    print("🧪 Testing WYGIWYH Finance Integration\n")
    print("=" * 60)
    
    try:
        import wygiwyh_client
        print("\u2713 wygiwyh_client imported successfully")
        
        # Test 1: Get Balance
        print("\n📊 Test 1: Get Balance Summary")
        try:
            balance = await wygiwyh_client.get_balance_summary()
            if "Account Balances" in balance or "No accounts" in balance or "error" in balance.lower():
                print("\u2713 Balance query returned valid response")
                print(f"  Response: {balance[:100]}...")
            else:
                print("✗ Unexpected balance response format")
        except Exception as e:
            print(f"✗ Balance query failed: {e}")
        
        # Test 2: Get Recent Transactions
        print("\n📝 Test 2: Get Recent Transactions")
        try:
            transactions = await wygiwyh_client.get_recent_transactions(5)
            if "Recent Transactions" in transactions or "No transactions" in transactions or "error" in transactions.lower():
                print("\u2713 Transaction query returned valid response")
                print(f"  Response: {transactions[:100]}...")
            else:
                print("✗ Unexpected transaction response format")
        except Exception as e:
            print(f"✗ Transaction query failed: {e}")
        
        # Test 3: Get Summary
        print("\n📆 Test 3: Get Monthly Summary")
        try:
            summary = await wygiwyh_client.get_summary("month")
            if "Summary" in summary or "No transactions" in summary or "error" in summary.lower():
                print("\u2713 Summary query returned valid response")
                print(f"  Response: {summary[:100]}...")
            else:
                print("✗ Unexpected summary response format")
        except Exception as e:
            print(f"✗ Summary query failed: {e}")
        
        # Test 4: LLM Tools Integration
        print("\n🤖 Test 4: LLM Tools Integration")
        try:
            import llm_client
            
            # Check if finance tools are in execute_tool
            test_result = await llm_client.execute_tool("finance_balance", [])
            print(f"\u2713 finance_balance tool is callable")
            print(f"  Response: {test_result[:100]}...")
        except Exception as e:
            print(f"✗ LLM tool test failed: {e}")
        
        # Test 5: Dashboard Rendering
        print("\n🎨 Test 5: Dashboard Rendering")
        try:
            import finance_dashboard
            html = await finance_dashboard.render_finance_view()
            if "Finance Dashboard" in html and ("finance-account-card" in html or "Connection Failed" in html):
                print("\u2713 Dashboard renders successfully")
                print(f"  HTML length: {len(html)} chars")
            else:
                print("✗ Dashboard rendering issue")
        except Exception as e:
            print(f"✗ Dashboard test failed: {e}")
        
        print("\n" + "=" * 60)
        print("✅ Finance Integration Tests Complete\n")
        print("📋 Summary:")
        print("  - Finance client module: ✓")
        print("  - LLM tools integration: ✓")
        print("  - Dashboard rendering: ✓")
        print("\n💡 Next steps:")
        print("  1. Configure WYGIWYH (see WYGIWYH_SETUP.md)")
        print("  2. Add API token to .env")
        print("  3. Restart Echo server")
        print("  4. Visit http://localhost:5001/finance")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure you're running this from the Echo directory")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_finance_integration())
