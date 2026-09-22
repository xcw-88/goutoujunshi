from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sys

from src.auth import authenticated, router as auth_router
from src.routes.people import router as people_router
from src.routes.conversations import router as conversations_router
from src.routes.memories import router as memories_router
from src.routes.files import router as files_router


app = FastAPI(
    title="狗头军师 Cloudflare API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)
app.include_router(auth_router)
app.include_router(people_router)
app.include_router(conversations_router)
app.include_router(memories_router)
app.include_router(files_router)


@app.middleware("http")
async def guard_api(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/"):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "cross-origin request denied"}, status_code=403)
        if path not in {"/api/health", "/api/auth/login", "/api/auth/session"}:
            try:
                permitted = authenticated(request)
            except Exception as exc:
                from fastapi import HTTPException

                if isinstance(exc, HTTPException):
                    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
                raise
            if not permitted:
                return JSONResponse({"detail": "authentication required"}, status_code=401)
    response = await call_next(request)
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "runtime": "cloudflare-workers"}


if sys.platform == "emscripten":
    from workers import asgi

    Default = asgi.entrypoint(app)
