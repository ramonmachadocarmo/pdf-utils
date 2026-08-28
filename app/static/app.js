const state = {
  jobId: null,
  pageCount: 0,
  pageIndex: 0,
  editsByPage: {},
  dirtyPages: new Set(),
  tool: "pen",
  zoom: 1,
  searchHits: [],
  searchCursor: -1,
};

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const panel = document.getElementById("panel");
const fileName = document.getElementById("file-name");
const pageCountEl = document.getElementById("page-count");
const preview = document.getElementById("preview");
const canvas = document.getElementById("draw-layer");
const stage = document.getElementById("stage");
const viewport = document.getElementById("viewport");
const thumbs = document.getElementById("thumbs");
const pageCurrent = document.getElementById("page-current");
const pageTotal = document.getElementById("page-total");
const prevBtn = document.getElementById("prev-page");
const nextBtn = document.getElementById("next-page");
const form = document.getElementById("convert-form");
const formatSelect = document.getElementById("format");
const dpiField = document.getElementById("dpi-field");
const qualityField = document.getElementById("quality-field");
const convertBtn = document.getElementById("convert-btn");
const statusEl = document.getElementById("status");
const penColor = document.getElementById("pen-color");
const penWidth = document.getElementById("pen-width");
const stampCluster = document.getElementById("stamp-cluster");
const stampKind = document.getElementById("stamp-kind");
const focusBtn = document.getElementById("focus-btn");
const focusBar = document.getElementById("focus-bar");
const focusExit = document.getElementById("focus-exit");
const focusPrev = document.getElementById("focus-prev");
const focusNext = document.getElementById("focus-next");
const focusZoomIn = document.getElementById("focus-zoom-in");
const focusZoomOut = document.getElementById("focus-zoom-out");
const focusZoomLabel = document.getElementById("focus-zoom-label");
const pageCurrentFocus = document.getElementById("page-current-focus");
const pageTotalFocus = document.getElementById("page-total-focus");
const undoBtn = document.getElementById("undo-stroke");
const clearBtn = document.getElementById("clear-strokes");
const saveInkBtn = document.getElementById("save-ink");
const downloadPdfBtn = document.getElementById("download-pdf");
const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const searchPrev = document.getElementById("search-prev");
const searchNext = document.getElementById("search-next");
const searchCount = document.getElementById("search-count");
const zoomInBtn = document.getElementById("zoom-in");
const zoomOutBtn = document.getElementById("zoom-out");
const zoomLabel = document.getElementById("zoom-label");
const rotateBtn = document.getElementById("rotate-btn");
const nightBtn = document.getElementById("night-btn");

const editor = window.PdfEditorUI.createEditorController({
  canvas,
  getTool: () => state.tool,
  getColor: () => penColor.value,
  getWidthPx: () => Number(penWidth.value),
  getStampKind: () => stampKind.value,
  onChange: (edits) => {
    state.editsByPage[state.pageIndex] = edits;
    if (editor.hasEdits(edits)) state.dirtyPages.add(state.pageIndex);
    else state.dirtyPages.delete(state.pageIndex);
  },
});

function setStatus(text) {
  statusEl.textContent = text;
}

function emptyEdits() {
  return { strokes: [], texts: [], highlights: [], stamps: [], history: [] };
}

function syncFormatFields() {
  const isDocx = formatSelect.value === "docx";
  dpiField.hidden = isDocx;
  qualityField.hidden = isDocx || formatSelect.value === "png";
}

function syncPager() {
  const current = String(state.pageIndex + 1);
  const total = String(state.pageCount);
  pageCurrent.textContent = current;
  pageTotal.textContent = total;
  pageCurrentFocus.textContent = current;
  pageTotalFocus.textContent = total;
  prevBtn.disabled = state.pageIndex <= 0;
  nextBtn.disabled = state.pageIndex >= state.pageCount - 1;
  focusPrev.disabled = state.pageIndex <= 0;
  focusNext.disabled = state.pageIndex >= state.pageCount - 1;
  thumbs.querySelectorAll("button").forEach((btn) => {
    btn.classList.toggle("active", Number(btn.dataset.page) === state.pageIndex);
  });
}

function syncToolUi() {
  document.querySelectorAll(".tool").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tool === state.tool);
  });
  stampCluster.classList.toggle("is-active", state.tool === "stamp");
  canvas.style.cursor = state.tool === "pan" ? "grab" : state.tool === "text" ? "text" : "crosshair";
}

function applyZoom() {
  stage.style.transform = `scale(${state.zoom})`;
  stage.style.transformOrigin = "top left";
  const baseH = preview.offsetHeight || 0;
  stage.style.height = `${Math.max(baseH * state.zoom, baseH)}px`;
  const label = `${Math.round(state.zoom * 100)}%`;
  zoomLabel.textContent = label;
  focusZoomLabel.textContent = label;
}

