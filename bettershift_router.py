"""
BetterShift Smart Router for Echo V3
====================================
Handles all BetterShift operations with hardcoded domain knowledge.
Designed to be driven by simple LLM extraction or deterministic patterns.

This allows even 4B models to reliably manage shifts by:
1. Reducing cognitive load (1 tool instead of 11)
2. Hardcoding entity mappings (no multi-turn memory recall)
3. Hardcoding shift types (SA, SA+, Off)
4. Providing deterministic shortcuts for common patterns
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import pytz

import bettershift_client

# =============================================================================
# HARDCODED DOMAIN KNOWLEDGE
# =============================================================================

# Entity name -> BetterShift calendar ID
# These are loaded from notes but hardcoded for reliability
ENTITIES: Dict[str, str] = {
    "nirvan": "ab75b3a5-61fc-4b59-a7b4-59b3099e4917",
    "dom": "a36b99cf-927e-414c-820f-27dd2e3ccbb1",
    "marley": "1093844c-b5d0-4067-941c-78f1d03fc085",
    # Aliases for "me/my/I"
    "me": "1093844c-b5d0-4067-941c-78f1d03fc085",
    "my": "1093844c-b5d0-4067-941c-78f1d03fc085",
    "i": "1093844c-b5d0-4067-941c-78f1d03fc085",
}

# Group aliases
ENTITY_GROUPS: Dict[str, list] = {
    "the guys": ["nirvan", "dom"],
    "the team": ["nirvan", "dom"],
    "everyone": ["nirvan", "dom", "marley"],
    "all": ["nirvan", "dom", "marley"],
}

# Shift type -> parameters
SHIFT_TYPES: Dict[str, Dict[str, Any]] = {
    "sa": {
        "title": "SA",
        "start_time": "15:30",
        "end_time": "23:30",
        "is_all_day": False,
    },
    "sa+": {
        "title": "SA+",
        "start_time": "15:30",
        "end_time": "01:00",  # Next day
        "is_all_day": False,
    },
    "off": {
        "title": "Off",
        "start_time": None,
        "end_time": None,
        "is_all_day": True,
    },
}

# =============================================================================
# DETERMINISTIC PATTERN MATCHING (Bypasses LLM entirely)
# =============================================================================

# Patterns that can be handled without LLM
# Format: (regex_pattern, action_type)
# Groups: (1) person, (2) shift_type or date, (3) date if applicable

SHORTCUT_PATTERNS = [
    # "Nirvan is on SA Wednesday" / "Nirvan is on SA+ February 15"
    (r"(\w+)\s+is\s+on\s+(sa\+?)\s+(?:shift\s+)?(?:on\s+)?(.+)", "add"),
    
    # "Put Dom on SA tomorrow" / "Put Nirvan on SA+ Feb 20"
    (r"put\s+(\w+)\s+on\s+(sa\+?)\s+(?:shift\s+)?(?:on\s+)?(.+)", "add"),
    
    # "Add SA shift for Nirvan on Wednesday"
    (r"add\s+(sa\+?)\s+(?:shift\s+)?for\s+(\w+)\s+(?:on\s+)?(.+)", "add_reversed"),
    
    # "Nirvan is off Wednesday" / "Dom is off February 15"
    (r"(\w+)\s+is\s+off\s+(?:on\s+)?(.+)", "add_off"),
    
    # "Remove Nirvan's shift on Wednesday" / "Delete Dom's shift Feb 20"
    (r"(?:remove|delete|cancel)\s+(\w+)(?:'s)?\s+shift\s+(?:on\s+)?(.+)", "remove"),
    
    # "What are Nirvan's shifts" / "Show Dom's shifts on Feb 15"
    (r"(?:what\s+are|show|list)\s+(\w+)(?:'s)?\s+shifts?\s+(?:on\s+)?(.+)", "list"),
    
    # "Who's working today" / "Who is on shift February 15"
    (r"who(?:'s| is)\s+(?:working|on\s+shift)\s+(?:on\s+)?(.+)", "list_all"),
    
    # "Nirvan's shifts this week"
    (r"(\w+)(?:'s)?\s+shifts?\s+(?:this\s+)?(.+)", "list"),
]


def try_shortcut(user_input: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Try to match user input against deterministic patterns.
    Returns (action, person, shift_type, date) or None if no match.
    """
    text = user_input.lower().strip()
    
    for pattern, action_type in SHORTCUT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            
            if action_type == "add":
                # Groups: person, shift_type, date
                return ("add", groups[0], groups[1], groups[2])
            
            elif action_type == "add_reversed":
                # Groups: shift_type, person, date
                return ("add", groups[1], groups[0], groups[2])
            
            elif action_type == "add_off":
                # Groups: person, date
                return ("add", groups[0], "off", groups[1])
            
            elif action_type == "remove":
                # Groups: person, date
                return ("remove", groups[0], None, groups[1])
            
            elif action_type == "list":
                # Groups: person, date (optional)
                return ("list", groups[0], None, groups[1] if len(groups) > 1 else "today")
            
            elif action_type == "list_all":
                # Groups: date
                return ("list", "all", None, groups[0])
    
    return None


