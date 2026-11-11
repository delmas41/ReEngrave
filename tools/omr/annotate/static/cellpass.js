// ROADMAP 2.287 round 3 -- the CELL PASS (pass 2). One canvas zoomed to one cell, the page's ink tinted by state
// (server-rendered for the visible region), label shapes drawn over it. What pass 1 claimed is blue and final;
// you label only what is left. No framework, no build step. The canvas, zoom and drag-follow are pagepass.js's.
"use strict";
const $ = (id) => document.getElementById(id);
const cv = $("cv"), ctx = cv.getContext("2d");
// kinds on the number row first, then letters that no other key uses
const KEY_FOR = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "m", "y", "e", "o", "z"];
const Z_MIN = 0.03, Z_MAX = 6, EDGE = 40;
const COL = { pending: "#CC79A7", confirmed: "#009E73", noise: "#8c8c8c" };
const KIND_TITLE = { staffedge: "staff edge", notehead: "notehead", ledger: "ledger line", dot: "dot", other: "other (fermata, grace ...)" };

const S = {
  meta: null, labels: [], cells: [], totals: null,
  kind: null, cls: {},          // active kind (one at a time) and the chosen class per kind
  cell: null,                   // the current cell id
  sel: null, hover: null,
  view: { x: 0, y: 0, z: 0.5 }, img: null, imgBox: null, hl: null, rev: 0,
  poly: null, polyMode: false, redraw: null, changeKind: false, hidePrefill: false,
  drag: null, space: false, mouse: [0, 0], overCanvas: false, req: 0, onlyWork: true,
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
let toastTimer = null;
function toast(t) { const e = $("toast"); e.textContent = t; e.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { e.hidden = true; }, 5000); }
function take(st) {
  if (st.meta) S.meta = st.meta;
  S.labels = st.labels; S.cells = st.cells; S.totals = st.totals;
  S.rev++; S.hl = null;
  renderAll(); fetchInk(); fetchOwned(); draw();
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
function clampView() {
  const vw = cw() / S.view.z, vh = ch() / S.view.z;
  S.view.x = Math.max(-0.5 * vw, Math.min(S.meta.width - 0.5 * vw, S.view.x));
  S.view.y = Math.max(-0.5 * vh, Math.min(S.meta.height - 0.5 * vh, S.view.y));
}
function fit(rect, pad = 24) {
  const w = rect[2] - rect[0], h = rect[3] - rect[1];
  const z = Math.min((cw() - pad) / w, (ch() - pad) / h);
  S.view.z = Math.max(Z_MIN, Math.min(Z_MAX, z)); S.view.x = rect[0] - (cw() / S.view.z - w) / 2; S.view.y = rect[1] - (ch() / S.view.z - h) / 2;
  viewChanged(true);
}
function zoomAt(sx, sy, f) {
  const [px, py] = toPage(sx, sy);
  S.view.z = Math.max(Z_MIN, Math.min(Z_MAX, S.view.z * f));
  S.view.x = px - sx / S.view.z; S.view.y = py - sy / S.view.z;
  viewChanged(true);
}
function viewChanged(zoomed) { fetchInk(); if (zoomed) fetchOwned(); draw(); }
const curCell = () => S.cells.find((c) => c.id === S.cell);
const fitCell = () => { const c = curCell(); if (c) fit(c.rect, 16); };
function inCell(l, c = curCell()) {
  if (!c) return false;
  const b = bbox(l.shape), x = (b[0] + b[2]) / 2, y = (b[1] + b[3]) / 2;
  return x >= c.rect[0] && x <= c.rect[2] && y >= c.rect[1] && y <= c.rect[3];
}

// ---------------------------------------------------------------- the ink picture
let inkTimer = null, lastInk = 0;
function fetchInk() { clearTimeout(inkTimer); inkTimer = setTimeout(fetchInkNow, 110); }
function fetchInkWhileMoving() { if (performance.now() - lastInk > 260) { clearTimeout(inkTimer); fetchInkNow(); } else fetchInk(); }
async function fetchInkNow() {
  if (!S.meta) return;
  lastInk = performance.now();
  const id = ++S.req, v = S.view;
  const x0 = Math.max(0, v.x), y0 = Math.max(0, v.y);
  const x1 = Math.min(S.meta.width, v.x + cw() / v.z), y1 = Math.min(S.meta.height, v.y + ch() / v.z);
  if (x1 <= x0 || y1 <= y0) return;
  const w = Math.max(50, Math.round((x1 - x0) * v.z * Math.min(2, window.devicePixelRatio || 1)));
  const r = await fetch(`/api/cp/render?x0=${x0}&y0=${y0}&x1=${x1}&y1=${y1}&w=${w}`);
  if (!r.ok || id !== S.req) return;
  const blob = await r.blob(), im = new Image();
  im.onload = () => { if (id !== S.req) return; S.img = im; S.imgBox = [x0, y0, x1, y1]; setSave("saved"); draw(); };
  im.src = URL.createObjectURL(blob);
}
let hlTimer = null;
const highlightId = () => { const l = S.labels.find((x) => x.id === (S.hover || S.sel)); return l && l.state !== "rejected" && !l.auto_pct ? l.id : null; };
function fetchOwned() {
  clearTimeout(hlTimer);
  hlTimer = setTimeout(async () => {
    const id = highlightId();
    if (!id) { if (S.hl) { S.hl = null; draw(); } return; }
    const l = S.labels.find((x) => x.id === id), b = bbox(l.shape);
    const k = Math.min(2, window.devicePixelRatio || 1);
    const w = Math.max(1, Math.min(4000, Math.round((b[2] - b[0] + 6) * Math.max(0.05, S.view.z) * k)));
    if (S.hl && S.hl.id === id && S.hl.rev === S.rev && S.hl.w === w) return;
    const rev = S.rev;
    const r = await fetch(`/api/cp/owned/${id}?w=${w}`);
    if (rev !== S.rev || id !== highlightId()) return;
    if (r.status === 204 || !r.ok) { S.hl = { id, rev, w, img: null, box: null }; draw(); return; }
    const box = r.headers.get("X-Region").split(",").map(Number), im = new Image();
    im.onload = () => { if (rev !== S.rev || id !== highlightId()) return; S.hl = { id, rev, w, img: im, box }; draw(); };
    im.src = URL.createObjectURL(await r.blob());
  }, 90);
}

// ---------------------------------------------------------------- drawing
const colorOf = (l) => l.state === "pending" ? COL.pending : l.kind === "noise" ? COL.noise : COL.confirmed;
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
// a pre-fill pass 1 already claimed (auto) or that claims no ink is not waiting for you: not drawn as a box
const waiting = (l) => l.state === "pending" && !l.auto_pct && !l.empty && !l.covered;
const shown = (l) => l.state !== "rejected" && !l.auto_pct && !l.covered && !(l.state === "pending" && S.hidePrefill);
const labelText = (l) => (l.kind === "notehead" || l.kind === "flag" || l.kind === "rest" || l.kind === "accidental" ? l.cls.replace(/^(notehead|flag|rest|accidental)/, "$1 ") : l.kind) + (l.state === "pending" && l.empty ? " (no ink)" : "");
function draw() {
  if (!S.meta) return;
  const k = window.devicePixelRatio || 1;
  cv.width = cw() * k; cv.height = ch() * k;
  ctx.setTransform(k, 0, 0, k, 0, 0);
  ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, cw(), ch());
  if (S.img && S.imgBox) {
    const [a, b] = toScreen(S.imgBox[0], S.imgBox[1]), [c, d] = toScreen(S.imgBox[2], S.imgBox[3]);
    ctx.imageSmoothingEnabled = S.view.z < 1; ctx.drawImage(S.img, a, b, c - a, d - b);
  }
  if (S.hl && S.hl.img && S.hl.id === highlightId()) {
    const [a, b] = toScreen(S.hl.box[0], S.hl.box[1]), [c, d] = toScreen(S.hl.box[2], S.hl.box[3]);
    ctx.imageSmoothingEnabled = S.view.z < 1; ctx.drawImage(S.hl.img, a, b, c - a, d - b);
  }
  // this cell's own window (the cells overlap a little; the ink beyond it is shown but is another cell's work first)
  const c = curCell();
  if (c) { const [a, b] = toScreen(c.rect[0], c.rect[1]), [e, f] = toScreen(c.rect[2], c.rect[3]);
    ctx.setLineDash([10, 6]); ctx.strokeStyle = "#555"; ctx.lineWidth = 1.5; ctx.strokeRect(a, b, e - a, f - b); ctx.setLineDash([]); }
  const vx0 = S.view.x, vy0 = S.view.y, vx1 = S.view.x + cw() / S.view.z, vy1 = S.view.y + ch() / S.view.z;
  for (const l of S.labels) {
    if (!shown(l)) continue;
    const bb = bbox(l.shape);
    if (bb[2] < vx0 || bb[0] > vx1 || bb[3] < vy0 || bb[1] > vy1) continue;
    const quiet = S.kind && l.kind !== S.kind;
    const col = colorOf(l), sel = l.id === S.sel, hov = l.id === S.hover;
    path(l.shape);
    if (l.state === "pending") { ctx.fillStyle = "rgba(204,121,167,0.08)"; ctx.fill(); ctx.setLineDash([7, 5]); } else ctx.setLineDash([]);
    ctx.globalAlpha = quiet && !sel && !hov ? 0.3 : 1;
    ctx.lineWidth = sel ? 5 : 3; ctx.strokeStyle = "#fff"; ctx.stroke();
    ctx.lineWidth = sel ? 3 : hov ? 2.4 : 1.4; ctx.strokeStyle = sel ? "#111" : col; ctx.stroke();
    ctx.setLineDash([]);
    if (sel || hov || (S.view.z > 0.5 && (!S.kind || l.kind === S.kind))) {
      const t = labelText(l), [tx, ty] = toScreen(bb[0], bb[1]);
      ctx.font = "11px -apple-system, Helvetica, sans-serif";
      const tw = ctx.measureText(t).width + 6;
      ctx.fillStyle = col; ctx.fillRect(tx, ty - 14, tw, 13);
      ctx.fillStyle = "#fff"; ctx.fillText(t, tx + 3, ty - 4);
    }
    ctx.globalAlpha = 1;
  }
  ctx.setLineDash([]);
  if (S.drag && S.drag.mode === "draw") {
    const [x0, y0] = toScreen(S.drag.fromPage[0], S.drag.fromPage[1]), [x1, y1] = S.mouse;
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 4; ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
    ctx.strokeStyle = "#111"; ctx.lineWidth = 2; ctx.setLineDash([4, 3]); ctx.strokeRect(x0, y0, x1 - x0, y1 - y0); ctx.setLineDash([]);
  }
  if (S.poly && S.poly.length) {
    ctx.strokeStyle = "#111"; ctx.lineWidth = 2; ctx.beginPath();
    S.poly.forEach((p, i) => { const [x, y] = toScreen(p[0], p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.lineTo(S.mouse[0], S.mouse[1]); ctx.stroke();
  }
  $("zlvl").textContent = Math.round(S.view.z * 100) + "%";
  hint();
}
function hint() {
  let t;
  if (S.changeKind) t = "Change kind: press the kind's key (Esc cancels)";
  else if (S.redraw) t = "Redraw: drag the new box (Esc cancels)";
  else if (S.poly) t = "Polygon: click each corner, Enter closes, Esc cancels";
  else if (S.kind) t = "Drawing: " + S.kind + " (" + (S.cls[S.kind] || S.kind) + ")" + (S.polyMode ? " (polygon)" : " (box)") +
    " — drag round the mark. Shift+T confirms every waiting " + S.kind + " in this cell.";
  else t = "Pick a kind on the left. Blue ink is final (the page pass); vermilion is what is left.";
  $("hint").textContent = t;
}

// ---------------------------------------------------------------- side panels
const cellLabels = () => S.labels.filter((l) => inCell(l));
function queue() {
  const q = S.labels.filter((l) => waiting(l) && inCell(l) && (!S.kind || l.kind === S.kind));
  q.sort((a, b) => { const A = bbox(a.shape), B = bbox(b.shape); return A[0] - B[0] || A[1] - B[1]; });
  return q;
}
function renderAll() {
  const m = S.meta; if (!m) return;
  $("pg").textContent = `${m.edition} p${m.page}`;
  renderPalette(); renderTotals(); renderSel(); renderQueue(); renderCells(); renderNav();
}
function renderNav() {
  const c = curCell(); if (!c) return;
  $("cellname").textContent = c.id;
  $("cellpos").textContent = `(${c.order + 1} of ${S.cells.length}) · ${c.pct}% of its ink left`;
}
function renderPalette() {
  const p = $("palette"); p.innerHTML = "";
  const labs = cellLabels();
  S.meta.kinds.forEach((k, i) => {
    const w = labs.filter((l) => l.kind === k && waiting(l)).length, d = labs.filter((l) => l.kind === k && l.state === "confirmed").length;
    const b = document.createElement("button");
    b.className = S.kind === k ? "on" : "";
    b.innerHTML = `<span class="k">${KEY_FOR[i] || ""}</span>${KIND_TITLE[k] || k}<span class="n">${d} done<br>${w} waiting</span>`;
    b.onclick = () => pickKind(k);
    p.appendChild(b);
  });
  if (S.kind) {
    const cl = S.meta.classes[S.kind] || [S.kind];
    if (cl.length > 1) {
      const d = document.createElement("div"); d.className = "sub";
      d.innerHTML = `Class for a new ${KIND_TITLE[S.kind] || S.kind} box <kbd>q</kbd>/<kbd>w</kbd><select id="clsdraw">` +
        cl.map((c) => `<option value="${c}"${(S.cls[S.kind] || cl[0]) === c ? " selected" : ""}>${c}</option>`).join("") + `</select>`;
      p.appendChild(d);
      $("clsdraw").onchange = (e) => { S.cls[S.kind] = e.target.value; hint(); };
    }
  }
  const n = document.createElement("div"); n.className = "none";
  n.textContent = "Counts are for this cell. What pass 1 claimed is blue: you cannot label it again.";
  p.appendChild(n);
}
function renderTotals() {
  const pal = S.meta.palette, t = S.totals;
  $("legend").innerHTML = `
    <li><span class="sw" style="background:${pal["unclaimed"]}"></span>ink nobody has claimed yet (label it)</li>
    <li><span class="sw" style="background:${pal["page pass"]}"></span>claimed in the PAGE pass: final, cannot be labelled again</li>
    <li><span class="sw dash" style="background-color:${pal["pre-fill"]}"></span>under a pre-fill still waiting for you</li>
    <li><span class="sw" style="background:${pal["cell pass"]}"></span>claimed by a cell-pass label you confirmed</li>
    <li><span class="sw noise"></span>marked noise (not music)</li>
    <li><span class="sw" style="background:#000;box-shadow:0 0 0 2px #fff inset"></span>hover or select: the ink it owns</li>`;
  const un = Math.max(0, t.unclaimed_pct - t.under_prefill_pct);
  $("bar").innerHTML = [[t.page_pct, pal["page pass"]], [t.cell_pct, pal["cell pass"]], [t.noise_pct, pal["noise"]],
    [t.under_prefill_pct, pal["pre-fill"]], [un, pal["unclaimed"]]].map((x) => `<i style="width:${x[0]}%;background:${x[1]}"></i>`).join("");
  const claimed = t.page_pct + t.cell_pct + t.noise_pct;
  $("pct").innerHTML = `<b>${claimed.toFixed(1)}%</b> of the page's ink is claimed<br>` +
    `<span class="muted">${t.page_pct.toFixed(1)}% page pass · ${t.cell_pct.toFixed(1)}% cell pass · ${t.noise_pct.toFixed(1)}% noise · ` +
    `${t.under_prefill_pct.toFixed(1)}% under waiting pre-fills · ${un.toFixed(1)}% unclaimed (${t.unclaimed_px.toLocaleString()} px)</span>`;
  const el = $("done");
  el.className = "doneline" + (t.done ? " ok" : "");
  el.innerHTML = t.done ? "PAGE DONE: every ink pixel is claimed by a confirmed label of either pass, or marked noise." :
    `Page done when no ink is left unclaimed and nothing waits: <b>${t.cells_left}</b> of ${S.cells.length} cells still have work; ` +
    `${t.pending} pre-fills waiting, ${t.auto_resolved} resolved by the page pass, ${t.covered} covered by a label you confirmed, ${t.empty} claim no ink.`;
}
function renderSel() {
  const l = S.labels.find((x) => x.id === S.sel);
  $("selbox").hidden = !l;
  if (!l) return;
  $("selid").textContent = l.id;
  const ref = l.ink_ref ? ` · roles ${l.ink_ref.roles.join("+")}${l.ink_ref.cut ? " · cut at the shape" : ""}` : "";
  $("seldesc").innerHTML = `<b>${l.kind}</b> (${l.cls}) — ${l.state === "pending" ? "PRE-FILL, not yours yet" : "confirmed"}` +
    `<br><span class="muted">${l.origin}${l.source ? " · " + l.source : ""} · owns ${l.px == null ? 0 : l.px} px of ink${ref}</span>` +
    (l.empty ? `<div class="note">This box claims no ink (nothing of its kind under it, or pass 1 owns it). Fix it or reject it.</div>` : "") +
    (l.note ? `<div class="note">${l.note}</div>` : "");
  const cl = S.meta.classes[l.kind] || [l.cls];
  $("clsrow").hidden = cl.length < 2;
  $("clssel").innerHTML = cl.map((c) => `<option value="${c}">${c}</option>`).join("");
  $("clssel").value = l.cls;
  $("b-confirm").disabled = l.state !== "pending"; $("b-reject").disabled = l.state !== "pending";
  $("b-delete").disabled = l.state === "pending";
}
function renderQueue() {
  const c = curCell(), q = queue();
  const auto = S.labels.filter((l) => l.auto_pct && inCell(l)).length, empty = S.labels.filter((l) => l.state === "pending" && l.empty && inCell(l)).length;
  $("qn").textContent = `(${q.length} waiting${S.kind ? " " + S.kind : ""})`;
  $("autonote").textContent = [auto ? `${auto} pre-fill${auto > 1 ? "s" : ""} here already claimed by the page pass (resolved, hidden).` : "",
    empty ? `${empty} claim${empty > 1 ? "" : "s"} no ink (fix or reject).` : ""].filter(Boolean).join(" ");
  $("queue").innerHTML = "";
  q.slice(0, 80).forEach((x) => {
    const li = document.createElement("li"); if (x.id === S.sel) li.className = "cur";
    li.innerHTML = `<span>${x.cls}</span><span class="w">${x.px || 0} px</span>`;
    li.onclick = () => select(x.id);
    $("queue").appendChild(li);
  });
}
function workCells() { return S.cells.filter((c) => c.unclaimed_px > 0 || c.waiting > 0); }
function renderCells() {
  S.onlyWork = $("onlywork").checked;
  const list = S.onlyWork ? workCells() : S.cells;
  $("cellsn").textContent = `(${workCells().length} with work, ${S.cells.length} cells)`;
  const ul = $("celllist"); ul.innerHTML = "";
  list.forEach((c) => {
    const li = document.createElement("li"); li.className = (c.id === S.cell ? "cur " : "") + (c.unclaimed_px === 0 && !c.waiting ? "zero" : "");
    li.innerHTML = `<span>${c.id}${c.kind !== "measure" ? " (" + c.kind + ")" : ""}</span><span class="pc">${c.pct}%</span><span class="wt">${c.waiting ? c.waiting + "w" : ""}</span>`;
    li.title = `${c.unclaimed_px} of ${c.ink_px} px unclaimed · ${c.waiting} pre-fills waiting`;
    li.onclick = () => gotoCell(c.id);
    ul.appendChild(li);
  });
  const cur = ul.querySelector(".cur"); if (cur) cur.scrollIntoView({ block: "nearest" });
}
$("onlywork").onchange = renderCells;
function gotoCell(id, noFit) {
  S.cell = id; S.sel = null; S.hover = null;
  renderAll(); if (!noFit) fitCell(); else draw();
  fetchOwned();
}
function stepCell(dir) {
  const c = curCell(); if (!c) return;
  const work = (x) => x.unclaimed_px > 0 || x.waiting > 0;
  let i = c.order;
  for (let n = 0; n < S.cells.length; n++) {
    i = (i + dir + S.cells.length) % S.cells.length;
    if (work(S.cells[i])) { gotoCell(S.cells[i].id); return; }
  }
  toast("No cell has work left.");
}
function pickKind(k) {
  if (S.changeKind && S.sel) { S.changeKind = false; edit(S.sel, { kind: k }); return; }
  S.kind = S.kind === k ? null : k; S.poly = null; S.redraw = null; renderPalette(); renderQueue(); draw();
}
function select(id) { S.sel = id; S.redraw = null; S.changeKind = false; renderSel(); renderQueue(); fetchOwned(); draw();
  const l = S.labels.find((x) => x.id === id); if (l && !inView(l)) centerOnLabel(l); }
function inView(l) { const b = bbox(l.shape); return b[0] >= S.view.x && b[2] <= S.view.x + cw() / S.view.z && b[1] >= S.view.y && b[3] <= S.view.y + ch() / S.view.z; }
function centerOnLabel(l) { const b = bbox(l.shape); S.view.x = (b[0] + b[2]) / 2 - cw() / 2 / S.view.z; S.view.y = (b[1] + b[3]) / 2 - ch() / 2 / S.view.z; viewChanged(true); }

// ---------------------------------------------------------------- label actions
async function create(kind, shape) {
  const cl = S.meta.classes[kind] || [kind];
  const st = await api("/api/cp/label", { kind, cls: S.cls[kind] || cl[0], shape, cell_id: S.cell });
  take(st); select(st.label.id);
}
async function act(id, action, extra = {}) { const st = await api("/api/cp/label/" + id, { action, ...extra }); take(st); return st; }
async function edit(id, f) { await act(id, "edit", f); }
const cur = () => S.labels.find((x) => x.id === S.sel);
function nextWaiting(dir) {
  const q = queue(); if (!q.length) { S.sel = null; renderSel(); draw(); return; }
  let i = q.findIndex((x) => x.id === S.sel);
  i = i < 0 ? (dir > 0 ? 0 : q.length - 1) : (i + dir + q.length) % q.length;
  select(q[i].id);
}
async function confirm() { const l = cur(); if (l && l.state === "pending") { await act(l.id, "confirm"); nextWaiting(1); } }
async function reject() {
  const l = cur(); if (!l) return;
  await act(l.id, l.state === "pending" ? "reject" : "delete");
  if (l.state === "pending") nextWaiting(1); else { S.sel = null; renderSel(); }
}
async function del() { const l = cur(); if (l && l.state !== "pending") { await act(l.id, "delete"); S.sel = null; renderSel(); } }
async function bulk() {
  if (!S.kind) { toast("Pick ONE kind first: the bulk confirm never crosses kinds."); return; }
  const n = queue().length;
  if (!n) { toast(`Nothing waiting of ${S.kind} in this cell.`); return; }
  const st = await api("/api/cp/bulk", { cell_id: S.cell, kind: S.kind });
  take(st);
  toast(`Confirmed ${st.bulk.confirmed} ${S.kind} pre-fill${st.bulk.confirmed > 1 ? "s" : ""} in ${S.cell}` +
    (st.bulk.skipped_empty ? ` (${st.bulk.skipped_empty} claim no ink: left)` : "") + `. u undoes all of them.`);
}
async function undo() { take(await api("/api/cp/undo", {})); }

// ---------------------------------------------------------------- mouse
function hit(px, py) {
  let best = null;
  for (const l of S.labels) {
    if (!shown(l)) continue;
    if (contains(l.shape, px, py) && (!best || area(l.shape) < area(best.shape))) best = l;
  }
  return best;
}
const pos = (e) => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
const clampPage = (p) => [Math.max(0, Math.min(S.meta.width, p[0])), Math.max(0, Math.min(S.meta.height, p[1]))];
let panRAF = 0;
function edgeVelocity(sx, sy) {
  const ax = (v, n) => v < EDGE ? -(((EDGE - v) / EDGE) * 9 + Math.max(0, -v) * 0.15)
    : v > n - EDGE ? (((v - (n - EDGE)) / EDGE) * 9 + Math.max(0, v - n) * 0.15) : 0;
  const cap = (v) => Math.max(-90, Math.min(90, v));
  return [cap(ax(sx, cw())), cap(ax(sy, ch()))];
}
function panning() { return (S.drag && S.drag.mode === "draw") || (S.poly && S.overCanvas); }
function panLoop() {
  panRAF = 0; if (!panning()) return;
  const [vx, vy] = edgeVelocity(S.mouse[0], S.mouse[1]);
  if (vx || vy) { S.view.x += vx / S.view.z; S.view.y += vy / S.view.z; clampView(); fetchInkWhileMoving(); draw(); }
  panRAF = requestAnimationFrame(panLoop);
}
function startPanLoop() { if (!panRAF) panRAF = requestAnimationFrame(panLoop); }
cv.addEventListener("mousedown", (e) => {
  cv.focus(); const [sx, sy] = pos(e); S.mouse = [sx, sy];
  if (S.poly !== null || (S.polyMode && S.kind)) return;
  const hand = S.space || e.button === 1 || (!S.kind && !S.redraw);
  S.drag = { mode: hand ? "pan" : "draw", from: [sx, sy], fromPage: toPage(sx, sy), moved: false, v0: { ...S.view } };
  if (hand) cv.classList.add("pan"); else startPanLoop();
});
cv.addEventListener("mouseenter", () => { S.overCanvas = true; });
cv.addEventListener("mouseleave", () => { S.overCanvas = false; S.hover = null; fetchOwned(); draw(); });
window.addEventListener("mousemove", (e) => {
  const [sx, sy] = pos(e); S.mouse = [sx, sy];
  const d = S.drag;
  if (!d) {
    if (S.poly) { draw(); startPanLoop(); }
    if (S.overCanvas && !S.poly) { const l = hit(...toPage(sx, sy)), id = l ? l.id : null; if (id !== S.hover) { S.hover = id; fetchOwned(); draw(); } }
    return;
  }
  if (Math.hypot(sx - d.from[0], sy - d.from[1]) > 4) d.moved = true;
  if (d.mode === "pan" && d.moved) { S.view.x = d.v0.x - (sx - d.from[0]) / S.view.z; S.view.y = d.v0.y - (sy - d.from[1]) / S.view.z; draw(); }
  if (d.mode === "draw") { draw(); startPanLoop(); }
});
window.addEventListener("mouseup", async (e) => {
  const d = S.drag; if (!d) return; S.drag = null; cv.classList.remove("pan");
  const [sx, sy] = pos(e);
  if (d.mode === "pan") { if (d.moved) fetchInk(); else clickAt(sx, sy); draw(); return; }
  if (!d.moved) { clickAt(sx, sy); return; }
  const a = clampPage(d.fromPage), b = clampPage(toPage(sx, sy));
  fetchInk();
  await commitShape({ rect: [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])] });
});
function clickAt(sx, sy) {
  const [px, py] = toPage(sx, sy);
  if (S.polyMode && S.kind) { (S.poly = S.poly || []).push(clampPage([px, py])); draw(); startPanLoop(); return; }
  const l = hit(px, py); if (l) select(l.id); else if (S.sel) { S.sel = null; renderSel(); renderQueue(); fetchOwned(); draw(); }
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
  const unit = e.deltaMode === 1 ? 33 : e.deltaMode === 2 ? 400 : 1;
  const dx = e.deltaX * unit, dy = e.deltaY * unit;
  if (e.shiftKey && !e.ctrlKey) { S.view.x += (dx || dy) / S.view.z; S.view.y += (dx ? dy : 0) / S.view.z; clampView(); viewChanged(false); }
  else zoomAt(sx, sy, Math.exp(-dy * (e.ctrlKey ? 0.01 : 0.0018)));
}, { passive: false });
window.addEventListener("resize", () => { draw(); fetchInk(); });
$("zin").onclick = () => zoomAt(cw() / 2, ch() / 2, 1.4);
$("zout").onclick = () => zoomAt(cw() / 2, ch() / 2, 1 / 1.4);
$("zfit").onclick = fitCell;
$("prev").onclick = () => stepCell(-1); $("next").onclick = () => stepCell(1);

