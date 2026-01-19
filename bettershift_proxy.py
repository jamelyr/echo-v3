"""Echo-side proxy for BetterShift API."""
import os
from typing import Dict, Optional
import httpx
from starlette.responses import JSONResponse

BETTERSHIFT_BASE_URL = os.getenv("BETTERSHIFT_BASE_URL", "http://127.0.0.1:3000")
BETTERSHIFT_API_KEY = os.getenv("BETTERSHIFT_API_KEY", "")


def _build_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if BETTERSHIFT_API_KEY:
        headers["X-API-Key"] = BETTERSHIFT_API_KEY
    return headers


async def forward_request(request, path: str):
    url = f"{BETTERSHIFT_BASE_URL}{path}"
    method = request.method
    params = dict(request.query_params)
    body: Optional[dict] = None
    if method in {"POST", "PUT", "PATCH"}:
        try:
            body = await request.json()
        except Exception:
            body = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(method, url, params=params, json=body, headers=_build_headers())

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    return JSONResponse(data, status_code=resp.status_code)
