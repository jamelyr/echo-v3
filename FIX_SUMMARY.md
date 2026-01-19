# Echo v2 - Complete Change Log

## Core Fixes (LM Studio Compatibility)

### LM Studio API Compatibility ✅

**Issue**: `response_format={"type": "json_object"}` caused 400 errors  
**Fix**: Removed incompatible parameter from `llm_client.py`  
**Impact**: Intent parsing now works with LM Studio v1.x

### Database Cleanup ✅

**Issue**: Test data ("Echo-99" codes) polluted RAG retrieval  
**Fix**: `DELETE FROM notes WHERE content LIKE '%secret%' OR content LIKE '%Echo-99%'`  
**Impact**: Clean, accurate memory retrieval

---

## New Features

| Feature | Files | Description |
|---------|-------|-------------|
| **Personal Context Layer** | `user_context.json`, `context_manager.py` | Persistent user profile (name, location, team) injected into all prompts |
| **Direct GPT Access** | `bot.py` | `/gpt` command for cloud model queries |
| **Local News** | `llm_client.py`, `news_sources.txt` | `/news` reads from local config |
| **Audio STT** | `bot.py` + Whisper | Voice message transcription |

---

## Environment Fixes

### Whisper Installation ✅

**Issue**: `No module named 'whisper'` despite installation  
**Root Cause**: Whisper installed in system Python, not `echo_env`  
**Fix**: `pip install openai-whisper` in virtual environment

### FFMPEG Resolution ✅

**Issue**: `No such file or directory: 'ffmpeg'`  
**Root Cause**: Virtual environment PATH doesn't include `/opt/homebrew/bin`  
**Fix**: Symlinked ffmpeg: `echo_env/bin/ffmpeg → /opt/homebrew/bin/ffmpeg`

### Discord Message Limits ✅

**Issue**: Bot crashed on responses >2000 chars  
**Fix**: Added response splitting in `process_instruction()`

---

## Production Cleanup

### Code Optimization

- Removed all DEBUG print statements
- Cleaned up audio handler verbosity
- Production-ready error logging only

### File Cleanup

Deleted temporary artifacts:

- `ffmpeg.zip` (25MB)
- `ffmpeg` binary (80MB duplicate)  
- `verify_whisper.py` (test script)
- `DIAGNOSTIC_REPORT.md` (outdated)

---

## Verification Status

✅ **Core Functions**: Tasks, notes, web search, RAG  
✅ **Slash Commands**: All working (`/sleep`, `/wake`, `/gpt`, `/news`, `/context_*`)  
✅ **Audio**: Transcription functional  
✅ **Environment**: Virtual environment properly configured  
✅ **Context Layer**: User profile active

---

## Known Minor Issues

**Intent Parsing for Notes**:  
"Remember that X" → Detects intent but fails to extract content  
*Status*: Low priority, workaround: "save note: X"

---

## Documentation

- **Architecture**: [architecture.md](file:///Users/marley/.gemini/antigravity/brain/d2092d14-91cf-413b-803c-2072b9f38f6d/architecture.md)
- **Walkthrough**: [walkthrough.md](file:///Users/marley/.gemini/antigravity/brain/d2092d14-91cf-413b-803c-2072b9f38f6d/walkthrough.md)  
- **Full Changelog**: `MIGRATION.txt`
