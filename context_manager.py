"""
Dynamic Personal Context Layer for Echo Bot.
Manages persistent user context that gets injected into LLM prompts.
"""
import json
import os

CONTEXT_FILE = os.path.join(os.path.dirname(__file__), "user_context.json")

# Default context (used if file doesn't exist)
# Job-specific info should be stored in RAG notes, not hard-coded here
DEFAULT_CONTEXT = {
    "name": "User",
    "location": "",
    "profession": "",
    "team": [],
    "tech_ecosystem": ["MacOS", "iOS"],
    "communication_style": "Concise, Clear, Friendly, No Fluff",
    "memory_support": True
}

def load_context() -> dict:
    """Load context from file, or return defaults if file missing/corrupted."""
    try:
        if os.path.exists(CONTEXT_FILE):
            with open(CONTEXT_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Context] Error loading context: {e}")
    return DEFAULT_CONTEXT.copy()

def save_context(context: dict) -> bool:
    """Save context to file. Returns True on success."""
    try:
        with open(CONTEXT_FILE, 'w') as f:
            json.dump(context, f, indent=4)
        return True
    except Exception as e:
        print(f"[Context] Error saving context: {e}")
        return False

def update_field(key: str, value: str) -> tuple:
    """
    Update a specific field in context.
    Returns (success: bool, message: str)
    """
    context = load_context()
    
    # Normalize key
    key = key.lower().strip().replace(" ", "_")
    
    # Handle list fields
    if key in ["team", "tech_ecosystem"]:
        # Parse comma-separated values
        value = [v.strip() for v in value.split(",")]
    elif key == "memory_support":
        # Parse boolean
        value = value.lower() in ["true", "yes", "1", "on"]
    
    # Check if key exists
    if key not in context:
        valid_keys = ", ".join(context.keys())
        return (False, f"Unknown field '{key}'. Valid fields: {valid_keys}")
    
    context[key] = value
    
    if save_context(context):
        return (True, f"**{key}** is now **{value}**")
    else:
        return (False, "Failed to save context file")

def format_for_prompt() -> str:
    """
    Format user context as a string to inject into system prompts.
    Designed to help the LLM understand the user's situation.
    """
    ctx = load_context()
    
    parts = []
    
    # Name
    if ctx.get("name"):
        parts.append(f"User's name: {ctx['name']}")
    
    # Location
    if ctx.get("location"):
        parts.append(f"User's location: {ctx['location']}")
    
    # Profession
    if ctx.get("profession"):
        parts.append(f"User's profession: {ctx['profession']}")
    
    # Team
    if ctx.get("team"):
        team_str = " and ".join(ctx["team"]) if len(ctx["team"]) <= 2 else ", ".join(ctx["team"])
        parts.append(f"User's team/colleagues: {team_str}. When user mentions 'the guys' or 'the team', they mean these people.")
    
    # Tech
    if ctx.get("tech_ecosystem"):
        parts.append(f"User's tech: {', '.join(ctx['tech_ecosystem'])}. Provide platform-specific answers when relevant.")
    
    # Communication style
    if ctx.get("communication_style"):
        parts.append(f"Communication preference: {ctx['communication_style']}. Match this style in responses.")
    
    # Memory support
    if ctx.get("memory_support"):
        parts.append("User appreciates reminders and memory support. Proactively recall relevant past information.")
    
    return "\n".join(parts)

def get_location() -> str:
    """Helper to get just the location (for weather queries, etc.)"""
    return load_context().get("location", "Mauritius")

def get_context_summary() -> str:
    """Returns a formatted summary of all context for /status or display."""
    ctx = load_context()
    lines = []
    for key, value in ctx.items():
        if isinstance(value, list):
            value = ", ".join(value)
        lines.append(f"• **{key}**: {value}")
    return "\n".join(lines)
