"""
Echo V3 - Intelligence Client (ReAct Engine)
Replaces Semantic Router with a Reasoning+Acting Tool Loop.
"""
import os
import json
import httpx
import asyncio
import subprocess
import re
import ast
import pytz
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

import database
import news_aggregator
import context_manager
import mlx_embeddings
import bettershift_client
import bettershift_router
import wygiwyh_client
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
MLX_URL = "http://127.0.0.1:1234/v1"


# --- TOOLS DEFINITION ---

TOOLS_PROMPT = """
You have access to the following tools:

1.  **add_task(description: str)**
    - Adds a new task to the user's todo list.
    - Example: `Tool: add_task("Buy milk")`

2.  **list_tasks()**
    - Lists all pending tasks with their IDs.
    - Example: `Tool: list_tasks()`

3.  **complete_task(task_id: int)**
    - Marks a specific task as done. Use list_tasks() first to get the ID.
    - Example: `Tool: complete_task(42)`

4.  **complete_all_tasks()**
    - Marks ALL pending tasks as done.
    - Example: `Tool: complete_all_tasks()`

5.  **delete_completed_tasks()**
    - Permanently removes all finished tasks.
    - Example: `Tool: delete_completed_tasks()`

6.  **delete_task(task_id: int)**
    - Permanently removes a task by ID.
    - Example: `Tool: delete_task(42)`

7.  **search_web(query: str)**
    - Searches the internet for live information. Use this for questions about current events, prices, or facts you don't know.
    - Example: `Tool: search_web("price of bitcoin")`

8.  **get_news(topic: str = None)**
    - Fetches the latest news headlines.
    - Example (general): `Tool: get_news()`
    - Example (specific): `Tool: get_news("politics")`

9.  **sleep_mode()**
    - Shuts down the AI engine to save RAM.
    - Example: `Tool: sleep_mode()`

10. **wake_mode()**
    - Starts the AI engine.
    - Example: `Tool: wake_mode()`

11. **archive_session()**
    - Archives the current chat history and completed tasks to a permanent file.
    - Clears the active chat context to free up memory.
    - Example: `Tool: archive_session()`

12. **browse_web(query: str)**
    - Use this to visit specific websites, perform deep research, or when 'search_web' is not detailed enough.
    - Example: `Tool: browse_web("Go to YCombinator and summarize top post")`

13. **shift(action: str, person: str, shift_type: str, date: str)**
    - Manages BetterShift schedules for the team.
    - Actions: "add", "remove", "list"
    - People: "Nirvan", "Dom", "Marley", "me", "all"
    - Shift types: "SA" (15:30-23:30), "SA+" (15:30-01:00), "Off"
    - Dates: "today", "tomorrow", day names, or YYYY-MM-DD
    - Examples:
      `Tool: shift("add", "Nirvan", "SA", "Wednesday")`
      `Tool: shift("add", "Dom", "SA+", "tomorrow")`
      `Tool: shift("add", "Nirvan", "Off", "Friday")`
      `Tool: shift("remove", "Dom", "SA", "Wednesday")`
      `Tool: shift("list", "Nirvan", None, "today")`
      `Tool: shift("list", "all", None, "tomorrow")`

14. **save_note(content: str)**
    - Saves a personal note/memory to permanent storage for future recall.
    - Use this when the user asks you to remember something.
    - Example: `Tool: save_note("Door code is 9876")`

15. **recall_notes(query: str)**
    - Searches your memory for previously saved notes related to the query.
    - Use this when the user asks about something they told you before.
    - Example: `Tool: recall_notes("door code")`
    - Example: `Tool: recall_notes("favorite pizza")`

16. **finance_balance(account: str = None)**
    - View current balance across all accounts or a specific account.
    - Example: `Tool: finance_balance()`
    - Example: `Tool: finance_balance("Checking")`

17. **finance_add_expense(amount: float, category: str, description: str, account: str = None)**
    - Record an expense transaction.
    - Example: `Tool: finance_add_expense(45.50, "Food", "Groceries at supermarket")`

18. **finance_add_income(amount: float, source: str, description: str, account: str = None)**
    - Record income transaction.
    - Example: `Tool: finance_add_income(2500, "Salary", "Monthly paycheck")`

19. **finance_summary(period: str = "month")**
    - Get financial summary (income, expenses, net).
    - Periods: "week", "month", "year"
    - Example: `Tool: finance_summary("month")`

20. **finance_transactions(limit: int = 10, category: str = None)**
    - List recent transactions with optional category filter.
    - Example: `Tool: finance_transactions(5, "Food")`
 
21. **recall_facts(query: str, fact_type: str = None)**
    - Searches auto-extracted facts (entities, preferences, tech stack, patterns, context).
    - fact_type: Optional filter - "entity", "preference", "tech_stack", "pattern", "context"
    - Use this when user asks about preferences, people, tools, or things they mentioned before.
    - Example: `Tool: recall_facts("Nirvan")`
    - Example: `Tool: recall_facts("preferences")`
    - Example: `Tool: recall_facts("tech stack", "tech_stack")`
 
 FORMAT INSTRUCTIONS:
- To use a tool, you MUST output: `Tool: tool_name(arguments)`
- To speak to the user, you MUST output: `Answer: your message`
- You can "Think" before acting using `Thought: ...`

EXAMPLE 1 (Task):
User: Remind me to call Mom
Thought: I need to add a task.
Tool: add_task("Call Mom")
Observation: ✅ Added task ID 5: Call Mom
Answer: I've added "Call Mom" to your list.

EXAMPLE 2 (Chat):
User: Hello
Thought: The user is greeting me. No tool needed.
Answer: Hi there! How can I help you today?

EXAMPLE 3 (Archive):
User: Archive this chat
Thought: User wants to save this session and clear memory.
Tool: archive_session()

EXAMPLE 4 (Memory - Save):
User: Remember my door code is 9876
Thought: User wants me to save this information permanently.
Tool: save_note("Door code is 9876")
Observation: ✅ Saved note ID 14 to memory.
Answer: Got it! I've saved your door code to permanent memory.

EXAMPLE 5 (Memory - Recall):
User: What's my door code?
Thought: User is asking about something they told me before. I should search my memory.
Tool: recall_notes("door code")
Observation: Found 1 note: "Door code is 9876"
Answer: Your door code is 9876.

EXAMPLE 6 (BetterShift - Simple):
User: Nirvan is on SA shift Wednesday
Thought: I need to add an SA shift for Nirvan on Wednesday.
Tool: shift("add", "Nirvan", "SA", "Wednesday")
Observation: ✅ Nirvan is on SA (15:30-23:30) on 2026-01-22
Answer: Done! Nirvan is scheduled for SA shift on Wednesday.

EXAMPLE 7 (BetterShift - Who's Working):
User: Who's working tomorrow?
Thought: I need to check the schedule for tomorrow.
Tool: shift("list", "all", None, "tomorrow")
Observation: 📅 Who's working on 2026-01-21:
  • Nirvan: SA (15:30-23:30)
  • Dom: Off
  • Marley: Off
Answer: Tomorrow Nirvan is on SA shift (15:30-23:30). Dom and Marley are off.
"""

