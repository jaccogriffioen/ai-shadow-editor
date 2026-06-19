"""Export approved (and reverted) images to a local folder.

Approved images are exported as the processed result, converted to the batch's
chosen output format. Reverted images are exported as the untouched original.
Originals are never modified.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/api/batches", tags=["export"])

_EXT = {"jpg": ".jpg", "jpeg": ".jpg", "png": ".png", "webp": ".webp"}


def _save_as(result_path: str, dest: Path, fmt: str) -> None:
    im = PILImage.open(result_path)
    if fmt in ("jpg", "jpeg"):
        im.convert("RGB").save(dest, "JPEG", quality=95)
    elif fmt == "webp":
        im.save(dest, "WEBP", quality=92)
    else:  # png
        im.save(dest, "PNG")


def _unique(dest_dir: Path, filename: str) -> Path:
    target = dest_dir / filename
    i = 1
    while target.exists():
        target = dest_dir / f"{Path(filename).stem}_{i}{Path(filename).suffix}"
        i += 1
    return target


@router.post("/{batch_id}/export")
def export_batch(batch_id: int, payload: dict = Body(...), session: Session = Depends(get_db)):
    batch = session.get(models.Batch, batch_id)
    if batch is None:
        raise HTTPException(404, "Batch not found")

    dest_raw = (payload.get("dest") or "").strip()
    if not dest_raw:
        raise HTTPException(400, "No destination folder provided")
    dest_dir = Path(dest_raw).expanduser()
    dest_dir.mkdir(parents=True, exist_ok=True)

    out_fmt = batch.config.get("output_format", "original")
    images = session.query(models.Image).filter(models.Image.batch_id == batch_id).all()

    exported = approved = reverted = skipped = 0
    errors: list[str] = []

    for img in images:
        try:
            if img.review_status == "approved" and img.result_path and Path(img.result_path).exists():
                stem = Path(img.filename).stem
                if out_fmt == "original":
                    ext = Path(img.filename).suffix.lower() or ".png"
                    fmt = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp"}.get(
                        ext.lstrip("."), "png"
                    )
                else:
                    ext = _EXT.get(out_fmt, ".png")
                    fmt = out_fmt
                target = _unique(dest_dir, f"{stem}{ext}")
                _save_as(img.result_path, target, fmt)
                exported += 1
                approved += 1
            elif img.review_status == "reverted" and Path(img.original_path).exists():
                target = _unique(dest_dir, Path(img.original_path).name)
                shutil.copy2(img.original_path, target)
                exported += 1
                reverted += 1
            else:
                skipped += 1
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            errors.append(f"{img.filename}: {exc}")

    return {
        "dest": str(dest_dir), "exported": exported, "approved": approved,
        "reverted": reverted, "skipped": skipped, "errors": errors,
    }
