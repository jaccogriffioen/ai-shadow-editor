const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, TableOfContents, LevelFormat
} = require("docx");
const fs = require("fs");

const BLUE = "1F3864";
const LIGHT_BLUE = "D5E8F0";
const MID_BLUE = "2E75B6";
const WHITE = "FFFFFF";
const GRAY = "F2F2F2";

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 200 },
    children: [new TextRun({ text, bold: true, size: 32, font: "Arial", color: BLUE })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 300, after: 160 },
    children: [new TextRun({ text, bold: true, size: 26, font: "Arial", color: MID_BLUE })]
  });
}

function p(text, options = {}) {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    children: [new TextRun({ text, size: 22, font: "Arial", ...options })]
  });
}

function mono(text) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    indent: { left: 720 },
    children: [new TextRun({ text, size: 20, font: "Courier New", color: "333333" })]
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text, size: 22, font: "Arial" })]
  });
}

function numbered(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "numbers", level },
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text, size: 22, font: "Arial" })]
  });
}

function spacer() {
  return new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun("")] });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function headerRow(cells, widths) {
  return new TableRow({
    tableHeader: true,
    children: cells.map((text, i) =>
      new TableCell({
        borders,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: BLUE, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 100, left: 150, right: 150 },
        children: [new Paragraph({
          children: [new TextRun({ text, bold: true, size: 20, font: "Arial", color: WHITE })]
        })]
      })
    )
  });
}

function dataRow(cells, widths, shade = false) {
  return new TableRow({
    children: cells.map((text, i) =>
      new TableCell({
        borders,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: shade ? GRAY : WHITE, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 150, right: 150 },
        children: [new Paragraph({
          children: [new TextRun({ text, size: 20, font: "Arial" })]
        })]
      })
    )
  });
}

function table(headers, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      headerRow(headers, widths),
      ...rows.map((row, i) => dataRow(row, widths, i % 2 === 1))
    ]
  });
}

