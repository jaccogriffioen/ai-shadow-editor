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

# Default editing instruction sent to the generative model for every image.
# Editable per batch on the confirmation screen, and per image during review.
DEFAULT_PROMPT = (
    "Remove the large soft drop shadow beneath and around the product and "
    "replace it with only a small, subtle, tight contact shadow directly under "
    "the product. Keep the product itself - its shape, packaging, label text and "
    "colours - perfectly unchanged. Keep the plain light-grey studio background "
    "clean and even. Photorealistic e-commerce product photo."
)

# Instruction-editing models selectable per batch (fal.ai endpoints).
# `image_urls` lists models that take a list of images instead of `image_url`.
EDIT_MODELS = [
    {"id": "fal-ai/flux-pro/kontext", "label": "FLUX.1 Kontext [pro]"},
    {"id": "fal-ai/flux-pro/kontext/max", "label": "FLUX.1 Kontext [max]"},
    {"id": "fal-ai/flux-kontext/dev", "label": "FLUX.1 Kontext [dev] (cheaper)"},
    {"id": "fal-ai/gemini-25-flash-image/edit", "label": "Nano Banana (Gemini 2.5 Flash Image)"},
    {"id": "fal-ai/qwen-image-edit", "label": "Qwen Image Edit"},
    {"id": "fal-ai/bytedance/seededit/v3/edit-image", "label": "SeedEdit 3.0"},
]
IMAGE_URLS_MODELS = {"fal-ai/gemini-25-flash-image/edit"}

# Default processing configuration applied to a new batch.
DEFAULT_CONFIG = {
    "fal_model": "fal-ai/flux-pro/kontext",
    "prompt": DEFAULT_PROMPT,
    "output_format": "original",  # original | jpg | png | webp
    "guidance_scale": 3.5,        # used by models that support it (e.g. FLUX Kontext)
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
