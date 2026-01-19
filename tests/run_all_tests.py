#!/usr/bin/env python3
"""Test Suite Runner - Generates comprehensive feature report"""
import sys
import os
# Add parent directory to path for module imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
os.chdir(parent_dir)  # Change to parent dir for database paths

from datetime import datetime

results = []

def test(name, condition, details=""):
    status = "✅ PASS" if condition else "❌ FAIL"
    results.append((name, status, details))
    print(f"{status}: {name}" + (f" - {details}" if details else ""))

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    results.append(("---", title, "---"))

# ============================================================
#  TEST 1: CONTEXT MANAGER
# ============================================================
section("Context Manager")

try:
    import context_manager
    test("Import context_manager", True)
    
    ctx = context_manager.load_context()
    test("Load context", isinstance(ctx, dict))
    test("Has name field", "name" in ctx, f"name={ctx.get('name')}")
    test("Has location field", "location" in ctx, f"location={ctx.get('location')}")
    test("Has team field", "team" in ctx, f"team={ctx.get('team')}")
    
    formatted = context_manager.format_for_prompt()
    test("Format for prompt", len(formatted) > 0, f"{len(formatted)} chars")
    test("Name in prompt", "Marley" in formatted or "User" in formatted)
    
    summary = context_manager.get_context_summary()
    test("Get context summary", len(summary) > 0)
except Exception as e:
    test("Context Manager Module", False, str(e))

# ============================================================
#  TEST 2: NOTE PROCESSOR (SimpleMem-Inspired)
# ============================================================
section("Note Processor (SimpleMem)")

try:
    import note_processor
    test("Import note_processor", True)
    
    # Timestamp normalization
    result = note_processor.normalize_timestamps("meet Bob tomorrow")
    has_date = "202" in result  # Should contain year like 2026
    test("Timestamp normalization", has_date, f"'{result}'")
    
    # Entity resolution
    result = note_processor.resolve_entities("tell the guys to come")
    has_names = "Dominique" in result or "Nirvan" in result or "the guys" not in result.lower()
    test("Entity resolution (team)", has_names, f"'{result}'")
    
    # Full pipeline
    processed = note_processor.process_note("remind the guys tomorrow about meeting")
    test("Full note processing", len(processed) > 0, f"'{processed}'")
    
    # Task processing
    desc, due = note_processor.process_task("call Dan", "tomorrow")
    test("Task processing", due is not None and "202" in str(due), f"due={due}")
    
except Exception as e:
    test("Note Processor Module", False, str(e))

# ============================================================
#  TEST 3: DATABASE
# ============================================================
section("Database Operations")

try:
    import database
    test("Import database", True)
    
    database.init_db()
    test("Initialize DB", True)
    
    # Test task operations
    task_id = database.add_task("TEST_TASK_AUTOMATED", "2099-12-31")
    test("Add task", task_id > 0, f"ID={task_id}")
    
    tasks = database.get_tasks()
    test("Get tasks", len(tasks) > 0)
    
    completed = database.complete_task(task_id)
    test("Complete task", completed)
    
    deleted = database.delete_task(task_id)
    test("Delete task", deleted)
    
    # Test note operations
    note_id = database.add_note("TEST_NOTE_AUTOMATED", [0.1]*384)
    test("Add note with embedding", note_id > 0, f"ID={note_id}")
    
except Exception as e:
    test("Database Module", False, str(e))

# ============================================================
#  TEST 4: LLM CLIENT (Import Only - No API Calls)
# ============================================================
section("LLM Client Structure")

try:
    import llm_client
    test("Import llm_client", True)
    
    test("Has process_input", hasattr(llm_client, 'process_input'))
    test("Has parse_tool", hasattr(llm_client, 'parse_tool'))
    test("Has execute_tool", hasattr(llm_client, 'execute_tool'))
    test("Has call_llm", hasattr(llm_client, 'call_llm'))
    test("Has TOOLS_PROMPT", hasattr(llm_client, 'TOOLS_PROMPT'))
    test("Has task query patterns", hasattr(llm_client, 'TASK_QUERY_PATTERNS'))
    
except Exception as e:
    test("LLM Client Module", False, str(e))

# ============================================================
#  TEST 5: WHISPER/AUDIO
# ============================================================
section("Audio Transcription (Whisper)")

try:
    import whisper
    test("Import whisper", True)
    test("Whisper has load_model", hasattr(whisper, 'load_model'))
except ImportError as e:
    test("Import whisper", False, "Module not found - run with venv python")
except Exception as e:
    test("Whisper Module", False, str(e))

# ============================================================
#  TEST 6: DEPENDENCIES
# ============================================================
section("Core Dependencies")

deps = [
    ("discord", "Discord.py"),
    ("openai", "OpenAI Client"),
    ("dotenv", "python-dotenv"),
    ("numpy", "NumPy"),
    ("dateparser", "Date Parser"),
]

for module, name in deps:
    try:
        __import__(module)
        test(f"{name}", True)
    except ImportError:
        test(f"{name}", False, "Not installed")

# ============================================================
#  GENERATE REPORT
# ============================================================
print("\n" + "="*60)
print("  FINAL REPORT")
print("="*60)

passed = sum(1 for r in results if r[1] == "✅ PASS")
failed = sum(1 for r in results if r[1] == "❌ FAIL")
total = passed + failed

print(f"\nTotal Tests: {total}")
print(f"Passed: {passed} ({100*passed/max(total,1):.0f}%)")
print(f"Failed: {failed}")

if failed > 0:
    print("\n❌ FAILURES:")
    for name, status, detail in results:
        if status == "❌ FAIL":
            print(f"  - {name}: {detail}")

print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)