function setFocusMode(on) {
  document.body.classList.toggle("focus-mode", on);
  focusBar.hidden = !on;
  focusBtn.textContent = on ? t("focus.toggle.off") : t("focus.toggle.on");
  requestAnimationFrame(() => {
    fitCanvas();
  });
}

function fitCanvas() {
  const rect = stage.getBoundingClientRect();
  const width = Math.max(1, Math.floor(rect.width / state.zoom));
  const height = Math.max(1, Math.floor(rect.height / state.zoom));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  const box = window.PdfEditorUI.contentBoxForObjectFitContain(preview, canvas.width, canvas.height);
  editor.setContentBox(box);
  editor.redraw();
}

function persistCurrentPage() {
  state.editsByPage[state.pageIndex] = editor.getEdits();
}

function loadPageEdits() {
  editor.setEdits(state.editsByPage[state.pageIndex] || emptyEdits());
  const pageHits = state.searchHits.filter((h) => h.page_index === state.pageIndex);
  editor.setSearchHits(pageHits);
}

function renderThumbs() {
  thumbs.innerHTML = "";
  for (let i = 0; i < state.pageCount; i += 1) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "thumb";
    btn.dataset.page = String(i);
    btn.innerHTML = `<img alt="${t("thumb.alt", { n: i + 1 })}" src="/api/preview/${state.jobId}/${i}?dpi=48&t=${Date.now()}" /><span>${i + 1}</span>`;
    btn.addEventListener("click", async () => {
      if (i === state.pageIndex) return;
      await changePage(i);
    });
    thumbs.appendChild(btn);
  }
}

async function loadPreview() {
  if (!state.jobId) return;
  await new Promise((resolve, reject) => {
    preview.onload = () => {
      preview.classList.add("is-ready");
      resolve();
    };
    preview.onerror = () => {
      preview.classList.remove("is-ready");
      preview.removeAttribute("src");
      reject(new Error(t("status.preview_failed")));
    };
    preview.src = `/api/preview/${state.jobId}/${state.pageIndex}?dpi=160&t=${Date.now()}`;
  });
  syncPager();
  applyZoom();
  fitCanvas();
  loadPageEdits();
}

async function applyLoadedJob(data) {
  state.jobId = data.job_id;
  state.pageCount = data.page_count;
  state.pageIndex = 0;
  state.editsByPage = {};
  state.dirtyPages = new Set();
  state.searchHits = [];
  state.searchCursor = -1;
  searchCount.textContent = "0";

  fileName.textContent = data.filename;
  pageCountEl.textContent = String(data.page_count);
  panel.hidden = false;
  document.body.classList.add("editing");
  renderThumbs();
  setStatus(t("status.tools_ready"));
  await loadPreview();
}

async function uploadFile(file) {
  if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
    setStatus(t("status.select_pdf"));
    return;
  }

  setStatus(t("status.uploading"));
  const body = new FormData();
  body.append("file", file);

  const res = await fetch("/api/upload", { method: "POST", body });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    setStatus(err.detail || t("status.upload_failed"));
    return;
  }

  await applyLoadedJob(await res.json());
}

async function openLocalFile(path) {
  setStatus(t("status.uploading"));
  const res = await fetch(`/api/open-local?path=${encodeURIComponent(path)}`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    setStatus(err.detail || t("status.upload_failed"));
    return;
  }

  await applyLoadedJob(await res.json());
}

const mergeBtn = document.getElementById("merge-btn");
const mergeInput = document.getElementById("merge-input");
const mergeModal = document.getElementById("merge-modal");
const mergeSizeList = document.getElementById("merge-size-list");
const mergeCancelBtn = document.getElementById("merge-cancel");
const mergeConfirmBtn = document.getElementById("merge-confirm");

let pendingMergeId = null;

mergeBtn.addEventListener("click", () => mergeInput.click());

mergeInput.addEventListener("change", async () => {
  const files = Array.from(mergeInput.files || []);
  mergeInput.value = "";
  const minRequired = state.jobId ? 1 : 2;
  if (files.length < minRequired) {
    setStatus(t(state.jobId ? "status.merge_select_one" : "status.merge_select_two"));
    return;
  }
  await inspectMerge(files);
});

async function inspectMerge(files) {
  setStatus(t("status.merge_uploading"));
  const body = new FormData();
  for (const file of files) body.append("files", file);
  if (state.jobId) body.append("current_job_id", state.jobId);

  const res = await fetch("/api/merge/inspect", { method: "POST", body });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    setStatus(err.detail || t("status.merge_failed"));
    return;
  }

  const data = await res.json();
  pendingMergeId = data.merge_id;

  if (data.uniform) {
    const [size] = data.sizes;
    await executeMerge(size.width, size.height);
    return;
  }

  showMergeSizePicker(data.sizes);
}

