from fastapi import FastAPI
import sys

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
app.include_router(people_router)
app.include_router(conversations_router)
app.include_router(memories_router)
app.include_router(files_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "runtime": "cloudflare-workers"}


if sys.platform == "emscripten":
    from workers import asgi

    Default = asgi.entrypoint(app)
