"""
Visual parameter tuner — run: python ui.py → open http://localhost:7860
"""

import gradio as gr
from PIL import Image
from pathlib import Path
from demo import remove_background, clean_edges, apply_shadow

# Two-level cache: raw cutout keyed by image id, cleaned cutout keyed by (image_id, erode, feather)
_raw_cache:   dict = {}
_clean_cache: dict = {}


def get_cutout(image: Image.Image, erode: int, feather: float) -> tuple[Image.Image, tuple[int, int]]:
    img_key = id(image)

    # Run rembg only once per image
    if img_key not in _raw_cache:
        _raw_cache.clear()
        _clean_cache.clear()
        original_size = image.size
        product = remove_background(image)
        bbox = product.getbbox()
        if bbox:
            pad = 10
            product = product.crop((
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(product.width,  bbox[2] + pad),
                min(product.height, bbox[3] + pad),
            ))
        _raw_cache[img_key] = (product, original_size)

    raw_product, original_size = _raw_cache[img_key]

    # Re-run edge cleanup whenever erode/feather change (fast)
    clean_key = (img_key, erode, round(feather, 2))
    if clean_key not in _clean_cache:
        _clean_cache[clean_key] = clean_edges(raw_product, erode=int(erode), feather=feather)

    return _clean_cache[clean_key], original_size


def preview(image, opacity, blur, height, x_offset, y_offset, erode, feather, bg_r, bg_g, bg_b):
    if image is None:
        return None
    product, original_size = get_cutout(image, int(erode), feather)
    return apply_shadow(
        product, original_size,
        shadow_opacity=opacity,
        shadow_blur=int(blur),
        shadow_height=height,
        shadow_x_offset=x_offset,
        shadow_y_offset=y_offset,
        background_color=(int(bg_r), int(bg_g), int(bg_b)),
    )


def save_result(image, opacity, blur, height, x_offset, y_offset, erode, feather, bg_r, bg_g, bg_b):
    if image is None:
        return "⚠️  No image loaded."
    result = preview(image, opacity, blur, height, x_offset, y_offset, erode, feather, bg_r, bg_g, bg_b)
    out_dir = Path("product_images_final")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "preview_result.png"
    result.save(str(out_path), format="PNG")
    return f"✅  Saved → {out_path}"


raw_dir     = Path("product_images_raw")
raw_choices = sorted([
    str(p) for p in raw_dir.glob("*")
    if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
]) if raw_dir.exists() else []

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, body, .gradio-container {
    font-family: 'Inter', sans-serif !important;
    box-sizing: border-box;
}
body, .gradio-container {
    background: #0c0c14 !important;
}
footer { display: none !important; }

/* Header */
#app-header {
    background: linear-gradient(135deg, #4318d1 0%, #9b23e8 55%, #e8238b 100%);
    border-radius: 18px;
    padding: 26px 32px 24px;
    margin-bottom: 14px;
}
#app-header h1 {
    color: #fff !important;
    font-size: 24px !important;
    font-weight: 700 !important;
    margin: 0 0 5px !important;
    letter-spacing: -0.4px !important;
}
#app-header p {
    color: rgba(255,255,255,0.68) !important;
    font-size: 13px !important;
    margin: 0 !important;
    line-height: 1.6 !important;
}

/* Panels */
.panel {
    background: #13131f !important;
    border: 1px solid #22223a !important;
    border-radius: 18px !important;
    padding: 24px !important;
}

/* Divider labels */
.divider {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 20px 0 12px;
    color: #7c6fff !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}
.divider::before, .divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #22223a;
}
.divider:first-child { margin-top: 0; }

