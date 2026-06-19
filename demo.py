from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw
import numpy as np
from rembg import remove, new_session

# --- Tune these ---
SHADOW_OPACITY    = 0.42   # 0.0 – 1.0  overall darkness
SHADOW_BLUR       = 28     # softness (higher = more diffuse)
SHADOW_HEIGHT     = 0.10   # how tall the projected shadow is, as fraction of product height
SHADOW_X_OFFSET   = 0.06   # horizontal shift as fraction of product width (+ve = right, -ve = left)
SHADOW_Y_OFFSET   = 0.005  # vertical gap below product base as fraction of product height
BACKGROUND_COLOR  = (232, 232, 235)
EDGE_ERODE        = 2      # pixels to shrink alpha (removes fringe/halo, 1–4)
EDGE_FEATHER      = 0.3    # alpha blur radius for smooth edge transition (keep low to preserve sharpness)
# ------------------

_session = None

def get_session():
    global _session
    if _session is None:
        print("Loading model...")
        _session = new_session("u2net")
    return _session


def remove_background(image: Image.Image) -> Image.Image:
    return remove(image.convert("RGB"), session=get_session()).convert("RGBA")


def clean_edges(product: Image.Image, erode: int = 2, feather: float = 0.8) -> Image.Image:
    """
    Fix fringe/halo artifacts left by background removal.
    erode:   shrinks the alpha mask (removes 1-3px of fringe)
    feather: smooths the edge (slight alpha blur for natural transition)
    """
    r, g, b, a = product.split()

    # Morphological erosion: shrink alpha by taking local minimum
    for _ in range(erode):
        a = a.filter(ImageFilter.MinFilter(3))

    # Feather: gentle blur on alpha for smooth edge
    if feather > 0:
        a = a.filter(ImageFilter.GaussianBlur(radius=feather))

    return Image.merge("RGBA", (r, g, b, a))


def make_contact_shadow(
    product: Image.Image,
    shadow_height: float,
    shadow_x_offset: float,
    shadow_blur: int,
    shadow_opacity: float,
) -> tuple[Image.Image, int, int]:
    """
    Derives the shadow from the product's real silhouette:
    - takes the alpha mask
    - squishes it flat (simulates floor projection)
    - blurs heavily
    Returns (shadow_rgba, offset_x, offset_y) relative to product top-left.
    """
    alpha = product.split()[3]
    w, h  = product.size
    pad   = shadow_blur * 3

    shadow_h = max(6, int(h * shadow_height))

    # Squish the real silhouette down to shadow_h pixels tall
    squished = alpha.resize((w, shadow_h), Image.LANCZOS)

    # Paint it black onto a padded canvas
    canvas = Image.new("RGBA", (w + pad * 2, shadow_h + pad * 2), (0, 0, 0, 0))
    black  = Image.new("RGBA", (w, shadow_h), (0, 0, 0, 255))
    canvas.paste(black, (pad, pad), mask=squished)

    # Blur
    canvas = canvas.filter(ImageFilter.GaussianBlur(radius=shadow_blur))

    # Apply opacity
    r, g, b, a = canvas.split()
    a = a.point(lambda x: int(x * shadow_opacity))
    canvas = Image.merge("RGBA", (r, g, b, a))

    # Anchor: shadow base aligns with product base, horizontally centered + offset
    offset_x = -pad + int(w * shadow_x_offset)
    offset_y = h - shadow_h - pad  # shadow base = product base

    return canvas, offset_x, offset_y


def apply_shadow(
    product: Image.Image,
    original_size: tuple[int, int],
    shadow_opacity: float,
    shadow_blur: int,
    shadow_height: float,
    shadow_x_offset: float,
    shadow_y_offset: float,
    background_color: tuple[int, int, int],
) -> Image.Image:
    canvas_w, canvas_h = original_size

    prod_x = (canvas_w - product.width)  // 2
    prod_y = (canvas_h - product.height) // 2 - int(product.height * 0.04)

    shadow, sh_off_x, sh_off_y = make_contact_shadow(
        product, shadow_height, shadow_x_offset, shadow_blur, shadow_opacity,
    )

    extra_y = int(product.height * shadow_y_offset)
    shadow_x = prod_x + sh_off_x
    shadow_y = prod_y + sh_off_y + extra_y

    bg = Image.new("RGBA", (canvas_w, canvas_h), (*background_color, 255))
    bg.paste(shadow, (shadow_x, shadow_y), mask=shadow)
    bg.paste(product, (prod_x, prod_y),   mask=product)

    return bg.convert("RGB")


def process(
    input_path: str,
    output_path: str,
    shadow_opacity:  float = SHADOW_OPACITY,
    shadow_blur:     int   = SHADOW_BLUR,
    shadow_height:   float = SHADOW_HEIGHT,
    shadow_x_offset: float = SHADOW_X_OFFSET,
    shadow_y_offset: float = SHADOW_Y_OFFSET,
    background_color: tuple[int, int, int] = BACKGROUND_COLOR,
    edge_erode:      int   = EDGE_ERODE,
    edge_feather:    float = EDGE_FEATHER,
):
    image = Image.open(input_path).convert("RGB")
    original_size = image.size

    print("Removing background...")
    product = remove_background(image)
    product = clean_edges(product, erode=edge_erode, feather=edge_feather)

    # Crop tight to subject
    bbox = product.getbbox()
    if bbox:
        pad = 10
        product = product.crop((
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(product.width,  bbox[2] + pad),
            min(product.height, bbox[3] + pad),
        ))

    result = apply_shadow(
        product, original_size,
        shadow_opacity, shadow_blur,
        shadow_height, shadow_x_offset,
        shadow_y_offset, background_color,
    )
    # Save as PNG (lossless) to avoid JPEG compression artifacts
    out = Path(output_path).with_suffix(".png")
    result.save(str(out), format="PNG")
    print(f"Saved → {out}")


if __name__ == "__main__":
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
            print(f"\n--- {img_path.name} ---")
            process(str(img_path), str(out_path))
