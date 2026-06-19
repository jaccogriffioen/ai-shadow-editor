"""
Shadow reduction via image processing.
No background removal — edits the shadow directly in the original image.

Run: python shadow_reduce.py <input> <output>
 or: python shadow_reduce.py   (processes all images in product_images_raw/)
"""

import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

# --- Tune these ---
SHADOW_STRENGTH   = 0.80   # how much to reduce the shadow (0.0 = no change, 1.0 = fully remove)
SHADOW_THRESHOLD  = 28     # how many RGB units darker than background counts as shadow
EDGE_BLEND        = 18     # feather radius at shadow boundary (smooth transition)
SAMPLE_MARGIN     = 0.05   # fraction of image edge used to sample background color
# ------------------


def sample_background_color(img_arr: np.ndarray) -> np.ndarray:
    """
    Estimate background color by sampling pixels along the image border.
    Uses the median to be robust against product pixels at the edges.
    """
    h, w = img_arr.shape[:2]
    m = max(1, int(min(h, w) * SAMPLE_MARGIN))

    border = np.concatenate([
        img_arr[:m, :].reshape(-1, 3),    # top strip
        img_arr[-m:, :].reshape(-1, 3),   # bottom strip
        img_arr[:, :m].reshape(-1, 3),    # left strip
        img_arr[:, -m:].reshape(-1, 3),   # right strip
    ], axis=0)

    return np.median(border, axis=0)  # shape (3,)


def build_shadow_mask(img_arr: np.ndarray, bg_color: np.ndarray, threshold: float) -> np.ndarray:
    """
    Returns a float mask [0.0, 1.0] where 1.0 = shadow pixel.
    Shadow = pixel is darker than background by at least `threshold` in luminance.
    """
    # Luminance of each pixel and of background
    lum = 0.299 * img_arr[:,:,0] + 0.587 * img_arr[:,:,1] + 0.114 * img_arr[:,:,2]
    bg_lum = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]

    darkness = bg_lum - lum  # positive where pixel is darker than background

    # Hard mask: pixels darker than threshold
    hard_mask = np.clip((darkness - threshold / 2) / (threshold / 2), 0.0, 1.0)

    return hard_mask.astype(np.float32)


def reduce_shadow(
    image: Image.Image,
    shadow_strength: float  = SHADOW_STRENGTH,
    shadow_threshold: float = SHADOW_THRESHOLD,
    edge_blend: int         = EDGE_BLEND,
) -> Image.Image:
    img_arr = np.array(image.convert("RGB")).astype(np.float32)
    h, w    = img_arr.shape[:2]

    # 1. Estimate background color
    bg_color = sample_background_color(img_arr)

    # 2. Build raw shadow mask
    mask = build_shadow_mask(img_arr, bg_color, shadow_threshold)

    # 3. Feather the mask edges for a smooth blend
    mask_img    = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    mask_img    = mask_img.filter(ImageFilter.GaussianBlur(radius=edge_blend))
    soft_mask   = np.array(mask_img).astype(np.float32) / 255.0  # [0,1]

    # 4. Blend shadow pixels toward background color
    #    output = original + mask * strength * (bg_color - original)
    correction  = (bg_color - img_arr) * soft_mask[:, :, np.newaxis] * shadow_strength
    result_arr  = np.clip(img_arr + correction, 0, 255).astype(np.uint8)

    return Image.fromarray(result_arr)


def process(input_path: str, output_path: str):
    print(f"Processing {Path(input_path).name} ...")
    image  = Image.open(input_path)
    result = reduce_shadow(image)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, format="PNG")
    print(f"  Saved → {output_path}")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        process(sys.argv[1], sys.argv[2])
    else:
        input_dir  = Path("product_images_raw")
        output_dir = Path("product_images_final")
        output_dir.mkdir(exist_ok=True)
        supported = {".jpg", ".jpeg", ".png", ".webp"}
        images = [f for f in input_dir.iterdir() if f.suffix.lower() in supported]
        if not images:
            print(f"No images found in {input_dir}/")
        else:
            for img_path in images:
                out_path = output_dir / (img_path.stem + ".png")
                process(str(img_path), str(out_path))
