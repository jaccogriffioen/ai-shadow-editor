"""Background removal backends.

Removing the product from its background deletes the original (large) shadow by
definition. A new, small, consistent shadow is then composited in shadow.py.

  - "fal"   : fal.ai removal model (BRIA / BiRefNet) — uses API credits
  - "rembg" : local u2net removal — offline, free
"""
from __future__ import annotations

import io

import requests
from PIL import Image

# rembg is heavy; import lazily and cache the session.
_REMBG_SESSION = None


def _get_rembg_session():
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        from rembg import new_session
        _REMBG_SESSION = new_session("u2net")
    return _REMBG_SESSION


def remove_background_rembg(image: Image.Image) -> Image.Image:
    """Local background removal via rembg/u2net. Returns RGBA."""
    from rembg import remove
    if image.mode != "RGB":
        image = image.convert("RGB")
    return remove(image, session=_get_rembg_session()).convert("RGBA")


def remove_background_fal(path: str, model: str) -> Image.Image:
    """Background removal via a fal.ai model. Returns RGBA.
    Requires FAL_KEY in the environment."""
    import fal_client

    image_url = fal_client.upload_file(path)
    result = fal_client.subscribe(model, arguments={"image_url": image_url}, with_logs=False)
    out_url = _extract_image_url(result)
    if not out_url:
        raise RuntimeError(
            f"{model} returned no image (keys: {list(result.keys()) if isinstance(result, dict) else type(result)})"
        )
    resp = requests.get(out_url, timeout=180)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGBA")


def _extract_image_url(result: dict) -> str | None:
    if not isinstance(result, dict):
        return None
    img = result.get("image")
    if isinstance(img, dict) and img.get("url"):
        return img["url"]
    if isinstance(img, str):
        return img
    images = result.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict):
            return first.get("url")
        if isinstance(first, str):
            return first
    return None
