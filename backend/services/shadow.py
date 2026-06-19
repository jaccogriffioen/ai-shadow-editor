"""Deterministic directional cast-shadow compositing.

Given a product cut out on a transparent background, this projects the product
silhouette into a soft *cast* shadow as if lit from one side, anchored at the
product's base so it looks grounded (not floating), then composites product +
shadow onto a clean canvas. The same parameters produce the same shadow on
every image, guaranteeing visual consistency across a batch.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def crop_to_subject(image: Image.Image, padding: int = 20) -> Image.Image:
    """Crop transparent margins, keeping a small padding."""
    bbox = image.getbbox()
    if bbox is None:
        return image
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(image.width, bbox[2] + padding)
    bottom = min(image.height, bbox[3] + padding)
    return image.crop((left, top, right, bottom))


def composite(product: Image.Image, params: dict) -> Image.Image:
    """Composite product + a directional cast shadow onto a clean background.

    The shadow is the product silhouette sheared toward the side opposite the
    light and foreshortened, anchored at the product's base. Returns RGB.

    Params:
      direction      "left" | "right" — which side the light comes from.
                     Light from the left casts the shadow to the right.
      skew           horizontal lean as a fraction of shadow height (0 = straight).
      length         shadow height as a fraction of product height (foreshorten).
      opacity        0.0 - 1.0
      blur           gaussian softness
      margin         clean border around everything (fraction of product size)
      bg_color       [r, g, b] canvas colour
    """
    direction = params.get("direction", "left")
    skew = float(params.get("skew", 0.45))
    length = max(0.05, float(params.get("length", 0.9)))
    opacity = float(params.get("opacity", 0.4))
    blur = int(params.get("blur", 25))
    margin = float(params.get("margin", 0.18))
    bg_color = tuple(params.get("bg_color", [255, 255, 255]))

    # Light from the left -> shadow goes right (sign +1); from the right -> left.
    sign = 1 if direction == "left" else -1

    if product.mode != "RGBA":
        product = product.convert("RGBA")
    w, h = product.size

    horiz = int(abs(skew) * length * h)            # horizontal reach of the lean
    pad = max(int(max(w, h) * margin), blur * 2)   # border + room for the blur

    canvas_w = w + horiz + 2 * pad
    canvas_h = h + 2 * pad
    # Give the shadow room on its side: product hugs the opposite side.
    prod_x = pad if sign > 0 else pad + horiz
    prod_y = pad
    base_y = prod_y + h

    # Product placed on a full-canvas layer.
    prod_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    prod_layer.paste(product, (prod_x, prod_y), product)

    # Black silhouette from the product's alpha, in canvas space.
    alpha_full = prod_layer.getchannel("A")
    zero = Image.new("L", (canvas_w, canvas_h), 0)
    silhouette = Image.merge("RGBA", (zero, zero, zero, alpha_full))

    # Affine maps each OUTPUT pixel back to the silhouette INPUT pixel:
    #   x_in = Xo + sign*skew*Yo - sign*skew*base_y
    #   y_in = Yo/length + base_y - base_y/length
    # which anchors the base (no shift, no scale) and leans/foreshortens above it.
    coeffs = (
        1.0, sign * skew, -sign * skew * base_y,
        0.0, 1.0 / length, base_y - base_y / length,
    )
    shadow = silhouette.transform(
        (canvas_w, canvas_h), Image.AFFINE, coeffs, resample=Image.BILINEAR
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur))

    arr = np.array(shadow)
    arr[:, :, 3] = (arr[:, :, 3] * opacity).astype(np.uint8)
    shadow = Image.fromarray(arr)

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (*bg_color, 255))
    canvas.paste(shadow, (0, 0), shadow)
    canvas.paste(prod_layer, (0, 0), prod_layer)
    return canvas.convert("RGB")