# =============================================================================
# DATE PARSING (Reused from llm_client but standalone for this module)
# =============================================================================

def parse_date(date_str: str) -> str:
    """
    Convert relative dates to YYYY-MM-DD format.
    Handles: today, tomorrow, monday-sunday, next week, YYYY-MM-DD
    """
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    
    # Strip punctuation and whitespace
    date_str_lower = date_str.lower().strip().rstrip('?!.')
    tz = pytz.timezone('Indian/Mauritius')
    now = datetime.now(tz)
    
    # Already formatted
    if re.match(r'\d{4}-\d{2}-\d{2}', date_str_lower):
        return date_str_lower
    
    # Relative dates
    if date_str_lower == "today":
        return now.strftime("%Y-%m-%d")
    
    if date_str_lower == "tomorrow":
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if date_str_lower == "yesterday":
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Day names
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if date_str_lower in days:
        target_day = days.index(date_str_lower)
        current_day = now.weekday()
        days_ahead = target_day - current_day
        if days_ahead <= 0:  # Target day is today or in the past, go to next week
            days_ahead += 7
        return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # "next X" patterns
    if date_str_lower.startswith("next "):
        day_name = date_str_lower[5:].strip()
        if day_name in days:
            target_day = days.index(day_name)
            current_day = now.weekday()
            days_ahead = target_day - current_day + 7  # Always next week
            return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # Month + day patterns: "February 15", "Jan 20", "march 3rd"
    months = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6,
        "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9,
        "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
    }
    
    # Try to parse "Month Day" format
    month_day_match = re.match(r'(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?', date_str_lower)
    if month_day_match:
        month_name = month_day_match.group(1)
        day = int(month_day_match.group(2))
        if month_name in months:
            month = months[month_name]
            year = now.year
            # If the date has passed this year, assume next year
            try:
                target_date = datetime(year, month, day, tzinfo=tz)
                if target_date < now:
                    target_date = datetime(year + 1, month, day, tzinfo=tz)
                return target_date.strftime("%Y-%m-%d")
            except ValueError:
                pass  # Invalid date (e.g., Feb 30)
    
    # Fallback: return as-is (might be a date string)
    return date_str


# =============================================================================
# MAIN HANDLER
# =============================================================================

async def handle_shift(action: str, person: str, shift_type: Optional[str], date: str) -> str:
    """
    Single entry point for all BetterShift operations.
    
    Args:
        action: "add", "remove", "list"
        person: "Nirvan", "Dom", "Marley", "me", "all"
        shift_type: "SA", "SA+", "Off", or None for list/remove
        date: Any date format (parsed internally)
    
    Returns:
        Human-readable result string
    """
    person_lower = person.lower().strip()
    parsed_date = parse_date(date)
    
    # Handle "list all" specially - don't iterate through group
    if action == "list" and person_lower in ("all", "everyone"):
        return await _list_all_shifts(parsed_date)
    
    # Handle group references (for add/remove operations on multiple people)
    if person_lower in ENTITY_GROUPS and action != "list":
        results = []
        for entity_name in ENTITY_GROUPS[person_lower]:
            result = await _handle_single(action, entity_name, shift_type, parsed_date)
            results.append(result)
        return "\n".join(results)
    
    return await _handle_single(action, person_lower, shift_type, parsed_date)


async def _handle_single(action: str, person: str, shift_type: Optional[str], date: str) -> str:
    """Handle operation for a single person."""
    
    # Resolve person -> calendar_id
    calendar_id = ENTITIES.get(person.lower())
    if not calendar_id:
        known = [k for k in ENTITIES.keys() if k not in ("me", "my", "i")]
        return f"❓ Don't know who '{person}' is. Known people: {', '.join(known)}"
    
    # Dispatch to action handler
    if action == "add":
        return await _add_shift(calendar_id, person, shift_type, date)
    elif action == "remove":
        return await _remove_shift(calendar_id, person, shift_type, date)
    elif action == "list":
        return await _list_shifts(calendar_id, person, date)
    else:
        return f"❓ Unknown action '{action}'. Use: add, remove, list"


