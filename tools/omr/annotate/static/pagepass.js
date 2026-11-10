// ROADMAP 2.287 -- the PAGE PASS. One canvas, the page's ink tinted by claim state (server-rendered
// for the visible region), label shapes drawn over it. No framework, no build step.
// Round 2 (Sean 2026-11-10): zoom with buttons / keys / wheel at the cursor; the view follows a drag past the
// edge; hovering or selecting a label draws exactly the ink it owns; a meter is one box; a word may be a block.
"use strict";
const $ = (id) => document.getElementById(id);
const cv = $("cv"), ctx = cv.getContext("2d");
// kinds 1-9 on the number row; hairpin v (a wedge), repeat r. `0` fits the page and `-` / `+` zoom, so they are not kinds.
const KEY_FOR = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "v", "r"];
const Z_MIN = 0.03, Z_MAX = 6;
const EDGE = 40;            // px band at the canvas edge where a drag pulls the view along

const S = {
  meta: null, labels: [], counts: {}, stats: null, covered: {},
  kind: null,                 // the active kind (one at a time: Sean labels one symbol type per pass)
  drawSub: "",                // a word box drawn as a text block: title | subtitle | composer | other
  sel: null,                  // selected label id
  hover: null,                // label under the pointer (when not drawing)
  view: { x: 0, y: 0, z: 0.2 },  // page px at the canvas's top-left; css px per page px
  img: null, imgBox: null,    // last ink picture and the page region it covers
  hl: null, rev: 0,           // the owned-ink highlight {id, img, box, rev, w} and the state revision
  poly: null,                 // polygon in progress: [[x,y], ...]
  polyMode: false, redraw: null, changeKind: false, hidePrefill: false,
  drag: null, space: false, mouse: [0, 0], overCanvas: false, req: 0, busy: false,
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
  S.labels = st.labels; S.counts = st.counts; S.stats = st.stats; S.covered = st.covered || {};
  S.rev++; S.hl = null;
  renderSide(); renderPalette(); fetchInk(); fetchOwned(); draw();
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
  // the page stays reachable: at most half a screen of margin past any page edge
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
function fitPage() { fit([0, 0, S.meta.width, S.meta.height]); }
function centerOn(label) {
  const b = bbox(label.shape), w = b[2] - b[0], h = b[3] - b[1], cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
  const sp = S.meta.sp || 32;
  // zoom so the mark is comfortably visible (at least 8 spaces across, at most the current system)
  const want = Math.min(cw() / Math.max(w * 1.6, 10 * sp), ch() / Math.max(h * 2.5, 8 * sp));
  S.view.z = Math.max(0.18, Math.min(want, 1.2));
  S.view.x = cx - cw() / 2 / S.view.z; S.view.y = cy - ch() / 2 / S.view.z;
  viewChanged(true);
}
function zoomAt(sx, sy, f) {
  const [px, py] = toPage(sx, sy);
  S.view.z = Math.max(Z_MIN, Math.min(Z_MAX, S.view.z * f));
  S.view.x = px - sx / S.view.z; S.view.y = py - sy / S.view.z;
  viewChanged(true);
}
// the view moved: redraw now (the old picture is scaled meanwhile), fetch the real ink picture once it settles
function viewChanged(zoomed) { fetchInk(); if (zoomed) fetchOwned(); draw(); }

// ---------------------------------------------------------------- the ink picture
let inkTimer = null, lastInk = 0;
function fetchInk() { clearTimeout(inkTimer); inkTimer = setTimeout(fetchInkNow, 110); }
// while the view is being pulled along by a drag, refresh the picture about 4 times a second rather than
// only once it stops (a debounce would leave the new ground blank until the pointer lets go)
function fetchInkWhileMoving() { if (performance.now() - lastInk > 260) { clearTimeout(inkTimer); fetchInkNow(); } else fetchInk(); }
async function fetchInkNow() {
  {
    lastInk = performance.now();
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
  }
}

// ---------------------------------------------------------------- the owned-ink highlight (what a label owns)
let hlTimer = null;
const highlightId = () => { const l = S.labels.find((x) => x.id === (S.hover || S.sel)); return l && l.state !== "rejected" ? l.id : null; };
function fetchOwned() {
  clearTimeout(hlTimer);
  hlTimer = setTimeout(async () => {
    const id = highlightId();
    if (!id) { if (S.hl) { S.hl = null; draw(); } return; }
    const l = S.labels.find((x) => x.id === id), b = bbox(l.shape);
    const k = Math.min(2, window.devicePixelRatio || 1);
    const w = Math.max(1, Math.min(4000, Math.round((b[2] - b[0] + 6) * Math.min(1, S.view.z) * k)));
    if (S.hl && S.hl.id === id && S.hl.rev === S.rev && S.hl.w === w) return;
    const rev = S.rev;
    const r = await fetch(`/api/pp/owned/${id}?w=${w}`);
    if (rev !== S.rev || id !== highlightId()) return;
    if (r.status === 204 || !r.ok) { S.hl = { id, rev, w, img: null, box: null }; draw(); return; }
    const box = r.headers.get("X-Region").split(",").map(Number), im = new Image();
    im.onload = () => { if (rev !== S.rev || id !== highlightId()) return; S.hl = { id, rev, w, img: im, box }; draw(); };
    im.src = URL.createObjectURL(await r.blob());
  }, 90);
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
const shown = (l) => l.state !== "rejected" && !S.covered[l.id] && !(l.state === "pending" && S.hidePrefill);
const labelText = (l) => l.kind + (l.sub ? " " + l.sub : "") + (l.text ? " “" + l.text + "”" : "");
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
  // exactly the ink the hovered / selected label owns (black on a white halo)
  if (S.hl && S.hl.img && S.hl.id === highlightId()) {
    const [a, b] = toScreen(S.hl.box[0], S.hl.box[1]), [c, d] = toScreen(S.hl.box[2], S.hl.box[3]);
    ctx.imageSmoothingEnabled = S.view.z < 1; ctx.drawImage(S.hl.img, a, b, c - a, d - b);
  }
  // page edge
  { const [a, b] = toScreen(0, 0), [c, d] = toScreen(S.meta.width, S.meta.height);
    ctx.strokeStyle = "#999"; ctx.lineWidth = 1; ctx.strokeRect(a, b, c - a, d - b); }
  for (const l of S.labels) {
    if (!shown(l)) continue;
    const quiet = S.kind && l.kind !== S.kind;
    const col = colorOf(l), sel = l.id === S.sel, hov = l.id === S.hover;
    path(l.shape);
    if (l.state === "pending") {
      ctx.fillStyle = "rgba(204,121,167,0.10)"; ctx.fill();
      ctx.setLineDash([7, 5]);
    } else { ctx.setLineDash([]); }
    ctx.globalAlpha = quiet && !sel && !hov ? 0.35 : 1;
    ctx.lineWidth = sel ? 5 : 3; ctx.strokeStyle = "#fff"; ctx.stroke();      // halo
    ctx.lineWidth = sel ? 3 : hov ? 2.4 : 1.6; ctx.strokeStyle = sel ? "#111" : col; ctx.stroke();
    ctx.setLineDash([]);
    const b = bbox(l.shape), [tx, ty] = toScreen(b[0], b[1]);
    if (sel || hov || S.view.z > 0.4 || (l.kind === S.kind && S.view.z > 0.12)) {
      const t = labelText(l);
      ctx.font = "11px -apple-system, Helvetica, sans-serif";
      const tw = ctx.measureText(t).width + 6;
      ctx.fillStyle = l.state === "pending" ? "#CC79A7" : "#0072B2"; ctx.fillRect(tx, ty - 14, tw, 13);
      ctx.fillStyle = "#fff"; ctx.fillText(t, tx + 3, ty - 4);
    }
    ctx.globalAlpha = 1;
  }
  // a shape being drawn: its first corner is a PAGE point, so the box keeps growing while the view follows the drag
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
  let t = "";
  if (S.changeKind) t = "Change kind: press the kind's key (Esc cancels)";
  else if (S.redraw) t = "Redraw: drag the new box for " + S.redraw + " (Esc cancels)";
  else if (S.poly) t = "Polygon: click each corner, Enter closes, Esc cancels";
  else if (S.kind) t = "Drawing: " + S.kind + (S.kind === "word" && S.drawSub ? " (" + S.drawSub + " block)" : "") +
    (S.polyMode ? " (polygon)" : " (box)") + " — drag on the page; the view follows a drag past the edge. Click a label to select it.";
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
  if (S.kind === "word") {
    const d = document.createElement("div"); d.className = "wordsub";
    d.innerHTML = `<label>Box is <select id="wordsub"><option value="">one word or phrase (type it)</option>` +
      S.meta.word_blocks.map((s) => `<option value="${s}"${S.drawSub === s ? " selected" : ""}>a ${s} block (text optional)</option>`).join("") +
      `</select></label><div class="muted">Instrument names, crooks like (C), tempo and expression words stay single words with their text.</div>`;
    p.appendChild(d);
    $("wordsub").value = S.drawSub; $("wordsub").onchange = (e) => { S.drawSub = e.target.value; hint(); };
  }
  if (S.kind === "meter") {
    const d = document.createElement("div"); d.className = "wordsub";
    d.innerHTML = `One box around the WHOLE meter (6 over 8 together); type its value, e.g. <b>6/8</b>, <b>C</b>, <b>2/2</b>.`;
    p.appendChild(d);
  }
  const n = document.createElement("div"); n.className = "none";
  n.textContent = "Staff first, repeats last: the order the reader claims them in.";
  p.appendChild(n);
}
function pickKind(k) {
  if (S.changeKind && S.sel) { S.changeKind = false; edit(S.sel, { kind: k }); return; }
  S.kind = S.kind === k ? null : k; S.poly = null; S.redraw = null; renderPalette(); renderSide(); draw();
}
function subOptions(kind) {
  if (kind === "arc") return [["", "(not said)"], ["tie", "tie"], ["slur", "slur"]];
  if (kind === "word") return [["", "one word or phrase"]].concat(S.meta.word_blocks.map((s) => [s, s + " block"]));
  return null;
}
function renderSide() {
  const m = S.meta; if (!m) return;
  $("pg").textContent = `${m.edition} p${m.page}`;
  const sys = $("systems");
  if (!sys.childElementCount) {
    const g = document.createElement("button"); g.textContent = "page"; g.onclick = fitPage; sys.appendChild(g);
    if (m.systems.length > 1) m.systems.forEach((s, i) => { const b = document.createElement("button"); b.textContent = "system " + (i + 1); b.onclick = () => fitSystem(i); sys.appendChild(b); });
    const lab = document.createElement("span"); lab.className = "muted"; lab.textContent = " staff:"; sys.appendChild(lab);
    m.strips.forEach((s, i) => { const b = document.createElement("button"); b.textContent = String(i + 1); b.title = `system ${s.system + 1}, staff ${s.staff + 1}: fit its width`; b.onclick = () => fitStrip(i * 3); sys.appendChild(b); });
  }
  const pal = m.palette, st = S.stats;
  $("legend").innerHTML = `
    <li><span class="sw" style="background:${pal["unclaimed"]}"></span>ink nobody has claimed yet</li>
    <li><span class="sw" style="background:${pal["claimed"]}"></span>claimed by a label you confirmed</li>
    <li><span class="sw dash" style="background-color:${pal["pending"]}"></span>under a pre-fill (not yours yet)</li>
    <li><span class="sw" style="background:${pal["cell pass"]}"></span>claimed in the cell pass</li>
    <li><span class="sw" style="background:${pal["contested"]}"></span>CONTESTED: ${st.contested_px} px reached by two boxes of one size — owned by neither</li>
    <li><span class="sw" style="background:#000;box-shadow:0 0 0 2px #fff inset"></span>hover or select a label: the ink it owns</li>`;
  $("bar").innerHTML = ["claimed", "pending", "cellpass", "contested", "unclaimed"].map((k, i) =>
    `<i style="width:${st[k + "_pct"]}%;background:${[pal["claimed"], pal["pending"], pal["cell pass"], pal["contested"], pal["unclaimed"]][i]}"></i>`).join("");
  $("pct").innerHTML = `<b>${st.claimed_pct.toFixed(1)}%</b> of the page's ink is claimed by what you confirmed<br>` +
    `<span class="muted">${st.pending_pct.toFixed(1)}% under pre-fills · ${st.cellpass_pct.toFixed(1)}% cell pass · ${st.contested_pct.toFixed(1)}% contested · ${st.unclaimed_pct.toFixed(1)}% unclaimed</span>`;
  // selected
  const l = S.labels.find((x) => x.id === S.sel);
  $("selbox").hidden = !l;
  if (l) {
    $("selid").textContent = l.id;
    const parts = l.parts && l.parts.length ? ` · digits ${l.parts.map((p) => p.text || "?").join(" ")} (${l.parts[0].from})` : "";
    let owns = l.px != null ? " · owns " + l.px + " px of ink" : "";
    if (l.lost_px) owns += ` · ${l.lost_px} px went to tighter ${l.lost_to.join(", ")}`;
    $("seldesc").innerHTML = `<b>${l.kind}</b>${l.sub ? " (" + l.sub + ")" : ""} — ${l.state === "pending" ? "PRE-FILL, not yours yet" : "confirmed"}` +
      `<br><span class="muted">${l.origin}${l.source ? " · " + l.source : ""}${owns}${parts}</span>` +
      (l.contested_px ? `<div class="warn">${l.contested_px} px CONTESTED with ${l.contested_with.join(", ")} (same size): draw one tighter, or delete one.</div>` : "") +
      (l.cut ? `<div class="note">This box sits on ONE merged piece of ink, so it cuts the piece at its edge. Use a polygon to cut it exactly.</div>` : "") +
      (S.covered[l.id] ? `<div class="note">Resolved by the text block ${S.covered[l.id]}: needs no answer.</div>` : "") +
      (l.note ? `<div class="note">${l.note}</div>` : "");
    $("textrow").hidden = !m.text_kinds.includes(l.kind) || (l.kind === "word" && l.sub);
    $("text").value = l.text || "";
    $("text").placeholder = l.kind === "meter" ? "the whole meter: 6/8, C, 2/2 … Enter" : "type the words, Enter";
    const so = subOptions(l.kind);
    $("subrow").hidden = !so;
    if (so) { $("sub").innerHTML = so.map(([v, t]) => `<option value="${v}">${t}</option>`).join(""); $("sub").value = l.sub || ""; }
    $("subname").textContent = l.kind === "arc" ? "Arc is a" : "Word box is";
    $("b-confirm").disabled = l.state !== "pending"; $("b-reject").disabled = l.state !== "pending";
    $("b-delete").disabled = l.state === "pending";
  }
  // queue
  const q = queue(), nc = Object.keys(S.covered).length; $("qn").textContent = `(${q.length}${S.kind ? " " + S.kind : ""})`;
  $("covered").textContent = nc ? `${nc} pre-fill word${nc > 1 ? "s" : ""} lie inside your text block${nc > 1 ? "s" : ""}: resolved by the block, hidden, nothing to answer.` : "";
  $("queue").innerHTML = "";
  q.slice(0, 120).forEach((x) => {
    const li = document.createElement("li"); if (x.id === S.sel) li.className = "cur";
    li.innerHTML = `<span>${x.kind}${x.sub ? " " + x.sub : ""}${x.text ? " “" + x.text + "”" : ""}</span><span class="w">${x.note ? "see note" : ""}</span>`;
    li.onclick = () => { select(x.id); centerOn(x); };
    $("queue").appendChild(li);
  });
}
function queue() {
  const q = S.labels.filter((l) => l.state === "pending" && !S.covered[l.id] && (!S.kind || l.kind === S.kind));
  q.sort((a, b) => { const A = bbox(a.shape), B = bbox(b.shape); return Math.round(A[1] / (S.meta.sp * 12)) - Math.round(B[1] / (S.meta.sp * 12)) || A[0] - B[0]; });
  return q;
}
function select(id) { S.sel = id; S.redraw = null; S.changeKind = false; renderSide(); fetchOwned(); draw(); }
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
  const body = { kind, shape };
  if (kind === "word" && S.drawSub) body.sub = S.drawSub;
  const st = await api("/api/pp/label", body);
  take(st); select(st.label.id);
  if (S.meta.text_kinds.includes(kind) && !(kind === "word" && S.drawSub)) { $("text").focus(); setSave(kind === "meter" ? "type the whole meter (6/8), Enter" : "type the text, Enter"); }
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
    if (!shown(l)) continue;
    if (contains(l.shape, px, py) && (!best || area(l.shape) < area(best.shape))) best = l;
  }
  return best;
}
const pos = (e) => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
const clampPage = (p) => [Math.max(0, Math.min(S.meta.width, p[0])), Math.max(0, Math.min(S.meta.height, p[1]))];

