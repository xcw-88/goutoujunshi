from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request

from src.db import Database


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid4().hex


def env(request: Request) -> Any:
    return request.scope["env"]


def db(request: Request) -> Database:
    return Database(env(request).DB)


def require(row: dict[str, Any] | None, resource: str) -> dict[str, Any]:
    if row is None:
        raise HTTPException(404, f"{resource} not found")
    return row
