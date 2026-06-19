"""
Visual tuner for shadow_reduce.py
Run: python shadow_reduce_ui.py  →  open http://localhost:7860
"""

import gradio as gr
from PIL import Image
from pathlib import Path
from shadow_reduce import reduce_shadow, sample_background_color
import numpy as np


def preview(image, strength, threshold, edge_blend):
    if image is None:
        return None, None
    result = reduce_shadow(
        image,
        shadow_strength=strength,
        shadow_threshold=threshold,
        edge_blend=int(edge_blend),
    )
    return image, result   # before / after


def show_mask(image, threshold, edge_blend):
    """Show detected shadow mask so user can see what's being targeted."""
    if image is None:
        return None
    from shadow_reduce import build_shadow_mask, sample_background_color
    from PIL import ImageFilter
    img_arr  = np.array(image.convert("RGB")).astype(np.float32)
    bg_color = sample_background_color(img_arr)
    mask     = build_shadow_mask(img_arr, bg_color, threshold)
    mask_img = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=int(edge_blend)))
    return mask_img.convert("RGB")


def save_result(image, strength, threshold, edge_blend):
    if image is None:
        return "⚠️  No image loaded."
    result = reduce_shadow(image, shadow_strength=strength,
                           shadow_threshold=threshold, edge_blend=int(edge_blend))
    out_dir  = Path("product_images_final")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "shadow_reduced.png"
    result.save(str(out_path), format="PNG")
    return f"✅  Saved → {out_path}"


