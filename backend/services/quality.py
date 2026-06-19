"""Automated quality checks that decide whether an edited image is flagged.

Philosophy (per spec): flag aggressively. It is better to flag a good image
(the reviewer unflags it in seconds) than to let a bad one through.

With instruction editing the model returns a full edited image, so the checks
compare the original against the result:
  1. No-change      — the model returned essentially the same image (edit failed)
  2. Shadow reduction — the result is still as dark as the original (shadow kept)
  3. Background uniformity — the result background is patchy / artifacted
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def _luminance(arr: np.ndarray) -> np.ndarray:
    return 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]


def _border_pixels(arr: np.ndarray, frac: float = 0.05) -> np.ndarray:
    h, w = arr.shape[:2]
    m = max(1, int(min(h, w) * frac))
    return np.concatenate([
        arr[:m, :].reshape(-1, 3), arr[-m:, :].reshape(-1, 3),
        arr[:, :m].reshape(-1, 3), arr[:, -m:].reshape(-1, 3),
    ], axis=0)


def _dark_fraction(image: Image.Image, threshold: float = 35.0) -> float:
    """Fraction of pixels meaningfully darker than the border background."""
    arr = np.array(image.convert("RGB")).astype(np.float32)
    border = _border_pixels(arr)
    bg_lum = float(np.median(_luminance(border.reshape(1, -1, 3))))
    lum = _luminance(arr)
    return float(np.mean((bg_lum - lum) > threshold))


def check_no_change(original: Image.Image, result: Image.Image) -> list[str]:
    a = np.asarray(original.convert("RGB").resize((256, 256))).astype(np.float32)
    b = np.asarray(result.convert("RGB").resize((256, 256))).astype(np.float32)
    diff = float(np.mean(np.abs(a - b)))
    if diff < 3.0:
        return ["AI made little or no visible change to the image"]
    return []


def check_shadow_reduction(original: Image.Image, result: Image.Image) -> list[str]:
    before = _dark_fraction(original)
    after = _dark_fraction(result)
    if before <= 1e-4:
        return []
    if after / before > 0.8:
        return [
            f"Shadow not sufficiently reduced "
            f"(dark area {after / before * 100:.0f}% of original)"
        ]
    return []


def check_background_uniformity(result: Image.Image) -> list[str]:
    arr = np.array(result.convert("RGB")).astype(np.float32)
    border = _border_pixels(arr, frac=0.06)
    spread = float(np.mean(np.std(border, axis=0)))
    if spread > 18.0:
        return [f"Background looks patchy/non-uniform (spread={spread:.1f})"]
    return []


def evaluate(original: Image.Image, result: Image.Image) -> list[str]:
    """Run all checks and return a list of flag reasons.
    An empty list means the image passed."""
    reasons: list[str] = []
    reasons += check_no_change(original, result)
    reasons += check_shadow_reduction(original, result)
    reasons += check_background_uniformity(result)
    return reasons
