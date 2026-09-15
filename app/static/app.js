const state = {
  jobId: null,
  pageCount: 0,
  pageIndex: 0,
  dirtyPages: new Set(),
  tool: "pen",
  zoom: 1,
  searchHits: [],
  searchCursor: -1,
};

let pageEls = [];
let pageControllers = [];
let loadObserver = null;
let currentObserver = null;

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const panel = document.getElementById("panel");
const fileName = document.getElementById("file-name");
const pageCountEl = document.getElementById("page-count");
const pagesEl = document.getElementById("pages");
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
const copyTextBtn = document.getElementById("copy-text-btn");
const printFrom = document.getElementById("print-from");
const printTo = document.getElementById("print-to");
const printBtn = document.getElementById("print-btn");

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
  const cursor = state.tool === "pan" ? "grab" : state.tool === "text" ? "text" : "crosshair";
  pageEls.forEach((p) => {
    p.canvas.style.cursor = cursor;
  });
}

function applyZoom() {
  pagesEl.style.setProperty("--zoom", String(state.zoom));
  const label = `${Math.round(state.zoom * 100)}%`;
  zoomLabel.textContent = label;
  focusZoomLabel.textContent = label;
  requestAnimationFrame(fitAllCanvases);
}

function setFocusMode(on) {
  document.body.classList.toggle("focus-mode", on);
  focusBar.hidden = !on;
  focusBtn.textContent = on ? t("focus.toggle.off") : t("focus.toggle.on");
  requestAnimationFrame(fitAllCanvases);
}

function fitCanvasForPage(index) {
  const entry = pageEls[index];
  if (!entry) return;
  const rect = entry.stage.getBoundingClientRect();
  const width = Math.max(1, Math.floor(rect.width));
  const height = Math.max(1, Math.floor(rect.height));
  if (entry.canvas.width !== width || entry.canvas.height !== height) {
    entry.canvas.width = width;
    entry.canvas.height = height;
  }
  const box = window.PdfEditorUI.contentBoxForObjectFitContain(entry.img, entry.canvas.width, entry.canvas.height);
  pageControllers[index].setContentBox(box);
  pageControllers[index].redraw();
}

function fitAllCanvases() {
  pageEls.forEach((p, i) => {
    if (p.loaded) fitCanvasForPage(i);
  });
}

async function loadPageImage(index) {
  const entry = pageEls[index];
  if (!entry || entry.loaded) return;
  entry.loaded = true;
  await new Promise((resolve) => {
    entry.img.onload = () => {
      entry.img.classList.add("is-ready");
      if (entry.img.naturalWidth && entry.img.naturalHeight) {
        entry.stage.style.aspectRatio = `${entry.img.naturalWidth} / ${entry.img.naturalHeight}`;
      }
      fitCanvasForPage(index);
      resolve();
    };
    entry.img.onerror = () => {
      entry.loaded = false;
      resolve();
    };
    entry.img.src = `/api/preview/${state.jobId}/${index}?dpi=160&t=${Date.now()}`;
  });
}

function reloadPageImage(index) {
  const entry = pageEls[index];
  if (!entry) return Promise.resolve();
  entry.loaded = false;
  entry.img.classList.remove("is-ready");
  return loadPageImage(index);
}

function setupLazyLoad() {
  loadObserver?.disconnect();
  loadObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        loadPageImage(Number(entry.target.dataset.page));
      }
    },
    { root: viewport, rootMargin: "600px 0px", threshold: 0.01 }
  );
  pageEls.forEach((p) => loadObserver.observe(p.block));
}

function setupCurrentTracking() {
  currentObserver?.disconnect();
  const ratios = new Map();
  currentObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) ratios.set(Number(entry.target.dataset.page), entry.intersectionRatio);
      let best = state.pageIndex;
      let bestRatio = -1;
      for (const [idx, ratio] of ratios) {
        if (ratio > bestRatio) {
          bestRatio = ratio;
          best = idx;
        }
      }
      if (best !== state.pageIndex) {
        state.pageIndex = best;
        syncPager();
      }
    },
    { root: viewport, threshold: [0, 0.25, 0.5, 0.75, 1] }
  );
  pageEls.forEach((p) => currentObserver.observe(p.block));
}