# --- CORE AGENT LOOP ---

async def process_input(user_input, user_id="default", history=[]):
    """
    Main ReAct Loop:
    1. Construct Prompt (System + Tools + History + User)
    2. Model Inference
    3. Check for Tool Call
    4. Execute Tool (if any)
    5. Recurse or Return Answer
    """
    print(f"🧠 Processing: '{user_input}'")

    # Fast-path: deterministic task listing fallback
    if _looks_like_task_query(user_input):
        observation = await execute_tool("list_tasks", [])
        return observation

    # Fast-path: deterministic task completion/deletion by description
    task_action = _extract_task_action(user_input)
    if task_action:
        action, description = task_action
        if action == "complete":
            observation = await execute_tool("complete_task_by_description", [description])
        else:
            observation = await execute_tool("delete_task_by_description", [description])
        if not observation.startswith("Error"):
            return observation

    # Fast-path: deterministic news fallback
    if _looks_like_news_query(user_input):
        topic = _extract_news_topic(user_input)
        observation = await execute_tool("get_news", [topic] if topic else [])
        return observation

    # Fast-path: BetterShift queries - use smart router (handles entity resolution)
    if _looks_like_bettershift_query(user_input):
        # First try the new smart router (handles "Nirvan is on SA Wednesday" etc.)
        smart_result = await bettershift_router.try_handle_bettershift(user_input)
        if smart_result is not None:
            return smart_result
        # Fallback to old direct handler for calendar-id based queries
        direct = await _handle_bettershift_direct(user_input)
        if direct is not None:
            return direct
    
    # Fast-path: Memory recall queries
    # DISABLED - was returning raw notes instead of natural answers
    # Let the LLM handle recall with proper formatting
    # if _looks_like_recall_query(user_input):
    #     query_text = user_input
    #     observation = await execute_tool("recall_notes", [query_text])
    #     if "Found" in observation and "note(s)" in observation:
    #         return observation
    
    # Fast-path: "Who is working?" queries
    if _looks_like_who_working_query(user_input):
        observation = await execute_tool("check_entity_status", [])
        # Let LLM add context from memory if needed
        if "❌" not in observation:
            return observation
    
    # 1. Build Context
    # Always recall professional profile to understand current job context
    profile_recall = await execute_tool("recall_notes", ["professional profile team job role"])
    
    # Extract relevant context from memory
    memory_context = ""
    if profile_recall and "Found" in profile_recall:
        memory_context = "\n\nCONTEXT FROM MEMORY:\n" + profile_recall
    
    # Entity Pre-Fetching: Scan user input for entity names and pre-fetch their context
    # Common entity patterns: proper names (capitalized words), "I/me", team references
    entity_hints = []
    
    # Check for specific names mentioned in user input
    words = user_input.split()
    capitalized_words = [w.strip('.,!?') for w in words if w and w[0].isupper() and len(w) > 1]
    
    # Also check for personal pronouns and team references
    if any(word in user_input.lower() for word in ['i am', 'im ', 'me ', 'my ', 'myself']):
        entity_hints.append("my calendar my schedule")
    
    if any(word in user_input.lower() for word in ['team', 'everyone', 'all', 'guys']):
        entity_hints.append("team members calendars")
    
    # Pre-fetch context for mentioned entities
    if capitalized_words:
        for name in capitalized_words[:3]:  # Limit to 3 to avoid too many queries
            entity_context = await execute_tool("recall_notes", [f"{name} calendar id"])
            if entity_context and "Found" in entity_context:
                memory_context += f"\n\nENTITY INFO ({name}):\n{entity_context}"
    
    # Fetch relevant auto-extracted facts
    import fact_extractor
    fact_query = user_input
    fact_context = await fact_extractor.recall_facts(fact_query, limit=3)
    if "Found" in fact_context:
        memory_context += f"\n\nAUTO-EXTRACTED FACTS:\n{fact_context}"
    
    system_prompt = f"""You are Echo, a private AI assistant.
{context_manager.format_for_prompt()}{memory_context}

{TOOLS_PROMPT}

IMPORTANT:
- You do NOT know the user's current tasks, news, calendars, or shifts unless you use a tool.
- If the user asks about tasks, you MUST use `Tool: list_tasks()`.
- If the user asks you to remember something, you MUST use `Tool: save_note()` to persist it.
- If the user asks about something they told you before, you MUST use `Tool: recall_notes()` to search your memory.
- For BetterShift requests, use the BetterShift tools instead of guessing.
- Do not hallucinate or guess.
- Use recall_notes to understand the user's professional context, team members, and specific project requirements.

CRITICAL FOR FINANCE TOOLS:
- When you receive ANY request about money/finance (amounts, expenses, income, transactions, balances), you MUST use a finance tool.
- NEVER respond with "added" or "recorded" without first calling `Tool: finance_add_expense(...)` or `Tool: finance_add_income(...)`
- Format requirement: You MUST start with "Tool:" and the function name, no exceptions
- Examples of correct responses:
  - "add expense 50 for food" -> `Tool: finance_add_expense(50, "Food", "...")`
  - "income 100 from salary" -> `Tool: finance_add_income(100, "Salary", "...")`
  - "show my balance" -> `Tool: finance_balance()`
- WRONG responses (DO NOT DO THIS):
  - ❌ "Added 50 MUR expense"
  - ❌ "Income of 100 recorded"
  - ❌ "Your balance is 50 MUR"
- CORRECT responses:
  - ✅ `Tool: finance_add_expense(50, "Food", "Dinner")`
  - ✅ `Tool: finance_balance()`

ENTITY MAPPING RULES:
- ALWAYS verify the subject of the sentence (e.g., "Dom", "Nirvan", "I", "me", "my team").
- Map each entity to their unique ID by using recall_notes("entity_name calendar id").
- For "I" or "me", look for "my calendar" or user's name in memory.
- For multi-person requests, handle EACH entity separately with their correct ID.
- Never guess or reuse IDs - always verify from memory first.

Current Date & Time: {datetime.now(pytz.timezone('Indian/Mauritius')).strftime("%A, %B %d, %Y at %I:%M %p")} (Mauritius Time)
Today is: {datetime.now(pytz.timezone('Indian/Mauritius')).strftime("%A")}
Current Year: {datetime.now(pytz.timezone('Indian/Mauritius')).year}
"""
    
    # Format messages for the API
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add History (Limited to last 10 for better context on follow-ups)
    if history:
        for m in history[-10:]:
            # Filter out tool internals if stored differently, or just pass simple text
            role = m["role"]
            content = m.get("content", "")
            if not content: continue
            if role not in ["user", "assistant"]: continue
            
            # For follow-ups: keep news headlines even if long, but truncate very large responses
            if len(content) > 2000:
                # Keep the first 1500 chars for context, add indicator
                content = content[:1500] + "\n[... content truncated ...]"
            
            messages.append({"role": role, "content": content})
    
    messages.append({"role": "user", "content": user_input})
    
    # 2. Reasoning Loop (Max 6 turns for complex multi-entity operations)
    for turn in range(6):
        response_text = await call_llm(messages)
        print(f"🤖 Trace (Turn {turn}): {response_text[:100]}...")
        
        # 3. Parse Tool
        tool_call = parse_tool(response_text)
        
        if tool_call:
            name, args = tool_call
            print(f"🛠️ Executing: {name}{args}")
            
            # 4. Execute
            observation = await execute_tool(name, args)
            print(f"👀 Observation: {observation[:100]}...")
            
            # Feed back to LLM
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": f"Observation: {observation}"})
            
            # Loop continues to let LLM analyze observation and give Final Answer
        
        else:
            # No tool call -> Final Answer
            # Strip "Answer: " prefix if present for cleaner chat
            final = response_text
            if "Answer:" in final:
                final = final.split("Answer:", 1)[1].strip()
            return final

    return "Thinking loop limit reached. I did the actions, but got confused summarizing them."

