"""
Browser Tool - Webctl Integration
Uses cosinusalpha/webctl CLI for stateful browser automation.
Token-efficient snapshots for LLM processing.
"""
import subprocess
import json
import sys
from typing import Optional


def _run_webctl(*args, timeout: int = 30, quiet: bool = False) -> dict:
    """
    Run a webctl command and return parsed result.
    Args:
        args: webctl command args (e.g., "snapshot", "--interactive-only", "--limit", "30")
        timeout: command timeout in seconds
        quiet: suppress verbose output
    Returns:
        dict with keys: status (ok/error), output (str), error (str), returncode (int)
    """
    cmd = ["webctl"] + list(args)
    if quiet:
        cmd.insert(1, "-q")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "output": result.stdout.strip(),
            "error": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "output": "",
            "error": f"Command timed out after {timeout}s",
            "returncode": -1
        }
    except Exception as e:
        return {
            "status": "error",
            "output": "",
            "error": str(e),
            "returncode": -1
        }


def start_session(mode: str = "attended") -> str:
    """
    Start a browser session.
    Args:
        mode: "attended" or "unattended"
    Returns:
        Status message
    """
    result = _run_webctl("start", "--mode", mode)
    if result["status"] == "ok":
        return f"✅ Browser session started ({mode} mode)"
    else:
        return f"❌ Failed to start browser: {result['error']}"


def snapshot(
    view: str = "a11y",
    interactive_only: bool = True,
    limit: int = 30,
    within: Optional[str] = None
) -> str:
    """
    Take a token-efficient snapshot of the current page.
    
    Args:
        view: "a11y" (default, best for LLM), "md" (markdown), "dom-lite"
        interactive_only: Only return interactive elements (saves tokens)
        limit: Max nodes to return (M4 KV cache limit)
        within: Scope to container (e.g., "role=main")
    
    Returns:
        Snapshot output (limited to first 50 lines for LLM)
    """
    args = ["snapshot", "-v", view]
    
    if interactive_only:
        args.append("-i")
    
    if limit:
        args.extend(["-l", str(limit)])
    
    if within:
        args.extend(["-w", within])
    
    result = _run_webctl(*args, quiet=True)
    
    if result["status"] == "ok":
        # Truncate to first 50 lines to prevent context overflow
        lines = result["output"].split("\n")[:50]
        return "\n".join(lines)
    else:
        return f"❌ Snapshot error: {result['error']}"


def navigate(url: str, wait: str = "load") -> str:
    """
    Navigate to a URL.
    
    Args:
        url: Target URL
        wait: Wait condition: "load", "domcontentloaded", "networkidle"
    
    Returns:
        Navigation status
    """
    result = _run_webctl("navigate", url, "-w", wait, quiet=True)
    
    if result["status"] == "ok":
        return f"✅ Navigated to {url}"
    else:
        return f"❌ Navigation failed: {result['error']}"


def click(selector: str) -> str:
    """Click an element by selector/role/text."""
    result = _run_webctl("click", selector, quiet=True)
    
    if result["status"] == "ok":
        return f"✅ Clicked: {selector}"
    else:
        return f"❌ Click failed: {result['error']}"


def type_text(selector: str, text: str) -> str:
    """Type text into an element."""
    result = _run_webctl("type", selector, text, quiet=True)
    
    if result["status"] == "ok":
        return f"✅ Typed into {selector}"
    else:
        return f"❌ Type failed: {result['error']}"


def scroll(direction: str = "down", amount: int = 3) -> str:
    """Scroll the page."""
    result = _run_webctl("scroll", direction, str(amount), quiet=True)
    
    if result["status"] == "ok":
        return f"✅ Scrolled {direction}"
    else:
        return f"❌ Scroll failed: {result['error']}"


def browse(query: str) -> str:
    """
    High-level browse function: plan and execute browser task.
    
    For now, this is a simple wrapper. In the future, integrate with LLM planning.
    """
    # Start session if not already running
    start_session("unattended")
    
    # Take a snapshot to understand current state
    snapshot_result = snapshot(interactive_only=True, limit=30)
    
    return f"🌍 Browser Observation:\n{query}\n\nCurrent Page State:\n{snapshot_result}"
