function createPenController({ canvas, getColor, getWidthPx, onChange }) {
  const ctx = canvas.getContext("2d");
  let strokes = [];
  let draft = null;
  let drawing = false;
  let content = { left: 0, top: 0, width: 0, height: 0 };

  function setContentBox(box) {
    content = box;
  }

  function setStrokes(next) {
    strokes = next.map((stroke) => ({
      color: stroke.color,
      width: stroke.width,
      points: stroke.points.map((p) => ({ x: p.x, y: p.y })),
    }));
    redraw();
    onChange?.(strokes);
  }

  function getStrokes() {
    return strokes;
  }

  function clear() {
    strokes = [];
    draft = null;
    redraw();
    onChange?.(strokes);
  }

  function undo() {
    strokes.pop();
    draft = null;
    redraw();
    onChange?.(strokes);
  }

  function toNorm(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left - content.left;
    const y = clientY - rect.top - content.top;
    if (content.width <= 0 || content.height <= 0) return null;
    const nx = x / content.width;
    const ny = y / content.height;
    if (nx < 0 || ny < 0 || nx > 1 || ny > 1) return null;
    return { x: nx, y: ny };
  }

  function strokeWidthNorm() {
    if (content.width <= 0) return 0.004;
    return Math.max(0.001, getWidthPx() / content.width);
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

  function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const stroke of strokes) drawStroke(stroke);
    if (draft) drawStroke(draft);
  }

  function pointerDown(e) {
    const point = toNorm(e.clientX, e.clientY);
    if (!point) return;
    canvas.setPointerCapture(e.pointerId);
    drawing = true;
    draft = {
      color: getColor(),
      width: strokeWidthNorm(),
      points: [point],
    };
    redraw();
  }

  function pointerMove(e) {
    if (!drawing || !draft) return;
    const point = toNorm(e.clientX, e.clientY);
    if (!point) return;
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
    if (draft && draft.points.length >= 2) {
      strokes.push(draft);
      onChange?.(strokes);
    }
    draft = null;
    redraw();
  }

  canvas.addEventListener("pointerdown", pointerDown);
  canvas.addEventListener("pointermove", pointerMove);
  canvas.addEventListener("pointerup", pointerUp);
  canvas.addEventListener("pointercancel", pointerUp);

  return { setContentBox, setStrokes, getStrokes, clear, undo, redraw };
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

window.PdfPen = { createPenController, contentBoxForObjectFitContain };