# --- HELPER FUNCTIONS ---

TASK_QUERY_PATTERNS = re.compile(
    r"\b(show|list|get|what are|what do|what's) (my )?(tasks|task list|todo|to-do)\b",
    re.IGNORECASE,
)

NEWS_QUERY_PATTERNS = re.compile(
    r"\b(news|headlines|daily news|latest news)\b",
    re.IGNORECASE,
)

BETTERSHIFT_QUERY_PATTERNS = re.compile(
    r"\b(calendar|calendars|shift|shifts|schedule|preset|presets|note|notes|sa\+?|working|on shift|is off)\b",
    re.IGNORECASE,
)

RECALL_QUERY_PATTERNS = re.compile(
    r"\b(what's my|what is my|what was|tell me my|remind me|do you remember|what did i tell you|recall|when is|where is)\b",
    re.IGNORECASE,
)

WHO_WORKING_PATTERNS = re.compile(
    r"\b(who is working|who's working|who is on shift|who's on shift|is anyone working|who is available|who's available|coverage|who is here|who's here)\b",
    re.IGNORECASE,
)

TASK_ACTION_PATTERNS = [
    (re.compile(r"\b(complete|finish|done|mark done)\s+task\s+(.+)", re.IGNORECASE), "complete"),
    (re.compile(r"\b(delete|remove|clear)\s+task\s+(.+)", re.IGNORECASE), "delete"),
]

