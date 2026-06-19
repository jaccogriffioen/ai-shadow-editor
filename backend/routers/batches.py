"""Batch lifecycle: create, configure, ingest images, and control processing."""
from __future__ import annotations

import copy
import shutil
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import config, models
from ..database import get_db
from ..services import processor

router = APIRouter(prefix="/api/batches", tags=["batches"])


def _serialize(session: Session, batch: models.Batch) -> dict:
    return batch.to_dict(counts=processor.counts(session, batch.id))


def _merged_config(overrides: dict | None) -> dict:
    cfg = copy.deepcopy(config.DEFAULT_CONFIG)
    if overrides:
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(cfg.get(key), dict):
                cfg[key].update(value)
            else:
                cfg[key] = value
    return cfg


def _get_batch(session: Session, batch_id: int) -> models.Batch:
    batch = session.get(models.Batch, batch_id)
    if batch is None:
        raise HTTPException(404, "Batch not found")
    return batch


@router.post("")
def create_batch(payload: dict = Body(default={}), session: Session = Depends(get_db)):
    batch = models.Batch(
        name=payload.get("name") or "Untitled batch",
        status="created",
    )
    batch.config = _merged_config(payload.get("config"))
    session.add(batch)
    session.commit()
    return _serialize(session, batch)


@router.get("")
def list_batches(session: Session = Depends(get_db)):
    batches = session.query(models.Batch).order_by(models.Batch.id.desc()).all()
    return [_serialize(session, b) for b in batches]


@router.get("/{batch_id}")
def get_batch(batch_id: int, session: Session = Depends(get_db)):
    return _serialize(session, _get_batch(session, batch_id))


@router.patch("/{batch_id}")
def update_batch(batch_id: int, payload: dict = Body(...), session: Session = Depends(get_db)):
    batch = _get_batch(session, batch_id)
    if "name" in payload:
        batch.name = payload["name"]
    if "config" in payload:
        merged = batch.config
        for key, value in (payload["config"] or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            else:
                merged[key] = value
        batch.config = merged
    session.commit()
    return _serialize(session, batch)


@router.delete("/{batch_id}")
def delete_batch(batch_id: int, session: Session = Depends(get_db)):
    batch = _get_batch(session, batch_id)
    session.delete(batch)
    session.commit()
    shutil.rmtree(config.batch_root(batch_id), ignore_errors=True)
    return {"ok": True}


def _unique_path(directory: Path, filename: str) -> Path:
    name = Path(filename).name or "image"
    target = directory / name
    i = 1
    while target.exists():
        target = directory / f"{Path(name).stem}_{i}{Path(name).suffix}"
        i += 1
    return target


@router.post("/{batch_id}/upload")
def upload_images(
    batch_id: int,
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_db),
):
    batch = _get_batch(session, batch_id)
    input_dir = config.batch_subdir(batch_id, "input")
    added = 0
    for upload in files:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in config.SUPPORTED_EXTENSIONS:
            continue
        dest = _unique_path(input_dir, upload.filename or "image")
        with dest.open("wb") as out:
            shutil.copyfileobj(upload.file, out)
        session.add(models.Image(
            batch_id=batch_id, filename=dest.name,
            original_path=str(dest), status="pending",
        ))
        added += 1
    session.commit()
    return {"added": added, "batch": _serialize(session, batch)}


@router.post("/{batch_id}/scan")
def scan_folder(batch_id: int, payload: dict = Body(...), session: Session = Depends(get_db)):
    """Reference images from a local folder in place (no copy). The real path
    for the 4,000-image workflow."""
    batch = _get_batch(session, batch_id)
    raw = (payload.get("path") or "").strip()
    if not raw:
        raise HTTPException(400, "No folder path provided")
    folder = Path(raw).expanduser()
    if not folder.is_dir():
        raise HTTPException(400, f"Not a folder: {folder}")

    existing = {
        p for (p,) in session.query(models.Image.original_path)
        .filter(models.Image.batch_id == batch_id).all()
    }
    added = 0
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() not in config.SUPPORTED_EXTENSIONS:
            continue
        if str(path) in existing:
            continue
        session.add(models.Image(
            batch_id=batch_id, filename=path.name,
            original_path=str(path), status="pending",
        ))
        added += 1
    batch.source_dir = str(folder)
    session.commit()
    return {"added": added, "batch": _serialize(session, batch)}


@router.post("/{batch_id}/start")
async def start_batch(batch_id: int, session: Session = Depends(get_db)):
    batch = _get_batch(session, batch_id)
    pending = (
        session.query(models.Image)
        .filter(models.Image.batch_id == batch_id, models.Image.status == "pending")
        .count()
    )
    if pending == 0:
        raise HTTPException(400, "No pending images to process")
    if not processor.start(batch_id):
        raise HTTPException(409, "Batch is already processing")
    return {"ok": True, "pending": pending}


@router.post("/{batch_id}/pause")
def pause_batch(batch_id: int):
    if not processor.pause(batch_id):
        raise HTTPException(409, "Batch is not currently processing")
    return {"ok": True}


@router.post("/{batch_id}/resume")
async def resume_batch(batch_id: int, session: Session = Depends(get_db)):
    return await start_batch(batch_id, session)


@router.post("/{batch_id}/cancel")
def cancel_batch(batch_id: int):
    if not processor.cancel(batch_id):
        raise HTTPException(409, "Batch is not currently processing")
    return {"ok": True}


@router.post("/{batch_id}/sample")
async def sample_batch(batch_id: int, payload: dict = Body(default={}), session: Session = Depends(get_db)):
    """Process a single image with the current (or overridden) settings so the
    user can preview the look before committing the whole batch."""
    import asyncio

    _get_batch(session, batch_id)
    first = (
        session.query(models.Image.id)
        .filter(models.Image.batch_id == batch_id)
        .order_by(models.Image.id)
        .first()
    )
    if first is None:
        raise HTTPException(400, "Batch has no images yet")
    image_id = first[0]
    result = await asyncio.to_thread(
        processor.process_image_sync, image_id, payload.get("config")
    )
    return result
