from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import sys

from auth import authenticated, router as auth_router
from routes.people import router as people_router
from routes.conversations import router as conversations_router
from routes.memories import router as memories_router
from routes.files import router as files_router
from routes.settings import router as settings_router
from routes.chat import router as chat_router
from routes.imports import router as imports_router


app = FastAPI(
    title="狗头军师 Cloudflare API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(auth_router)
app.include_router(people_router)
app.include_router(conversations_router)
app.include_router(memories_router)
app.include_router(files_router)
app.include_router(settings_router)
app.include_router(chat_router)
app.include_router(imports_router)


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
            except HTTPException as exc:
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
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
