import { h, render } from "https://esm.sh/preact@10.24.3";
import { useState, useEffect, useRef, useCallback } from "https://esm.sh/preact@10.24.3/hooks";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(h);

// --- API helpers -------------------------------------------------------------
async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}
const jpost = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
const jpatch = (path, body) =>
  api(path, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

function hexToRgb(hex) {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [255, 255, 255];
}
const rgbToHex = (rgb) =>
  "#" + (rgb || [255, 255, 255]).map((v) => v.toString(16).padStart(2, "0")).join("");

// Populated from /api/status (config.EDIT_MODELS). Fallback list mirrors it.
let EDIT_MODELS = [
  { id: "fal-ai/flux-pro/kontext", label: "FLUX.1 Kontext [pro]" },
  { id: "fal-ai/flux-pro/kontext/max", label: "FLUX.1 Kontext [max]" },
  { id: "fal-ai/flux-kontext/dev", label: "FLUX.1 Kontext [dev] (cheaper)" },
  { id: "fal-ai/gemini-25-flash-image/edit", label: "Nano Banana (Gemini 2.5 Flash Image)" },
  { id: "fal-ai/qwen-image-edit", label: "Qwen Image Edit" },
  { id: "fal-ai/bytedance/seededit/v3/edit-image", label: "SeedEdit 3.0" },
];
const modelLabel = (id) => EDIT_MODELS.find((m) => m.id === id)?.label || id;

// --- Small UI pieces ---------------------------------------------------------
const Btn = ({ onClick, children, kind = "primary", disabled, type }) => {
  const styles = {
    primary: "bg-brand text-white hover:bg-brand-mid",
    secondary: "bg-white text-brand border border-brand/30 hover:bg-brand-light/40",
    ghost: "bg-transparent text-slate-600 hover:bg-slate-100",
    danger: "bg-red-600 text-white hover:bg-red-700",
    success: "bg-emerald-600 text-white hover:bg-emerald-700",
  };
  return html`<button type=${type || "button"} disabled=${disabled} onClick=${onClick}
    class=${`px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-40 disabled:cursor-not-allowed ${styles[kind]}`}>
    ${children}</button>`;
};

const Header = ({ navigate, current }) => html`
  <header class="bg-brand text-white shadow">
    <div class="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
      <div class="flex items-center gap-3 cursor-pointer" onClick=${() => navigate("home")}>
        <div class="w-9 h-9 rounded-lg bg-white/15 flex items-center justify-center text-lg">◐</div>
        <div>
          <div class="font-semibold leading-tight">AI Shadow Editor</div>
          <div class="text-xs text-white/70 leading-tight">Batch product-image shadow tool</div>
        </div>
      </div>
      <button onClick=${() => navigate("home")}
        class=${`text-sm px-3 py-1.5 rounded-md ${current === "home" ? "bg-white/20" : "hover:bg-white/10"}`}>
        Batches</button>
    </div>
  </header>`;

const Bar = ({ counts }) => {
  const total = counts.total || 0;
  const done = counts.done || 0;
  const pct = total ? Math.round((done / total) * 100) : 0;
  return html`
    <div>
      <div class="h-3 bg-slate-200 rounded-full overflow-hidden">
        <div class="h-full bg-brand-mid transition-all" style=${`width:${pct}%`}></div>
      </div>
      <div class="text-xs text-slate-500 mt-1">${done} / ${total} processed · ${pct}%</div>
    </div>`;
};

// --- Home --------------------------------------------------------------------
function Home({ navigate }) {
  const [batches, setBatches] = useState(null);
  const load = () => api("/api/batches").then(setBatches).catch(() => setBatches([]));
  useEffect(() => { load(); }, []);

  const del = async (id, e) => {
    e.stopPropagation();
    if (!confirm("Delete this batch and its processed files? Originals are untouched.")) return;
    await api(`/api/batches/${id}`, { method: "DELETE" });
    load();
  };

  const statusBadge = (s) => {
    const map = {
      created: "bg-slate-100 text-slate-600", processing: "bg-amber-100 text-amber-700",
      paused: "bg-blue-100 text-blue-700", done: "bg-emerald-100 text-emerald-700",
      error: "bg-red-100 text-red-700",
    };
    return html`<span class=${`text-xs px-2 py-0.5 rounded-full ${map[s] || map.created}`}>${s}</span>`;
  };

  return html`
    <div class="max-w-6xl mx-auto px-6 py-8">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-brand">Batches</h1>
        <${Btn} onClick=${() => navigate("new")}>+ New batch<//>
      </div>
      ${batches === null && html`<div class="text-slate-400">Loading…</div>`}
      ${batches && batches.length === 0 && html`
        <div class="bg-white border border-dashed border-slate-300 rounded-xl p-12 text-center text-slate-500">
          <div class="text-4xl mb-3">📦</div>
          <p class="mb-4">No batches yet. Create one to start editing shadows.</p>
          <${Btn} onClick=${() => navigate("new")}>+ New batch<//>
        </div>`}
      <div class="grid gap-3">
        ${(batches || []).map((b) => html`
          <div key=${b.id} onClick=${() => navigate(b.status === "done" || b.counts.done ? "review" : "processing", b.id)}
            class="bg-white rounded-xl border border-slate-200 p-4 flex items-center justify-between hover:shadow-sm cursor-pointer">
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-slate-800">${b.name}</span>
                ${statusBadge(b.status)}
                <span class="text-xs text-slate-400">#${b.id}</span>
              </div>
              <div class="text-xs text-slate-500 mt-1">
                ${b.counts.total} images · ${b.counts.done} done · ${b.counts.flagged} flagged · ${b.counts.approved} approved
                · model: ${modelLabel(b.config.fal_model)}
              </div>
            </div>
            <div class="flex items-center gap-2">
              <${Btn} kind="secondary" onClick=${(e) => { e.stopPropagation(); navigate("review", b.id); }}>Review<//>
              <${Btn} kind="ghost" onClick=${(e) => del(b.id, e)}>🗑<//>
            </div>
          </div>`)}
      </div>
    </div>`;
}

// --- Shadow / config controls ------------------------------------------------
const Field = ({ label, children, hint }) => html`
  <label class="block mb-3">
    <div class="text-sm font-medium text-slate-700 mb-1">${label}</div>
    ${children}
    ${hint && html`<div class="text-xs text-slate-400 mt-1">${hint}</div>`}
  </label>`;

const Slider = ({ label, value, min, max, step, onInput, fmt }) => html`
  <div class="mb-3">
    <div class="flex justify-between text-sm mb-1">
      <span class="text-slate-700">${label}</span>
      <span class="text-slate-500 tabular-nums">${fmt ? fmt(value) : value}</span>
    </div>
    <input type="range" min=${min} max=${max} step=${step} value=${value}
      onInput=${(e) => onInput(parseFloat(e.target.value))} class="w-full accent-brand-mid" />
  </div>`;

function ConfigForm({ config, setConfig, falKeyPresent }) {
  const set = (k, v) => setConfig({ ...config, [k]: v });
  const isKontext = (config.fal_model || "").includes("kontext");

  return html`
    <div class="grid md:grid-cols-2 gap-6">
      <div>
        <${Field} label="AI editing model" hint="The model that edits each image. Use the preview below to test it on one image before processing the whole batch.">
          <select value=${config.fal_model} onChange=${(e) => set("fal_model", e.target.value)}
            class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
            ${EDIT_MODELS.map((m) => html`<option value=${m.id}>${m.label}</option>`)}
          </select>
          ${!falKeyPresent && html`<div class="text-xs text-red-500 mt-1">No fal.ai API key detected on the server.</div>`}
        <//>

        <${Field} label="Output format" hint="Applied when you export approved images">
          <select value=${config.output_format} onChange=${(e) => set("output_format", e.target.value)}
            class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
            <option value="original">Preserve original</option>
            <option value="jpg">JPG</option>
            <option value="png">PNG</option>
            <option value="webp">WebP (recommended for web)</option>
          </select>
        <//>

        ${isKontext && html`
          <${Slider} label="Guidance scale" value=${config.guidance_scale ?? 3.5} min=1 max=10 step=0.5
            onInput=${(v) => set("guidance_scale", v)} fmt=${(v) => v.toFixed(1)} />`}
      </div>

      <div>
        <${Field} label="Editing instruction (prompt)" hint="Sent with every image in the batch. You can still override it per image during review.">
          <textarea value=${config.prompt} onInput=${(e) => set("prompt", e.target.value)} rows="8"
            class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm leading-relaxed"></textarea>
        <//>
      </div>
    </div>`;
}

// --- New batch ---------------------------------------------------------------
function NewBatch({ navigate, falKeyPresent, defaultConfig }) {
  const [batch, setBatch] = useState(null);
  const [config, setConfig] = useState(defaultConfig);
  const [name, setName] = useState("");
  const [count, setCount] = useState(0);
  const [scanPath, setScanPath] = useState("");
  const [busy, setBusy] = useState("");
  const [sample, setSample] = useState(null);
  const [err, setErr] = useState("");
  const dropRef = useRef();

  const batchRef = useRef(null);

  // Create the draft batch lazily — only once the user actually adds images,
  // so abandoning the New Batch screen never leaves an orphan "Untitled batch".
  const ensureBatch = async () => {
    if (batchRef.current) return batchRef.current;
    const b = await jpost("/api/batches", { name: name || "Untitled batch", config });
    batchRef.current = b;
    setBatch(b);
    return b;
  };

  const refresh = async () => {
    const b = await api(`/api/batches/${batchRef.current.id}`);
    setBatch(b); setCount(b.counts.total);
  };

  const uploadFiles = async (files) => {
    if (!files.length) return;
    setBusy("Uploading…"); setErr("");
    try {
      const b = await ensureBatch();
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      await api(`/api/batches/${b.id}/upload`, { method: "POST", body: fd });
      await refresh();
    } catch (e) { setErr(e.message); }
    setBusy("");
  };

  const onDrop = (e) => {
    e.preventDefault();
    dropRef.current?.classList.remove("ring-2");
    uploadFiles([...e.dataTransfer.files]);
  };
  const onPick = (e) => uploadFiles([...e.target.files]);

  const scan = async () => {
    if (!scanPath.trim()) return;
    setBusy("Scanning folder…"); setErr("");
    try {
      const b = await ensureBatch();
      const r = await jpost(`/api/batches/${b.id}/scan`, { path: scanPath });
      await refresh();
      if (r.added === 0) setErr("No supported images found in that folder.");
    } catch (e) { setErr(e.message); }
    setBusy("");
  };

  const doSample = async () => {
    setBusy("Rendering preview…"); setErr(""); setSample(null);
    try {
      const b = await ensureBatch();
      await jpatch(`/api/batches/${b.id}`, { name, config });
      const r = await jpost(`/api/batches/${b.id}/sample`, { config });
      if (r.status === "error") { setErr("Preview failed: " + r.error); }
      else setSample({ id: r.id, t: Date.now(), flagged: r.flagged, reasons: r.reasons });
    } catch (e) { setErr(e.message); }
    setBusy("");
  };

  const start = async () => {
    setBusy("Starting…"); setErr("");
    try {
      const b = await ensureBatch();
      await jpatch(`/api/batches/${b.id}`, { name, config });
      await jpost(`/api/batches/${b.id}/start`);
      navigate("processing", b.id);
    } catch (e) { setErr(e.message); setBusy(""); }
  };

  return html`
    <div class="max-w-5xl mx-auto px-6 py-8 space-y-6">
      <h1 class="text-2xl font-bold text-brand">New batch</h1>

      <section class="bg-white rounded-xl border border-slate-200 p-5">
        <h2 class="font-semibold text-slate-800 mb-3">1 · Name</h2>
        <input value=${name} onInput=${(e) => setName(e.target.value)} placeholder="e.g. Spring catalogue"
          class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
      </section>

      <section class="bg-white rounded-xl border border-slate-200 p-5">
        <h2 class="font-semibold text-slate-800 mb-3">2 · Add images <span class="text-sm font-normal text-slate-400">(${count} added)</span></h2>
        <div ref=${dropRef} onDragOver=${(e) => { e.preventDefault(); dropRef.current?.classList.add("ring-2"); }}
          onDragLeave=${() => dropRef.current?.classList.remove("ring-2")} onDrop=${onDrop}
          class="border-2 border-dashed border-slate-300 ring-brand-mid rounded-xl p-8 text-center text-slate-500">
          <div class="text-3xl mb-2">⬇️</div>
          <p class="mb-2">Drag & drop images here</p>
          <label class="inline-block text-sm text-brand-mid cursor-pointer underline">
            or browse files
            <input type="file" multiple accept="image/*" class="hidden" onChange=${onPick} />
          </label>
        </div>
        <div class="mt-4">
          <div class="text-sm text-slate-600 mb-1">…or reference a local folder directly (no copy — best for thousands of images)</div>
          <div class="flex gap-2">
            <input value=${scanPath} onInput=${(e) => setScanPath(e.target.value)}
              placeholder="/Users/you/product_images_raw"
              class="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono" />
            <${Btn} kind="secondary" onClick=${scan}>Scan folder<//>
          </div>
        </div>
      </section>

      <section class="bg-white rounded-xl border border-slate-200 p-5">
        <h2 class="font-semibold text-slate-800 mb-3">3 · Configure</h2>
        <${ConfigForm} config=${config} setConfig=${setConfig} falKeyPresent=${falKeyPresent} />
      </section>

      <section class="bg-white rounded-xl border border-slate-200 p-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-semibold text-slate-800">4 · Preview</h2>
          <${Btn} kind="secondary" onClick=${doSample} disabled=${count === 0 || !!busy}>Generate sample preview<//>
        </div>
        ${count === 0 && html`<div class="text-sm text-slate-400">Add at least one image to preview.</div>`}
        ${sample && html`
          <div>
            <div class="grid grid-cols-2 gap-4">
              <figure><figcaption class="text-xs text-slate-500 mb-1">Original</figcaption>
                <img src=${`/api/images/${sample.id}/original?t=${sample.t}`} class="w-full rounded-lg border border-slate-200" /></figure>
              <figure><figcaption class="text-xs text-slate-500 mb-1">Result</figcaption>
                <img src=${`/api/images/${sample.id}/result?t=${sample.t}`} class="w-full rounded-lg border border-slate-200 checker" /></figure>
            </div>
            ${sample.flagged && html`<div class="mt-2 text-sm text-red-600">⚠ Would be flagged: ${sample.reasons.join("; ")}</div>`}
          </div>`}
      </section>

      ${err && html`<div class="text-sm text-red-600">${err}</div>`}

      <div class="flex items-center justify-between">
        <${Btn} kind="ghost" onClick=${() => navigate("home")}>Cancel<//>
        <div class="flex items-center gap-3">
          ${busy && html`<span class="text-sm text-slate-400">${busy}</span>`}
          <${Btn} onClick=${start} disabled=${count === 0 || !!busy}>Confirm & Start (${count})<//>
        </div>
      </div>
    </div>`;
}

// --- Processing --------------------------------------------------------------
function Processing({ navigate, batchId }) {
  const [batch, setBatch] = useState(null);
  const [counts, setCounts] = useState({ total: 0, done: 0, flagged: 0, error: 0 });
  const [last, setLast] = useState([]);
  const [status, setStatus] = useState("");
  const wsRef = useRef();

  useEffect(() => {
    api(`/api/batches/${batchId}`).then((b) => { setBatch(b); setCounts(b.counts); setStatus(b.status); });
    const ws = new WebSocket(`ws://${location.host}/ws/batches/${batchId}`);
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.counts) setCounts(m.counts);
      if (m.status) setStatus(m.status);
      if (m.type === "progress" && m.image) setLast((l) => [m.image, ...l].slice(0, 8));
    };
    return () => ws.close();
  }, [batchId]);

  const pause = () => jpost(`/api/batches/${batchId}/pause`).catch(() => {});
  const cancel = () => jpost(`/api/batches/${batchId}/cancel`).catch(() => {});
  const resume = () => jpost(`/api/batches/${batchId}/resume`).then(() => setStatus("processing")).catch((e) => alert(e.message));

  const running = status === "processing";
  const finished = counts.total > 0 && counts.done + counts.error >= counts.total;

  return html`
    <div class="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-brand">${batch?.name || "Processing"}</h1>
        <span class="text-sm px-3 py-1 rounded-full bg-slate-100 text-slate-600">${status}</span>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-6">
        <${Bar} counts=${counts} />
        <div class="grid grid-cols-4 gap-3 mt-5 text-center">
          ${[["Total", counts.total, "text-slate-700"], ["Done", counts.done, "text-emerald-600"],
             ["Flagged", counts.flagged, "text-red-600"], ["Errors", counts.error, "text-amber-600"]].map(
            ([l, v, c]) => html`<div class="bg-slate-50 rounded-lg py-3">
              <div class=${`text-2xl font-bold ${c}`}>${v}</div><div class="text-xs text-slate-500">${l}</div></div>`)}
        </div>
        <div class="flex gap-2 mt-6">
          ${running && html`<${Btn} kind="secondary" onClick=${pause}>Pause<//>`}
          ${running && html`<${Btn} kind="danger" onClick=${cancel}>Cancel<//>`}
          ${!running && !finished && html`<${Btn} onClick=${resume}>Resume<//>`}
          <div class="flex-1"></div>
          <${Btn} onClick=${() => navigate("review", batchId)}>Go to review →<//>
        </div>
      </div>

      ${last.length > 0 && html`
        <div class="bg-white rounded-xl border border-slate-200 p-5">
          <h2 class="text-sm font-semibold text-slate-700 mb-3">Recently processed</h2>
          <div class="grid grid-cols-8 gap-2">
            ${last.map((im) => html`
              <div key=${im.id} class=${`relative rounded-lg overflow-hidden border-2 ${im.flagged ? "border-red-400" : "border-transparent"}`}>
                <img src=${`/api/images/${im.id}/thumb?which=result&size=120`} class="w-full aspect-square object-cover checker" />
              </div>`)}
          </div>
        </div>`}
    </div>`;
}

// --- Review ------------------------------------------------------------------
const FILTERS = [
  { key: "all", label: "All", q: {} },
  { key: "flagged", label: "Flagged", q: { flagged: "true" } },
  { key: "pending", label: "Needs review", q: { review: "pending", status: "done" } },
  { key: "approved", label: "Approved", q: { review: "approved" } },
  { key: "reverted", label: "Reverted", q: { review: "reverted" } },
  { key: "error", label: "Errors", q: { status: "error" } },
];

function Review({ navigate, batchId }) {
  const [batch, setBatch] = useState(null);
  const [filter, setFilter] = useState("all");
  const [data, setData] = useState({ items: [], total: 0 });
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const pageSize = 60;

  const loadBatch = () => api(`/api/batches/${batchId}`).then(setBatch);
  const load = useCallback(() => {
    const f = FILTERS.find((x) => x.key === filter);
    const params = new URLSearchParams({ page, page_size: pageSize, ...f.q });
    api(`/api/batches/${batchId}/images?${params}`).then(setData);
  }, [batchId, filter, page]);

  useEffect(() => { loadBatch(); }, [batchId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(1); }, [filter]);

  const afterAction = () => { load(); loadBatch(); };
  const pages = Math.max(1, Math.ceil(data.total / pageSize));

  const ring = (im) => {
    if (im.status === "error") return "border-amber-400";
    if (im.flagged) return "border-red-400";
    if (im.review_status === "approved") return "border-emerald-400";
    if (im.review_status === "reverted") return "border-slate-400";
    return "border-transparent";
  };

  return html`
    <div class="max-w-6xl mx-auto px-6 py-8">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h1 class="text-2xl font-bold text-brand">${batch?.name || "Review"}</h1>
          ${batch && html`<div class="text-xs text-slate-500 mt-1">
            ${batch.counts.total} images · ${batch.counts.flagged} flagged · ${batch.counts.approved} approved · ${batch.counts.reverted} reverted</div>`}
        </div>
        <div class="flex gap-2">
          <${Btn} kind="secondary" onClick=${() => navigate("processing", batchId)}>Processing<//>
          <${Btn} kind="success" onClick=${() => navigate("export", batchId)}>Export →<//>
        </div>
      </div>

      <div class="flex flex-wrap gap-2 mb-4">
        ${FILTERS.map((f) => html`
          <button key=${f.key} onClick=${() => setFilter(f.key)}
            class=${`px-3 py-1.5 rounded-full text-sm ${filter === f.key ? "bg-brand text-white" : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"}`}>
            ${f.label} ${batch && f.key === "flagged" ? `(${batch.counts.flagged})` : ""}</button>`)}
      </div>

      ${data.items.length === 0 && html`<div class="text-slate-400 py-12 text-center">No images in this view.</div>`}

      <div class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
        ${data.items.map((im) => html`
          <div key=${im.id} onClick=${() => setSelected(im)}
            class=${`relative rounded-lg overflow-hidden border-2 cursor-pointer hover:shadow ${ring(im)}`}>
            <img src=${`/api/images/${im.id}/thumb?which=result&size=240&v=${im.review_status}${im.flagged}`}
              class="w-full aspect-square object-cover checker" loading="lazy" />
            ${im.flagged && html`<span class="absolute top-1 right-1 bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded">flag</span>`}
            ${im.review_status === "approved" && html`<span class="absolute top-1 right-1 bg-emerald-500 text-white text-[10px] px-1.5 py-0.5 rounded">✓</span>`}
          </div>`)}
      </div>

      ${pages > 1 && html`
        <div class="flex items-center justify-center gap-3 mt-6">
          <${Btn} kind="ghost" onClick=${() => setPage((p) => Math.max(1, p - 1))} disabled=${page === 1}>← Prev<//>
          <span class="text-sm text-slate-500">Page ${page} / ${pages}</span>
          <${Btn} kind="ghost" onClick=${() => setPage((p) => Math.min(pages, p + 1))} disabled=${page === pages}>Next →<//>
        </div>`}

      ${selected && html`<${Detail} image=${selected} batch=${batch} onClose=${() => setSelected(null)} onChange=${afterAction} setSelected=${setSelected} />`}
    </div>`;
}

function Detail({ image, batch, onClose, onChange, setSelected }) {
  const [busy, setBusy] = useState("");
  const [t, setT] = useState(Date.now());
  const [prompt, setPrompt] = useState(batch?.config?.prompt || "");
  const [model, setModel] = useState(batch?.config?.fal_model || EDIT_MODELS[0].id);
  const [reasons, setReasons] = useState(image.reasons || []);
  const [flagged, setFlagged] = useState(image.flagged);
  const [review, setReview] = useState(image.review_status);

  const act = async (fn) => { setBusy("…"); try { await fn(); onChange(); } catch (e) { alert(e.message); } setBusy(""); };
  const approve = () => act(async () => { await jpost(`/api/images/${image.id}/approve`); setReview("approved"); });
  const revert = () => act(async () => { await jpost(`/api/images/${image.id}/revert`); setReview("reverted"); });
  const toggleFlag = () => act(async () => {
    await jpost(`/api/images/${image.id}/${flagged ? "unflag" : "flag"}`); setFlagged(!flagged);
  });
  const reprocess = () => act(async () => {
    setBusy("Reprocessing…");
    const r = await jpost(`/api/images/${image.id}/reprocess`, {
      config: { fal_model: model, prompt },
    });
    setT(Date.now()); setReasons(r.reasons || []); setFlagged(!!r.flagged); setReview("pending");
  });

  return html`
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50" onClick=${onClose}>
      <div class="bg-white rounded-2xl max-w-4xl w-full max-h-[92vh] overflow-auto" onClick=${(e) => e.stopPropagation()}>
        <div class="flex items-center justify-between p-4 border-b border-slate-100">
          <div class="font-semibold text-slate-800 truncate">${image.filename}</div>
          <button onClick=${onClose} class="text-slate-400 hover:text-slate-700 text-xl leading-none">✕</button>
        </div>
        <div class="p-5 grid md:grid-cols-2 gap-4">
          <figure><figcaption class="text-xs text-slate-500 mb-1">Original</figcaption>
            <img src=${`/api/images/${image.id}/original?t=${t}`} class="w-full rounded-lg border border-slate-200" /></figure>
          <figure><figcaption class="text-xs text-slate-500 mb-1">Result</figcaption>
            <img src=${`/api/images/${image.id}/result?t=${t}`} class="w-full rounded-lg border border-slate-200 checker"
              onError=${(e) => { e.target.style.display = "none"; }} /></figure>
        </div>

        <div class="px-5">
          <div class=${`flex items-center gap-2 text-sm ${flagged ? "text-red-600" : "text-emerald-600"}`}>
            <span>${flagged ? "⚠ Flagged" : "✓ Looks OK"}</span>
            <span class="text-slate-400">·</span>
            <span class="text-slate-500">Review: ${review}</span>
          </div>
          ${reasons.length > 0 && html`<ul class="mt-1 text-xs text-red-500 list-disc list-inside">${reasons.map((r) => html`<li>${r}</li>`)}</ul>`}
        </div>

        <div class="p-5 flex flex-wrap gap-2 border-t border-slate-100 mt-4">
          <${Btn} kind="success" onClick=${approve} disabled=${!!busy}>Approve<//>
          <${Btn} kind="secondary" onClick=${toggleFlag} disabled=${!!busy}>${flagged ? "Unflag" : "Flag"}<//>
          <${Btn} kind="ghost" onClick=${revert} disabled=${!!busy}>Revert to original<//>
          <div class="flex-1"></div>
          ${busy && html`<span class="text-sm text-slate-400 self-center">${busy}</span>`}
        </div>

        <div class="px-5 pb-5">
          <details class="bg-slate-50 rounded-lg border border-slate-200 p-3">
            <summary class="text-sm font-medium text-slate-700 cursor-pointer">Re-run this image with a different prompt or model</summary>
            <div class="mt-3">
              <${Field} label="Model">
                <select value=${model} onChange=${(e) => setModel(e.target.value)}
                  class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                  ${EDIT_MODELS.map((m) => html`<option value=${m.id}>${m.label}</option>`)}
                </select>
              <//>
              <${Field} label="Editing instruction (prompt)">
                <textarea value=${prompt} onInput=${(e) => setPrompt(e.target.value)} rows="4"
                  class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"></textarea>
              <//>
              <${Btn} onClick=${reprocess} disabled=${!!busy}>Reprocess image<//>
            </div>
          </details>
        </div>
      </div>
    </div>`;
}

// --- Export ------------------------------------------------------------------
function Export({ navigate, batchId }) {
  const [batch, setBatch] = useState(null);
  const [dest, setDest] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => { api(`/api/batches/${batchId}`).then(setBatch); }, [batchId]);

  const run = async () => {
    if (!dest.trim()) { setErr("Enter a destination folder."); return; }
    setBusy(true); setErr(""); setResult(null);
    try { setResult(await jpost(`/api/batches/${batchId}/export`, { dest })); }
    catch (e) { setErr(e.message); }
    setBusy(false);
  };

  const c = batch?.counts || {};
  return html`
    <div class="max-w-3xl mx-auto px-6 py-8 space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-brand">Export — ${batch?.name || ""}</h1>
        <${Btn} kind="secondary" onClick=${() => navigate("review", batchId)}>← Back to review<//>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-5">
        <div class="grid grid-cols-3 gap-3 text-center mb-5">
          <div class="bg-emerald-50 rounded-lg py-3"><div class="text-2xl font-bold text-emerald-600">${c.approved || 0}</div><div class="text-xs text-slate-500">Approved → result</div></div>
          <div class="bg-slate-50 rounded-lg py-3"><div class="text-2xl font-bold text-slate-600">${c.reverted || 0}</div><div class="text-xs text-slate-500">Reverted → original</div></div>
          <div class="bg-amber-50 rounded-lg py-3"><div class="text-2xl font-bold text-amber-600">${(c.total || 0) - (c.approved || 0) - (c.reverted || 0)}</div><div class="text-xs text-slate-500">Skipped</div></div>
        </div>

        <${Field} label="Destination folder" hint=${`Files export as ${batch?.config?.output_format === "original" ? "their original format" : batch?.config?.output_format?.toUpperCase()}. Originals are never modified.`}>
          <input value=${dest} onInput=${(e) => setDest(e.target.value)} placeholder="/Users/you/Desktop/edited-products"
            class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono" />
        <//>

        ${err && html`<div class="text-sm text-red-600 mb-2">${err}</div>`}
        <${Btn} onClick=${run} disabled=${busy}>${busy ? "Exporting…" : "Export approved images"}<//>

        ${result && html`
          <div class="mt-5 p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-sm text-emerald-800">
            <div class="font-medium">Exported ${result.exported} files to:</div>
            <div class="font-mono text-xs mt-1 break-all">${result.dest}</div>
            <div class="mt-2 text-emerald-700">${result.approved} approved · ${result.reverted} reverted · ${result.skipped} skipped</div>
            ${result.errors?.length > 0 && html`<div class="mt-2 text-red-600">${result.errors.length} error(s): ${result.errors.slice(0, 3).join("; ")}</div>`}
          </div>`}
      </div>
    </div>`;
}

// --- Root --------------------------------------------------------------------
function App() {
  const [route, setRoute] = useState({ view: "home", batchId: null });
  const [meta, setMeta] = useState({ fal_key_present: false, default_config: null });
  const navigate = (view, batchId = null) => setRoute({ view, batchId });

  useEffect(() => {
    api("/api/status").then((m) => {
      if (m.edit_models?.length) EDIT_MODELS = m.edit_models;
      setMeta(m);
    }).catch(() => {});
  }, []);
  if (!meta.default_config) return html`<div class="p-8 text-slate-400">Loading…</div>`;

  let page;
  if (route.view === "home") page = html`<${Home} navigate=${navigate} />`;
  else if (route.view === "new") page = html`<${NewBatch} navigate=${navigate} falKeyPresent=${meta.fal_key_present} defaultConfig=${meta.default_config} />`;
  else if (route.view === "processing") page = html`<${Processing} navigate=${navigate} batchId=${route.batchId} />`;
  else if (route.view === "review") page = html`<${Review} navigate=${navigate} batchId=${route.batchId} />`;
  else if (route.view === "export") page = html`<${Export} navigate=${navigate} batchId=${route.batchId} />`;

  return html`<div class="min-h-screen"><${Header} navigate=${navigate} current=${route.view} />${page}</div>`;
}

render(html`<${App} />`, document.getElementById("app"));
