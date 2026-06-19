"""Batch processing orchestration.

Runs the per-image pipeline in a worker thread (fal.ai calls are blocking),
streams progress over WebSocket, and supports pause / resume / cancel. State is
persisted per image so an interrupted batch resumes from where it stopped.
"""
from __future__ import annotations

import asyncio

from PIL import Image as PILImage
from sqlalchemy import func

from .. import config, models
from ..database import SessionLocal
from . import editing, quality
from .ws import manager

# batch_id -> control dict {"pause": bool, "cancel": bool, "task": asyncio.Task}
RUNNING: dict[int, dict] = {}


def is_running(batch_id: int) -> bool:
    return batch_id in RUNNING


def counts(session, batch_id: int) -> dict:
    rows = (
        session.query(models.Image.status, func.count())
        .filter(models.Image.batch_id == batch_id)
        .group_by(models.Image.status)
        .all()
    )
    by = {status: n for status, n in rows}
    flagged = (
        session.query(func.count())
        .filter(
            models.Image.batch_id == batch_id,
            models.Image.flagged.is_(True),
            models.Image.status == "done",
        )
        .scalar()
    )
    return {
        "total": sum(by.values()),
        "done": by.get("done", 0),
        "pending": by.get("pending", 0),
        "processing": by.get("processing", 0),
        "error": by.get("error", 0),
        "flagged": flagged or 0,
    }


def process_image_sync(image_id: int, overrides: dict | None = None) -> dict:
    """Run the generative edit for one image in its own DB session.
    Safe to call from a worker thread. Returns a small summary dict.

    `overrides` is a partial config merged over the batch config — used when
    re-processing a single image with an adjusted prompt or model from the
    review screen.
    """
    session = SessionLocal()
    try:
        img = session.get(models.Image, image_id)
        if img is None:
            return {"id": image_id, "status": "error", "error": "image not found"}
        batch = session.get(models.Batch, img.batch_id)
        cfg = {**config.DEFAULT_CONFIG, **batch.config}
        if overrides:
            cfg = {**cfg, **{k: v for k, v in overrides.items() if v is not None}}

        img.status = "processing"
        session.commit()

        original = PILImage.open(img.original_path)
        original.load()

        model = cfg.get("fal_model") or config.DEFAULT_CONFIG["fal_model"]
        # Only FLUX Kontext accepts guidance_scale; other models reject unknown args.
        extra = {}
        if "kontext" in model and cfg.get("guidance_scale") is not None:
            extra["guidance_scale"] = cfg["guidance_scale"]
        result = editing.edit_image_fal(
            img.original_path, model,
            cfg.get("prompt") or config.DEFAULT_PROMPT,
            extra=extra,
        )

        reasons = quality.evaluate(original.convert("RGB"), result)

        out_dir = config.batch_subdir(img.batch_id, "processed")
        out_path = out_dir / f"{image_id}.png"
        result.save(out_path)

        # Clear any stale thumbnail cache for this image.
        cache = config.batch_subdir(img.batch_id, "cache")
        for f in cache.glob(f"{image_id}_*.jpg"):
            f.unlink(missing_ok=True)

        img.result_path = str(out_path)
        img.status = "done"
        img.flagged = bool(reasons)
        img.reasons = reasons
        img.review_status = "pending"
        img.error = None
        session.commit()
        return {
            "id": image_id, "filename": img.filename, "status": "done",
            "flagged": img.flagged, "reasons": reasons,
        }
    except Exception as exc:  # noqa: BLE001 — any failure flags the image
        session.rollback()
        img = session.get(models.Image, image_id)
        if img is not None:
            img.status = "error"
            img.error = str(exc)
            img.flagged = True
            img.reasons = [f"Processing error: {exc}"]
            session.commit()
        return {"id": image_id, "status": "error", "error": str(exc)}
    finally:
        session.close()


def _next_pending_id(session, batch_id: int):
    row = (
        session.query(models.Image.id)
        .filter(models.Image.batch_id == batch_id, models.Image.status == "pending")
        .order_by(models.Image.id)
        .first()
    )
    return row[0] if row else None


async def run_batch(batch_id: int) -> None:
    ctrl = RUNNING[batch_id]
    session = SessionLocal()
    try:
        batch = session.get(models.Batch, batch_id)
        if batch is None:
            return
        batch.status = "processing"
        session.commit()
        await manager.broadcast(batch_id, {
            "type": "status", "status": "processing", "counts": counts(session, batch_id),
        })

        while True:
            if ctrl["cancel"] or ctrl["pause"]:
                break
            image_id = _next_pending_id(session, batch_id)
            if image_id is None:
                break

            result = await asyncio.to_thread(process_image_sync, image_id)
            session.expire_all()  # refresh counts from the worker's commit
            await manager.broadcast(batch_id, {
                "type": "progress",
                "image": result,
                "counts": counts(session, batch_id),
            })

        # Decide final status.
        remaining = _next_pending_id(session, batch_id)
        if ctrl["cancel"] or ctrl["pause"]:
            final = "paused"
        elif remaining is None:
            final = "done"
        else:
            final = "paused"
        batch = session.get(models.Batch, batch_id)
        batch.status = final
        session.commit()
        await manager.broadcast(batch_id, {
            "type": "status", "status": final, "counts": counts(session, batch_id),
        })
    finally:
        session.close()
        RUNNING.pop(batch_id, None)


def start(batch_id: int) -> bool:
    """Launch processing for a batch. Returns False if already running."""
    if batch_id in RUNNING:
        return False
    ctrl = {"pause": False, "cancel": False, "task": None}
    RUNNING[batch_id] = ctrl
    ctrl["task"] = asyncio.create_task(run_batch(batch_id))
    return True


def pause(batch_id: int) -> bool:
    ctrl = RUNNING.get(batch_id)
    if not ctrl:
        return False
    ctrl["pause"] = True
    return True


def cancel(batch_id: int) -> bool:
    ctrl = RUNNING.get(batch_id)
    if not ctrl:
        return False
    ctrl["cancel"] = True
    return True


def recover_on_startup() -> None:
    """Mark interrupted work so it can be resumed cleanly after a restart."""
    session = SessionLocal()
    try:
        session.query(models.Image).filter(models.Image.status == "processing").update(
            {models.Image.status: "pending"}
        )
        session.query(models.Batch).filter(models.Batch.status == "processing").update(
            {models.Batch.status: "paused"}
        )
        session.commit()
    finally:
        session.close()
