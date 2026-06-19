"""AI Shadow Editor — FastAPI application entrypoint.

Run from the project root:
    venv/bin/uvicorn backend.main:app --port 8000
Then open http://localhost:8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .database import init_db
from .routers import batches, export, images
from .services import processor
from .services.ws import manager

FRONTEND_DIR = config.BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    processor.recover_on_startup()
    yield


app = FastAPI(title="AI Shadow Editor", lifespan=lifespan)

app.include_router(batches.router)
app.include_router(images.router)
app.include_router(export.router)


@app.get("/api/status")
def status():
    return {
        "ok": True,
        "fal_key_present": bool(config.FAL_KEY),
        "default_config": config.DEFAULT_CONFIG,
        "removal_models": config.REMOVAL_MODELS,
    }


@app.websocket("/ws/batches/{batch_id}")
async def batch_ws(websocket: WebSocket, batch_id: int):
    await manager.connect(batch_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keepalive; client messages ignored
    except WebSocketDisconnect:
        manager.disconnect(batch_id, websocket)
    except Exception:
        manager.disconnect(batch_id, websocket)


# --- Static frontend ---------------------------------------------------------
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def index():
    """Serve index.html with a cache-busting version on app.js (its mtime), so
    the browser always fetches the latest frontend after an edit."""
    html = (FRONTEND_DIR / "index.html").read_text()
    version = int((FRONTEND_DIR / "app.js").stat().st_mtime)
    html = html.replace("/static/app.js", f"/static/app.js?v={version}")
    return HTMLResponse(html, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