# Pre-compiled patterns for BetterShift direct handling (saves CPU on each call)
_RE_LIST_SHIFTS = re.compile(r"list shifts.*calendar\s+([\w-]+)(?:.*(\d{4}-\d{2}-\d{2}))?", re.IGNORECASE)
_RE_CREATE_SHIFT = re.compile(
    r"(?:create|add).*shift.*calendar\s+([\w-]+).*?(?:titled|title)\s+([^\n]+?)\s+on\s+(\d{4}-\d{2}-\d{2})(?:.*?from\s+(\d{2}:\d{2})\s+to\s+(\d{2}:\d{2}))?",
    re.IGNORECASE,
)
_RE_CREATE_PRESET = re.compile(
    r"(?:create|add).*preset.*calendar\s+([\w-]+).*?(?:titled|title)\s+([^\n]+?)(?:\s+from\s+(\d{2}:\d{2})\s+to\s+(\d{2}:\d{2}))?",
    re.IGNORECASE,
)
_RE_DELETE_PRESET = re.compile(r"delete preset\s+([\w-]+)", re.IGNORECASE)
_RE_CREATE_NOTE = re.compile(
    r"(?:add|create).*note.*calendar\s+([\w-]+).*?on\s+(\d{4}-\d{2}-\d{2}).*?note\s+(.+)$",
    re.IGNORECASE,
)
_RE_LIST_NOTES = re.compile(r"list notes.*calendar\s+([\w-]+)(?:.*(\d{4}-\d{2}-\d{2}))?", re.IGNORECASE)


def _looks_like_task_query(text: str) -> bool:
    if not text:
        return False
    # Only trigger if user explicitly asks to list/show tasks
    # Avoid triggering on casual mentions of "task" in conversation
    return bool(TASK_QUERY_PATTERNS.search(text))


def _extract_news_topic(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"news\s+(?:about|on|regarding)?\s*(.+)$", text, re.IGNORECASE)
    if match:
        topic = match.group(1).strip()
        return topic if topic and topic.lower() not in {"today", "latest"} else ""
    return ""


def _looks_like_news_query(text: str) -> bool:
    if not text:
        return False
    return bool(NEWS_QUERY_PATTERNS.search(text))


def _looks_like_bettershift_query(text: str) -> bool:
    if not text:
        return False
    return bool(BETTERSHIFT_QUERY_PATTERNS.search(text))


def _looks_like_recall_query(text: str) -> bool:
    """Check if user is asking about something they told the agent before."""
    if not text:
        return False
    # Look for recall patterns OR possessive questions (e.g., "What's Sarah's birthday?")
    has_recall = bool(RECALL_QUERY_PATTERNS.search(text))
    has_possessive = "'s" in text and any(word in text.lower() for word in ['what', 'where', 'when', 'who', 'which'])
    return has_recall or has_possessive


def _truncate_context(text: str, max_lines: int = 50) -> str:
    """
    Truncate text to max_lines before sending to LLM to prevent context overflow.
    Preserves token efficiency and prevents thinking loop errors.
    """
    if not text:
        return text
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text
    truncated = "\n".join(lines[:max_lines])
    remaining = len(lines) - max_lines
    return f"{truncated}\n\n[... {remaining} more lines truncated ...]"


def _looks_like_who_working_query(text: str) -> bool:
    """Check if user is asking about who is currently working/available."""
    if not text:
        return False
    return bool(WHO_WORKING_PATTERNS.search(text))


def _extract_task_action(text: str) -> Optional[tuple]:
    """Extract task action (complete/delete) and description from input."""
    if not text:
        return None
    for pattern, action in TASK_ACTION_PATTERNS:
        match = pattern.search(text)
        if match:
            description = match.group(2).strip().strip('"\'')
            if description:
                return action, description
    return None


async def _handle_bettershift_direct(text: str):
    lowered = text.lower().strip()
    if any(k in lowered for k in ["list calendars", "show calendars", "calendars"]):
        return await execute_tool("list_calendars", [])

    match = _RE_LIST_SHIFTS.search(lowered)
    if match:
        calendar_id = match.group(1)
        date = match.group(2)
        args = [calendar_id] + ([date] if date else [])
        return await execute_tool("list_shifts", args)

    create_match = _RE_CREATE_SHIFT.search(lowered)
    if create_match:
        calendar_id = create_match.group(1)
        title = create_match.group(2).strip()
        date = create_match.group(3)
        start_time = create_match.group(4)
        end_time = create_match.group(5)
        args = [calendar_id, title, date]
        if start_time:
            args.append(start_time)
        if end_time:
            args.append(end_time)
        return await execute_tool("create_shift", args)

    preset_match = _RE_CREATE_PRESET.search(lowered)
    if preset_match:
        calendar_id = preset_match.group(1)
        title = preset_match.group(2).strip()
        start_time = preset_match.group(3)
        end_time = preset_match.group(4)
        args = [calendar_id, title]
        if start_time:
            args.append(start_time)
        if end_time:
            args.append(end_time)
        return await execute_tool("create_preset", args)

    delete_preset_match = _RE_DELETE_PRESET.search(lowered)
    if delete_preset_match:
        preset_id = delete_preset_match.group(1)
        return await execute_tool("delete_preset", [preset_id])

    note_match = _RE_CREATE_NOTE.search(lowered)
    if note_match:
        calendar_id = note_match.group(1)
        date = note_match.group(2)
        note = note_match.group(3).strip()
        return await execute_tool("create_note", [calendar_id, date, note])

    list_notes_match = _RE_LIST_NOTES.search(lowered)
    if list_notes_match:
        calendar_id = list_notes_match.group(1)
        date = list_notes_match.group(2)
        args = [calendar_id] + ([date] if date else [])
        return await execute_tool("list_notes", args)

    return None


