const state = {
  jobId: null,
  pageCount: 0,
  pageIndex: 0,
  strokesByPage: {},
  dirtyPages: new Set(),
};

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const panel = document.getElementById("panel");
const fileName = document.getElementById("file-name");
const pageCountEl = document.getElementById("page-count");
const preview = document.getElementById("preview");
const canvas = document.getElementById("draw-layer");
const stage = document.getElementById("stage");
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
const undoBtn = document.getElementById("undo-stroke");
const clearBtn = document.getElementById("clear-strokes");
const saveInkBtn = document.getElementById("save-ink");
const downloadPdfBtn = document.getElementById("download-pdf");

const pen = window.PdfPen.createPenController({
  canvas,
  getColor: () => penColor.value,
  getWidthPx: () => Number(penWidth.value),
  onChange: (strokes) => {
    state.strokesByPage[state.pageIndex] = strokes;
    if (strokes.length) state.dirtyPages.add(state.pageIndex);
    else state.dirtyPages.delete(state.pageIndex);
  },
});

function setStatus(text) {
  statusEl.textContent = text;
}

function syncFormatFields() {
  const isDocx = formatSelect.value === "docx";
  dpiField.hidden = isDocx;
  qualityField.hidden = isDocx || formatSelect.value === "png";
}

function syncPager() {
  pageCurrent.textContent = String(state.pageIndex + 1);
  pageTotal.textContent = String(state.pageCount);
  prevBtn.disabled = state.pageIndex <= 0;
  nextBtn.disabled = state.pageIndex >= state.pageCount - 1;
}

function fitCanvas() {
  const rect = stage.getBoundingClientRect();
  const width = Math.max(1, Math.floor(rect.width));
  const height = Math.max(1, Math.floor(rect.height));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  const box = window.PdfPen.contentBoxForObjectFitContain(preview, canvas.width, canvas.height);
  pen.setContentBox(box);
  pen.redraw();
}

function persistCurrentPage() {
  state.strokesByPage[state.pageIndex] = pen.getStrokes();
}

function loadPageStrokes() {
  pen.setStrokes(state.strokesByPage[state.pageIndex] || []);
}

async function loadPreview() {
  if (!state.jobId) return;
  await new Promise((resolve, reject) => {
    preview.onload = () => resolve();
    preview.onerror = () => reject(new Error("falha ao carregar preview"));
    preview.src = `/api/preview/${state.jobId}/${state.pageIndex}?dpi=140&t=${Date.now()}`;
  });
  syncPager();
  fitCanvas();
  loadPageStrokes();
}

async function uploadFile(file) {
  if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
    setStatus("Selecione um PDF válido.");
    return;
  }

  setStatus("Enviando…");
  const body = new FormData();
  body.append("file", file);

  const res = await fetch("/api/upload", { method: "POST", body });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    setStatus(err.detail || "Falha no upload.");
    return;
  }

  const data = await res.json();
  state.jobId = data.job_id;
  state.pageCount = data.page_count;
  state.pageIndex = 0;
  state.strokesByPage = {};
  state.dirtyPages = new Set();

  fileName.textContent = data.filename;
  pageCountEl.textContent = String(data.page_count);
  panel.hidden = false;
  setStatus("Use o mouse para riscar. Depois salve o risco no PDF.");
  await loadPreview();
}

async function changePage(nextIndex) {
  persistCurrentPage();
  state.pageIndex = nextIndex;
  await loadPreview();
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

undoBtn.addEventListener("click", () => pen.undo());
clearBtn.addEventListener("click", () => pen.clear());

saveInkBtn.addEventListener("click", async () => {
  if (!state.jobId) return;
  persistCurrentPage();

  const pages = [...state.dirtyPages]
    .map((pageIndex) => ({
      page_index: pageIndex,
      strokes: state.strokesByPage[pageIndex] || [],
    }))
    .filter((page) => page.strokes.length > 0);

  if (!pages.length) {
    setStatus("Nada para salvar nesta sessão.");
    return;
  }

  saveInkBtn.disabled = true;
  setStatus("Gravando risco no PDF…");
  try {
    const res = await fetch(`/api/annotate/${state.jobId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pages }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setStatus(err.detail || "Falha ao salvar risco.");
      return;
    }

    state.strokesByPage = {};
    state.dirtyPages = new Set();
    await loadPreview();
    setStatus("Risco salvo no PDF.");
  } catch {
    setStatus("Erro de rede ao salvar.");
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

formatSelect.addEventListener("change", syncFormatFields);

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.jobId) return;

  convertBtn.disabled = true;
  setStatus("Convertendo…");

  const body = new FormData(form);
  try {
    const res = await fetch(`/api/convert/${state.jobId}`, { method: "POST", body });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setStatus(err.detail || "Falha na conversão.");
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
    setStatus("Download iniciado.");
  } catch {
    setStatus("Erro de rede na conversão.");
  } finally {
    convertBtn.disabled = false;
  }
});

window.addEventListener("resize", fitCanvas);
syncFormatFields();
