"""Fail-closed single-user authentication for the cloud API.

Static frontend files contain no private data and bypass Python; every data/API
route requires this signed, HttpOnly cookie. Secrets are Worker bindings only.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from src.common import env


router = APIRouter(prefix="/api/auth", tags=["auth"])
COOKIE_NAME = "goutou_session"
SESSION_SECONDS = 7 * 24 * 60 * 60


class LoginInput(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


def _secrets(request: Request) -> tuple[str, str]:
    bindings = env(request)
    password = str(getattr(bindings, "GOUTOU_ACCESS_PASSWORD", ""))
    key = str(getattr(bindings, "GOUTOU_SESSION_SECRET", ""))
    if not password or len(key) < 32:
        raise HTTPException(503, "cloud authentication is not configured")
    return password, key


def _signature(expires: int, key: str) -> str:
    return hmac.new(key.encode(), str(expires).encode(), hashlib.sha256).hexdigest()


def authenticated(request: Request) -> bool:
    _, key = _secrets(request)
    token = request.cookies.get(COOKIE_NAME, "")
    expires_text, separator, signature = token.partition(".")
    if not separator or not expires_text.isascii() or not expires_text.isdecimal():
        return False
    expires = int(expires_text)
    if expires <= int(time.time()) or expires > int(time.time()) + SESSION_SECONDS:
        return False
    return hmac.compare_digest(signature, _signature(expires, key))


@router.post("/login")
async def login(payload: LoginInput, request: Request, response: Response) -> dict[str, bool]:
    password, key = _secrets(request)
    if not hmac.compare_digest(payload.password.encode(), password.encode()):
        raise HTTPException(401, "口令不正确")
    expires = int(time.time()) + SESSION_SECONDS
    response.set_cookie(
        COOKIE_NAME, f"{expires}.{_signature(expires, key)}",
        max_age=SESSION_SECONDS, path="/", httponly=True, secure=True, samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": True}


@router.get("/session")
async def session(request: Request) -> dict[str, bool]:
    return {"authenticated": authenticated(request)}


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="strict")
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": False}