raw_dir     = Path("product_images_raw")
raw_choices = sorted([
    str(p) for p in raw_dir.glob("*")
    if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
]) if raw_dir.exists() else []

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*, body, .gradio-container { font-family: 'Inter', sans-serif !important; }
body, .gradio-container    { background: #0c0c14 !important; }
footer { display: none !important; }

#app-header {
    background: linear-gradient(135deg, #0f7a55 0%, #0ea572 50%, #06c98a 100%);
    border-radius: 18px; padding: 26px 32px 22px; margin-bottom: 14px;
}
#app-header h1 {
    color:#fff !important; font-size:24px !important; font-weight:700 !important;
    margin:0 0 5px !important; letter-spacing:-0.4px !important;
}
#app-header p {
    color:rgba(255,255,255,0.7) !important; font-size:13px !important;
    margin:0 !important; line-height:1.6 !important;
}
.panel {
    background:#13131f !important; border:1px solid #22223a !important;
    border-radius:18px !important; padding:24px !important;
}
.divider {
    display:flex; align-items:center; gap:10px;
    margin:20px 0 12px; color:#34d399 !important;
    font-size:10px !important; font-weight:700 !important;
    letter-spacing:2px !important; text-transform:uppercase !important;
}
.divider::before, .divider::after {
    content:''; flex:1; height:1px; background:#22223a;
}
.divider:first-child { margin-top:0; }
label > span, .gradio-slider label span {
    color:#6ee7b7 !important; font-size:13px !important; font-weight:500 !important;
}
input[type=range]  { accent-color: #10b981 !important; }
input, select, textarea {
    background:#0c0c14 !important; border:1px solid #22223a !important;
    color:#e0e0f0 !important; border-radius:10px !important;
}
.gr-image, [data-testid="image"] {
    border-radius:14px !important; border:1px solid #22223a !important;
    background:#0c0c14 !important; overflow:hidden !important;
}
#btn-apply button {
    background: linear-gradient(135deg, #059669, #10b981) !important;
    border:none !important; border-radius:12px !important; color:#fff !important;
    font-size:15px !important; font-weight:600 !important; padding:13px 0 !important;
    width:100% !important; margin-top:8px !important;
}
#btn-apply button:hover { opacity:0.85 !important; }
#btn-mask button {
    background:transparent !important; border:1px solid #10b981 !important;
    border-radius:12px !important; color:#34d399 !important;
    font-size:14px !important; font-weight:500 !important; padding:11px 0 !important;
    width:100% !important; margin-top:6px !important;
}
#btn-mask button:hover { background:#0d2e22 !important; }
#btn-save button {
    background:transparent !important; border:1px solid #374151 !important;
    border-radius:12px !important; color:#6b7280 !important;
    font-size:14px !important; padding:10px 0 !important;
    width:100% !important; margin-top:6px !important;
}
#btn-save button:hover { background:#1a1a2e !important; }
#save-status textarea {
    background:transparent !important; border:none !important;
    color:#34d399 !important; font-size:13px !important; text-align:center !important;
}
"""

with gr.Blocks(title="Shadow Reducer", css=CSS, theme=gr.themes.Base()) as app:

    with gr.Column(elem_id="app-header"):
        gr.HTML("""
            <h1>🌿 Shadow Reducer</h1>
            <p>Edits the shadow directly in the original image — no background removal.
            Use <strong>Show Mask</strong> to see which pixels are being targeted, then tune the sliders.</p>
        """)

    with gr.Row(equal_height=False):

        # ── LEFT: Controls ─────────────────────────────────────
        with gr.Column(scale=1, min_width=320, elem_classes="panel"):

            gr.HTML("<div class='divider'>📁 Image</div>")
            if raw_choices:
                file_picker = gr.Dropdown(choices=raw_choices, label="From product_images_raw/")
            upload = gr.Image(type="pil", label="Upload image", height=200)

            gr.HTML("<div class='divider'>🎚️ Shadow Controls</div>")
            strength  = gr.Slider(0.0, 1.0, value=0.80, step=0.01,
                                  label="Strength — how much to reduce the shadow")
            threshold = gr.Slider(5,   80,  value=28,   step=1,
                                  label="Threshold — how dark a pixel must be to count as shadow")
            blend     = gr.Slider(0,   60,  value=18,   step=1,
                                  label="Edge Blend — feathering at shadow boundary")

            with gr.Row():
                apply_btn = gr.Button("▶  Apply",      elem_id="btn-apply")
            with gr.Row():
                mask_btn  = gr.Button("🔍  Show Mask", elem_id="btn-mask")
            with gr.Row():
                save_btn  = gr.Button("💾  Save",      elem_id="btn-save")
            save_status = gr.Textbox(label="", interactive=False, elem_id="save-status")

            gr.HTML("""
                <div style='margin-top:16px; padding:12px 14px; background:#0a1f16;
                     border:1px solid #1a4a33; border-radius:10px;
                     color:#6ee7b7; font-size:12px; line-height:1.7;'>
                    <strong>💡 How to tune:</strong><br>
                    1. Hit <em>Show Mask</em> — white = shadow being edited<br>
                    2. Raise <em>Threshold</em> if product is included in mask<br>
                    3. Lower <em>Threshold</em> if shadow isn't fully detected<br>
                    4. Adjust <em>Strength</em> for how much shadow to remove
                </div>
            """)

        # ── RIGHT: Preview ──────────────────────────────────────
        with gr.Column(scale=2, elem_classes="panel"):
            gr.HTML("<div class='divider'>👁 Before / After</div>")
            with gr.Row():
                before_img = gr.Image(type="pil", label="Original", height=460)
                after_img  = gr.Image(type="pil", label="Result",   height=460)
            gr.HTML("<div class='divider'>🔍 Shadow Mask</div>")
            mask_img = gr.Image(type="pil", label="Detected shadow (white = affected)", height=220)

    params = [upload, strength, threshold, blend]
    apply_btn.click(fn=preview,      inputs=params,            outputs=[before_img, after_img])
    mask_btn.click( fn=show_mask,    inputs=[upload, threshold, blend], outputs=mask_img)
    save_btn.click( fn=save_result,  inputs=params,            outputs=save_status)

    if raw_choices:
        def load_from_picker(path):
            return Image.open(path)
        file_picker.change(fn=load_from_picker, inputs=file_picker, outputs=upload)


if __name__ == "__main__":
    app.launch()
