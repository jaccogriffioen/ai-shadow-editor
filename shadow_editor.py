import argparse
import multiprocessing
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from rembg import remove, new_session


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

# Shadow tuning parameters
SHADOW_OPACITY = 0.45       # 0.0 - 1.0
SHADOW_BLUR_RADIUS = 22     # higher = softer/more spread shadow
SHADOW_HEIGHT_RATIO = 0.08  # shadow height as fraction of product height
SHADOW_WIDTH_RATIO = 1.1    # shadow width slightly wider than product
SHADOW_VERTICAL_OFFSET = 8  # pixels gap between product bottom and shadow
BACKGROUND_COLOR = (248, 248, 248)  # light grey, change to (255,255,255) for pure white
OUTPUT_SIZE = None          # set to e.g. (800, 800) to force a fixed canvas, or None to keep original


def load_session():
    """Load rembg model once per process (expensive, so done once)."""
    return new_session("u2net")


def remove_background(image: Image.Image, session) -> Image.Image:
    """Remove background and return RGBA image."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    result = remove(image, session=session)
    return result.convert("RGBA")


def crop_to_subject(image: Image.Image, padding: int = 20) -> Image.Image:
    """Crop transparent margins, keep a small padding."""
    bbox = image.getbbox()
    if bbox is None:
        return image
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(image.width, bbox[2] + padding)
    bottom = min(image.height, bbox[3] + padding)
    return image.crop((left, top, right, bottom))


def generate_shadow(product: Image.Image) -> tuple[Image.Image, tuple[int, int]]:
    """
    Generate a soft elliptical shadow based on the product's bottom silhouette.
    Returns the shadow image and its (x, y) offset relative to the product's top-left.
    """
    alpha = np.array(product.split()[3])

    # Find bounding box of non-transparent pixels
    rows = np.any(alpha > 10, axis=1)
    cols = np.any(alpha > 10, axis=0)
    if not rows.any():
        return Image.new("RGBA", product.size, (0, 0, 0, 0)), (0, 0)

    row_min, row_max = np.where(rows)[0][[0, -1]]
    col_min, col_max = np.where(cols)[0][[0, -1]]

    product_w = int(col_max - col_min)
    product_h = int(row_max - row_min)

    # Shadow ellipse dimensions
    shadow_w = int(product_w * SHADOW_WIDTH_RATIO)
    shadow_h = max(12, int(product_h * SHADOW_HEIGHT_RATIO))

    # Draw a filled black ellipse
    shadow_img = Image.new("RGBA", (shadow_w + SHADOW_BLUR_RADIUS * 4, shadow_h + SHADOW_BLUR_RADIUS * 4), (0, 0, 0, 0))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(shadow_img)
    pad = SHADOW_BLUR_RADIUS * 2
    draw.ellipse([pad, pad, shadow_w + pad, shadow_h + pad], fill=(0, 0, 0, 255))

    # Blur to make it soft
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR_RADIUS))

    # Apply opacity
    arr = np.array(shadow_img)
    arr[:, :, 3] = (arr[:, :, 3] * SHADOW_OPACITY).astype(np.uint8)
    shadow_img = Image.fromarray(arr)

    # Compute where to place the shadow relative to product top-left
    center_x = int(col_min + product_w // 2)
    shadow_x = center_x - shadow_img.width // 2
    shadow_y = int(row_max) + SHADOW_VERTICAL_OFFSET - pad

    return shadow_img, (shadow_x, shadow_y)


def composite(product: Image.Image) -> Image.Image:
    """Composite product + shadow onto a clean background."""
    target_size = OUTPUT_SIZE if OUTPUT_SIZE else product.size

    # Create background
    bg = Image.new("RGBA", target_size, (*BACKGROUND_COLOR, 255))

    # Center product on canvas
    prod_x = (target_size[0] - product.width) // 2
    prod_y = (target_size[1] - product.height) // 2

    # Generate and place shadow first (behind product)
    shadow, (sx, sy) = generate_shadow(product)
    shadow_x = prod_x + sx
    shadow_y = prod_y + sy
    bg.paste(shadow, (shadow_x, shadow_y), mask=shadow)

    # Place product on top
    bg.paste(product, (prod_x, prod_y), mask=product)

    return bg.convert("RGB")


def check_quality(product_rgba: Image.Image) -> tuple[bool, str]:
    """
    Heuristic quality check on the cutout.
    Returns (passed, reason).
    """
    alpha = np.array(product_rgba.split()[3])

    # Check that there's actually a subject
    subject_pixels = np.sum(alpha > 10)
    total_pixels = alpha.size
    subject_ratio = subject_pixels / total_pixels
    if subject_ratio < 0.02:
        return False, "subject too small — background removal may have failed"
    if subject_ratio > 0.97:
        return False, "almost no background removed — may be a plain white product on white bg"

    # Check edge roughness: count pixels in the alpha transition zone (10–245)
    transition = np.sum((alpha > 10) & (alpha < 245))
    edge_ratio = transition / max(subject_pixels, 1)
    if edge_ratio > 0.35:
        return False, f"edges look rough (ratio={edge_ratio:.2f}) — possible transparent/reflective packaging"

    return True, "ok"


def process_image(args: tuple) -> dict:
    """Process a single image. Designed to be called from a worker pool."""
    input_path, output_path, session = args

    result = {"file": input_path.name, "status": None, "reason": ""}

    try:
        image = Image.open(input_path)
    except Exception as e:
        result["status"] = "error"
        result["reason"] = f"could not open: {e}"
        return result

    try:
        product = remove_background(image, session)
    except Exception as e:
        result["status"] = "error"
        result["reason"] = f"background removal failed: {e}"
        return result

    passed, reason = check_quality(product)
    if not passed:
        result["status"] = "flagged"
        result["reason"] = reason
        # Still save the output so you can review it manually
        product = crop_to_subject(product)
        final = composite(product)
        flag_path = output_path.parent / "flagged" / output_path.name
        flag_path.parent.mkdir(parents=True, exist_ok=True)
        final.save(flag_path, quality=95)
        result["output"] = str(flag_path)
        return result

    product = crop_to_subject(product)
    final = composite(product)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(output_path, quality=95)

    result["status"] = "ok"
    result["output"] = str(output_path)
    return result


def run(input_dir: Path, output_dir: Path, workers: int):
    input_files = [
        f for f in input_dir.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not input_files:
        print(f"No supported images found in {input_dir}")
        sys.exit(1)

    print(f"Found {len(input_files)} images. Processing with {workers} worker(s)...")

    # Load model once (shared within process — each worker gets its own via initializer)
    session = load_session()

    tasks = []
    for f in input_files:
        out_name = f.stem + ".jpg"
        out_path = output_dir / out_name
        tasks.append((f, out_path, session))

    ok = flagged = errors = 0

    # Single-process loop (rembg model is not safely picklable for multiprocessing)
    for i, task in enumerate(tasks, 1):
        result = process_image(task)
        if result["status"] == "ok":
            ok += 1
        elif result["status"] == "flagged":
            flagged += 1
            print(f"  [FLAGGED] {result['file']} — {result['reason']}")
        else:
            errors += 1
            print(f"  [ERROR]   {result['file']} — {result['reason']}")

        if i % 50 == 0 or i == len(tasks):
            print(f"  Progress: {i}/{len(tasks)} ({ok} ok, {flagged} flagged, {errors} errors)")

    print(f"\nDone. {ok} ok · {flagged} flagged (saved to {output_dir}/flagged/) · {errors} errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch product image shadow editor")
    parser.add_argument("input", type=Path, help="Folder of raw product images")
    parser.add_argument("output", type=Path, help="Folder to save processed images")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers (default: 1)")
    args = parser.parse_args()

    run(args.input, args.output, args.workers)