async function scrollToPage(index) {
  const entry = pageEls[index];
  if (!entry) return;
  entry.block.scrollIntoView({ behavior: "smooth", block: "start" });
  state.pageIndex = index;
  syncPager();
  await loadPageImage(index);
}

function buildPages(data) {
  pagesEl.innerHTML = "";
  pageEls = [];
  pageControllers = [];

  data.pages.forEach((info, i) => {
    const block = document.createElement("div");
    block.className = "page-block";
    block.dataset.page = String(i);

    const stageDiv = document.createElement("div");
    stageDiv.className = "stage";
    if (info.width && info.height) {
      stageDiv.style.aspectRatio = `${info.width} / ${info.height}`;
    }

    const img = document.createElement("img");
    img.className = "page-preview";
    img.alt = "";
    img.draggable = false;

    const canvasEl = document.createElement("canvas");
    canvasEl.className = "page-canvas";
    canvasEl.setAttribute("aria-label", t("a11y.draw_layer"));

    stageDiv.append(img, canvasEl);
    block.appendChild(stageDiv);
    pagesEl.appendChild(block);

    const controller = window.PdfEditorUI.createEditorController({
      canvas: canvasEl,
      getTool: () => state.tool,
      getColor: () => penColor.value,
      getWidthPx: () => Number(penWidth.value),
      getStampKind: () => stampKind.value,
      onChange: (edits) => {
        if (controller.hasEdits(edits)) state.dirtyPages.add(i);
        else state.dirtyPages.delete(i);
      },
    });

    pageControllers.push(controller);
    pageEls.push({ block, stage: stageDiv, img, canvas: canvasEl, loaded: false });
  });
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
      await scrollToPage(i);
    });
    thumbs.appendChild(btn);
  }
}

function applySearchHitsToPages(hits) {
  const byPage = new Map();
  for (const hit of hits) {
    if (!byPage.has(hit.page_index)) byPage.set(hit.page_index, []);
    byPage.get(hit.page_index).push(hit);
  }
  pageControllers.forEach((controller, idx) => controller.setSearchHits(byPage.get(idx) || []));
}

async function applyLoadedJob(data) {
  state.jobId = data.job_id;
  state.pageCount = data.page_count;
  state.pageIndex = 0;
  state.dirtyPages = new Set();
  state.searchHits = [];
  state.searchCursor = -1;
  searchCount.textContent = "0";

  fileName.textContent = data.filename;
  pageCountEl.textContent = String(data.page_count);
  printFrom.max = String(data.page_count);
  printTo.max = String(data.page_count);
  printFrom.value = "1";
  printTo.value = String(data.page_count);
  panel.hidden = false;
  document.body.classList.add("editing");

  buildPages(data);
  renderThumbs();
  setupLazyLoad();
  setupCurrentTracking();
  applyZoom();
  syncPager();
  setStatus(t("status.tools_ready"));

  viewport.scrollTop = 0;
  await loadPageImage(0);
}