/* Slider labels */
.gradio-slider label span,
label > span.svelte-1b6s6s,
.gr-form label span {
    color: #b0a4ff !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
input[type=range] { accent-color: #7c3aed !important; }

/* Textbox / dropdown */
input, select, textarea {
    background: #0c0c14 !important;
    border: 1px solid #22223a !important;
    color: #e0e0f0 !important;
    border-radius: 10px !important;
}

/* Image areas */
.gr-image, [data-testid="image"] {
    border-radius: 14px !important;
    border: 1px solid #22223a !important;
    background: #0c0c14 !important;
    overflow: hidden !important;
}

/* Apply button */
#btn-apply > .wrap > button,
#btn-apply button {
    background: linear-gradient(135deg, #5418e8, #b918e8) !important;
    border: none !important;
    border-radius: 12px !important;
    color: #fff !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    padding: 13px 0 !important;
    width: 100% !important;
    letter-spacing: 0.2px !important;
    cursor: pointer !important;
    margin-top: 8px !important;
}
#btn-apply > .wrap > button:hover,
#btn-apply button:hover { opacity: 0.85 !important; }

/* Save button */
#btn-save > .wrap > button,
#btn-save button {
    background: transparent !important;
    border: 1px solid #5418e8 !important;
    border-radius: 12px !important;
    color: #9f7aea !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 11px 0 !important;
    width: 100% !important;
    cursor: pointer !important;
    margin-top: 6px !important;
}
#btn-save > .wrap > button:hover,
#btn-save button:hover { background: #1c1035 !important; }

/* Save status */
#save-status textarea {
    background: transparent !important;
    border: none !important;
    color: #34d399 !important;
    font-size: 13px !important;
    text-align: center !important;
}

/* RGB color sliders */
#bg-r label span { color: #f87171 !important; }
#bg-g label span { color: #4ade80 !important; }
#bg-b label span { color: #60a5fa !important; }
"""

with gr.Blocks(title="Shadow Editor", css=CSS, theme=gr.themes.Base()) as app:

    with gr.Column(elem_id="app-header"):
        gr.HTML("""
            <h1>🎨 Shadow Editor</h1>
            <p>Upload a product photo — background is removed automatically.
               Tune the shadow sliders and hit <strong>Apply</strong> to preview.</p>
        """)

    with gr.Row(equal_height=False, variant="panel"):

        # ── LEFT panel ─────────────────────────────────────────
        with gr.Column(scale=1, min_width=320, elem_classes="panel"):

            gr.HTML("<div class='divider'>📁 Image</div>")
            if raw_choices:
                file_picker = gr.Dropdown(choices=raw_choices, label="From product_images_raw/")
            upload = gr.Image(type="pil", label="Upload image", height=200)

            gr.HTML("<div class='divider'>✂️ Edge Cleanup</div>")
            erode   = gr.Slider(0, 6,   value=2,   step=1,   label="Erode — remove fringe (higher = tighter edge)")
            feather = gr.Slider(0, 3.0, value=0.3, step=0.1, label="Feather — smooth edge transition")

            gr.HTML("<div class='divider'>🌑 Shadow</div>")
            opacity  = gr.Slider(0.0,  1.0,  value=0.42, step=0.01, label="Opacity")
            blur     = gr.Slider(0,    80,   value=28,   step=1,    label="Blur — soft ↔ sharp")
            height   = gr.Slider(0.01, 0.4,  value=0.10, step=0.01, label="Height (flat ↔ tall)")
            x_offset = gr.Slider(-0.5, 0.5,  value=0.06, step=0.01, label="Horizontal offset  ← left / right →")
            y_offset = gr.Slider(-0.1, 0.3,  value=0.005,step=0.005,label="Vertical offset  (gap below product)")

            gr.HTML("<div class='divider'>🎨 Background</div>")
            with gr.Row():
                bg_r = gr.Slider(0, 255, value=232, step=1, label="R", elem_id="bg-r")
                bg_g = gr.Slider(0, 255, value=232, step=1, label="G", elem_id="bg-g")
                bg_b = gr.Slider(0, 255, value=235, step=1, label="B", elem_id="bg-b")

            with gr.Row():
                apply_btn = gr.Button("▶  Apply", elem_id="btn-apply")
            with gr.Row():
                save_btn  = gr.Button("💾  Save", elem_id="btn-save")
            save_status = gr.Textbox(label="", interactive=False, elem_id="save-status")

        # ── RIGHT panel ─────────────────────────────────────────
        with gr.Column(scale=2, elem_classes="panel"):
            gr.HTML("<div class='divider'>👁 Preview</div>")
            output_image = gr.Image(type="pil", label="", height=740)

    params = [upload, opacity, blur, height, x_offset, y_offset, erode, feather, bg_r, bg_g, bg_b]
    apply_btn.click(fn=preview,     inputs=params, outputs=output_image)
    save_btn.click( fn=save_result, inputs=params, outputs=save_status)

    if raw_choices:
        def load_from_picker(path):
            return Image.open(path)
        file_picker.change(fn=load_from_picker, inputs=file_picker, outputs=upload)


if __name__ == "__main__":
    app.launch()