const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } }
        }, {
          level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } }
        }]
      },
      {
        reference: "numbers",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } }
        }]
      }
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: BLUE },
        paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0 }
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: MID_BLUE },
        paragraph: { spacing: { before: 300, after: 160 }, outlineLevel: 1 }
      }
    ]
  },
  sections: [
    // ── COVER PAGE ──────────────────────────────────────────────
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
      },
      children: [
        spacer(), spacer(), spacer(), spacer(),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 400, after: 200 },
          children: [new TextRun({ text: "AI Shadow Editor", bold: true, size: 64, font: "Arial", color: BLUE })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 100, after: 100 },
          children: [new TextRun({ text: "Requirements & Solution Design Report", size: 36, font: "Arial", color: MID_BLUE })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 80, after: 80 },
          children: [new TextRun({ text: "Software Consultant Report", size: 26, font: "Arial", color: "666666", italics: true })]
        }),
        spacer(), spacer(),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "June 15, 2026", size: 24, font: "Arial", color: "444444" })]
        }),
        pageBreak()
      ]
    },
    // ── MAIN CONTENT ────────────────────────────────────────────
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: MID_BLUE, space: 1 } },
            children: [new TextRun({ text: "AI Shadow Editor — Requirements & Solution Design Report", size: 18, font: "Arial", color: "666666" })]
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            border: { top: { style: BorderStyle.SINGLE, size: 6, color: MID_BLUE, space: 1 } },
            children: [
              new TextRun({ text: "Page ", size: 18, font: "Arial", color: "666666" }),
              new TextRun({ children: [PageNumber.CURRENT], size: 18, font: "Arial", color: "666666" }),
              new TextRun({ text: " of ", size: 18, font: "Arial", color: "666666" }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, font: "Arial", color: "666666" })
            ]
          })]
        })
      },
      children: [
        // TABLE OF CONTENTS
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          children: [new TextRun({ text: "Table of Contents", bold: true, size: 32, font: "Arial", color: BLUE })]
        }),
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
        pageBreak(),

        // 1. EXECUTIVE SUMMARY
        h1("1. Executive Summary"),
        p("A web shop owner needs to batch-process approximately 4,000 product images to replace large, heavy drop shadows with a soft, small studio-style shadow using generative AI. Because AI results are inconsistent, a human review workflow is required after processing."),
        spacer(),
        p("The solution is a local server web app running on the user's machine, accessed via browser at localhost, with full state persistence so no progress is ever lost."),
        spacer(),

        // 2. PROBLEM STATEMENT
        h1("2. Problem Statement"),
        p("The client operates a web shop with approximately 4,000 product images. These images currently have large, heavy drop shadows that are inconsistent with the desired clean, minimal studio aesthetic."),
        spacer(),
        p("The goals are:"),
        bullet("Replace large shadows with a soft, small drop shadow, consistent across all images"),
        bullet("Process all images in batch using generative AI"),
        bullet("Review results and handle cases where the AI output is unsatisfactory"),
        bullet("Export approved images to a local folder for use in the web shop"),
        spacer(),

        // 3. REQUIREMENTS
        h1("3. Requirements"),
        h2("3.1 Functional Requirements"),

        p("FR-1: Image Ingestion", { bold: true }),
        bullet("Drag-and-drop interface to load images from a local folder"),
        bullet("Support JPG, PNG, WebP, TIFF, and RAW formats"),
        bullet("Images displayed in a queue before processing starts"),
        bullet("User can add or remove images before triggering the batch"),
        spacer(),

        p("FR-2: Batch Processing", { bold: true }),
        bullet("Process images sequentially via fal.ai generative AI API"),
        bullet("Target output: soft, small drop shadow beneath the product on a clean background"),
        bullet("Show real-time progress during the batch (progress bar, current image, count)"),
        bullet("Processing can be paused or cancelled mid-batch"),
        bullet("Before the batch starts, a Batch Configuration screen is shown (see FR-6)"),
        spacer(),

        p("FR-3: Auto-Flagging (conservative — over-flagging preferred)", { bold: true }),
        p("Flag an image automatically if ANY of the following are detected:"),
        bullet("Low AI confidence score returned by fal.ai"),
        bullet("Shadow area in output is within 80% of original shadow area (not sufficiently reduced)"),
        bullet("Edge detection finds distortion around the product silhouette"),
        bullet("Background has color inconsistency or artifacts above a threshold"),
        p("Note: The reviewer can always manually unflag any image.", { italics: true, color: "666666" }),
        spacer(),

        p("FR-4: Review Screen", { bold: true }),
        bullet("Grid view of all processed images"),
        bullet("Flagged images visually marked with a red border/highlight"),
        bullet("Click an image to see a side-by-side before/after preview"),
        bullet("Filter/sort by: All / Flagged / Approved / Pending"),
        bullet("Per-image actions:"),
        bullet("Approve — mark as accepted", 1),
        bullet("Re-prompt — send a custom or adjusted prompt to re-run fal.ai on that image", 1),
        bullet("Unflag — override the auto-flag and accept as-is", 1),
        bullet("Revert — discard AI result, keep original image", 1),
        spacer(),

        p("FR-5: Export", { bold: true }),
        bullet("Export all approved images to a local folder chosen by the user"),
        bullet("Originals are never overwritten — always kept intact"),
        bullet("Export preserves original filenames"),
        bullet("Output format selectable per batch (see FR-6)"),
        spacer(),

        p("FR-6: Batch Configuration Screen (shown before every batch)", { bold: true }),
        bullet("Current shadow settings: blur radius, opacity, offset, color (editable, defaults pre-filled)"),
        bullet("AI prompt shown and editable"),
        bullet("Output format selector: JPG / PNG / WebP / Preserve original"),
        bullet("Number of images queued"),
        bullet("Estimated API cost"),
        bullet("Sample preview applied to 1–2 images from the batch"),
        bullet("“Confirm & Start” button"),
        spacer(),

        p("FR-7: Batch History", { bold: true }),
        bullet("All batches stored with full state: images, results, flags, review decisions, export records"),
        bullet("Accessible from the home screen"),
        bullet("Any past batch can be reopened, re-reviewed, or re-exported"),
        spacer(),

        h2("3.2 Non-Functional Requirements"),
        table(
          ["ID", "Requirement", "Detail"],
          [
            ["NFR-1", "Web app UI", "Accessed at localhost in the browser"],
            ["NFR-2", "Local server", "Runs as a server process on the user’s machine — no cloud hosting required"],
            ["NFR-3", "API key security", "fal.ai API key stored in a local .env file, never hardcoded"],
            ["NFR-4", "Sequential processing", "No parallelism needed; steady queue is acceptable"],
            ["NFR-5", "Scale", "Must handle 4,000+ images without losing state"],
            ["NFR-6", "Single user", "No authentication or multi-user roles required"],
            ["NFR-7", "Persistence", "SQLite database — full state saved after every image; resumable after any interruption"],
            ["NFR-8", "Non-destructive", "Input files are never modified; originals always preserved"],
          ],
          [1200, 2800, 5360]
        ),
        spacer(),

        // 4. USER STORIES
        h1("4. User Stories"),
        table(
          ["Priority", "User Story", "Acceptance Criteria"],
          [
            ["P0", "As a user, I can drag and drop a folder of images to load them into a batch", "Images appear in a queue with thumbnails and a count"],
            ["P0", "As a user, I can review and confirm batch settings before processing starts", "Batch Configuration screen shown with shadow settings, prompt, format, and sample preview"],
            ["P0", "As a user, I can see real-time progress while images are being processed", "Progress bar shows X of N images, current image visible"],
            ["P0", "As a user, I can review all results in a grid after processing", "Grid shows all images; flagged ones have a red highlight"],
            ["P0", "As a user, I can click an image to see a before/after preview", "Side-by-side or toggle view of original vs. processed"],
            ["P0", "As a user, I can export approved images to a local folder", "Approved files saved to chosen path in chosen format"],
            ["P1", "As a user, I can re-send a custom prompt for a specific image", "Re-prompt reruns fal.ai on that image and updates the result in the review grid"],
            ["P1", "As a user, I can manually flag or unflag any image", "Flag/unflag toggles the red highlight and review status"],
            ["P1", "As a user, I can filter the review grid by status", "Filter bar: All / Flagged / Approved / Pending"],
            ["P2", "As a user, I can pause or cancel a running batch", "Pause/cancel controls visible during processing; state saved on pause"],
            ["P2", "As a user, my progress is preserved if the app is closed or machine restarts", "On relaunch, the current batch resumes from the last completed image"],
            ["P2", "As a user, I can revisit and re-export any past batch", "Home screen lists all past batches with status and date"],
          ],
          [900, 4200, 4260]
        ),
        spacer(),

        // 5. AI PROCESSING APPROACH
        h1("5. AI Processing Approach"),
        h2("5.1 Chosen Approach: Background Removal + Programmatic Shadow Generation"),
        p("Since all product images are already on a plain or white background, the processing pipeline uses two steps:"),
        spacer(),
        p("Step 1 — Background Removal (AI)", { bold: true }),
        p("The fal-ai/bria-background-removal model isolates the product by removing the existing background and shadow. BRIA is best-in-class for product photos on white or plain backgrounds."),
        spacer(),
        p("Step 2 — Shadow Compositing (Programmatic)", { bold: true }),
        p("A soft drop shadow is generated and composited beneath the isolated product using Pillow (Python image library). This step is entirely deterministic — the same shadow parameters are applied to every image in the batch, guaranteeing visual consistency across all 4,000 product photos."),
        spacer(),

        h2("5.2 Why Not Generative Inpainting?"),
        p("An alternative approach would use AI inpainting to modify the shadow area directly. This was rejected because:"),
        bullet("Inpainting introduces variance — the AI decides what the shadow looks like, producing inconsistent results"),
        bullet("For e-commerce, consistency is a hard requirement"),
        bullet("Inpainting would increase the rate of flagged images — the core problem to minimise"),
        bullet("The chosen approach is more predictable and cheaper to run"),
        spacer(),

        h2("5.3 Quality Flagging Pipeline"),
        p("After each image is processed, the following automated checks run:"),
        numbered("fal.ai confidence score check — flag if below threshold"),
        numbered("Shadow area ratio check — flag if output shadow is within 80% of original size"),
        numbered("Edge integrity check (OpenCV) — detect distortion around the product silhouette"),
        numbered("Background uniformity check (OpenCV) — detect color inconsistency or artifacts"),
        spacer(),
        p("Philosophy: flag aggressively. It is better to flag a good image (the reviewer unflagged it in seconds) than to miss a bad one that reaches the web shop.", { italics: true }),
        spacer(),

        // 6. ARCHITECTURE DESIGN
        h1("6. Architecture Design"),
        h2("6.1 Architecture Decision: Local Server"),
        p("The application runs as a local server process on the user’s machine and is accessed via a browser at localhost:8000. This was chosen over a cloud-hosted server or a native desktop app for the following reasons:"),
        spacer(),
        table(
          ["Factor", "Local Server", "Cloud Server", "Desktop App"],
          [
            ["Large local files / external drives", "Direct access, no upload", "Upload required — impractical for GBs of images", "Direct access"],
            ["Volatility / progress loss", "Solved by SQLite persistence", "N/A", "Solved by SQLite persistence"],
            ["Accessibility", "Localhost only — acceptable for single user", "Accessible anywhere", "Local only"],
            ["Complexity", "Low", "High (file sync, storage, auth)", "Medium (packaging, distribution)"],
            ["Future migration", "Easy to move to cloud if needed", "N/A", "Harder to migrate"],
          ],
          [2400, 2200, 2380, 2380]
        ),
        spacer(),

        h2("6.2 Architecture Diagram"),
        mono("Browser (localhost:8000)"),
        mono("  React + Tailwind CSS (static files served by FastAPI)"),
        mono("          |"),
        mono("          | HTTP / WebSocket"),
        mono("          |"),
        mono("    FastAPI (Python)"),
        mono("      /api/batches      — batch management"),
        mono("      /api/images       — image state & flags"),
        mono("      /api/process      — trigger processing & stream progress"),
        mono("      /api/export       — write approved files to disk"),
        mono("          |"),
        mono("    Processing Pipeline"),
        mono("      fal-ai SDK        — background removal (BRIA model)"),
        mono("      Pillow            — shadow compositing & format conversion"),
        mono("      OpenCV            — quality flagging checks"),
        mono("          |"),
        mono("    SQLite (via SQLAlchemy)"),
        mono("      batches table"),
        mono("      images table (status, flags, file paths, results)"),
        mono("      results table"),
        mono("          |"),
        mono("    Local Disk / External Drive"),
        mono("      /input            — original images (never modified)"),
        mono("      /output           — approved exports"),
        spacer(),

        h2("6.3 User Flow"),
        table(
          ["Screen", "Description"],
          [
            ["Home Screen", "Shows batch history and New Batch button"],
            ["New Batch Setup", "Drag & drop images, configure batch settings, preview sample, confirm"],
            ["Processing Screen", "Real-time progress bar, current image, pause/cancel controls"],
            ["Review Screen", "Grid with red-flagged images, before/after preview, per-image actions"],
            ["Export Screen", "Choose output folder, review summary, export approved images"],
          ],
          [2800, 6560]
        ),
        spacer(),

        // 7. TECH STACK
        h1("7. Tech Stack"),
        table(
          ["Layer", "Technology", "Reason for Choice"],
          [
            ["Backend", "Python + FastAPI", "First-class image processing ecosystem; fal.ai SDK is Python-native; automatic API documentation"],
            ["Frontend", "React + Tailwind CSS", "Handles dynamic review grid and real-time updates; served as static files by FastAPI — no separate server needed"],
            ["Database", "SQLite + SQLAlchemy", "Zero setup; single file on disk; survives restarts; clean ORM layer; perfect for single-user local app"],
            ["Image Processing", "Pillow", "Shadow compositing, format conversion, resizing"],
            ["Quality Checks", "OpenCV", "Edge detection (product distortion), shadow area comparison, background uniformity check"],
            ["AI / API", "fal-ai Python SDK", "Background removal via BRIA model; direct fal.ai platform integration"],
            ["Real-time Updates", "WebSocket", "Streams per-image progress from backend to browser without polling"],
            ["API Key Storage", ".env file", "fal.ai key stored locally, never hardcoded or committed to version control"],
          ],
          [2000, 2200, 5160]
        ),
        spacer(),

        h2("7.1 Key Technical Decisions"),
        table(
          ["Decision", "Choice", "Reason"],
          [
            ["Progress updates", "WebSocket", "Real-time per-image updates without polling"],
            ["File references", "Store file paths in DB, not file copies", "No duplication until export — fast and storage-efficient"],
            ["Shadow generation", "Pillow (code), not AI", "Deterministic — identical shadow on every image, guaranteeing consistency"],
            ["Background removal", "fal.ai BRIA model", "Best-in-class accuracy for product photos on plain backgrounds"],
            ["State resumability", "SQLite row per image with a status field", "On restart, query WHERE status = 'pending' and continue from where processing stopped"],
          ],
          [2400, 2800, 4160]
        ),
        spacer(),

        // 8. PROJECT STRUCTURE
        h1("8. Project Structure"),
        mono("shadow-editor/"),
        mono("├── backend/"),
        mono("│   ├── main.py                  # FastAPI app entry point"),
        mono("│   ├── database.py              # SQLAlchemy models and DB connection"),
        mono("│   ├── routers/"),
        mono("│   │   ├── batches.py           # Batch CRUD and history"),
        mono("│   │   ├── images.py            # Image state and flag management"),
        mono("│   │   └── export.py            # Export approved images to disk"),
        mono("│   ├── services/"),
        mono("│   │   ├── processor.py         # fal.ai + Pillow processing pipeline"),
        mono("│   │   └── quality.py           # OpenCV flagging logic"),
        mono("│   └── .env                     # FAL_API_KEY (not committed to version control)"),
        mono("├── frontend/"),
        mono("│   ├── src/"),
        mono("│   │   ├── pages/"),
        mono("│   │   │   ├── Home.tsx         # Batch history and new batch entry"),
        mono("│   │   │   ├── NewBatch.tsx     # Image ingestion and batch configuration"),
        mono("│   │   │   ├── Processing.tsx   # Real-time progress view"),
        mono("│   │   │   └── Review.tsx       # Review grid with before/after preview"),
        mono("│   │   └── components/          # Shared UI components"),
        mono("│   └── package.json"),
        mono("├── requirements.txt             # Python dependencies"),
        mono("└── README.md                    # Setup and run instructions"),
        spacer(),

        // 9. OPEN DECISIONS
        h1("9. Open Decisions & Future Considerations"),
        table(
          ["Topic", "Detail"],
          [
            ["Shadow fine-tuning", "Default shadow parameters (blur, opacity, offset) will need calibration against real product images. A test run on 10–20 samples is recommended before processing all 4,000."],
            ["Re-prompt limitation", "When a user re-prompts a flagged image, the system retries the full pipeline. If background removal itself is the failure point, the user’s custom prompt has limited effect — this should be communicated in the UI."],
            ["Output format recommendation", "WebP is recommended as the default output format — equivalent visual quality to JPG at roughly half the file size, supported by all modern browsers."],
            ["Scalability path", "The local server architecture can be migrated to a cloud deployment with minimal backend changes if volume grows. The main addition would be cloud storage (e.g. S3) replacing local file access."],
            ["Cost estimation", "fal.ai charges per API call. An estimated cost should be calculated and shown on the Batch Configuration screen before the user confirms a batch."],
          ],
          [2400, 6960]
        ),
        spacer(),
      ]
    }
  ]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/Users/jaccogriffioen/Documents/AI tooling projects/Shadow editor/AI_Shadow_Editor_Requirements_Report.docx", buffer);
  console.log("Done: AI_Shadow_Editor_Requirements_Report.docx");
});
