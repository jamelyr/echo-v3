"""
BetterShift client for Echo V3.
Provides minimal async wrappers around the BetterShift API.
"""
import os
from typing import Any, Dict, List, Optional
import httpx

BETTERSHIFT_BASE_URL = os.getenv("BETTERSHIFT_BASE_URL", "http://127.0.0.1:3000")
BETTERSHIFT_API_KEY = os.getenv("BETTERSHIFT_API_KEY", "")

# Shared client for connection pooling (saves ~10-20MB)
_client: Optional[httpx.AsyncClient] = None


def _build_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    if BETTERSHIFT_API_KEY:
        headers["X-API-Key"] = BETTERSHIFT_API_KEY
    return headers


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=20.0, limits=httpx.Limits(max_connections=10))
    return _client


async def request(method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{BETTERSHIFT_BASE_URL}{path}"
    client = _get_client()
    resp = await client.request(method, url, params=params, json=json, headers=_build_headers())
    if resp.status_code >= 400:
        raise RuntimeError(f"BetterShift API error {resp.status_code}: {resp.text}")
    if resp.text:
        try:
            return resp.json()
        except Exception:
            return {"raw": resp.text}
    return None


async def list_calendars() -> List[Dict[str, Any]]:
    data = await request("GET", "/api/calendars")
    return data or []


def _normalize_shift_date(shift: Dict[str, Any]) -> Dict[str, Any]:
    date_value = shift.get("date")
    if isinstance(date_value, str) and "T" in date_value:
        shift = {**shift}
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo

            tz_name = os.getenv("TZ")
            local_tz = ZoneInfo(tz_name) if tz_name else ZoneInfo("UTC")
            iso_value = date_value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_value)
            if dt.tzinfo is not None:
                dt = dt.astimezone(local_tz)
            shift["date"] = dt.date().isoformat()
        except Exception:
            shift["date"] = date_value.split("T", 1)[0]
    return shift


async def list_shifts(calendar_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"calendarId": calendar_id}
    if date:
        params["date"] = date
    data = await request("GET", "/api/shifts", params=params)
    shifts = data or []
    normalized = [_normalize_shift_date(s) for s in shifts]
    if date:
        for shift in normalized:
            shift["date"] = date
    return normalized


async def create_shift(
    calendar_id: str,
    title: str,
    date: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    color: Optional[str] = None,
    notes: Optional[str] = None,
    is_all_day: bool = False,
    is_secondary: bool = False,
    preset_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "calendarId": calendar_id,
        "title": title,
        "date": date,
        "startTime": start_time,
        "endTime": end_time,
        "color": color,
        "notes": notes,
        "isAllDay": is_all_day,
        "isSecondary": is_secondary,
        "presetId": preset_id,
    }
    return await request("POST", "/api/shifts", json=payload)


async def list_presets(calendar_id: str) -> List[Dict[str, Any]]:
    data = await request("GET", "/api/presets", params={"calendarId": calendar_id})
    return data or []


async def create_preset(
    calendar_id: str,
    title: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    color: Optional[str] = None,
    notes: Optional[str] = None,
    is_secondary: bool = False,
    is_all_day: bool = False,
    hide_from_stats: bool = False,
) -> Dict[str, Any]:
    payload = {
        "calendarId": calendar_id,
        "title": title,
        "startTime": start_time or "09:00",
        "endTime": end_time or "17:00",
        "color": color,
        "notes": notes,
        "isSecondary": is_secondary,
        "isAllDay": is_all_day,
        "hideFromStats": hide_from_stats,
    }
    return await request("POST", "/api/presets", json=payload)


async def delete_preset(preset_id: str) -> Dict[str, Any]:
    return await request("DELETE", f"/api/presets/{preset_id}")


async def delete_shift(shift_id: str) -> Dict[str, Any]:
    return await request("DELETE", f"/api/shifts/{shift_id}")


async def delete_note(note_id: str) -> Dict[str, Any]:
    return await request("DELETE", f"/api/notes/{note_id}")


def _normalize_note_date(note: Dict[str, Any]) -> Dict[str, Any]:
    date_value = note.get("date")
    if isinstance(date_value, str) and "T" in date_value:
        note = {**note}
        note["date"] = date_value.split("T", 1)[0]
    return note


async def list_notes(calendar_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"calendarId": calendar_id}
    if date:
        params["date"] = date
    data = await request("GET", "/api/notes", params=params)
    notes = data or []
    normalized = [_normalize_note_date(n) for n in notes]
    if date:
        for note in normalized:
            note["date"] = date
    return normalized


async def create_note(
    calendar_id: str,
    date: str,
    note: str,
    note_type: str = "note",
    color: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "calendarId": calendar_id,
        "date": date,
        "note": note,
        "type": note_type,
        "color": color,
    }
    return await request("POST", "/api/notes", json=payload)
