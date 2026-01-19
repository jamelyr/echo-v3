import asyncio
import database
import llm_client

async def test():
    # Setup
    database.init_db()
    print("--- Test Start ---")
    
    # 1. Add Task
    print("\n[Input]: 'add task buy milk'")
    res = await llm_client.process_input("add task buy milk")
    print(f"[Result]: {res}")
    
    tasks = database.get_tasks()
    print(f"[DB]: Found {len(tasks)} tasks.")
    for t in tasks: print(f" - {t['description']} ({t['status']})")
    
    # 2. Add with typo (Simulating user: 'reminders add rask')
    # My current logic likely fails this if 'task' is required word
    print("\n[Input]: 'remind me to call mom'")
    res = await llm_client.process_input("remind me to call mom")
    print(f"[Result]: {res}")
    
    # 3. Complete Task
    print("\n[Input]: 'complete task buy milk'")
    res = await llm_client.process_input("complete task buy milk")
    print(f"[Result]: {res}")
    
    tasks = database.get_tasks()
    for t in tasks: print(f" - {t['description']} ({t['status']})")

    # 4. Delete Task
    print("\n[Input]: 'delete task call mom'")
    res = await llm_client.process_input("delete task call mom")
    print(f"[Result]: {res}")

if __name__ == "__main__":
    asyncio.run(test())
