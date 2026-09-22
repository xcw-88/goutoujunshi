from fastapi import FastAPI
import sys


app = FastAPI(
    title="狗头军师 Cloudflare API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "runtime": "cloudflare-workers"}


if sys.platform == "emscripten":
    from workers import asgi

    Default = asgi.entrypoint(app)