// ---------------------------------------------------------------- keyboard
$("clssel").addEventListener("change", () => { const l = cur(); if (l) edit(l.id, { cls: $("clssel").value }); });
$("b-confirm").onclick = confirm; $("b-reject").onclick = reject; $("b-delete").onclick = del;
$("b-redraw").onclick = () => { if (S.sel) { S.redraw = S.sel; draw(); } };
$("b-kind").onclick = () => { if (S.sel) { S.changeKind = true; draw(); } };
$("b-bulk").onclick = bulk; $("b-undo").onclick = undo;
function cycleClass(d) {
  if (!S.kind) return;
  const cl = S.meta.classes[S.kind] || []; if (cl.length < 2) return;
  const i = Math.max(0, cl.indexOf(S.cls[S.kind] || cl[0]));
  S.cls[S.kind] = cl[(i + d + cl.length) % cl.length]; renderPalette(); hint();
}
window.addEventListener("keyup", (e) => { if (e.key === " ") S.space = false; });
window.addEventListener("keydown", async (e) => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.metaKey) {
    if (!((e.metaKey || e.ctrlKey) && e.key === "z")) return;
  }
  const k = e.key;
  if (k === " ") { S.space = true; e.preventDefault(); return; }
  const ki = KEY_FOR.indexOf(k);
  if (ki >= 0 && ki < S.meta.kinds.length) { pickKind(S.meta.kinds[ki]); return; }
  if (k === "Escape") { S.poly = null; S.redraw = null; S.changeKind = false; S.kind = null; S.sel = null; renderPalette(); renderSel(); renderQueue(); fetchOwned(); draw(); return; }
  if (k === "Enter" && S.poly) { closePoly(); return; }
  if (k === "Tab") { e.preventDefault(); stepCell(e.shiftKey ? -1 : 1); return; }
  if (k === "T") { bulk(); return; }
  if (k === "t") confirm();
  else if (k === "f") reject();
  else if (k === "x" || k === "Delete" || k === "Backspace") del();
  else if (k === "b" && S.sel) { S.redraw = S.sel; draw(); }
  else if (k === "c" && S.sel) { S.changeKind = true; draw(); }
  else if (k === "n") nextWaiting(1);
  else if (k === "p") { S.polyMode = !S.polyMode; S.poly = null; draw(); }
  else if (k === "q") cycleClass(-1);
  else if (k === "w") cycleClass(1);
  else if (k === "u" || ((e.ctrlKey || e.metaKey) && k === "z")) undo();
  else if (k === "g" || k === "0") fitCell();
  else if (k === "h") { S.hidePrefill = !S.hidePrefill; draw(); }
  else if (k === "+" || k === "=") zoomAt(cw() / 2, ch() / 2, 1.4);
  else if (k === "-" || k === "_") zoomAt(cw() / 2, ch() / 2, 1 / 1.4);
  else if (k.startsWith("Arrow")) {
    const s = 0.25 * cw() / S.view.z; if (k === "ArrowLeft") S.view.x -= s; if (k === "ArrowRight") S.view.x += s;
    if (k === "ArrowUp") S.view.y -= 0.25 * ch() / S.view.z; if (k === "ArrowDown") S.view.y += 0.25 * ch() / S.view.z;
    e.preventDefault(); clampView(); viewChanged(false);
  }
});

// ---------------------------------------------------------------- start
(async () => {
  const st = await api("/api/cp/state");
  S.meta = st.meta; S.labels = st.labels; S.cells = st.cells; S.totals = st.totals;
  const h = new URLSearchParams(location.hash.slice(1));     // #cell=s0-st9-m6&kind=notehead&sel=C3  (a bookmark / a scripted screenshot)
  const first = S.cells.find((c) => c.unclaimed_px > 0 || c.waiting > 0) || S.cells[0];
  S.cell = h.get("cell") || (first && first.id);
  if (h.get("kind")) S.kind = h.get("kind");
  renderAll();
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));   // let the layout settle before fitting
  fitCell();
  if (h.get("view")) { const v = h.get("view").split(",").map(Number); S.view = { x: v[0], y: v[1], z: v[2] }; viewChanged(true); }
  if (h.get("sel")) select(h.get("sel"));
  setSave("saved");
  window.CP = S;      // for a scripted check; not used by the page
})();
