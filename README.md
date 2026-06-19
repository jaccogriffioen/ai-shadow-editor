# AI Shadow Editor

Batch tool that replaces large product-photo shadows with a small, soft, consistent
studio shadow — with a human review step that flags results that don't look right.

It runs as a **local server** on your machine: files stay on your disk (no upload),
state is saved in SQLite (resumable after any interruption), and the UI is a web app
at `http://localhost:8000`.

## How it works

For each image:
1. **Background removal** isolates the product (removing the original shadow).
2. A **soft drop shadow** is composited beneath it on a clean background — the same
   shadow settings on every image, so the catalogue looks consistent.
3. **Automated quality checks** flag anything that looks off (failed cut-out, rough
   edges, patchy background). Flagging is deliberately aggressive — you can unflag in
   one click during review.

### Processing methods (chosen per batch)

| Method | What it does | Needs |
|--------|--------------|-------|
| **Local (rembg)** — default | u2net background removal + clean shadow. Free, offline. | one-time model download (~170 MB) |
| **fal.ai BRIA** | Cloud background removal + clean shadow. Best quality. | `FAL_KEY`, uses API credits |
| **Quick reduce** | Lightens the existing shadow in place. No background removal. Fastest. | nothing |

## Setup

```bash
# from the project root
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Your fal.ai key lives in `.env` (already created, git-ignored):

```
FAL_KEY=your-key-here
```

## Run

```bash
venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open **http://localhost:8000**.

## Using it

1. **New batch** → give it a name.
2. **Add images** — drag & drop, or paste a local folder path to reference thousands
   of images in place (no copy).
3. **Configure** — method, shadow style (opacity, softness, size, background colour),
   and output format (JPG / PNG / WebP / preserve original).
4. **Preview** a sample, then **Confirm & Start**.
5. **Review** — grid of results; flagged ones have a red border. Click any image for a
   before/after view. Approve, flag/unflag, revert to original, or re-run a single
   image with adjusted settings.
6. **Export** approved images to a folder you choose. Originals are never modified.

## Project layout

```
backend/
  main.py            FastAPI app, WebSocket, static serving
  config.py          paths, .env loading, default settings
  database.py        SQLAlchemy engine/session (SQLite)
  models.py          Batch, Image
  routers/           batches.py · images.py · export.py
  services/
    removal.py       fal.ai / rembg / reduce backends
    shadow.py        soft-shadow compositing
    quality.py       auto-flagging checks
    processor.py     batch runner (pause/resume/cancel, progress)
    ws.py            WebSocket manager
frontend/
  index.html         Tailwind shell
  app.js             Preact single-page UI (Home · New · Processing · Review · Export)
data/                SQLite DB + processed images + thumbnails (git-ignored)
```

## Notes

- **Originals are never overwritten.** Processed files live under `data/`; export copies
  approved results to your chosen folder.
- **Resumable:** if the server stops mid-batch, restart it and the batch picks up from
  the last completed image.
- The default shadow settings are a starting point — preview on a few images and tune
  opacity/softness/size before running all 4,000.
