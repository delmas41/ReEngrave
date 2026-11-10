// ROADMAP 2.287 -- the PAGE PASS. One canvas, the page's ink tinted by claim state (server-rendered
// for the visible region), label shapes drawn over it. No framework, no build step.
"use strict";
const $ = (id) => document.getElementById(id);
const cv = $("cv"), ctx = cv.getContext("2d");
const KEY_FOR = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-"];

const S = {
  meta: null, labels: [], counts: {}, stats: null,
  kind: null,                 // the active kind (one at a time: Sean labels one symbol type per pass)
  sel: null,                  // selected label id
  view: { x: 0, y: 0, z: 0.2 },  // page px at the canvas's top-left; css px per page px
  img: null, imgBox: null,    // last ink picture and the page region it covers
  poly: null,                 // polygon in progress: [[x,y], ...]
  polyMode: false, redraw: null, changeKind: false, hidePrefill: false,
  drag: null, space: false, mouse: [0, 0], req: 0, busy: false,
};

// ---------------------------------------------------------------- api
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) {
    let d = r.statusText; try { d = (await r.json()).detail || d; } catch (e) {}
    setSave("ERROR: " + d, true); throw new Error(d);
  }
  return r.json();
}
function setSave(t, bad) { const e = $("save"); e.textContent = t; e.style.color = bad ? "#ff8a80" : ""; }
function take(st) {
  if (st.meta) S.meta = st.meta;
  S.labels = st.labels; S.counts = st.counts; S.stats = st.stats;
  renderSide(); renderPalette(); fetchInk(); draw();
}

// ---------------------------------------------------------------- geometry
const cw = () => cv.clientWidth, ch = () => cv.clientHeight;
const toScreen = (x, y) => [(x - S.view.x) * S.view.z, (y - S.view.y) * S.view.z];
const toPage = (sx, sy) => [S.view.x + sx / S.view.z, S.view.y + sy / S.view.z];
function bbox(shape) {
  if (shape.rect) return shape.rect;
  const xs = shape.poly.map((p) => p[0]), ys = shape.poly.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}
function area(shape) { const b = bbox(shape); return (b[2] - b[0]) * (b[3] - b[1]); }
function contains(shape, x, y) {
  if (shape.rect) { const r = shape.rect; return x >= r[0] && x <= r[2] && y >= r[1] && y <= r[3]; }
  let inside = false; const p = shape.poly;
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    if ((p[i][1] > y) !== (p[j][1] > y) && x < (p[j][0] - p[i][0]) * (y - p[i][1]) / (p[j][1] - p[i][1] + 1e-12) + p[i][0]) inside = !inside;
  }
  return inside;
}
function fit(rect, pad = 24) {
  const w = rect[2] - rect[0], h = rect[3] - rect[1];
  const z = Math.min((cw() - pad) / w, (ch() - pad) / h);
  S.view.z = z; S.view.x = rect[0] - (cw() / z - w) / 2; S.view.y = rect[1] - (ch() / z - h) / 2;
  fetchInk(); draw();
}
function centerOn(label) {
  const b = bbox(label.shape), w = b[2] - b[0], h = b[3] - b[1], cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
  const sp = S.meta.sp || 32;
  // zoom so the mark is comfortably visible (at least 8 spaces across, at most the current system)
  const want = Math.min(cw() / Math.max(w * 1.6, 10 * sp), ch() / Math.max(h * 2.5, 8 * sp));
  S.view.z = Math.max(0.18, Math.min(want, 1.2));
  S.view.x = cx - cw() / 2 / S.view.z; S.view.y = cy - ch() / 2 / S.view.z;
  fetchInk(); draw();
}
function zoomAt(sx, sy, f) {
  const [px, py] = toPage(sx, sy);
  S.view.z = Math.max(0.05, Math.min(2.5, S.view.z * f));
  S.view.x = px - sx / S.view.z; S.view.y = py - sy / S.view.z;
  fetchInk(); draw();
}

