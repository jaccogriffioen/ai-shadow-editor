"""Application configuration, paths, and environment loading."""
import os
from pathlib import Path

# Project root (one level above /backend)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BATCHES_DIR = DATA_DIR / "batches"
DB_PATH = DATA_DIR / "shadow_editor.db"

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def _load_env() -> None:
    """Minimal .env loader (avoids a python-dotenv dependency).

    Lines are KEY=VALUE; existing environment variables win.
    """
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


_load_env()

# fal.ai reads FAL_KEY from the environment; we expose it for status checks.
FAL_KEY = os.environ.get("FAL_KEY", "")

# Background-removal options selectable per batch. The product is cut out
# (which removes the original shadow entirely) and a new, small, consistent
# shadow is composited underneath.
REMOVAL_MODELS = [
    {"id": "bria", "label": "fal.ai BRIA (recommended)", "backend": "fal",
     "model": "fal-ai/bria/background/remove"},
    {"id": "birefnet", "label": "fal.ai BiRefNet", "backend": "fal",
     "model": "fal-ai/birefnet"},
    {"id": "rembg", "label": "Local rembg (free, offline)", "backend": "rembg",
     "model": None},
]


def resolve_removal(removal_id: str) -> dict:
    for m in REMOVAL_MODELS:
        if m["id"] == removal_id:
            return m
    return REMOVAL_MODELS[0]


# Generative models that paint a realistic shadow onto the white-background
# cutout (used when shadow_mode == "ai"). All take a list of image URLs.
SHADOW_MODELS = [
    {"id": "fal-ai/gpt-image-1/edit-image", "label": "gpt-image-1 (ChatGPT image model)"},
    {"id": "fal-ai/gemini-25-flash-image/edit", "label": "Nano Banana (Gemini 2.5 Flash Image)"},
]

# Default instruction for the generative shadow step.
DEFAULT_SHADOW_PROMPT = (
    "Add a small, soft, realistic drop shadow on the ground beneath the product, "
    "lit from the upper left so the shadow falls gently to the lower right. "
    "Keep the product and the plain white background unchanged. "
    "Professional e-commerce product photo."
)


# Default processing configuration applied to a new batch.
DEFAULT_CONFIG = {
    "removal": "bria",            # id from REMOVAL_MODELS
    "shadow_mode": "ai",          # "ai" (generative) | "composite" (programmatic)
    "shadow_model": "fal-ai/gpt-image-1/edit-image",
    "shadow_prompt": DEFAULT_SHADOW_PROMPT,
    "output_format": "original",  # original | jpg | png | webp
    "shadow": {
        "direction": "left",      # light side: "left" casts shadow to the right
        "skew": 0.45,             # horizontal lean (fraction of shadow height)
        "length": 0.45,           # shadow height as fraction of product height
        "opacity": 0.30,          # 0.0 - 1.0
        "blur": 26,               # gaussian blur radius (softness)
        "margin": 0.18,           # clean margin around product (fraction of size)
        "bg_color": [255, 255, 255],
    },
}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)


def batch_root(batch_id: int) -> Path:
    return BATCHES_DIR / str(batch_id)


def batch_subdir(batch_id: int, name: str) -> Path:
    """Return (and create) a subdirectory for a batch: input | processed | cache."""
    path = batch_root(batch_id) / name
    path.mkdir(parents=True, exist_ok=True)
    return path
