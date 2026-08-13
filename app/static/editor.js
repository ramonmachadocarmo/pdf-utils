function createEditorController({ canvas, getTool, getColor, getWidthPx, getStampKind, onChange }) {
  const ctx = canvas.getContext("2d");
  let content = { left: 0, top: 0, width: 0, height: 0 };
  let edits = emptyEdits();
  let draft = null;
  let drawing = false;
  let searchHits = [];

  function emptyEdits() {
    return { strokes: [], texts: [], highlights: [], stamps: [], history: [] };
  }

  function setContentBox(box) {
    content = box;
  }

  function setEdits(next) {
    edits = {
      strokes: structuredClone(next.strokes || []),
      texts: structuredClone(next.texts || []),
      highlights: structuredClone(next.highlights || []),
      stamps: structuredClone(next.stamps || []),
      history: structuredClone(next.history || []),
    };
    redraw();
    onChange?.(edits);
  }

  function getEdits() {
    return edits;
  }

  function setSearchHits(hits) {
    searchHits = hits || [];
    redraw();
  }

  function commit(type, item) {
    edits[type].push(item);
    edits.history.push(type);
    onChange?.(edits);
  }

  function clear() {
    edits = emptyEdits();
    draft = null;
    redraw();
    onChange?.(edits);
  }

  function undo() {
    while (edits.history.length) {
      const type = edits.history[edits.history.length - 1];
      if (type && edits[type]?.length) {
        edits.history.pop();
        edits[type].pop();
        draft = null;
        redraw();
        onChange?.(edits);
        return;
      }
      edits.history.pop();
    }
    if (edits.stamps.length) edits.stamps.pop();
    else if (edits.texts.length) edits.texts.pop();
    else if (edits.highlights.length) edits.highlights.pop();
    else if (edits.strokes.length) edits.strokes.pop();
    draft = null;
    redraw();
    onChange?.(edits);
  }

  function hasEdits(value = edits) {
    return Boolean(
      value.strokes.length ||
        value.texts.length ||
        value.highlights.length ||
        value.stamps.length
    );
  }

  function toNorm(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (clientX - rect.left) * scaleX - content.left;
    const y = (clientY - rect.top) * scaleY - content.top;
    if (content.width <= 0 || content.height <= 0) return null;
    const nx = x / content.width;
    const ny = y / content.height;
    if (nx < 0 || ny < 0 || nx > 1 || ny > 1) return null;
    return { x: nx, y: ny };
  }

  function strokeWidthNorm() {
    const tool = getTool();
    const px = tool === "signature" ? Math.max(getWidthPx(), 8) : getWidthPx();
    if (content.width <= 0) return 0.004;
    return Math.max(0.001, px / content.width);
  }

  function drawStroke(stroke) {
    if (stroke.points.length < 2) return;
    ctx.save();
    ctx.strokeStyle = stroke.color;
    ctx.lineWidth = stroke.width * content.width;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    const first = stroke.points[0];
    ctx.moveTo(content.left + first.x * content.width, content.top + first.y * content.height);
    for (let i = 1; i < stroke.points.length; i += 1) {
      const p = stroke.points[i];
      ctx.lineTo(content.left + p.x * content.width, content.top + p.y * content.height);
    }
    ctx.stroke();
    ctx.restore();
  }

  function drawHighlight(box, alpha = 0.35) {
    const x = content.left + Math.min(box.x0, box.x1) * content.width;
    const y = content.top + Math.min(box.y0, box.y1) * content.height;
    const w = Math.abs(box.x1 - box.x0) * content.width;
    const h = Math.abs(box.y1 - box.y0) * content.height;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = box.color;
    ctx.fillRect(x, y, w, h);
    ctx.restore();
  }

  function drawText(box) {
    ctx.save();
    ctx.fillStyle = box.color;
    ctx.font = `${Math.max(10, box.size * content.height)}px Manrope, sans-serif`;
    ctx.fillText(
      box.text,
      content.left + box.x * content.width,
      content.top + box.y * content.height
    );
    ctx.restore();
  }

  function drawStamp(stamp) {
    const label =
      stamp.kind === "date"
        ? new Date().toISOString().slice(0, 10)
        : stamp.kind === "paid"
          ? "PAGO"
          : "APROVADO";
    const cx = content.left + stamp.x * content.width;
    const cy = content.top + stamp.y * content.height;
    ctx.save();
    ctx.font = `700 ${Math.max(12, 0.035 * content.height)}px Manrope, sans-serif`;
    ctx.strokeStyle = "#bf1f1f";
    ctx.fillStyle = "#bf1f1f";
    const metrics = ctx.measureText(label);
    const padX = 10;
    const padY = 8;
    const w = metrics.width + padX * 2;
    const h = Math.max(12, 0.035 * content.height) + padY * 2;
    ctx.lineWidth = 2;
    ctx.strokeRect(cx - w / 2, cy - h / 2, w, h);
    ctx.fillText(label, cx - metrics.width / 2, cy + h * 0.18);
    ctx.restore();
  }

  function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const hit of searchHits) drawHighlight({ ...hit, color: "#3d8bfd" }, 0.25);
    for (const box of edits.highlights) drawHighlight(box);
    for (const stroke of edits.strokes) drawStroke(stroke);
    for (const box of edits.texts) drawText(box);
    for (const stamp of edits.stamps) drawStamp(stamp);
    if (draft?.type === "stroke") drawStroke(draft);
    if (draft?.type === "highlight") drawHighlight(draft, 0.25);
  }

  function pointerDown(e) {
    const tool = getTool();
    if (tool === "pan") return;
    const point = toNorm(e.clientX, e.clientY);
    if (!point) return;

    if (tool === "text") {
      const text = window.prompt("Texto:");
      if (!text || !text.trim()) return;
      commit("texts", {
        x: point.x,
        y: point.y,
        text: text.trim(),
        color: getColor(),
        size: 0.03,
      });
      redraw();
      return;
    }

    if (tool === "stamp") {
      commit("stamps", { kind: getStampKind(), x: point.x, y: point.y });
      redraw();
      return;
    }

    canvas.setPointerCapture(e.pointerId);
    drawing = true;

    if (tool === "highlight") {
      draft = { type: "highlight", x0: point.x, y0: point.y, x1: point.x, y1: point.y, color: getColor() };
      redraw();
      return;
    }

    draft = {
      type: "stroke",
      color: tool === "signature" ? "#1a3c6e" : getColor(),
      width: strokeWidthNorm(),
      points: [point],
    };
    redraw();
  }

  function pointerMove(e) {
    if (!drawing || !draft) return;
    const point = toNorm(e.clientX, e.clientY);
    if (!point) return;

    if (draft.type === "highlight") {
      draft.x1 = point.x;
      draft.y1 = point.y;
      redraw();
      return;
    }

    const last = draft.points[draft.points.length - 1];
    const dx = point.x - last.x;
    const dy = point.y - last.y;
    if (dx * dx + dy * dy < 0.0000004) return;
    draft.points.push(point);
    redraw();
  }

  function pointerUp() {
    if (!drawing) return;
    drawing = false;

    if (draft?.type === "highlight") {
      if (Math.abs(draft.x1 - draft.x0) > 0.005 && Math.abs(draft.y1 - draft.y0) > 0.005) {
        commit("highlights", {
          x0: draft.x0,
          y0: draft.y0,
          x1: draft.x1,
          y1: draft.y1,
          color: draft.color,
        });
      }
    } else if (draft?.type === "stroke" && draft.points.length >= 2) {
      commit("strokes", {
        color: draft.color,
        width: draft.width,
        points: draft.points,
      });
    }

    draft = null;
    redraw();
  }

  canvas.addEventListener("pointerdown", pointerDown);
  canvas.addEventListener("pointermove", pointerMove);
  canvas.addEventListener("pointerup", pointerUp);
  canvas.addEventListener("pointercancel", pointerUp);

  return {
    setContentBox,
    setEdits,
    getEdits,
    clear,
    undo,
    redraw,
    hasEdits,
    setSearchHits,
  };
}

function contentBoxForObjectFitContain(img, canvasWidth, canvasHeight) {
  const naturalW = img.naturalWidth || 1;
  const naturalH = img.naturalHeight || 1;
  const scale = Math.min(canvasWidth / naturalW, canvasHeight / naturalH);
  const width = naturalW * scale;
  const height = naturalH * scale;
  const left = (canvasWidth - width) / 2;
  const top = (canvasHeight - height) / 2;
  return { left, top, width, height };
}

window.PdfEditorUI = { createEditorController, contentBoxForObjectFitContain };
