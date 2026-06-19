"""Generative instruction-editing via fal.ai.

Each image is sent to a fal.ai image-editing model together with a text
instruction (the prompt). The model returns the fully edited image — there is
no separate background-removal or shadow-compositing step. The editing model is
chosen per batch; different models use slightly different argument/response
shapes, handled here.
"""
from __future__ import annotations

import io

import requests
from PIL import Image

from .. import config


def _extract_image_url(result: dict) -> str | None:
    if not isinstance(result, dict):
        return None
    images = result.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict):
            return first.get("url")
        if isinstance(first, str):
            return first
    img = result.get("image")
    if isinstance(img, dict) and img.get("url"):
        return img["url"]
    if isinstance(img, str):
        return img
    return None


def edit_image_fal(path: str, model: str, prompt: str, extra: dict | None = None) -> Image.Image:
    """Run a fal.ai editing model on a local image and return the result (RGB).

    Requires FAL_KEY in the environment.
    """
    import fal_client

    if not prompt or not prompt.strip():
        prompt = config.DEFAULT_PROMPT

    image_url = fal_client.upload_file(path)
    args: dict = {"prompt": prompt}
    if model in config.IMAGE_URLS_MODELS:
        args["image_urls"] = [image_url]
    else:
        args["image_url"] = image_url
    if extra:
        args.update(extra)

    result = fal_client.subscribe(model, arguments=args, with_logs=False)
    out_url = _extract_image_url(result)
    if not out_url:
        raise RuntimeError(
            f"{model} returned no image (keys: {list(result.keys()) if isinstance(result, dict) else type(result)})"
        )
    resp = requests.get(out_url, timeout=180)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")