// ---------------------------------------------------------------- the ink picture
let inkTimer = null;
function fetchInk() {
  clearTimeout(inkTimer);
  inkTimer = setTimeout(async () => {
    const id = ++S.req, v = S.view;
    const x0 = Math.max(0, v.x), y0 = Math.max(0, v.y);
    const x1 = Math.min(S.meta.width, v.x + cw() / v.z), y1 = Math.min(S.meta.height, v.y + ch() / v.z);
    if (x1 <= x0 || y1 <= y0) return;
    const w = Math.max(50, Math.round((x1 - x0) * v.z * Math.min(2, window.devicePixelRatio || 1)));
    setSave("drawing the ink …");
    const r = await fetch(`/api/pp/render?x0=${x0}&y0=${y0}&x1=${x1}&y1=${y1}&w=${w}`);
    if (!r.ok || id !== S.req) return;
    const blob = await r.blob(), im = new Image();
    im.onload = () => { if (id !== S.req) return; S.img = im; S.imgBox = [x0, y0, x1, y1]; setSave("saved"); draw(); };
    im.src = URL.createObjectURL(blob);
  }, 70);
}

// ---------------------------------------------------------------- drawing
function colorOf(l) { return l.state === "pending" ? "#CC79A7" : "#0072B2"; }
function path(shape) {
  ctx.beginPath();
  if (shape.rect) {
    const [a, b] = toScreen(shape.rect[0], shape.rect[1]), [c, d] = toScreen(shape.rect[2], shape.rect[3]);
    ctx.rect(a, b, c - a, d - b);
  } else {
    shape.poly.forEach((p, i) => { const [x, y] = toScreen(p[0], p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.closePath();
  }
}
function draw() {
  if (!S.meta) return;
  const W = cv.width = cw() * (window.devicePixelRatio || 1), H = cv.height = ch() * (window.devicePixelRatio || 1);
  const k = window.devicePixelRatio || 1;
  ctx.setTransform(k, 0, 0, k, 0, 0);
  ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, cw(), ch());
  if (S.img && S.imgBox) {
    const [a, b] = toScreen(S.imgBox[0], S.imgBox[1]), [c, d] = toScreen(S.imgBox[2], S.imgBox[3]);
    ctx.imageSmoothingEnabled = S.view.z < 1;
    ctx.drawImage(S.img, a, b, c - a, d - b);
  }
  // page edge
  { const [a, b] = toScreen(0, 0), [c, d] = toScreen(S.meta.width, S.meta.height);
    ctx.strokeStyle = "#999"; ctx.lineWidth = 1; ctx.strokeRect(a, b, c - a, d - b); }
  for (const l of S.labels) {
    if (l.state === "rejected") continue;
    if (l.state === "pending" && S.hidePrefill) continue;
    if (S.kind && l.kind !== S.kind && l.id !== S.sel) { /* other kinds stay visible but quiet */ }
    const quiet = S.kind && l.kind !== S.kind;
    const col = colorOf(l), sel = l.id === S.sel;
    path(l.shape);
    if (l.state === "pending") {
      ctx.fillStyle = "rgba(204,121,167,0.10)"; ctx.fill();
      ctx.setLineDash([7, 5]);
    } else { ctx.setLineDash([]); }
    ctx.globalAlpha = quiet && !sel ? 0.35 : 1;
    ctx.lineWidth = sel ? 5 : 3; ctx.strokeStyle = "#fff"; ctx.stroke();      // halo
    ctx.lineWidth = sel ? 3 : 1.6; ctx.strokeStyle = sel ? "#111" : col; ctx.stroke();
    ctx.setLineDash([]);
    const b = bbox(l.shape), [tx, ty] = toScreen(b[0], b[1]);
    if (sel || S.view.z > 0.4 || (l.kind === S.kind && S.view.z > 0.12)) {
      const t = l.kind + (l.sub ? " " + l.sub : "") + (l.text ? " “" + l.text + "”" : "");
      ctx.font = "11px -apple-system, Helvetica, sans-serif";
      const tw = ctx.measureText(t).width + 6;
      ctx.fillStyle = l.state === "pending" ? "#CC79A7" : "#0072B2"; ctx.fillRect(tx, ty - 14, tw, 13);
      ctx.fillStyle = "#fff"; ctx.fillText(t, tx + 3, ty - 4);
    }
    ctx.globalAlpha = 1;
  }
  // a shape being drawn
  ctx.setLineDash([]);
  if (S.drag && S.drag.mode === "draw") {
    const [x0, y0] = S.drag.from, [x1, y1] = S.mouse;
    ctx.strokeStyle = "#111"; ctx.lineWidth = 2; ctx.setLineDash([4, 3]); ctx.strokeRect(x0, y0, x1 - x0, y1 - y0); ctx.setLineDash([]);
  }
  if (S.poly && S.poly.length) {
    ctx.strokeStyle = "#111"; ctx.lineWidth = 2; ctx.beginPath();
    S.poly.forEach((p, i) => { const [x, y] = toScreen(p[0], p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.lineTo(S.mouse[0], S.mouse[1]); ctx.stroke();
  }
  hint();
}
function hint() {
  let t = "";
  if (S.changeKind) t = "Change kind: press the kind's number (Esc cancels)";
  else if (S.redraw) t = "Redraw: drag the new box for " + S.redraw + " (Esc cancels)";
  else if (S.poly) t = "Polygon: click each corner, Enter closes, Esc cancels";
  else if (S.kind) t = "Drawing: " + S.kind + (S.polyMode ? " (polygon)" : " (box)") + " — drag on the page. Click a label to select it.";
  else t = "Pick a kind on the left to draw. Click a label to select it; drag pans.";
  $("hint").textContent = t;
}

// ---------------------------------------------------------------- side panels
function renderPalette() {
  const p = $("palette"); p.innerHTML = "";
  S.meta.kinds.forEach((k, i) => {
    const c = S.counts[k] || { pending: 0, confirmed: 0 };
    const b = document.createElement("button");
    b.className = S.kind === k ? "on" : "";
    b.innerHTML = `<span class="k">${KEY_FOR[i] || ""}</span>${k}<span class="n">${c.confirmed} done<br>${c.pending} waiting</span>`;
    b.onclick = () => pickKind(k);
    p.appendChild(b);
  });
  const n = document.createElement("div"); n.className = "none";
  n.textContent = "Staff first, repeats last: the order the reader claims them in.";
  p.appendChild(n);
}
function pickKind(k) {
  if (S.changeKind && S.sel) { S.changeKind = false; edit(S.sel, { kind: k }); return; }
  S.kind = S.kind === k ? null : k; S.poly = null; S.redraw = null; renderPalette(); renderSide(); draw();
}
function renderSide() {
  const m = S.meta; if (!m) return;
  $("pg").textContent = `${m.edition} p${m.page}`;
  const sys = $("systems");
  if (!sys.childElementCount) {
    const g = document.createElement("button"); g.textContent = "page"; g.onclick = () => fit([0, 0, m.width, m.height]); sys.appendChild(g);
    if (m.systems.length > 1) m.systems.forEach((s, i) => { const b = document.createElement("button"); b.textContent = "system " + (i + 1); b.onclick = () => fitSystem(i); sys.appendChild(b); });
    const lab = document.createElement("span"); lab.className = "muted"; lab.textContent = " staff:"; sys.appendChild(lab);
    m.strips.forEach((s, i) => { const b = document.createElement("button"); b.textContent = String(i + 1); b.title = `system ${s.system + 1}, staff ${s.staff + 1}: fit its width`; b.onclick = () => fitStrip(i * 3); sys.appendChild(b); });
  }
  const pal = m.palette, st = S.stats;
  $("legend").innerHTML = `
    <li><span class="sw" style="background:${pal["unclaimed"]}"></span>ink nobody has claimed yet</li>
    <li><span class="sw" style="background:${pal["claimed"]}"></span>claimed by a label you confirmed</li>
    <li><span class="sw dash" style="background-color:${pal["pending"]}"></span>under a pre-fill (not yours yet)</li>
    <li><span class="sw" style="background:${pal["cell pass"]}"></span>claimed in the cell pass</li>`;
  $("bar").innerHTML = ["claimed", "pending", "cellpass", "unclaimed"].map((k, i) =>
    `<i style="width:${st[k + "_pct"]}%;background:${[pal["claimed"], pal["pending"], pal["cell pass"], pal["unclaimed"]][i]}"></i>`).join("");
  $("pct").innerHTML = `<b>${st.claimed_pct.toFixed(1)}%</b> of the page's ink is claimed by what you confirmed<br>` +
    `<span class="muted">${st.pending_pct.toFixed(1)}% under pre-fills · ${st.cellpass_pct.toFixed(1)}% cell pass · ${st.unclaimed_pct.toFixed(1)}% unclaimed</span>`;
  // selected
  const l = S.labels.find((x) => x.id === S.sel);
  $("selbox").hidden = !l;
  if (l) {
    $("selid").textContent = l.id;
    $("seldesc").innerHTML = `<b>${l.kind}</b>${l.sub ? " (" + l.sub + ")" : ""} — ${l.state === "pending" ? "PRE-FILL, not yours yet" : "confirmed"}` +
      `<br><span class="muted">${l.origin}${l.source ? " · " + l.source : ""}${l.px != null ? " · claims " + l.px + " px of ink" : ""}</span>` +
      (l.note ? `<div class="note">${l.note}</div>` : "");
    $("textrow").hidden = !m.text_kinds.includes(l.kind); $("text").value = l.text || "";
    $("subrow").hidden = l.kind !== "arc"; $("sub").value = l.sub || "";
    $("b-confirm").disabled = l.state !== "pending"; $("b-reject").disabled = l.state !== "pending";
    $("b-delete").disabled = l.state === "pending";
  }
  // queue
  const q = queue(); $("qn").textContent = `(${q.length}${S.kind ? " " + S.kind : ""})`;
  $("queue").innerHTML = "";
  q.slice(0, 120).forEach((x) => {
    const li = document.createElement("li"); if (x.id === S.sel) li.className = "cur";
    li.innerHTML = `<span>${x.kind}${x.sub ? " " + x.sub : ""}${x.text ? " “" + x.text + "”" : ""}</span><span class="w">${x.note ? "see note" : ""}</span>`;
    li.onclick = () => { select(x.id); centerOn(x); };
    $("queue").appendChild(li);
  });
}
function queue() {
  const q = S.labels.filter((l) => l.state === "pending" && (!S.kind || l.kind === S.kind));
  q.sort((a, b) => { const A = bbox(a.shape), B = bbox(b.shape); return Math.round(A[1] / (S.meta.sp * 12)) - Math.round(B[1] / (S.meta.sp * 12)) || A[0] - B[0]; });
  return q;
}
function select(id) { S.sel = id; S.redraw = null; S.changeKind = false; renderSide(); draw(); }
function fitSystem(i) { const s = S.meta.systems[i]; if (s) fit(s.rect, 12); }
// the working view: one staff, the page's full width (a full score's one system is too tall to label at 'fit system')
// A staff is walked in THIRDS (a 6000 px staff is a 1 px-thin line at full-width zoom; a third shows a slur's own curve).
function tiles() {
  if (S._tiles) return S._tiles;
  S._tiles = [];
  S.meta.strips.forEach((s, i) => {
    const w = s.rect[2] - s.rect[0], t = w / 3;
    for (let k = 0; k < 3; k++) S._tiles.push({ staff: i, rect: [s.rect[0] + k * t - 0.03 * w, s.rect[1], s.rect[0] + (k + 1) * t + 0.03 * w, s.rect[3]] });
  });
  return S._tiles;
}
function fitStrip(i) { const t = tiles()[i]; if (!t) return; S.stripI = i; fit(t.rect, 12); }

// ---------------------------------------------------------------- label actions
async function create(kind, shape) {
  const st = await api("/api/pp/label", { kind, shape });
  take(st); select(st.label.id);
  if (S.meta.text_kinds.includes(kind)) { $("text").focus(); setSave("type the text, Enter"); }
}
async function act(id, action, extra = {}) { const st = await api("/api/pp/label/" + id, { action, ...extra }); take(st); return st; }
async function edit(id, f) { await act(id, "edit", f); }
async function confirm() { const l = cur(); if (l && l.state === "pending") { await act(l.id, "confirm"); nextWaiting(1); } }
async function reject() {
  const l = cur(); if (!l) return;
  await act(l.id, l.state === "pending" ? "reject" : "delete");
  if (l.state === "pending") nextWaiting(1); else { S.sel = null; renderSide(); }
}
async function del() { const l = cur(); if (l && l.state !== "pending") { await act(l.id, "delete"); S.sel = null; renderSide(); } }
const cur = () => S.labels.find((x) => x.id === S.sel);
function nextWaiting(dir) {
  const q = queue(); if (!q.length) { S.sel = null; renderSide(); draw(); return; }
  let i = q.findIndex((x) => x.id === S.sel);
  i = i < 0 ? (dir > 0 ? 0 : q.length - 1) : (i + dir + q.length) % q.length;
  select(q[i].id); centerOn(q[i]);
}

// ---------------------------------------------------------------- mouse
function hit(px, py) {
  let best = null;
  for (const l of S.labels) {
    if (l.state === "rejected" || (l.state === "pending" && S.hidePrefill)) continue;
    if (contains(l.shape, px, py) && (!best || area(l.shape) < area(best.shape))) best = l;
  }
  return best;
}
const pos = (e) => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
cv.addEventListener("mousedown", (e) => {
  cv.focus(); const [sx, sy] = pos(e); S.mouse = [sx, sy];
  if (S.poly !== null || (S.polyMode && S.kind)) return;                 // polygon clicks handled on click
  const panning = S.space || e.button === 1 || (!S.kind && !S.redraw);
  S.drag = { mode: panning ? "pan" : "draw", from: [sx, sy], moved: false, v0: { ...S.view } };
  if (panning) cv.classList.add("pan");
});
window.addEventListener("mousemove", (e) => {
  const [sx, sy] = pos(e); S.mouse = [sx, sy];
  const d = S.drag; if (!d) { if (S.poly) draw(); return; }
  if (Math.hypot(sx - d.from[0], sy - d.from[1]) > 4) d.moved = true;
  if (d.mode === "pan" && d.moved) { S.view.x = d.v0.x - (sx - d.from[0]) / S.view.z; S.view.y = d.v0.y - (sy - d.from[1]) / S.view.z; draw(); }
  if (d.mode === "draw") draw();
});
window.addEventListener("mouseup", async (e) => {
  const d = S.drag; if (!d) return; S.drag = null; cv.classList.remove("pan");
  const [sx, sy] = pos(e);
  if (d.mode === "pan") { if (d.moved) fetchInk(); else clickAt(sx, sy); draw(); return; }
  if (!d.moved) { clickAt(sx, sy); return; }
  const a = toPage(d.from[0], d.from[1]), b = toPage(sx, sy);
  const rect = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
  await commitShape({ rect });
});
function clickAt(sx, sy) {
  const [px, py] = toPage(sx, sy);
  if (S.polyMode && S.kind) { (S.poly = S.poly || []).push([px, py]); draw(); return; }
  const l = hit(px, py); if (l) select(l.id); else if (S.sel) { S.sel = null; renderSide(); draw(); }
}
cv.addEventListener("click", (e) => { if (S.polyMode && S.kind && !S.drag) { const [sx, sy] = pos(e); clickAt(sx, sy); } });
cv.addEventListener("dblclick", () => { if (S.poly) { S.poly.pop(); closePoly(); } });
async function commitShape(shape) {
  if (S.redraw) { const id = S.redraw; S.redraw = null; await edit(id, { shape }); return; }
  if (S.kind) await create(S.kind, shape);
}
async function closePoly() {
  const p = S.poly; S.poly = null;
  if (!p || p.length < 3) { draw(); return; }
  await commitShape({ poly: p });
}
cv.addEventListener("wheel", (e) => {
  e.preventDefault(); const [sx, sy] = pos(e);
  if (e.ctrlKey) zoomAt(sx, sy, Math.exp(-e.deltaY * 0.01));
  else { S.view.x += e.deltaX / S.view.z; S.view.y += e.deltaY / S.view.z; fetchInk(); draw(); }
}, { passive: false });
window.addEventListener("resize", () => { draw(); fetchInk(); });

// ---------------------------------------------------------------- keyboard
$("text").addEventListener("keydown", async (e) => {
  if (e.key === "Enter") { await edit(S.sel, { text: $("text").value }); cv.focus(); }
  if (e.key === "Escape") cv.focus();
  e.stopPropagation();
});
$("sub").addEventListener("change", () => edit(S.sel, { sub: $("sub").value }));
$("b-confirm").onclick = confirm; $("b-reject").onclick = reject; $("b-delete").onclick = del;
$("b-redraw").onclick = () => { if (S.sel) { S.redraw = S.sel; draw(); } };
$("b-kind").onclick = () => { if (S.sel) { S.changeKind = true; draw(); } };
window.addEventListener("keyup", (e) => { if (e.key === " ") S.space = false; });
window.addEventListener("keydown", async (e) => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.metaKey) {
    if (!((e.metaKey || e.ctrlKey) && e.key === "z")) return;
  }
  const k = e.key;
  if (k === " ") { S.space = true; e.preventDefault(); return; }
  const ki = KEY_FOR.indexOf(k);
  if (ki >= 0 && ki < S.meta.kinds.length) { pickKind(S.meta.kinds[ki]); return; }
  if (k === "Escape") { S.poly = null; S.redraw = null; S.changeKind = false; S.kind = null; S.sel = null; renderPalette(); renderSide(); draw(); return; }
  if (k === "Enter" && S.poly) { closePoly(); return; }
  if (k === "Tab") { e.preventDefault(); nextWaiting(e.shiftKey ? -1 : 1); return; }
  if (k === "t") confirm();
  else if (k === "f") reject();
  else if (k === "x" || k === "Delete" || k === "Backspace") del();
  else if (k === "b" && S.sel) { S.redraw = S.sel; draw(); }
  else if (k === "c" && S.sel) { S.changeKind = true; draw(); }
  else if (k === "p") { S.polyMode = !S.polyMode; S.poly = null; draw(); }
  else if (k === "u" || ((e.ctrlKey || e.metaKey) && k === "z")) { take(await api("/api/pp/undo", {})); }
  else if (k === "g") fit([0, 0, S.meta.width, S.meta.height]);
  else if (k === "[" || k === "]") { const n = tiles().length; if (n) { fitStrip(((S.stripI ?? -1) + (k === "]" ? 1 : -1) + n) % n); } }
  else if (k === "h") { S.hidePrefill = !S.hidePrefill; draw(); }
  else if (k === "+" || k === "=") zoomAt(cw() / 2, ch() / 2, 1.25);
  else if (k === "_") zoomAt(cw() / 2, ch() / 2, 0.8);
  else if (k.startsWith("Arrow")) {
    const s = 0.25 * cw() / S.view.z; if (k === "ArrowLeft") S.view.x -= s; if (k === "ArrowRight") S.view.x += s;
    if (k === "ArrowUp") S.view.y -= 0.25 * ch() / S.view.z; if (k === "ArrowDown") S.view.y += 0.25 * ch() / S.view.z;
    e.preventDefault(); fetchInk(); draw();
  }
});

// ---------------------------------------------------------------- start
(async () => {
  const st = await api("/api/pp/state");
  S.meta = st.meta; S.labels = st.labels; S.counts = st.counts; S.stats = st.stats;
  renderPalette(); renderSide();
  const h = new URLSearchParams(location.hash.slice(1));     // #view=x,y,z&kind=arc  (a bookmark / a scripted screenshot)
  if (h.get("kind")) S.kind = h.get("kind");
  if (h.get("view")) { const v = h.get("view").split(",").map(Number); S.view = { x: v[0], y: v[1], z: v[2] }; fetchInk(); draw(); }
  else if (S.meta.strips.length) fitStrip(0); else fit([0, 0, S.meta.width, S.meta.height]);
  renderPalette(); renderSide();
  setSave("saved");
})();
