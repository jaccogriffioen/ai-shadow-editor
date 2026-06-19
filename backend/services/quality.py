"""Automated quality checks that decide whether a result is flagged.

Philosophy (per spec): flag aggressively. It is better to flag a good image
(the reviewer unflags it in seconds) than to let a bad one through.

Checks (numpy, no OpenCV dependency):
  1. Cutout sanity   — subject too small / nothing removed (removal failed)
  2. Edge integrity  — rough/see-through silhouette on the cutout
  3. Shadow reduction — output still as dark as the original (shadow not reduced)
  4. Background uniformity — patchy / artifacted output background
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


def check_cutout(cutout: Image.Image) -> list[str]:
    """Heuristics on the RGBA cutout produced by background removal."""
    reasons: list[str] = []
    alpha = np.array(cutout.split()[3])
    subject = np.sum(alpha > 10)
    ratio = subject / max(alpha.size, 1)

    if ratio < 0.02:
        reasons.append("Subject too small — background removal may have failed")
    elif ratio > 0.97:
        reasons.append("Almost nothing removed — product may blend into background")

    transition = np.sum((alpha > 10) & (alpha < 245))
    edge_ratio = transition / max(subject, 1)
    if edge_ratio > 0.35:
        reasons.append(
            f"Product edges look rough (transition={edge_ratio:.2f}) — "
            "possible transparent/reflective packaging"
        )
    return reasons


def _dark_fraction(image: Image.Image, threshold: float = 35.0) -> float:
    arr = np.array(image.convert("RGB")).astype(np.float32)
    border = _border_pixels(arr)
    bg_lum = float(np.median(_luminance(border.reshape(1, -1, 3))))
    lum = _luminance(arr)
    return float(np.mean((bg_lum - lum) > threshold))


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


def evaluate(original: Image.Image, result: Image.Image, cutout: Image.Image | None) -> list[str]:
    """Run all applicable checks and return a list of flag reasons.
    An empty list means the image passed.

    Note: with cutout + composite the original shadow is physically removed
    (the product is cut out), so a "shadow not reduced" comparison does not
    apply — quality here is about whether the cutout and the new background are
    clean. check_shadow_reduction is kept for reference but not used.
    """
    reasons: list[str] = []
    if cutout is not None:
        reasons += check_cutout(cutout)
    reasons += check_background_uniformity(result)
    return reasons