function showMergeSizePicker(sizes) {
  mergeSizeList.innerHTML = "";
  sizes.forEach((size, i) => {
    const label = document.createElement("label");
    label.className = "merge-size-option";
    label.dataset.width = String(size.width);
    label.dataset.height = String(size.height);
    label.innerHTML = `
      <input type="radio" name="merge-size" value="${i}" ${i === 0 ? "checked" : ""} />
      <span>${Math.round(size.width)} × ${Math.round(size.height)} pt · ${size.page_count} ${t("merge.pages")}</span>
    `;
    mergeSizeList.appendChild(label);
  });
  mergeModal.hidden = false;
}

mergeCancelBtn.addEventListener("click", () => {
  mergeModal.hidden = true;
  pendingMergeId = null;
});

mergeConfirmBtn.addEventListener("click", async () => {
  const selected = mergeSizeList.querySelector("input[name='merge-size']:checked");
  if (!selected || !pendingMergeId) return;
  const option = selected.closest(".merge-size-option");
  mergeModal.hidden = true;
  await executeMerge(Number(option.dataset.width), Number(option.dataset.height));
});

async function executeMerge(width, height) {
  if (!pendingMergeId) return;
  const mergeId = pendingMergeId;
  pendingMergeId = null;

  setStatus(t("status.merge_uploading"));
  const res = await fetch("/api/merge/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ merge_id: mergeId, width, height }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    setStatus(err.detail || t("status.merge_failed"));
    return;
  }

  await applyLoadedJob(await res.json());
}

async function changePage(nextIndex) {
  persistCurrentPage();
  state.pageIndex = nextIndex;
  await loadPreview();
}

async function runSearch() {
  if (!state.jobId) return;
  const q = searchInput.value.trim();
  if (!q) {
    state.searchHits = [];
    state.searchCursor = -1;
    searchCount.textContent = "0";
    editor.setSearchHits([]);
    return;
  }
  const res = await fetch(`/api/search/${state.jobId}?q=${encodeURIComponent(q)}`);
  if (!res.ok) {
    setStatus(t("status.search_failed"));
    return;
  }
  const data = await res.json();
  state.searchHits = data.hits;
  state.searchCursor = data.hits.length ? 0 : -1;
  searchCount.textContent = String(data.count);
  if (state.searchCursor >= 0) await jumpToSearchHit(state.searchCursor);
  else {
    editor.setSearchHits([]);
    setStatus(t("status.search_empty"));
  }
}

async function jumpToSearchHit(index) {
  const hit = state.searchHits[index];
  if (!hit) return;
  state.searchCursor = index;
  searchCount.textContent = `${index + 1}/${state.searchHits.length}`;
  if (hit.page_index !== state.pageIndex) await changePage(hit.page_index);
  else {
    editor.setSearchHits(state.searchHits.filter((h) => h.page_index === state.pageIndex));
  }
}

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  uploadFile(e.dataTransfer?.files?.[0]);
});
fileInput.addEventListener("change", () => uploadFile(fileInput.files?.[0]));

prevBtn.addEventListener("click", async () => {
  if (state.pageIndex <= 0) return;
  await changePage(state.pageIndex - 1);
});
nextBtn.addEventListener("click", async () => {
  if (state.pageIndex >= state.pageCount - 1) return;
  await changePage(state.pageIndex + 1);
});

document.querySelectorAll(".tool").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.tool = btn.dataset.tool;
    syncToolUi();
  });
});

stampKind.addEventListener("change", () => {
  state.tool = "stamp";
  syncToolUi();
});
stampKind.addEventListener("focus", () => {
  state.tool = "stamp";
  syncToolUi();
});

undoBtn.addEventListener("click", () => editor.undo());
clearBtn.addEventListener("click", () => editor.clear());

