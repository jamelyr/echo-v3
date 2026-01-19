# Echo V3 Bug & Fix Log

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