// --- the view follows a drag (or a polygon being drawn) that reaches the canvas edge, at a speed that grows with
// the overshoot: inside the EDGE band it ramps from 0 to ~14 px a frame at the edge; beyond the edge (pointer
// outside the canvas, even outside the window while the button is held) it keeps growing. Screen px per frame, so
// it feels the same at any zoom, and the box keeps growing in PAGE coordinates (its first corner is a page point).
let panRAF = 0;
function edgeVelocity(sx, sy) {
  const ax = (v, n) => v < EDGE ? -(((EDGE - v) / EDGE) * 9 + Math.max(0, -v) * 0.15)
    : v > n - EDGE ? (((v - (n - EDGE)) / EDGE) * 9 + Math.max(0, v - n) * 0.15) : 0;
  const cap = (v) => Math.max(-90, Math.min(90, v));
  return [cap(ax(sx, cw())), cap(ax(sy, ch()))];
}
function panning() { return (S.drag && S.drag.mode === "draw") || (S.poly && S.overCanvas); }
function panLoop() {
  panRAF = 0;
  if (!panning()) return;
  const [vx, vy] = edgeVelocity(S.mouse[0], S.mouse[1]);
  if (vx || vy) { S.view.x += vx / S.view.z; S.view.y += vy / S.view.z; clampView(); fetchInkWhileMoving(); draw(); }
  panRAF = requestAnimationFrame(panLoop);
}
function startPanLoop() { if (!panRAF) panRAF = requestAnimationFrame(panLoop); }

