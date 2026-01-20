# Echo V3 Bug & Fix Log

## 2026-01-19

### Fixed
- **Critical Bug: Archive function deleted tasks permanently instead of archiving** - `archive_chat()` now calls `archive_completed_tasks()` instead of `delete_completed_tasks()`, properly marking tasks as 'archived' so they appear in the Archives page (web_server.py:2140)
- **Database functions returning incorrect values** - Fixed 6 functions that checked `conn.total_changes` before `conn.commit()`, causing them to always return 0/False. Now using `cursor.rowcount` after commit:
  - `delete_note()` - Now correctly returns True/False (database.py:146-153)
  - `delete_task()` - Now correctly returns True/False (database.py:244-251)
  - `delete_completed_tasks()` - Now returns actual count (database.py:253-260)
  - `complete_task()` - Now correctly returns True/False (database.py:175-183)
  - `complete_all_tasks()` - Now returns actual count (database.py:185-193)
  - `archive_completed_tasks()` - Now returns actual count (database.py:264-273)

### Security
- **Path traversal vulnerability fixed** - `delete_archive_file()` now uses `os.path.basename()` to prevent path traversal attacks including URL-encoded variants, and validates file extensions (web_server.py:2009-2024)

### Improved
- **Error handling for archive file operations** - Added try-except blocks when reading archive files during search and display to gracefully handle corrupted/missing files (web_server.py:1390, 1406)
- **Confirmation dialog for archive action** - Added `hx-confirm` attribute to Archive button to prevent accidental data loss (web_server.py:984)

### Testing
- Added comprehensive test suite (`tmp_rovodev_test_bug_fixes.py`) covering:
  - Database return value correctness (delete, complete, archive operations)
  - Archive workflow (tasks marked as 'archived' instead of deleted)
  - Security (path traversal protection with URL encoding)
  - Error handling (graceful failures for missing/corrupted files)
  - Complete end-to-end archive workflow
  - **Result: 27/27 tests passed** ✅

## 2026-01-15

- **Bug**: Python 3.9 incompatibility with `FastHTML` (requires 3.10+).
  - **Fix**: Replaced FastHTML with pure Starlette + HTMX (`web_server.py`).
- **Bug**: `mlx_server.py` used `temp` instead of `temperature` in `generate()`.
  - **Fix**: Removed `temp` argument (MLX LM uses defaults or `temperature` depending on version, stripped to safe defaults).
- **Bug**: `mlx_server.py` tried to load HuggingFace model when local path existed.
  - **Fix**: Hardcoded local path for Phi-4-mini in `mlx_server.py`.
- **Bug**: Port 1234 conflicts.
  - **Fix**: Added `pkill` cleanup in `run.sh`.
- **Bug**: CSS f-string conflict in `web_server.py`.
  - **Fix**: Escaped curly braces in CSS template.

## Next Steps

- Implement Model Swapping logic in `mlx_server.py`.
- Add UI for model swapping in `web_server.py`.
