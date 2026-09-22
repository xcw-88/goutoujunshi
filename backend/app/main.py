from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.files import router as files_router
from app.api.health import router as health_router
from app.api.imports import router as imports_router
from app.api.memories import router as memories_router
from app.api.people import router as people_router
from app.core.database import init_database
from app.core.logging import configure_logging


configure_logging()
logger = logging.getLogger("goutoujunshi.http")

@asynccontextmanager
async def lifespan(application: FastAPI):
    if not getattr(application.state, "skip_database_init", False):
        init_database()
    yield


app = FastAPI(
    title="Goutoujunshi Web API",
    version="0.1.0",
    description="Local, single-user API for the goutoujunshi skill.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("route=%s error_type=unhandled", request.url.path)
        raise
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "route=%s method=%s status=%s latency_ms=%s",
        request.url.path,
        request.method,
        response.status_code,
        latency_ms,
    )
    return response


app.include_router(health_router)
app.include_router(people_router)
app.include_router(conversations_router)
app.include_router(memories_router)
app.include_router(files_router)
app.include_router(imports_router)
app.include_router(chat_router)
