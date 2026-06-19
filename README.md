# AI Shadow Editor

Batch tool that edits the shadows in product photos using a **generative AI
image-editing model** — turning a large, heavy shadow into a small, subtle one —
with a human review step that flags results that don't look right.

It runs as a **local server** on your machine: files stay on your disk (no upload),
batch state is saved in SQLite (resumable after any interruption), and the UI is a
web app at `http://localhost:8000`.

## Demos

**Generative editing approach** (current) — choose a fal.ai editing model and an
editable prompt per batch:

https://github.com/user-attachments/assets/ec54acad-1c5f-437d-b87d-691eaccbbcd1

**Image-processing approach** — background removal (BRIA / rembg) + a programmatic
shadow composite. This is the version tagged
[`image-processing`](../../tree/image-processing); see
[Testing the image-processing approach](#testing-the-image-processing-approach):

https://github.com/user-attachments/assets/5ea7da7a-3db5-49dd-ac15-cab4d64ed86c

<sub>Downloadable copies live in [`demos/`](demos/).</sub>

## How it works

For each image in a batch:
1. The image is sent to a fal.ai image-editing model together with an **editing
   instruction** (the prompt) — e.g. *"replace the large shadow with a small, soft
   one; keep the product unchanged."*
2. The model returns the edited image.
3. **Automated quality checks** flag anything that looks off (no visible change,
   shadow not reduced, patchy background). Flagging is deliberately aggressive —
   you can unflag in one click during review.

You choose the editing model **and** the prompt per batch, and can override either
on a single image while reviewing.

### Editing models (chosen per batch)

| Model | Notes |
|-------|-------|
| **FLUX.1 Kontext [pro]** — default | Strong product/identity preservation. Supports a guidance-scale control. |
| **FLUX.1 Kontext [max]** | Higher quality, more expensive. |
| **FLUX.1 Kontext [dev]** | Cheaper Kontext variant. |
| **Nano Banana (Gemini 2.5 Flash Image)** | Good at compositing/relighting edits. |
| **Qwen Image Edit** | General instruction editing. |
| **SeedEdit 3.0** | General instruction editing. |

All run on **fal.ai** and use API credits.

> **Heads-up on quality:** generative editing is not perfectly consistent. Some
> models barely change a soft, low-contrast shadow. Use the in-app **sample
> preview** to test a model + prompt on a single image before committing a whole
> batch, and rely on the review/flagging step to catch misses.

## Setup

Requires Python 3.11+ and a [fal.ai](https://fal.ai) API key.

```bash
# from the project root
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Put your fal.ai key in a `.env` file at the project root (git-ignored — never
committed):

```
FAL_KEY=your-key-here
```

## Run

```bash
venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open **http://localhost:8000**.

> Run only one server at a time. If a stale process is holding the port:
> `pkill -f "uvicorn backend.main"` before restarting.

## Using it

1. **New batch** → give it a name.
2. **Add images** — drag & drop, or paste a local folder path to reference
   thousands of images in place (no copy).
3. **Configure** — pick the **AI editing model**, edit the **prompt**, and choose
   the **output format** (JPG / PNG / WebP / preserve original).
4. **Preview** a sample to test the model + prompt on one image, then
   **Confirm & Start**.
5. **Review** — grid of results; flagged ones have a red border. Click any image
   for a before/after view. Approve, flag/unflag, revert to original, or re-run a
   single image with a different prompt or model.
6. **Export** approved images to a folder you choose. Originals are never modified.

## Testing the image-processing approach

An earlier approach — **background removal (BRIA / rembg) + a programmatic shadow
composite** instead of a generative model — is preserved at the git tag
**`image-processing`**. To run it:

```bash
pkill -f "uvicorn backend.main"     # stop any running server
git checkout image-processing       # jump to that version (detached HEAD)

venv/bin/uvicorn backend.main:app --port 8000
# test at http://localhost:8000

git checkout main                   # return to the latest (generative) version
```

`.env`, `data/`, and `venv/` are git-ignored, so switching versions never touches
your key, database, or installed packages. `git checkout image-processing` leaves
you in "detached HEAD" (normal for viewing an old commit) — `git checkout main`
brings you back.

## Project layout

```
backend/
  main.py            FastAPI app, WebSocket, static serving (cache-busted)
  config.py          paths, .env loading, models + default settings
  database.py        SQLAlchemy engine/session (SQLite)
  models.py          Batch, Image
  routers/           batches.py · images.py · export.py
  services/
    editing.py       generative instruction-editing via fal.ai
    quality.py       auto-flagging checks
    processor.py     batch runner (pause/resume/cancel, live progress)
    ws.py            WebSocket manager
frontend/
  index.html         Tailwind shell
  app.js             Preact single-page UI (Home · New · Processing · Review · Export)
data/                SQLite DB + processed images + thumbnails (git-ignored)
```

## Notes

- **Originals are never overwritten.** Processed files live under `data/`; export
  copies approved results to your chosen folder.
- **Resumable:** if the server stops mid-batch, restart it and the batch picks up
  from the last completed image.
- **Single user, local:** no authentication; designed to run on your own machine.
- A `.gitignore` keeps `.env` (your key), `venv/`, and `data/` out of version
  control.
