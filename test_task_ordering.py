import database
import asyncio

def test_ordering():
    print("🧪 Testing Task Ordering...")
    
    # 1. Setup: Clear and Add Tasks
    database.init_db()
    conn = database.get_connection()
    conn.execute("DELETE FROM tasks")
    conn.commit()
    conn.close()
    
    t1 = database.add_task("Task 1 (Oldest)")
    t2 = database.add_task("Task 2 (Middle)")
    t3 = database.add_task("Task 3 (Newest)")
    
    print(f"Created IDs: {t1}, {t2}, {t3}")
    
    # 2. Verify Get Tasks
    tasks = database.get_tasks()
    print("\n[Database Output]")
    ids = [t['id'] for t in tasks]
    print(f"IDs returned: {ids}")
    
    if ids == [t3, t2, t1]:
        print("✅ PASS: Tasks are ordered Newest -> Oldest (DESC)")
    else:
        print(f"❌ FAIL: Expected {[t3, t2, t1]}, got {ids}")
        
    # 3. Verify Prompt Context Construction (Simulating llm_client)
    task_list = "\n".join([f"{t['id']}: {t['description']}" for t in tasks])
    print("\n[LLM Context String]")
    print(task_list)
    
    # Check if top item is the last added task
    lines = task_list.split('\n')
    if str(t3) in lines[0]:
        print("✅ PASS: LLM sees the newest task first.")
    else:
        print("❌ FAIL: LLM sees checking ordering.")

if __name__ == "__main__":
    test_ordering()
