from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request

from app.schemas.settings import SettingsRead, SettingsUpdate
from common import db, env, now


router = APIRouter(prefix="/api/settings", tags=["settings"])
MODEL_KEYS = ("base_url", "model", "temperature", "max_tokens")
GEMINI_HOST = "generativelanguage.googleapis.com"
ENV_KEYS = {
    "base_url": "GOUTOU_API_BASE",
    "model": "GOUTOU_MODEL",
    "temperature": "GOUTOU_TEMPERATURE",
    "max_tokens": "GOUTOU_MAX_TOKENS",
}


def api_key_secret(base_url: str) -> str:
    return "GOUTOU_GEMINI_API_KEY" if urlparse(base_url).hostname == GEMINI_HOST else "GOUTOU_API_KEY"


async def values(request: Request) -> dict:
    rows = await db(request).all("SELECT key, value FROM settings")
    stored = {row["key"]: row["value"] for row in rows}
    bindings = env(request)
    result = {
        key: stored.get(key, str(getattr(bindings, ENV_KEYS[key], "")))
        for key in MODEL_KEYS
    }
    result["temperature"] = float(result["temperature"] or 0.7)
    result["max_tokens"] = int(result["max_tokens"] or 1200)
    result["api_key"] = str(getattr(bindings, api_key_secret(result["base_url"]), ""))
    return result


@router.get("", response_model=SettingsRead)
async def read_settings(request: Request) -> SettingsRead:
    current = await values(request)
    has_key = bool(current.pop("api_key"))
    return SettingsRead(**current, api_key_configured=has_key, api_key_masked="Secret 已配置" if has_key else None)


@router.patch("", response_model=SettingsRead)
async def update_settings(payload: SettingsUpdate, request: Request) -> SettingsRead:
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("api_key") or changes.get("clear_api_key"):
        raise HTTPException(400, "API Key must be changed using the GOUTOU_API_KEY Worker Secret")
    if "base_url" in changes and changes["base_url"] is not None:
        parsed = urlparse(changes["base_url"])
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise HTTPException(400, "cloud model base_url must be HTTPS without embedded credentials")
    for key in MODEL_KEYS:
        value = changes.get(key)
        if value is not None:
            await db(request).run(
                """INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
                key, str(value), now(),
            )
    return await read_settings(request)