def parse_tool(text):
    """
    Looks for `Tool: name(args)` pattern.
    Returns (name, list_of_args) or None.
    """
    if not text:
        return None

    # Try strict match first: Tool: name(args)
    match = re.search(r"Tool:\s*(\w+)\s*\((.*?)\)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        # Fallback: Tool: name (no parentheses)
        match = re.search(r"Tool:\s*(\w+)", text, re.IGNORECASE)

    if match:
        name = match.group(1)
        args_str = match.group(2) if match.lastindex and match.lastindex >= 2 else ""

        # Clean up args_str - remove markdown, trailing characters, etc.
        if args_str:
            args_str = args_str.strip()

        # Safe arg parsing (handling quoted strings, ints, etc.)
        args = []
        if args_str:
            try:
                args = ast.literal_eval(f"[{args_str}]")
            except Exception:
                # Fallback: pass raw string if eval fails
                args = [args_str.strip('"').strip("'")]

        return name, args
    return None


def parse_date(date_str):
    """
    Converts relative dates (tomorrow, wednesday, etc.) to YYYY-MM-DD format.
    Returns the date string in ISO format, or original if already formatted.
    """
    if not date_str or not isinstance(date_str, str):
        return date_str
    
    date_str_lower = date_str.lower().strip()
    mauritius_tz = pytz.timezone('Indian/Mauritius')
    now = datetime.now(mauritius_tz)
    
    # Already in YYYY-MM-DD format
    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
        return date_str
    
    # Today
    if date_str_lower in ['today', 'now']:
        return now.strftime('%Y-%m-%d')
    
    # Tomorrow
    if date_str_lower == 'tomorrow':
        tomorrow = now + timedelta(days=1)
        return tomorrow.strftime('%Y-%m-%d')
    
    # Day names (monday, tuesday, etc.)
    days_of_week = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    if date_str_lower in days_of_week:
        target_day = days_of_week[date_str_lower]
        current_day = now.weekday()
        
        # Calculate days until target day
        days_ahead = target_day - current_day
        if days_ahead <= 0:  # Target day already passed this week
            days_ahead += 7
        
        target_date = now + timedelta(days=days_ahead)
        return target_date.strftime('%Y-%m-%d')
    
    # If we can't parse it, return as-is
    return date_str


def parse_all_tools(text):
    """
    Extracts ALL tool calls from LLM response for parallel execution.
    Returns list of (name, [args_list]) tuples.
    Useful for multi-entity operations like updating multiple calendars.
    """
    if not text:
        return []
    
    tools = []
    
    # Find all Tool: name(args) patterns
    matches = re.findall(r"Tool:\s*(\w+)\s*\((.*?)\)", text, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        name = match[0].strip()
        args_str = match[1].strip()
        
        # Parse args safely
        args = []
        if args_str:
            try:
                args = ast.literal_eval(f"[{args_str}]")
            except Exception:
                args = [args_str.strip('"').strip("'")]
        
        tools.append((name, args))
    
    # If no parentheses format found, try simpler pattern
    if not tools:
        matches = re.findall(r"Tool:\s*(\w+)", text, re.IGNORECASE)
        for name in matches:
            tools.append((name.strip(), []))
    
    return tools


async def execute_tool(name, args):
    try:
        if name == "add_task":
            desc = args[0] if args else "Untitled Task"
            tid = database.add_task(desc)
            return f"✅ Added task ID {tid}: {desc}"
            
        elif name == "list_tasks":
            tasks = database.get_tasks(status='pending')
            if not tasks: return "No pending tasks."
            return "\n".join([f"- ID {t['id']}: {t['description']}" for t in tasks])
            
        elif name == "complete_task":
            tid = int(args[0])
            if database.complete_task(tid):
                return f"✅ Marked task {tid} as complete."
            else:
                return f"❌ Task {tid} not found."

        elif name == "complete_task_by_description":
            if not args:
                return "Error: description is required."
            task = database.complete_task_by_description(args[0])
            if task:
                return f"✅ Marked task '{task['description']}' as complete."
            return "❌ No matching pending task found."
        
        elif name == "complete_all_tasks":
            c = database.complete_all_tasks()
            return f"✅ Completed {c} tasks."
            
        elif name == "delete_completed_tasks":
            c = database.delete_completed_tasks()
            return f"🗑️ Deleted {c} completed tasks."

        elif name == "delete_task":
            if not args:
                return "Error: task_id is required."
            tid = int(args[0])
            if database.delete_task(tid):
                return f"🗑️ Deleted task {tid}."
            return f"❌ Task {tid} not found."

        elif name == "delete_task_by_description":
            if not args:
                return "Error: description is required."
            task = database.delete_task_by_description(args[0])
            if task:
                return f"🗑️ Deleted task '{task['description']}'."
            return "❌ No matching task found."
        
        elif name == "archive_session":
            # 1. Fetch Data
            chats = database.get_all_chat_history()
            tasks = database.get_tasks(status='completed')
            
            # 1.5 Extract Facts (before archive)
            import fact_extractor
            extraction_result = await fact_extractor.extract_and_archive_facts(chats, archive_source="session")
            
            # 2. Generate Content
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            filename = f"archives/archive_{datetime.now().strftime('%Y-%m-%d_%H%M')}.txt"
            
            content = f"=== ECHO ARCHIVE [{timestamp}] ===\n\n"
            
            content += "[COMPLETED TASKS]\n"
            for t in tasks:
                completed = t.get('completed_at') or "N/A"
                content += f"[x] {t['description']} (Completed: {completed})\n"
            
            content += "\n[CHAT LOG]\n"
            for msg in chats:
                content += f"{msg['role'].upper()}: {msg['content']}\n"
                
            # 3. Save File
            with open(filename, "w") as f:
                f.write(content)
                
            # 4. Cleanup DB
            database.clear_chat_history()
            count = database.archive_completed_tasks()
            
            # 5. Build response
            response = f"✅ Session archived to {filename}. Context cleared. {count} tasks moved to archive."
            
            if extraction_result.get("stored", 0) > 0:
                response += f"\n\n📝 Extracted {extraction_result['stored']} facts:"
                for fact in extraction_result['facts'][:3]:  # Show top 3
                    response += f"\n  - [{fact['type'].upper()}] {fact['value'][:60]}..."
                if len(extraction_result['facts']) > 3:
                    response += f"\n  - ...and {len(extraction_result['facts']) - 3} more"
            elif extraction_result.get("skipped"):
                response += f"\n\n⏭️  Fact extraction skipped: {extraction_result['reason']}"
            
            return response
            
        elif name == "search_web":

            q = args[0]
            if not TAVILY_API_KEY: return "Error: No TAVILY_API_KEY configured."
            async with httpx.AsyncClient() as client:
                data = await client.post("https://api.tavily.com/search",
                    json={"api_key": TAVILY_API_KEY, "query": q, "include_answer": True}, timeout=10)
                resp = data.json()
                return resp.get("answer") or str(resp.get("results", [])[:3])
                
        elif name == "get_news":
            topic = args[0] if args else None
            # Re-use logic from aggregator
            # Note: News aggregator is async and returns formatted string
            if "week" in (topic or "").lower():
                news_text = await news_aggregator.get_weekly_news()
            else:
                news_text = await news_aggregator.get_daily_news(topic)
            
            # news_aggregator returns pre-formatted string, just truncate and return
            if not news_text:
                return "No news available at this time."
            
            return _truncate_context(news_text, max_lines=50)
            
        elif name == "sleep_mode":
            subprocess.run(["pkill", "-f", "mlx_server.py"], check=False)
            return "✅ Sleep Mode Activated. Server stopped."
            
        elif name == "wake_mode":
            subprocess.Popen(["python", "mlx_server.py"], cwd=os.getcwd(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "✅ Wake Mode Initiated. Warming up..."

        elif name == "browse_web":
            # Lazy import to save ~50MB when not used
            from tools import browser_tool
            result = browser_tool.browse(args[0])
            # Truncate to prevent context overflow
            return _truncate_context(result, max_lines=50)

        elif name == "shift":
            # New unified BetterShift tool
            if len(args) < 4:
                return "Error: shift requires 4 args: action, person, shift_type, date"
            action, person, shift_type, date = args[0], args[1], args[2], args[3]
            # Handle None passed as string
            if shift_type == "None" or shift_type is None:
                shift_type = None
            return await bettershift_router.handle_shift(action, person, shift_type, date)

        elif name == "list_calendars":
            calendars = await bettershift_client.list_calendars()
            if not calendars:
                return "No calendars found."
            # Handle error responses (strings instead of list)
            if isinstance(calendars, str):
                return f"❌ BetterShift error: {calendars}"
            # Check for auth redirect
            if isinstance(calendars, dict) and 'raw' in calendars and 'login' in calendars.get('raw', ''):
                return "❌ BetterShift requires authentication. Please:\n1. Open http://localhost:3000 and login, OR\n2. Set BETTERSHIFT_API_KEY in .env file\n\nFor now, you can use Echo's built-in tasks and notes instead!"
            # Ensure we have a list of dicts
            if not isinstance(calendars, list):
                return f"❌ BetterShift returned unexpected format: {type(calendars)}"
            if len(calendars) == 0:
                return "No calendars found in BetterShift."
            return "\n".join([f"- {c.get('id')}: {c.get('name')} ({c.get('color')})" for c in calendars if isinstance(c, dict)])

        elif name == "list_shifts":
            if not args:
                return "Error: calendar_id is required."
            calendar_id = args[0]
            date_raw = args[1] if len(args) > 1 else None
            # Parse date (convert "tomorrow", "wednesday", etc. to YYYY-MM-DD)
            date = parse_date(date_raw) if date_raw else None
            shifts = await bettershift_client.list_shifts(calendar_id, date)
            if not shifts:
                return "No shifts found."
            return "\n".join([
                f"- {s.get('id')}: {s.get('title')} on {s.get('date')} ({s.get('startTime')} - {s.get('endTime')})"
                for s in shifts
            ])

        elif name == "create_shift":
            if len(args) < 3:
                return "Error: calendar_id, title, and date are required."
            calendar_id = args[0]
            title = args[1]
            date_raw = args[2]
            
            # Parse date (convert "tomorrow", "wednesday", etc. to YYYY-MM-DD)
            date = parse_date(date_raw)
            
            # Smart defaults based on title
            start_time = args[3] if len(args) > 3 else None
            end_time = args[4] if len(args) > 4 else None
            color = args[5] if len(args) > 5 else None
            notes = args[6] if len(args) > 6 else None
            
            # Auto-detect all-day shifts (Off, Leave, Vacation, etc.)
            is_all_day = bool(args[7]) if len(args) > 7 else (
                title.lower() in ['off', 'leave', 'vacation', 'holiday', 'absent', 'paternity leave', 'maternity leave']
            )
            
            is_secondary = bool(args[8]) if len(args) > 8 else False
            preset_id = args[9] if len(args) > 9 else None
            
            try:
                shift = await bettershift_client.create_shift(
                    calendar_id=calendar_id,
                    title=title,
                    date=date,
                    start_time=start_time,
                    end_time=end_time,
                    color=color,
                    notes=notes,
                    is_all_day=is_all_day,
                    is_secondary=is_secondary,
                    preset_id=preset_id,
                )
                return f"✅ Created shift '{shift.get('title')}' for {date} (ID: {shift.get('id')})"
            except Exception as e:
                return f"Tool Execution Error: {str(e)}"

        elif name == "list_presets":
            if not args:
                return "Error: calendar_id is required."
            presets = await bettershift_client.list_presets(args[0])
            if not presets:
                return "No presets found."
            return "\n".join([
                f"- {p.get('id')}: {p.get('title')} ({p.get('startTime')} - {p.get('endTime')})"
                for p in presets
            ])

        elif name == "create_preset":
            if len(args) < 2:
                return "Error: calendar_id and title are required."
            calendar_id = args[0]
            title = args[1]
            start_time = args[2] if len(args) > 2 else None
            end_time = args[3] if len(args) > 3 else None
            color = args[4] if len(args) > 4 else None
            notes = args[5] if len(args) > 5 else None
            is_secondary = bool(args[6]) if len(args) > 6 else False
            is_all_day = bool(args[7]) if len(args) > 7 else False
            hide_from_stats = bool(args[8]) if len(args) > 8 else False
            preset = await bettershift_client.create_preset(
                calendar_id=calendar_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                color=color,
                notes=notes,
                is_secondary=is_secondary,
                is_all_day=is_all_day,
                hide_from_stats=hide_from_stats,
            )
            return f"✅ Created preset {preset.get('id')} for {preset.get('title')}"

        elif name == "list_notes":
            if not args:
                return "Error: calendar_id is required."
            calendar_id = args[0]
            date = args[1] if len(args) > 1 else None
            notes = await bettershift_client.list_notes(calendar_id, date)
            if not notes:
                return "No notes found."
            return "\n".join([
                f"- {n.get('id')}: {n.get('note')} on {n.get('date')}"
                for n in notes
            ])

        elif name == "create_note":
            if len(args) < 3:
                return "Error: calendar_id, date, and note are required."
            calendar_id = args[0]
            date = args[1]
            note = args[2]
            note_type = args[3] if len(args) > 3 else "note"
            color = args[4] if len(args) > 4 else None
            created = await bettershift_client.create_note(
                calendar_id=calendar_id,
                date=date,
                note=note,
                note_type=note_type,
                color=color,
            )
            return f"✅ Added note {created.get('id')} on {created.get('date')}"

        elif name == "delete_preset":
            if not args:
                return "Error: preset_id is required."
            deleted = await bettershift_client.delete_preset(args[0])
            return f"🗑️ Deleted preset {deleted.get('id', args[0])}"
        
        elif name == "save_note":
            content = args[0] if args else "Empty note"
            # Generate embedding for semantic search
            embedding = mlx_embeddings.get_embedding(content)
            note_id = database.add_note(content, embedding)
            return f"✅ Saved note ID {note_id} to memory."
        
        elif name == "recall_notes":
            query = args[0] if args else ""
            if not query:
                return "Error: query is required for recall_notes."
            
            # Generate embedding for the query
            query_embedding = mlx_embeddings.get_embedding(query)
            
            if not query_embedding:
                return "❌ Could not generate embedding for query."
            
            # Get similar notes from database
            similar_notes = database.get_similar_notes(query_embedding, top_k=3)
            
            if not similar_notes:
                return "No relevant notes found in memory."
            
            # Format results
            result = f"Found {len(similar_notes)} note(s):\n"
            for note in similar_notes:
                result += f"- (ID {note['id']}, {note['created_at']}): {note['content']}\n"
            
            # Truncate to prevent context overflow
            return _truncate_context(result.strip(), max_lines=50)
        
        elif name == "recall_facts":
            import fact_extractor
            query = args[0] if args else ""
            fact_type = args[1] if len(args) > 1 else None
            
            if not query:
                return "Error: query is required for recall_facts."
            
            result = await fact_extractor.recall_facts(query, fact_type=fact_type, limit=5)
            return result
         
        elif name == "check_entity_status":
            # Get all calendars
            calendars = await bettershift_client.list_calendars()
            
            # Handle errors
            if isinstance(calendars, str):
                return f"❌ BetterShift error: {calendars}"
            if isinstance(calendars, dict) and 'raw' in calendars:
                return "❌ BetterShift requires authentication."
            if not isinstance(calendars, list) or len(calendars) == 0:
                return "No calendars found."
            
            # Get today's date and current time
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            
            entities = []
            
            # Check shifts for each calendar (each calendar represents a person/entity)
            for calendar in calendars:
                if not isinstance(calendar, dict):
                    continue
                    
                calendar_id = calendar.get('id')
                name = calendar.get('name', 'Unknown')
                
                # Get today's shifts for this entity
                shifts = await bettershift_client.list_shifts(calendar_id, today)
                
                status = "Off"
                time_info = ""
                
                if shifts and isinstance(shifts, list):
                    for shift in shifts:
                        start_time = shift.get('startTime', '')
                        end_time = shift.get('endTime', '')
                        is_all_day = shift.get('isAllDay', False)
                        title = shift.get('title', '').lower()
                        color = shift.get('color', '')
                        
                        # Handle all-day shifts (Off, Leave, Vacation, etc.)
                        if is_all_day or not (start_time and end_time):
                            # All-day shifts: Off, Leave, Vacation, etc.
                            title = shift.get('title', '').lower()
                            if 'off' in title or 'leave' in title or 'vacation' in title or 'paternity' in title:
                                status = "Off"
                            else:
                                status = "Active"
                            time_info = "all day"
                            break
                        
                        if start_time and end_time:
                            # Check if currently active
                            if start_time <= current_time <= end_time:
                                # Calculate time remaining
                                end_dt = datetime.strptime(f"{today} {end_time}", "%Y-%m-%d %H:%M")
                                remaining = end_dt - now
                                hours = int(remaining.total_seconds() // 3600)
                                minutes = int((remaining.total_seconds() % 3600) // 60)
                                
                                status = "Active"
                                if hours > 0:
                                    time_info = f"{hours}h {minutes}m remaining"
                                else:
                                    time_info = f"{minutes}m remaining"
                                break
                            
                            # Check if upcoming
                            elif current_time < start_time:
                                # Calculate time until start
                                start_dt = datetime.strptime(f"{today} {start_time}", "%Y-%m-%d %H:%M")
                                until_start = start_dt - now
                                hours = int(until_start.total_seconds() // 3600)
                                minutes = int((until_start.total_seconds() % 3600) // 60)
                                
                                status = "Upcoming"
                                if hours > 0:
                                    time_info = f"starts in {hours}h {minutes}m"
                                else:
                                    time_info = f"starts in {minutes}m"
                                break
                
                entities.append({
                    "name": name,
                    "status": status,
                    "time_info": time_info
                })
            
            # Format output
            if not entities:
                return "No entities found."
            
            # Sort: Active first, then Upcoming, then Off
            status_order = {"Active": 0, "Upcoming": 1, "Off": 2}
            entities.sort(key=lambda x: status_order.get(x["status"], 3))
            
            result = "Current Coverage:\n"
            for entity in entities:
                status_emoji = "🟢" if entity["status"] == "Active" else "🟡" if entity["status"] == "Upcoming" else "⚪"
                result += f"{status_emoji} {entity['name']} - {entity['status']}"
                if entity["time_info"]:
                    result += f" ({entity['time_info']})"
                result += "\n"
            
            return result.strip()
        
        elif name == "finance_balance":
            account_filter = args[0] if args else None
            return await wygiwyh_client.get_balance_summary(account_filter)
        
        elif name == "finance_add_expense":
            if len(args) < 3:
                return "Error: finance_add_expense requires amount, category, description"
            amount = float(args[0])
            category = args[1]
            description = args[2]
            account = args[3] if len(args) > 3 else None
            return await wygiwyh_client.create_expense(amount, category, description, account)
        
        elif name == "finance_add_income":
            if len(args) < 3:
                return "Error: finance_add_income requires amount, source, description"
            amount = float(args[0])
            source = args[1]
            description = args[2]
            account = args[3] if len(args) > 3 else None
            return await wygiwyh_client.create_income(amount, source, description, account)
        
        elif name == "finance_summary":
            period = args[0] if args else "month"
            return await wygiwyh_client.get_summary(period)
        
        elif name == "finance_transactions":
            limit = int(args[0]) if args else 10
            category = args[1] if len(args) > 1 else None
            return await wygiwyh_client.get_recent_transactions(limit, category)
            
        else:
            return f"Error: Tool '{name}' not found."
            
    except Exception as e:
        return f"Tool Execution Error: {e}"

async def call_llm(messages):
    params = {
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.1, # Very low temp to prevent hallucination
        "stop": ["Observation:"] # Stop at observation for ReAct loop
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{MLX_URL}/chat/completions", json=params)
            if resp.status_code == 200:
                ret = resp.json()["choices"][0]["message"]["content"].strip()

                # Handle reasoning models that output <|...|> tags
                if "<|" in ret and "|>" in ret:
                    # Extract only the part AFTER <|...|>
                    parts = ret.split("<|", 1)
                    if len(parts) > 1:
                        ret = parts[1].strip()
                elif "<|" in ret:
                    # Thinking started but not finished - strip it
                    ret = re.sub(r'<\|.*', '', ret, flags=re.DOTALL).strip()

                return ret
            return f"LLM Error: {resp.status_code}"
    except Exception as e:
        import traceback
        print(f"❌ LLM Connection Error Details: {e}")
        print(f"❌ Traceback:")
        traceback.print_exc()
        return f"Connection Error: {e}"