cv.addEventListener("mousedown", (e) => {
  cv.focus(); const [sx, sy] = pos(e); S.mouse = [sx, sy];
  if (S.poly !== null || (S.polyMode && S.kind)) return;                 // polygon clicks handled on click
  const panningHand = S.space || e.button === 1 || (!S.kind && !S.redraw);
  S.drag = { mode: panningHand ? "pan" : "draw", from: [sx, sy], fromPage: toPage(sx, sy), moved: false, v0: { ...S.view } };
  if (panningHand) cv.classList.add("pan"); else startPanLoop();
});
cv.addEventListener("mouseenter", () => { S.overCanvas = true; });
cv.addEventListener("mouseleave", () => { S.overCanvas = false; S.hover = null; fetchOwned(); draw(); });
window.addEventListener("mousemove", (e) => {
  const [sx, sy] = pos(e); S.mouse = [sx, sy];
  const d = S.drag;
  if (!d) {
    if (S.poly) { draw(); startPanLoop(); }
    if (S.overCanvas && !S.poly) {                                       // hover: highlight exactly the ink the label under the pointer owns
      const l = hit(...toPage(sx, sy)), id = l ? l.id : null;
      if (id !== S.hover) { S.hover = id; fetchOwned(); draw(); }
    }
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
  const rect = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
  fetchInk();
  await commitShape({ rect });
});
function clickAt(sx, sy) {
  const [px, py] = toPage(sx, sy);
  if (S.polyMode && S.kind) { (S.poly = S.poly || []).push(clampPage([px, py])); draw(); startPanLoop(); return; }
  const l = hit(px, py); if (l) select(l.id); else if (S.sel) { S.sel = null; renderSide(); fetchOwned(); draw(); }
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
// Wheel = ZOOM, centred on the pointer (smooth: the factor follows the wheel's own delta, so a trackpad is fine
// too). Shift + wheel pans. Pinch (ctrl + wheel on a trackpad) zooms faster.
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
$("zfit").onclick = fitPage;

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
  if (k === "Escape") { S.poly = null; S.redraw = null; S.changeKind = false; S.kind = null; S.sel = null; renderPalette(); renderSide(); fetchOwned(); draw(); return; }
  if (k === "Enter" && S.poly) { closePoly(); return; }
  if (k === "Tab") { e.preventDefault(); nextWaiting(e.shiftKey ? -1 : 1); return; }
  if (k === "t") confirm();
  else if (k === "f") reject();
  else if (k === "x" || k === "Delete" || k === "Backspace") del();
  else if (k === "b" && S.sel) { S.redraw = S.sel; draw(); }
  else if (k === "c" && S.sel) { S.changeKind = true; draw(); }
  else if (k === "p") { S.polyMode = !S.polyMode; S.poly = null; draw(); }
  else if (k === "u" || ((e.ctrlKey || e.metaKey) && k === "z")) { take(await api("/api/pp/undo", {})); }
  else if (k === "g" || k === "0") fitPage();
  else if (k === "[" || k === "]") { const n = tiles().length; if (n) { fitStrip(((S.stripI ?? -1) + (k === "]" ? 1 : -1) + n) % n); } }
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
  const st = await api("/api/pp/state");
  S.meta = st.meta; S.labels = st.labels; S.counts = st.counts; S.stats = st.stats; S.covered = st.covered || {};
  renderPalette(); renderSide();
  const h = new URLSearchParams(location.hash.slice(1));     // #view=x,y,z&kind=arc  (a bookmark / a scripted screenshot)
  if (h.get("kind")) S.kind = h.get("kind");
  if (h.get("view")) { const v = h.get("view").split(",").map(Number); S.view = { x: v[0], y: v[1], z: v[2] }; viewChanged(true); }
  else if (S.meta.strips.length) fitStrip(0); else fitPage();
  if (h.get("sel")) select(h.get("sel"));
  renderPalette(); renderSide();
  setSave("saved");
  window.PP = S;      // for a scripted check; not used by the page
})();
