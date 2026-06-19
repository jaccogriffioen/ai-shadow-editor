"""Per-image endpoints: listing, file/thumbnail serving, review actions, reprocess."""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from .. import config, models
from ..database import get_db
from ..services import processor

router = APIRouter(prefix="/api", tags=["images"])


@router.get("/batches/{batch_id}/images")
def list_images(
    batch_id: int,
    status: str | None = None,
    flagged: bool | None = None,
    review: str | None = None,
    page: int = 1,
    page_size: int = 60,
    session: Session = Depends(get_db),
):
    q = session.query(models.Image).filter(models.Image.batch_id == batch_id)
    if status:
        q = q.filter(models.Image.status == status)
    if flagged is not None:
        q = q.filter(models.Image.flagged.is_(flagged))
    if review:
        q = q.filter(models.Image.review_status == review)
    total = q.count()
    items = (
        q.order_by(models.Image.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [i.to_dict() for i in items],
        "total": total, "page": page, "page_size": page_size,
    }


def _get_image(session: Session, image_id: int) -> models.Image:
    img = session.get(models.Image, image_id)
    if img is None:
        raise HTTPException(404, "Image not found")
    return img


@router.get("/images/{image_id}/original")
def get_original(image_id: int, session: Session = Depends(get_db)):
    img = _get_image(session, image_id)
    if not Path(img.original_path).exists():
        raise HTTPException(404, "Original file missing")
    return FileResponse(img.original_path)


@router.get("/images/{image_id}/result")
def get_result(image_id: int, session: Session = Depends(get_db)):
    img = _get_image(session, image_id)
    if not img.result_path or not Path(img.result_path).exists():
        raise HTTPException(404, "No result yet")
    return FileResponse(img.result_path)


@router.get("/images/{image_id}/thumb")
def get_thumb(
    image_id: int,
    which: str = Query("result", pattern="^(result|original)$"),
    size: int = 320,
    session: Session = Depends(get_db),
):
    img = _get_image(session, image_id)
    src = img.result_path if which == "result" else img.original_path
    if which == "result" and (not src or not Path(src).exists()):
        src = img.original_path  # fall back to original if not processed yet
    if not src or not Path(src).exists():
        raise HTTPException(404, "Image file missing")

    cache_dir = config.batch_subdir(img.batch_id, "cache")
    cache_file = cache_dir / f"{image_id}_{which}_{size}.jpg"
    if not cache_file.exists():
        im = PILImage.open(src)
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.thumbnail((size, size))
        im.save(cache_file, "JPEG", quality=82)
    return FileResponse(cache_file)


# --- Review actions ----------------------------------------------------------

@router.post("/images/{image_id}/approve")
def approve(image_id: int, session: Session = Depends(get_db)):
    img = _get_image(session, image_id)
    img.review_status = "approved"
    session.commit()
    return img.to_dict()


@router.post("/images/{image_id}/revert")
def revert(image_id: int, session: Session = Depends(get_db)):
    img = _get_image(session, image_id)
    img.review_status = "reverted"
    session.commit()
    return img.to_dict()


@router.post("/images/{image_id}/flag")
def flag(image_id: int, session: Session = Depends(get_db)):
    img = _get_image(session, image_id)
    img.flagged = True
    session.commit()
    return img.to_dict()


@router.post("/images/{image_id}/unflag")
def unflag(image_id: int, session: Session = Depends(get_db)):
    img = _get_image(session, image_id)
    img.flagged = False
    session.commit()
    return img.to_dict()


@router.post("/images/{image_id}/reprocess")
async def reprocess(image_id: int, payload: dict = Body(default={}), session: Session = Depends(get_db)):
    """Re-run the pipeline on a single image, optionally with adjusted settings."""
    _get_image(session, image_id)
    result = await asyncio.to_thread(
        processor.process_image_sync, image_id, payload.get("config")
    )
    return result