async function uploadFile(file) {
  const name = file ? file.name.toLowerCase() : "";
  if (!file || !(name.endsWith(".pdf") || name.endsWith(".xml"))) {
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

async function runSearch() {
  if (!state.jobId) return;
  const q = searchInput.value.trim();
  if (!q) {
    state.searchHits = [];
    state.searchCursor = -1;
    searchCount.textContent = "0";
    applySearchHitsToPages([]);
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
  applySearchHitsToPages(data.hits);
  if (state.searchCursor >= 0) await jumpToSearchHit(state.searchCursor);
  else setStatus(t("status.search_empty"));
}

async function jumpToSearchHit(index) {
  const hit = state.searchHits[index];
  if (!hit) return;
  state.searchCursor = index;
  searchCount.textContent = `${index + 1}/${state.searchHits.length}`;
  await scrollToPage(hit.page_index);
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
  await scrollToPage(state.pageIndex - 1);
});
nextBtn.addEventListener("click", async () => {
  if (state.pageIndex >= state.pageCount - 1) return;
  await scrollToPage(state.pageIndex + 1);
});

document.querySelectorAll(".tool").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tool = btn.dataset.tool;
    state.tool = state.tool === tool && tool !== "pan" ? "pan" : tool;
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

undoBtn.addEventListener("click", () => pageControllers[state.pageIndex]?.undo());
clearBtn.addEventListener("click", () => pageControllers[state.pageIndex]?.clear());

saveInkBtn.addEventListener("click", async () => {
  if (!state.jobId) return;
  const dirtyIndices = [...state.dirtyPages];

  const pages = dirtyIndices
    .map((pageIndex) => ({
      page_index: pageIndex,
      ...(pageControllers[pageIndex]?.getEdits() || emptyEdits()),
    }))
    .filter((page) => pageControllers[page.page_index]?.hasEdits(page));

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
    state.dirtyPages = new Set();
    for (const idx of dirtyIndices) pageControllers[idx]?.clear();
    renderThumbs();
    for (const idx of dirtyIndices) await reloadPageImage(idx);
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
  const idx = state.pageIndex;
  const res = await fetch(`/api/rotate/${state.jobId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page_index: idx, degrees: 90 }),
  });
  if (!res.ok) {
    setStatus(t("status.rotate_failed"));
    return;
  }
  pageControllers[idx]?.clear();
  state.dirtyPages.delete(idx);
  renderThumbs();
  await reloadPageImage(idx);
  setStatus(t("status.rotated"));
});

nightBtn.addEventListener("click", () => {
  document.body.classList.toggle("night");
});

copyTextBtn.addEventListener("click", async () => {
  if (!state.jobId) return;
  try {
    const res = await fetch(`/api/text/${state.jobId}?page_index=${state.pageIndex}`);
    if (!res.ok) {
      setStatus(t("status.copy_failed"));
      return;
    }
    const data = await res.json();
    await navigator.clipboard.writeText(data.text);
    setStatus(t("status.copied"));
  } catch {
    setStatus(t("status.copy_failed"));
  }
});

printBtn.addEventListener("click", async () => {
  if (!state.jobId) return;
  const from = Math.max(1, Math.min(state.pageCount, Number(printFrom.value) || 1));
  const to = Math.max(from, Math.min(state.pageCount, Number(printTo.value) || from));

  setStatus(t("status.printing"));
  try {
    const res = await fetch(`/api/print/${state.jobId}?start=${from - 1}&end=${to - 1}`);
    if (!res.ok) {
      setStatus(t("status.print_failed"));
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const iframe = document.createElement("iframe");
    iframe.style.display = "none";
    document.body.appendChild(iframe);
    const cleanup = () => {
      URL.revokeObjectURL(url);
      iframe.remove();
    };
    iframe.onload = () => {
      const win = iframe.contentWindow;
      win.onafterprint = cleanup;
      win.focus();
      win.print();
      setTimeout(cleanup, 60000);
    };
    iframe.src = url;
  } catch {
    setStatus(t("status.print_network"));
  }
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
  viewport.scrollBy(panX - e.clientX, panY - e.clientY);
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

window.addEventListener("resize", fitAllCanvases);

document.getElementById("lang-select")?.addEventListener("change", async (e) => {
  await window.I18n.load(e.target.value);
  if (document.body.classList.contains("focus-mode")) {
    focusBtn.textContent = t("focus.toggle.off");
  }
  if (state.jobId) renderThumbs();
  pageControllers.forEach((c) => c.redraw());
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