saveInkBtn.addEventListener("click", async () => {
  if (!state.jobId) return;
  persistCurrentPage();

  const pages = [...state.dirtyPages]
    .map((pageIndex) => ({
      page_index: pageIndex,
      ...(state.editsByPage[pageIndex] || emptyEdits()),
    }))
    .filter((page) => editor.hasEdits(page));

  if (!pages.length) {
    setStatus(t("status.nothing_to_save"));
    return;
  }

  saveInkBtn.disabled = true;
  setStatus(t("status.saving"));
  try {
    const res = await fetch(`/api/annotate/${state.jobId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pages }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setStatus(err.detail || t("status.save_failed"));
      return;
    }
    state.editsByPage = {};
    state.dirtyPages = new Set();
    renderThumbs();
    await loadPreview();
    setStatus(t("status.saved"));
  } catch {
    setStatus(t("status.save_network"));
  } finally {
    saveInkBtn.disabled = false;
  }
});

downloadPdfBtn.addEventListener("click", () => {
  if (!state.jobId) return;
  const a = document.createElement("a");
  a.href = `/api/download/${state.jobId}?t=${Date.now()}`;
  a.download = "edited.pdf";
  a.click();
});

searchBtn.addEventListener("click", runSearch);
searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    runSearch();
  }
});
searchPrev.addEventListener("click", async () => {
  if (!state.searchHits.length) return;
  const next = (state.searchCursor - 1 + state.searchHits.length) % state.searchHits.length;
  await jumpToSearchHit(next);
});
searchNext.addEventListener("click", async () => {
  if (!state.searchHits.length) return;
  const next = (state.searchCursor + 1) % state.searchHits.length;
  await jumpToSearchHit(next);
});

function bumpZoom(delta) {
  state.zoom = Math.min(3, Math.max(0.5, state.zoom + delta));
  applyZoom();
  fitCanvas();
}

zoomInBtn.addEventListener("click", () => bumpZoom(0.25));
zoomOutBtn.addEventListener("click", () => bumpZoom(-0.25));
focusZoomIn.addEventListener("click", () => bumpZoom(0.25));
focusZoomOut.addEventListener("click", () => bumpZoom(-0.25));
focusPrev.addEventListener("click", () => prevBtn.click());
focusNext.addEventListener("click", () => nextBtn.click());
focusBtn.addEventListener("click", () => setFocusMode(true));
focusExit.addEventListener("click", () => setFocusMode(false));
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && document.body.classList.contains("focus-mode")) {
    setFocusMode(false);
  }
});

rotateBtn.addEventListener("click", async () => {
  if (!state.jobId) return;
  persistCurrentPage();
  const res = await fetch(`/api/rotate/${state.jobId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page_index: state.pageIndex, degrees: 90 }),
  });
  if (!res.ok) {
    setStatus(t("status.rotate_failed"));
    return;
  }
  state.editsByPage[state.pageIndex] = emptyEdits();
  state.dirtyPages.delete(state.pageIndex);
  renderThumbs();
  await loadPreview();
  setStatus(t("status.rotated"));
});

nightBtn.addEventListener("click", () => {
  document.body.classList.toggle("night");
});

let panning = false;
let panX = 0;
let panY = 0;
viewport.addEventListener("pointerdown", (e) => {
  if (state.tool !== "pan") return;
  panning = true;
  panX = e.clientX;
  panY = e.clientY;
  viewport.setPointerCapture(e.pointerId);
  viewport.style.cursor = "grabbing";
});
viewport.addEventListener("pointermove", (e) => {
  if (!panning) return;
  window.scrollBy(panX - e.clientX, panY - e.clientY);
  panX = e.clientX;
  panY = e.clientY;
});
viewport.addEventListener("pointerup", () => {
  panning = false;
  viewport.style.cursor = "";
});

formatSelect.addEventListener("change", syncFormatFields);
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.jobId) return;
  convertBtn.disabled = true;
  setStatus(t("status.converting"));
  const body = new FormData(form);
  try {
    const res = await fetch(`/api/convert/${state.jobId}`, { method: "POST", body });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setStatus(err.detail || t("status.convert_failed"));
      return;
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = /filename="?([^";]+)"?/i.exec(disposition);
    const name = match?.[1] || "converted.bin";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
    setStatus(t("status.download_started"));
  } catch {
    setStatus(t("status.convert_network"));
  } finally {
    convertBtn.disabled = false;
  }
});

window.addEventListener("resize", fitCanvas);

document.getElementById("lang-select")?.addEventListener("change", async (e) => {
  await window.I18n.load(e.target.value);
  if (document.body.classList.contains("focus-mode")) {
    focusBtn.textContent = t("focus.toggle.off");
  }
  if (state.jobId) renderThumbs();
  editor.redraw();
});

document.addEventListener("i18n:changed", () => {
  if (document.body.classList.contains("focus-mode")) {
    focusBtn.textContent = t("focus.toggle.off");
  }
});

async function checkForUpdate() {
  const banner = document.getElementById("update-banner");
  const versionEl = document.getElementById("update-version");
  if (!banner || !versionEl) return;

  try {
    const res = await fetch("/api/update-check");
    if (!res.ok) return;
    const data = await res.json();
    if (!data.update_available) return;

    versionEl.textContent = `v${data.latest_version}`;
    banner.href = data.download_url || data.release_url || "#";
    banner.hidden = false;
  } catch {
    // offline, blocked, or rate-limited — skip silently
  }
}

(async () => {
  await window.I18n.load(window.I18n.detect());
  syncFormatFields();
  syncToolUi();
  applyZoom();
  checkForUpdate();

  const openPath = new URLSearchParams(window.location.search).get("open");
  if (openPath) await openLocalFile(openPath);
})();
