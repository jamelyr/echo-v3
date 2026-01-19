"""
Note Processor - SimpleMem-Inspired Pre-Processing
Transforms raw notes into atomic, disambiguated facts before storage.
"""
import re
from datetime import datetime
from typing import Optional

# Try to import dateparser for relative date parsing
try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False
    print("Warning: dateparser not installed. Relative date parsing disabled.")

# Try to import context_manager for entity resolution
try:
    import context_manager
    CONTEXT_AVAILABLE = True
except ImportError:
    CONTEXT_AVAILABLE = False


def normalize_timestamps(text: str, reference_date: Optional[datetime] = None) -> str:
    """
    Convert relative time expressions to absolute timestamps.
    
    Examples:
        "meet Bob tomorrow at 2pm" → "meet Bob on 2026-01-12 at 14:00"
        "call Dan next week" → "call Dan on 2026-01-18"
    """
    if not DATEPARSER_AVAILABLE:
        return text
    
    if reference_date is None:
        reference_date = datetime.now()
    
    # Common relative time patterns
    patterns = [
        r'\b(tomorrow)\b',
        r'\b(today)\b',
        r'\b(yesterday)\b',
        r'\b(next week)\b',
        r'\b(next month)\b',
        r'\b(in \d+ days?)\b',
        r'\b(in \d+ weeks?)\b',
        r'\b(in \d+ hours?)\b',
        r'\b(this evening)\b',
        r'\b(this morning)\b',
        r'\b(tonight)\b',
        r'\b(later today)\b',
    ]
    
    result = text
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            relative_expr = match.group(0)
            parsed = dateparser.parse(
                relative_expr,
                settings={
                    'RELATIVE_BASE': reference_date,
                    'PREFER_DATES_FROM': 'future'
                }
            )
            if parsed:
                # Format based on whether time is present
                if 'morning' in relative_expr.lower() or 'evening' in relative_expr.lower():
                    formatted = parsed.strftime("%Y-%m-%d %H:%M")
                elif 'hour' in relative_expr.lower():
                    formatted = parsed.strftime("%Y-%m-%d %H:%M")
                else:
                    formatted = parsed.strftime("%Y-%m-%d")
                
                result = result.replace(relative_expr, f"on {formatted}", 1)
    
    return result


def resolve_entities(text: str) -> str:
    """
    Replace ambiguous entity references with concrete names from user context.
    
    Examples:
        "tell the guys" → "tell Dominique and Nirvan"
        "at work" → "at Plaine Mahnien, Mauritius"
    """
    if not CONTEXT_AVAILABLE:
        return text
    
    ctx = context_manager.load_context()
    
    # Team aliases
    team = ctx.get("team", [])
    if team:
        team_str = " and ".join(team) if len(team) <= 2 else ", ".join(team)
        
        # Common team aliases
        aliases = [
            r'\bthe guys\b',
            r'\bthe team\b',
            r'\beveryone\b',
            r'\bthe crew\b',
            r'\bthe boys\b',
        ]
        
        for alias in aliases:
            text = re.sub(alias, team_str, text, flags=re.IGNORECASE)
    
    # Location aliases
    location = ctx.get("location", "")
    if location:
        location_aliases = [
            (r'\bat work\b', f"at {location}"),
            (r'\bat the office\b', f"at {location}"),
            (r'\bat home\b', f"at {location}"),  # Assuming work-from-home in this context
        ]
        
        for pattern, replacement in location_aliases:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # User's own name (for third person references)
    name = ctx.get("name", "")
    if name:
        text = re.sub(r'\bmy name is (\w+)\b', f"User's name is {name}", text, flags=re.IGNORECASE)
    
    return text


def process_note(content: str) -> str:
    """
    Main entry point: Apply all preprocessing transformations to a note.
    
    Pipeline:
        1. Normalize timestamps (relative → absolute)
        2. Resolve entities (aliases → concrete names)
    
    Returns the transformed, atomic note content.
    """
    # Stage 1: Timestamp normalization
    content = normalize_timestamps(content)
    
    # Stage 2: Entity resolution
    content = resolve_entities(content)
    
    return content


def process_task(description: str, due_date: Optional[str] = None) -> tuple:
    """
    Process a task description and optional due date.
    
    Returns (processed_description, parsed_due_date)
    """
    # Process description
    description = resolve_entities(description)
    
    # Parse due date if it's a relative expression
    parsed_due = due_date
    if due_date and DATEPARSER_AVAILABLE:
        parsed = dateparser.parse(
            due_date,
            settings={'PREFER_DATES_FROM': 'future'}
        )
        if parsed:
            parsed_due = parsed.strftime("%Y-%m-%d")
    
    return description, parsed_due