async def _add_shift(calendar_id: str, person: str, shift_type: str, date: str) -> str:
    """Add a shift for a person."""
    if not shift_type:
        return f"❓ What type of shift? Use: SA, SA+, or Off"
    
    shift_info = SHIFT_TYPES.get(shift_type.lower().replace(" ", ""))
    if not shift_info:
        available = ", ".join(SHIFT_TYPES.keys())
        return f"❓ Unknown shift type '{shift_type}'. Available: {available}"
    
    try:
        result = await bettershift_client.create_shift(
            calendar_id=calendar_id,
            title=shift_info["title"],
            date=date,
            start_time=shift_info.get("start_time"),
            end_time=shift_info.get("end_time"),
            is_all_day=shift_info.get("is_all_day", False),
        )
        
        # Format nice response
        if shift_info.get("is_all_day"):
            return f"✅ {person.title()} is {shift_info['title']} on {date}"
        else:
            return f"✅ {person.title()} is on {shift_info['title']} ({shift_info['start_time']}-{shift_info['end_time']}) on {date}"
    
    except Exception as e:
        return f"❌ Failed to add shift: {str(e)}"


async def _remove_shift(calendar_id: str, person: str, shift_type: Optional[str], date: str) -> str:
    """Remove a shift for a person."""
    try:
        shifts = await bettershift_client.list_shifts(calendar_id, date)
        
        if not shifts:
            return f"❌ {person.title()} has no shifts on {date}"
        
        # Filter by type if specified
        if shift_type:
            shifts = [s for s in shifts if s.get("title", "").lower() == shift_type.lower()]
            if not shifts:
                return f"❌ {person.title()} has no '{shift_type}' shift on {date}"
        
        # Delete the first matching shift
        shift_to_delete = shifts[0]
        await bettershift_client.delete_shift(shift_to_delete["id"])
        
        return f"✅ Removed {shift_to_delete.get('title', 'shift')} for {person.title()} on {date}"
    
    except Exception as e:
        return f"❌ Failed to remove shift: {str(e)}"


async def _list_shifts(calendar_id: str, person: str, date: str) -> str:
    """List shifts for a person or everyone."""
    
    # Special case: list all people
    if person.lower() in ("all", "everyone"):
        return await _list_all_shifts(date)
    
    try:
        shifts = await bettershift_client.list_shifts(calendar_id, date)
        
        # Handle auth redirect (BetterShift not logged in)
        if isinstance(shifts, dict) and 'raw' in shifts:
            return "❌ BetterShift requires authentication. Please login at http://localhost:3000"
        
        if not shifts or not isinstance(shifts, list):
            return f"📅 {person.title()} has no shifts on {date}"
        
        lines = [f"📅 {person.title()}'s shifts on {date}:"]
        for s in shifts:
            if not isinstance(s, dict):
                continue
            title = s.get("title", "Shift")
            start = s.get("startTime", "")
            end = s.get("endTime", "")
            if start and end:
                lines.append(f"  • {title} ({start} - {end})")
            else:
                lines.append(f"  • {title}")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"❌ Failed to list shifts: {str(e)}"


async def _list_all_shifts(date: str) -> str:
    """List shifts for all known people."""
    lines = [f"📅 Who's working on {date}:"]
    
    # Only check actual people (not aliases)
    people = [k for k in ENTITIES.keys() if k not in ("me", "my", "i")]
    
    auth_error = False
    for person in people:
        calendar_id = ENTITIES[person]
        try:
            shifts = await bettershift_client.list_shifts(calendar_id, date)
            
            # Handle auth redirect
            if isinstance(shifts, dict) and 'raw' in shifts:
                auth_error = True
                lines.append(f"  • {person.title()}: (auth required)")
                continue
            
            if shifts and isinstance(shifts, list):
                for s in shifts:
                    if not isinstance(s, dict):
                        continue
                    title = s.get("title", "Shift")
                    start = s.get("startTime", "")
                    end = s.get("endTime", "")
                    if start and end:
                        lines.append(f"  • {person.title()}: {title} ({start}-{end})")
                    else:
                        lines.append(f"  • {person.title()}: {title}")
            else:
                lines.append(f"  • {person.title()}: Off")
        except Exception as e:
            lines.append(f"  • {person.title()}: (error)")
    
    if auth_error:
        return "❌ BetterShift requires authentication. Please login at http://localhost:3000"
    
    return "\n".join(lines)


# =============================================================================
# INTEGRATION HELPER (Called from llm_client.py)
# =============================================================================

async def try_handle_bettershift(user_input: str) -> Optional[str]:
    """
    Try to handle a BetterShift request deterministically.
    Returns result string if handled, None if LLM should handle it.
    
    This is the main entry point called from llm_client.py
    """
    shortcut = try_shortcut(user_input)
    if shortcut:
        action, person, shift_type, date = shortcut
        return await handle_shift(action, person, shift_type, date)
    
    return None
