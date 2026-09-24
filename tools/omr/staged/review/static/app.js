/* ReEngrave stage review — lane B, roadmap 3.4d.
 *
 * ⚠️⚠️ THE SPEC IS ONE SENTENCE FROM SEAN, and it is the whole design:
 *   *"I just want to click a box and type in what I think it is and save it,
 *    and then be able to draw a box around something that didn't get caught,
 *    or resize the box for the actual symbol — all without scrolling down the
 *    page. Make it as simple as you can."*
 *
 * So the CROP IS THE SCREEN. One bar at the top, the plate filling the rest,
 * and a popover that opens AT THE BOX he clicked. The stage views (which he
 * did not ask for and which put everything he did ask for under the fold)
 * live in a drawer that slides OVER the crop.
 *
 * ⚠️ NOTHING ABOUT THE SIDECAR CHANGED. Every answer posts the same action
 * shape it posted yesterday — `relabel_box`, `delete_box`, `own_box`,
 * `dup_box`, `unsure_box`, `add_box`, `redraw_box` — and the one addition,
 * `confirm_box`, is a row in lane (A)'s own `HUMAN_BOX_LABELS` and is
 * documented in SIDECAR.md. The viewer still knows no verb the ingest does
 * not.
 *
 * ⚠️ THE ONE PLACE CROP PIXELS BECOME PAGE PIXELS is `labels.js`'s
 * `cropToPage` / `pageToCrop`, which are the exact inverses of the server's
 * `CropFrame.to_page` / `to_crop` and are tested BOTH WAYS against
 * hand-computed numbers in `tools/omr/tests/test_stage_review.py`. The screen
 * transform below (pan and zoom) is a THIRD frame and never touches them: a
 * pixel goes screen → crop → page, in that order, every time.
 *
 * ⚠️ ONE CANVAS, NO PER-BOX DOM. The Litolff Viola staff carries 121 boxes
 * and a drag redraws the whole layer inside one `requestAnimationFrame`.
 */
'use strict';

const L = window;                    // labels.js publishes onto the window

const S = {
  session: null, staves: null, staff: null, gather: null, crop: null,
  cropImg: null, cropMeta: null, boxes: [], byGlyph: {},
  sel: null,                          // the selected glyph id
  view: {scale: 1, tx: 0, ty: 0},     // crop px -> screen px
  drag: null, pending: null, dupFor: null,
  pop: null,                          // {items, shown, idx, anchor, mode}
  sidecar: {actions: []}, sidecarPath: '',
  classes: null, labels: null,
  drawerView: 'actions', stageCache: {}, saving: 0, space: false,
  actionsOnGlyph: {},
};

const FAMILY_COLOUR = {
  notehead: '#c62828', rest: '#1565c0', clef: '#6a1b9a',
  key: '#00838f', accidental: '#ef6c00', other: '#757575',
};
const HUMAN = '#c0208a';
const HANDLE = 9;                     // screen px, the grab square
//: the drawer tabs that ARE stages — the others ('actions', 'pick') are not
const STAGE_TABS = ['adjudicate', 'evaluate', 'infer', 'export'];

// ── plumbing ────────────────────────────────────────────────────────────
function qs(o) {
  return Object.entries(o).filter(([, v]) => v !== null && v !== undefined)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
}
async function api(path, params) {
  const r = await fetch(path + (params ? '?' + qs(params) : ''));
  if (!r.ok) throw new Error((await r.text()).slice(0, 400));
  return r.json();
}
async function post(path, body) {
  const r = await fetch(path, {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  const text = await r.text();
  if (!r.ok) throw new Error(text.slice(0, 600));
  return JSON.parse(text);
}
function el(tag, attrs, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') n.className = v;
    else if (k === 'style') n.style.cssText = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) n.setAttribute(k, v);
  }
  for (const c of kids.flat()) {
    if (c === null || c === undefined || c === false) continue;
    n.appendChild(typeof c === 'string' || typeof c === 'number'
      ? document.createTextNode(String(c)) : c);
  }
  return n;
}
function $(id) { return document.getElementById(id); }
let _toastT = null;
function toast(msg, bad) {
  const t = $('toast');
  t.textContent = msg;
  t.className = 'toast' + (bad ? ' bad' : '');
  clearTimeout(_toastT);
  _toastT = setTimeout(() => t.classList.add('hidden'), bad ? 8000 : 2400);
}
function short(v) {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'object') {
    const s = JSON.stringify(v);
    return s.length > 160 ? s.slice(0, 160) + '…' : s;
  }
  return String(v);
}
function outcomeBadge(o) {
  return el('span', {class: 'badge b-' + (o || 'absent')}, o || 'no verdict');
}

// ── the three frames ────────────────────────────────────────────────────
// screen (what he points at) -> crop (what the PNG is in) -> page (what the
// record and the sidecar are in). Never a short cut between the first and
// the third.
function screenToCrop(sx, sy) {
  return [(sx - S.view.tx) / S.view.scale, (sy - S.view.ty) / S.view.scale];
}
function cropToScreen(cx, cy) {
  return [cx * S.view.scale + S.view.tx, cy * S.view.scale + S.view.ty];
}
function screenToPage(sx, sy) {
  const c = screenToCrop(sx, sy);
  return L.cropToPage(S.crop, c[0], c[1]);
}
function pageToScreen(x, y) {
  const c = L.pageToCrop(S.crop, x, y);
  return cropToScreen(c[0], c[1]);
}
function pageBoxToScreen(b) {
  const a = pageToScreen(b[0], b[1]), c = pageToScreen(b[2], b[3]);
  return [a[0], a[1], c[0], c[1]];
}

// ── boot ────────────────────────────────────────────────────────────────
async function boot() {
  S.session = await api('/api/session');
  $('provenance').innerHTML =
    `record <span class="mono">${S.session.record.split('/').pop()}</span> ·
     dpi ${S.session.dpi} · commit
     <span class="mono">${(S.session.provenance.commit || '?').slice(0, 8)}</span>
     ${S.session.is_a_baseline ? '' : '· <b>DIRTY TREE — not a baseline</b>'}`;
  S.classes = await api('/api/classes');
  // ⚠️ THE ANSWER SET COMES FROM THE SERVER, which takes it from lane (A)'s
  // `HUMAN_BOX_LABELS`. A sixth answer is one row in one Python table.
  S.labels = await api('/api/labels');
  S.staves = await api('/api/staves');

  wireBar();
  wireCanvas();
  wireKeys();
  const onResize = () => {
    sizeCanvas();
    // a pane that was 0 wide never got a fit; one that changed keeps his zoom
    if (!S.view.scale) fit(); else { draw(); positionPop(); }
  };
  window.addEventListener('resize', onResize);
  if (window.ResizeObserver) new ResizeObserver(onResize).observe($('stage'));

  const params = new URLSearchParams(location.search);
  const staff = params.get('staff') || S.session.default_staff
    || (S.staves.staves[0] || {}).staff;
  paintStaffPicker();
  if (!staff) return openDrawer('pick');
  try { await loadStaff(staff); }
  catch (e) { toast(String(e.message || e), true); openDrawer('pick'); }
}

/** ⚠️ A STAFF THAT WILL NOT LOAD MUST NOT KILL THE SCREEN. The sidecar is
 *  one staff per file, so picking a second one under an explicit
 *  `--sidecar` is REFUSED by the server — and the refusal belongs in a
 *  toast, not in a dead page. */
async function pickStaff(staff) {
  try { await loadStaff(staff); }
  catch (e) {
    toast(String(e.message || e), true);
    $('staffPick').value = S.staff || '';
  }
}

function paintStaffPicker() {
  const sel = $('staffPick');
  sel.replaceChildren(...S.staves.staves.map(r => el('option',
    {value: r.staff, ...(r.staff === S.staff ? {selected: ''} : {})},
    `${r.part_name || '(unnamed)'} — p${r.page} sys${r.system} · `
    + `${r.heads_lost} lost`)));
  sel.onchange = () => pickStaff(sel.value);
}

async function loadStaff(staff) {
  S.staff = staff;
  S.sel = null; S.pending = null; S.dupFor = null; S.stageCache = {};
  closePop();
  history.replaceState(null, '', `?staff=${encodeURIComponent(staff)}`);
  S.gather = await api('/api/gather', {staff});
  S.crop = S.gather.crop;
  S.boxes = S.gather.boxes;
  S.byGlyph = {};
  for (const b of S.boxes) S.byGlyph[b.glyph] = b;
  S.cropMeta = await api('/api/crop_meta', {staff});
  await loadSidecar();
  paintBar();
  paintStaffPicker();
  S.cropImg = null;
  const img = new Image();
  img.onload = () => { S.cropImg = img; sizeCanvas(); fit(); };
  img.onerror = () => { sizeCanvas(); draw();
    toast('the crop image would not load — the boxes are drawn over nothing',
          true); };
  img.src = S.gather.crop_url;
  sizeCanvas();
  draw();
  if (S.drawerOpen) paintDrawer();
}

function paintBar() {
  const g = S.gather;
  $('staffName').textContent = g.part_name || g.staff;
  const bars = g.cells.map(c => c.bar).filter(b => b !== null);
  $('staffBars').textContent =
    (bars.length ? `bars ${bars[0]}–${bars[bars.length - 1]}` : g.staff)
    + ` · ${g.counts.boxes_all} boxes`;
  const ctl = (S.cropMeta || {}).control || {};
  const chip = $('frameChip');
  if (ctl.ran && ctl.ok) { chip.classList.add('hidden'); }
  else {
    chip.classList.remove('hidden');
    chip.className = 'chip bad';
    chip.textContent = ctl.ran === false
      ? 'frame control NOT RUN' : 'FRAME CONTROL FAILED';
    chip.title = ctl.note || '';
  }
  const bad = ctl.ran && !ctl.ok;
  $('banner').classList.toggle('hidden', !bad);
  if (bad) {
    $('banner').textContent =
      'THIS RENDER IS NOT THE RECORD\'S RASTER — nothing drawn on it is '
      + 'evidence, and the server refuses every box action on it.';
  }
  paintSaveState();
}

function paintSaveState() {
  const chip = $('saveState');
  const n = (S.sidecar.actions || []).length;
  if (S.saving > 0) { chip.className = 'chip busy'; chip.textContent = 'saving…'; }
  else if (!n) { chip.className = 'chip ok'; chip.textContent = 'saved'; }
  else { chip.className = 'chip ok'; chip.textContent = n + ' saved'; }
  chip.title = S.sidecarPath;
}

function wireBar() {
  $('undoBtn').onclick = undoLast;
  $('rerunBtn').onclick = () => { openDrawer('actions'); rerun(); };
  $('drawerBtn').onclick = () => S.drawerOpen ? closeDrawer()
    : openDrawer(S.drawerView);
  $('drawerClose').onclick = closeDrawer;
  $('modalCancel').onclick = () => $('modal').classList.add('hidden');
  document.querySelectorAll('#tabs button').forEach(b => {
    b.onclick = () => openDrawer(b.dataset.view);
  });
}

// ═══════════════════════════════════════════════════════════════════════
// THE CANVAS — pan, zoom, and one redraw for everything
// ═══════════════════════════════════════════════════════════════════════

function sizeCanvas() {
  const c = $('crop'), st = $('stage');
  const dpr = window.devicePixelRatio || 1;
  const w = st.clientWidth, h = st.clientHeight;
  c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
  c.style.width = w + 'px'; c.style.height = h + 'px';
}

/** ⚠️ FIT TO WIDTH, VERTICALLY CENTRED — the state the page opens in and the
 *  one `f` returns to. A staff-system crop is ~8:1, so width is the fit that
 *  shows the bar he is looking for. */
function fit() {
  if (!S.crop) return;
  const st = $('stage');
  // ⚠️ A HIDDEN OR UNLAID-OUT PANE HAS WIDTH 0, and `scale = 0` draws a crop
  // of nothing over a page that looks broken. Measured: the first load in a
  // BACKGROUND tab fit at scale 0 and painted an empty screen. Wait for a
  // real width rather than dividing by it.
  if (!st.clientWidth || !st.clientHeight) {
    requestAnimationFrame(() => { sizeCanvas(); fit(); });
    return;
  }
  S.view.scale = st.clientWidth / S.crop.width;
  S.view.tx = 0;
  S.view.ty = (st.clientHeight - S.crop.height * S.view.scale) / 2;
  draw();
  positionPop();
}

function zoomAt(sx, sy, factor) {
  const before = screenToCrop(sx, sy);
  S.view.scale = Math.max(0.05, Math.min(24, S.view.scale * factor));
  const after = screenToCrop(sx, sy);
  S.view.tx += (after[0] - before[0]) * S.view.scale;
  S.view.ty += (after[1] - before[1]) * S.view.scale;
  draw();
  positionPop();
}

let _raf = null;
function draw() {
  if (_raf) return;
  _raf = requestAnimationFrame(() => { _raf = null; paintCanvas(); });
}

function paintCanvas() {
  const c = $('crop');
  if (!c || !S.crop) return;
  const dpr = window.devicePixelRatio || 1;
  const x = c.getContext('2d');
  x.setTransform(dpr, 0, 0, dpr, 0, 0);
  x.clearRect(0, 0, c.width / dpr, c.height / dpr);
  const v = S.view;

  // the plate
  if (S.cropImg) {
    x.imageSmoothingEnabled = true;
    x.drawImage(S.cropImg, v.tx, v.ty,
      S.crop.width * v.scale, S.crop.height * v.scale);
  } else {
    x.fillStyle = '#fff';
    x.fillRect(v.tx, v.ty, S.crop.width * v.scale, S.crop.height * v.scale);
    x.fillStyle = '#999'; x.font = '13px sans-serif';
    x.fillText('the crop is loading…', v.tx + 12, v.ty + 24);
  }

  // the bar numbers, along the top of the staff's own cells
  x.font = '11px ui-monospace,Menlo,monospace';
  for (const cell of S.gather.cells) {
    const p = pageBoxToScreen(cell.box);
    x.strokeStyle = 'rgba(120,120,120,.35)'; x.lineWidth = 1;
    x.beginPath(); x.moveTo(p[0], p[1]); x.lineTo(p[0], p[3]); x.stroke();
    x.fillStyle = '#6a6254';
    x.fillText(cell.bar === null ? 'c' + cell.index : String(cell.bar),
               p[0] + 3, p[1] - 3);
  }

  const mine = S.actionsOnGlyph;
  for (const b of S.boxes) {
    if (!b.bbox_page_px) continue;         // DECLINED: no page rectangle
    const p = pageBoxToScreen(b.bbox_page_px);
    const acts = mine[b.glyph] || [];
    const sel = S.sel === b.glyph;
    const said = acts.length ? acts[acts.length - 1] : null;
    x.lineWidth = sel ? 3 : 1.5;
    x.strokeStyle = said ? HUMAN : (FAMILY_COLOUR[b.family] || '#777');
    x.globalAlpha = (S.sel && !sel) ? 0.55 : 1;
    x.strokeRect(p[0], p[1], p[2] - p[0], p[3] - p[1]);
    if (said) drawSaidTag(x, p, said, b);
    x.globalAlpha = 1;
    if (sel) drawHandles(x, p);
  }

  // the boxes he drew that the detector never had
  for (const a of (S.sidecar.actions || [])) {
    if (a.kind !== 'add_box' || !a.bbox_page_px) continue;
    const p = pageBoxToScreen(a.bbox_page_px);
    x.strokeStyle = HUMAN; x.lineWidth = 2;
    x.setLineDash([]); x.strokeRect(p[0], p[1], p[2] - p[0], p[3] - p[1]);
    drawSaidTag(x, p, a, null);
  }

  // the rectangle under his hand, and the one waiting for a name
  const rect = (S.drag && S.drag.rect) || (S.pending && S.pending.screen);
  if (rect) {
    x.strokeStyle = HUMAN; x.lineWidth = 2; x.setLineDash([5, 3]);
    x.strokeRect(Math.min(rect[0], rect[2]), Math.min(rect[1], rect[3]),
      Math.abs(rect[2] - rect[0]), Math.abs(rect[3] - rect[1]));
    x.setLineDash([]);
  }
}

function drawSaidTag(x, p, a, b) {
  // ⚠️ THE TAG IS A REMINDER, NOT THE RECORD. `agree: quarter/eighth head
  // (black) — on a line` is wider than four boxes and buries its neighbours'
  // tags; the popover shows the whole sentence when he clicks.
  let word = sayWord(a, b);
  if (word.length > 20) word = word.slice(0, 19) + '…';
  if (!word) return;
  x.font = '11px -apple-system,sans-serif';
  const w = x.measureText(word).width + 8;
  const ty = p[1] - 14 < 2 ? p[3] + 2 : p[1] - 14;
  x.fillStyle = HUMAN;
  x.fillRect(p[0], ty, w, 13);
  x.fillStyle = '#fff';
  x.fillText(word, p[0] + 4, ty + 10);
}

/** The words for what he said about a box — the tag on the crop and the
 *  first line of the popover both use this one spelling. */
function sayWord(a, b) {
  if (!a) return '';
  if (a.kind === 'relabel_box' || a.kind === 'add_box')
    return L.friendlyName(a.category);
  if (a.kind === 'confirm_box') return 'agree ✓';
  if (a.kind === 'delete_box') return 'nothing';
  if (a.kind === 'unsure_box') return 'unsure';
  if (a.kind === 'dup_box') return 'duplicate';
  if (a.kind === 'own_box') {
    const st = (S.gather.system_staves || []).find(r => r.staff === a.staff);
    return (st && st.part_name) ? '⇢ ' + st.part_name : '⇢ ' + a.staff;
  }
  if (a.kind === 'redraw_box') return 'redrawn';
  return a.kind;
}

function drawHandles(x, p) {
  x.fillStyle = '#fff'; x.strokeStyle = HUMAN; x.lineWidth = 1.5;
  for (const [hx, hy] of handlePoints(p)) {
    x.fillRect(hx - HANDLE / 2, hy - HANDLE / 2, HANDLE, HANDLE);
    x.strokeRect(hx - HANDLE / 2, hy - HANDLE / 2, HANDLE, HANDLE);
  }
}
function handlePoints(p) {
  const mx = (p[0] + p[2]) / 2, my = (p[1] + p[3]) / 2;
  return [[p[0], p[1]], [mx, p[1]], [p[2], p[1]],
          [p[2], my], [p[2], p[3]], [mx, p[3]],
          [p[0], p[3]], [p[0], my]];
}
const HANDLE_CURSOR = ['nwse', 'ns', 'nesw', 'ew', 'nwse', 'ns', 'nesw', 'ew'];

// ── hit testing ─────────────────────────────────────────────────────────
function boxAt(sx, sy) {
  const [px, py] = screenToPage(sx, sy);
  let best = null;
  for (const b of S.boxes) {
    if (!b.bbox_page_px) continue;
    const [x0, y0, x1, y1] = b.bbox_page_px;
    if (px < x0 || px > x1 || py < y0 || py > y1) continue;
    const area = (x1 - x0) * (y1 - y0);
    if (!best || area < best.area) best = {b, area};
  }
  return best ? best.b : null;
}
function handleAt(sx, sy) {
  if (!S.sel) return -1;
  const b = S.byGlyph[S.sel];
  if (!b || !b.bbox_page_px) return -1;
  const p = pageBoxToScreen(b.bbox_page_px);
  const pts = handlePoints(p);
  for (let i = 0; i < pts.length; i++) {
    if (Math.abs(sx - pts[i][0]) <= HANDLE && Math.abs(sy - pts[i][1]) <= HANDLE)
      return i;
  }
  return -1;
}

/** The eight handles, applied to a page rectangle. Index order is
 *  `handlePoints`': TL, T, TR, R, BR, B, BL, L. */
function resizeBox(box, i, dx, dy) {
  const b = box.slice();
  if (i === 0 || i === 6 || i === 7) b[0] += dx;          // a left edge
  if (i === 2 || i === 3 || i === 4) b[2] += dx;          // a right edge
  if (i === 0 || i === 1 || i === 2) b[1] += dy;          // a top edge
  if (i === 4 || i === 5 || i === 6) b[3] += dy;          // a bottom edge
  return [Math.min(b[0], b[2]), Math.min(b[1], b[3]),
          Math.max(b[0], b[2]), Math.max(b[1], b[3])];
}

// ── the pointer ─────────────────────────────────────────────────────────
// ⚠️ NO MODE TOGGLE, AND NO ADD TOOL. Sean asked to *draw a box around
// something that didn't get caught* in the same breath as clicking one, so
// the gesture decides: on empty plate = draw, on a handle = resize, inside
// the selected box = move, held space or the middle button = pan.
function wireCanvas() {
  const c = $('crop');
  const at = e => {
    const r = c.getBoundingClientRect();
    return [e.clientX - r.left, e.clientY - r.top];
  };

  c.addEventListener('mousemove', e => {
    const [sx, sy] = at(e);
    if (S.drag) return onDragMove(sx, sy);
    const h = handleAt(sx, sy);
    const over = boxAt(sx, sy);
    c.className = S.space ? 'panning'
      : h >= 0 ? HANDLE_CURSOR[h]
      : (over && over.glyph === S.sel) ? 'move'
      : over ? 'overBox' : '';
  });

  c.addEventListener('mousedown', e => {
    const [sx, sy] = at(e);
    if (e.button === 1 || e.button === 2 || S.space) {
      S.drag = {mode: 'pan', sx, sy, tx: S.view.tx, ty: S.view.ty};
      c.className = 'panning';
      e.preventDefault();
      return;
    }
    if (e.button !== 0) return;
    const h = handleAt(sx, sy);
    if (h >= 0) {
      const b = S.byGlyph[S.sel];
      S.drag = {mode: 'resize', i: h, sx, sy, glyph: S.sel,
                orig: b.bbox_page_px.slice(), box: b.bbox_page_px.slice()};
      closePop();
      return;
    }
    const hit = boxAt(sx, sy);
    if (S.dupFor) {                       // "…a duplicate of THAT one"
      const src = S.dupFor; S.dupFor = null;
      if (!hit) return toast('that is not a box — nothing filed', true);
      if (hit.glyph === src.glyph) return toast('a box cannot duplicate itself', true);
      return fileAction({kind: 'dup_box', glyph: src.glyph, of: hit.glyph});
    }
    if (hit && hit.glyph === S.sel) {
      S.drag = {mode: 'move', sx, sy, glyph: hit.glyph,
                orig: hit.bbox_page_px.slice(), box: hit.bbox_page_px.slice()};
      return;
    }
    if (hit) { S.drag = {mode: 'click', sx, sy, hit}; return; }
    S.drag = {mode: 'draw', sx, sy, rect: [sx, sy, sx, sy]};
    closePop();
  });

  window.addEventListener('mousemove', e => {
    if (!S.drag) return;
    const r = c.getBoundingClientRect();
    onDragMove(e.clientX - r.left, e.clientY - r.top);
  });
  window.addEventListener('mouseup', e => {
    if (!S.drag) return;
    const r = c.getBoundingClientRect();
    onDragEnd(e.clientX - r.left, e.clientY - r.top);
  });
  c.addEventListener('contextmenu', e => e.preventDefault());

  // ⚠️ ZOOM AROUND THE CURSOR — the point under his finger does not move.
  // A pinch arrives as a wheel event with `ctrlKey`, and is the same gesture.
  c.addEventListener('wheel', e => {
    e.preventDefault();
    if (e.shiftKey) {                          // a deliberate sideways pan
      S.view.tx -= e.deltaX || e.deltaY;
      draw(); positionPop(); return;
    }
    const [sx, sy] = at(e);
    const k = Math.exp(-(e.deltaY) * (e.ctrlKey ? 0.012 : 0.0035));
    zoomAt(sx, sy, k);
  }, {passive: false});
}

function onDragMove(sx, sy) {
  const d = S.drag;
  if (d.mode === 'pan') {
    S.view.tx = d.tx + (sx - d.sx); S.view.ty = d.ty + (sy - d.sy);
    draw(); positionPop(); return;
  }
  if (d.mode === 'draw') { d.rect = [d.sx, d.sy, sx, sy]; draw(); return; }
  if (d.mode === 'click') {
    if (Math.abs(sx - d.sx) > 3 || Math.abs(sy - d.sy) > 3) d.moved = true;
    return;
  }
  const dpx = (sx - d.sx) / S.view.scale / S.crop.zoom;
  const dpy = (sy - d.sy) / S.view.scale / S.crop.zoom;
  if (d.mode === 'move') {
    d.box = [d.orig[0] + dpx, d.orig[1] + dpy, d.orig[2] + dpx, d.orig[3] + dpy];
  } else {
    d.box = resizeBox(d.orig, d.i, dpx, dpy);
  }
  // ⚠️ THE LIVE RECTANGLE IS THE BOX'S OWN — one canvas, no DOM.
  S.byGlyph[d.glyph].bbox_page_px = d.box;
  d.dirty = Math.abs(dpx) > 0.5 || Math.abs(dpy) > 0.5;
  draw();
}

function onDragEnd(sx, sy) {
  const d = S.drag; S.drag = null;
  $('crop').className = '';
  if (d.mode === 'pan') { draw(); return; }
  if (d.mode === 'click') {
    select(d.hit.glyph);
    if (!d.moved) openPop(d.hit.glyph);
    return;
  }
  if (d.mode === 'draw') {
    const w = Math.abs(sx - d.sx), h = Math.abs(sy - d.sy);
    draw();
    if (w < 5 || h < 5) { select(null); closePop(); return; }
    const screen = [Math.min(d.sx, sx), Math.min(d.sy, sy),
                    Math.max(d.sx, sx), Math.max(d.sy, sy)];
    const cropBox = [...screenToCrop(screen[0], screen[1]),
                     ...screenToCrop(screen[2], screen[3])];
    const page = L.boxToPage(S.crop, cropBox);
    // ⚠️ NOTHING IS SAVED UNTIL A CLASS IS CHOSEN. A human box with no name
    // is `Q.INK`, which GATHER already files and this tool may not
    // manufacture — lane (A) refuses an `add_box` with no `category`.
    S.pending = {page, cropBox, screen, cell: cellUnder(page)};
    select(null);
    openPop(null, {isNew: true});
    return;
  }
  // move / resize — the box is where he put it, so file the redraw
  if (!d.dirty) { draw(); return; }
  const b = S.byGlyph[d.glyph];
  fileAction({kind: 'redraw_box', glyph: d.glyph,
              bbox_page_px: b.bbox_page_px.map(n => +n.toFixed(2)),
              prior_bbox_page_px: d.orig,
              crop_px: L.boxToCrop(S.crop, b.bbox_page_px)})
    .catch(() => { b.bbox_page_px = d.orig; draw(); });
}

function cellUnder(page) {
  const cx = (page[0] + page[2]) / 2, cy = (page[1] + page[3]) / 2;
  const hits = S.gather.cells.filter(c =>
    cx >= c.box[0] && cx <= c.box[2] && cy >= c.box[1] && cy <= c.box[3]);
  // ⚠️ ONE CELL OR NONE. The padded cell reaches the next staff's ink
  // (CLAUDE.md §10) and lane (A) refuses a box whose cell it cannot resolve
  // rather than guessing — so the viewer guesses no harder than it does.
  if (hits.length !== 1) return null;
  const p = S.staff.split('/');
  return `cell/${p[1]}/${p[2]}/${p[3]}/${hits[0].index}`;
}

function select(glyph) {
  S.sel = glyph;
  draw();
}

// ═══════════════════════════════════════════════════════════════════════
// THE POPOVER — click a box, type what it is, Enter
// ═══════════════════════════════════════════════════════════════════════

function openPop(glyph, opts) {
  const o = opts || {};
  const b = glyph ? S.byGlyph[glyph] : null;
  if (glyph && !b) return;
  if (b && !b.bbox_page_px) {
    return toast('this row carries no page rectangle — DECLINED, not '
                 + 'defaulted, so it cannot be drawn or relabelled', true);
  }
  const items = L.buildAnswers({
    classes: S.classes.names, labels: S.labels.labels,
    staves: S.gather.system_staves || [],
    current: b ? b.class : null, isNew: !!o.isNew});
  S.pop = {items, glyph, isNew: !!o.isNew, idx: 0, shown: []};
  const said = glyph ? (S.actionsOnGlyph[glyph] || []) : [];
  const head = $('popHead');
  head.replaceChildren(
    o.isNew
      ? el('b', {}, 'a box the detector missed')
      : el('b', {}, L.friendlyName(b.class)),
    o.isNew ? el('span', {class: 'tiny'},
        S.pending.cell ? S.pending.cell.split('/').slice(4).join('/') + ' — '
          + 'cell resolved' : 'inside no single cell — lane (A) will refuse '
          + 'this box and say so')
      : el('span', {class: 'mono tiny'}, b.class),
    ...said.map(a => el('span', {class: 'said'},
      'you said: ' + sayWord(a, b),
      el('button', {class: 'x', title: 'take it back',
                    onclick: ev => { ev.stopPropagation(); undoOne(a.id); }},
        ' ×'))));
  const inp = $('popInput');
  inp.value = '';
  inp.placeholder = o.isNew ? 'what is it?  (Esc discards the box)'
    : 'type what it is — ' + L.friendlyName(b.class);
  $('pop').classList.remove('hidden');
  paintPopList();
  positionPop();
  inp.focus();
}

function closePop(discardPending) {
  S.pop = null;
  $('pop').classList.add('hidden');
  if (discardPending !== false && S.pending) { S.pending = null; draw(); }
}

function positionPop() {
  const pop = $('pop');
  if (!S.pop || pop.classList.contains('hidden')) return;
  const st = $('stage');
  let anchor;
  if (S.pop.isNew && S.pending) anchor = S.pending.screen;
  else {
    const b = S.byGlyph[S.pop.glyph];
    if (!b || !b.bbox_page_px) return;
    anchor = pageBoxToScreen(b.bbox_page_px);
  }
  const w = pop.offsetWidth || 310, h = pop.offsetHeight || 300;
  // beside the box, and FLIPPED to stay on screen
  let x = anchor[2] + 12;
  if (x + w > st.clientWidth - 6) x = anchor[0] - w - 12;
  if (x < 6) x = Math.min(Math.max(6, anchor[0]), st.clientWidth - w - 6);
  let y = anchor[1] - 6;
  if (y + h > st.clientHeight - 6) y = st.clientHeight - h - 6;
  if (y < 6) y = 6;
  pop.style.left = Math.round(x) + 'px';
  pop.style.top = Math.round(y) + 'px';
}

function paintPopList() {
  if (!S.pop) return;
  const q = $('popInput').value;
  const shown = L.filterAnswers(S.pop.items, q).slice(0, 60);
  S.pop.shown = shown;
  if (S.pop.idx >= shown.length) S.pop.idx = 0;
  const host = $('popList');
  if (!shown.length) {
    host.replaceChildren(el('div', {class: 'popEmpty'},
      'nothing matches. The list is the canonical 157 from '
      + '`class_aliases.canonical` plus the human answers — this tool may '
      + 'not invent a name.'));
    return;
  }
  host.replaceChildren(...shown.map((it, i) => el('div', {
    class: 'popItem' + (i === S.pop.idx ? ' on' : '')
      + (it.group === 'answer' ? ' answer' : '')
      + (it.current ? ' cur' : ''),
    onmousedown: e => { e.preventDefault(); chooseItem(it); }},
    el('span', {class: it.group === 'answer' ? 'word' : ''}, it.text),
    it.sub ? el('span', {class: 'sub'},
      it.current ? it.sub + ' ✓' : it.sub) : null)));
  const on = host.children[S.pop.idx];
  if (on && on.scrollIntoView) on.scrollIntoView({block: 'nearest'});
}

async function chooseItem(it) {
  const p = S.pop;
  if (!p) return;
  if (p.isNew) {
    if (it.group !== 'class') {            // "nothing" on a box he just drew
      closePop(); toast('the rectangle is discarded — nothing saved');
      return;
    }
    const pend = S.pending;
    closePop(false); S.pending = null;
    await fileAction({kind: 'add_box', bbox_page_px: pend.page,
                      crop_px: pend.cropBox,
                      ...(pend.cell ? {cell: pend.cell} : {}),
                      category: it.cls});
    return;
  }
  const b = S.byGlyph[p.glyph];
  closePop();
  if (it.group === 'class') {
    // ⚠️ THE SAME CLASS IS AN ANSWER TOO. Typing what the machine already
    // said is *I looked and it is right*, and it is filed as `confirm_box`
    // rather than dropped — a reader who agreed and a reader who never
    // looked are exactly what this record exists to keep apart.
    return fileAction({kind: it.cls === b.class ? 'confirm_box' : 'relabel_box',
                       glyph: b.glyph, category: it.cls});
  }
  if (it.kind === 'dup_box') {
    S.dupFor = b;
    return toast('now click the box this one duplicates');
  }
  if (it.kind === 'own_box') {
    return fileAction({kind: 'own_box', glyph: b.glyph, staff: it.staff});
  }
  if (it.kind === 'confirm_box') {
    return fileAction({kind: 'confirm_box', glyph: b.glyph,
                       category: b.class});
  }
  return fileAction({kind: it.kind, glyph: b.glyph});
}

// ── the keyboard ────────────────────────────────────────────────────────
function wireKeys() {
  const inp = $('popInput');
  inp.addEventListener('input', () => { S.pop && (S.pop.idx = 0); paintPopList(); });
  inp.addEventListener('keydown', e => {
    if (!S.pop) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const n = S.pop.shown.length;
      if (!n) return;
      S.pop.idx = (S.pop.idx + (e.key === 'ArrowDown' ? 1 : n - 1)) % n;
      return paintPopList();
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      const it = S.pop.shown[S.pop.idx];
      if (it) chooseItem(it);
      return;
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      const wasNew = S.pop.isNew;
      closePop();
      if (wasNew) toast('the rectangle is discarded — nothing saved');
      return;
    }
    if (e.key === 'Backspace' && !inp.value && !S.pop.isNew) {
      // ⚠️ THE FASTEST ANSWER ON THE PAGE. Half of what he does is *there is
      // nothing there*, and it is one key.
      e.preventDefault();
      const g = S.pop.glyph;
      closePop();
      fileAction({kind: 'delete_box', glyph: g});
    }
  });

  window.addEventListener('keydown', e => {
    if (e.key === ' ' && !isTyping(e)) { S.space = true; }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === 'Escape') {
      if (!$('modal').classList.contains('hidden'))
        return $('modal').classList.add('hidden');
      if (S.pop) return closePop();
      if (S.dupFor) { S.dupFor = null; return toast('never mind'); }
      if (S.drawerOpen) return closeDrawer();
      return select(null);
    }
    if (isTyping(e)) return;
    if (e.key === 'Tab') {
      // ⚠️ LEFT TO RIGHT, the order he reads the bar in.
      e.preventDefault();
      const drawn = S.boxes.filter(b => b.bbox_page_px)
        .sort((a, b) => a.bbox_page_px[0] - b.bbox_page_px[0]);
      if (!drawn.length) return;
      const i = drawn.findIndex(b => b.glyph === S.sel);
      const nxt = drawn[(i + (e.shiftKey ? drawn.length - 1 : 1) + drawn.length)
                        % drawn.length] || drawn[0];
      select(nxt.glyph);
      scrollTo(nxt);
      return;
    }
    if (e.key === 'Enter' && S.sel) { e.preventDefault(); return openPop(S.sel); }
    if (e.key === 'f') { e.preventDefault(); return fit(); }
    if (e.key === 'z') { e.preventDefault(); return undoLast(); }
    if (e.key === '+' || e.key === '=') {
      return zoomAt($('stage').clientWidth / 2, $('stage').clientHeight / 2, 1.25);
    }
    if (e.key === '-') {
      return zoomAt($('stage').clientWidth / 2, $('stage').clientHeight / 2, 0.8);
    }
    if (!S.sel) return;
    if (e.key === 'Delete' || e.key === 'Backspace') {
      e.preventDefault();
      return fileAction({kind: 'delete_box', glyph: S.sel});
    }
    if (e.key === 'u') { e.preventDefault();
      return fileAction({kind: 'unsure_box', glyph: S.sel}); }
  });
  window.addEventListener('keyup', e => { if (e.key === ' ') S.space = false; });
}
function isTyping(e) {
  const t = (e.target.tagName || '').toLowerCase();
  return t === 'input' || t === 'textarea' || t === 'select';
}

/** Bring a box into view without moving the zoom — Tab must not teleport. */
function scrollTo(b) {
  const st = $('stage');
  const p = pageBoxToScreen(b.bbox_page_px);
  const m = 60;
  if (p[0] < m) S.view.tx += m - p[0];
  if (p[2] > st.clientWidth - m) S.view.tx -= p[2] - (st.clientWidth - m);
  if (p[1] < m) S.view.ty += m - p[1];
  if (p[3] > st.clientHeight - m) S.view.ty -= p[3] - (st.clientHeight - m);
  draw();
}

// ═══════════════════════════════════════════════════════════════════════
// THE SIDECAR
// ═══════════════════════════════════════════════════════════════════════

async function loadSidecar() {
  const r = await api('/api/sidecar', {staff: S.staff});
  S.sidecar = r.sidecar; S.sidecarPath = r.path;
  indexActions();
}
function indexActions() {
  const by = {};
  for (const a of (S.sidecar.actions || [])) {
    if (a.glyph) (by[a.glyph] = by[a.glyph] || []).push(a);
  }
  S.actionsOnGlyph = by;
  paintSaveState();
}

/** Every answer lands here, and it posts the sidecar action UNCHANGED —
 *  `stage: "gather"` and the fields the contract names, nothing else. */
async function fileAction(action) {
  S.saving++; paintSaveState();
  try {
    // ⚠️ `review_staff` IS THE PAGE'S STAFF; `staff` BELONGS TO THE ACTION.
    // `own_box` names the staff that OWNS the box under that key, and while
    // both meanings shared one word every *belongs to the staff above* was
    // refused by the server as naming no staff at all.
    const r = await post('/api/sidecar/action',
      {review_staff: S.staff, stage: 'gather', note: '', ...action});
    S.sidecar = r.sidecar; S.sidecarPath = r.path;
    indexActions(); draw();
    if (S.drawerOpen && S.drawerView === 'actions') paintDrawer();
    toast(sayWord(r.action, null) + ' — saved');
    return r.action;
  } catch (e) {
    toast(String(e.message || e), true);
    throw e;
  } finally { S.saving--; paintSaveState(); }
}

async function undoOne(id) {
  S.saving++; paintSaveState();
  try {
    const r = await post('/api/sidecar/undo', {staff: S.staff, id});
    S.sidecar = r.sidecar;
    indexActions();
    // ⚠️ A REDRAW TAKEN BACK PUTS THE MACHINE'S OWN BOX BACK ON THE SCREEN.
    const undone = (r.removed && id) || null;
    if (undone) await refreshBoxes();
    draw();
    if (S.drawerOpen && S.drawerView === 'actions') paintDrawer();
    toast('took back ' + id);
  } catch (e) { toast(String(e.message || e), true); }
  finally { S.saving--; paintSaveState(); }
}
async function undoLast() {
  const acts = S.sidecar.actions || [];
  if (!acts.length) return toast('nothing to take back');
  await undoOne(acts[acts.length - 1].id);
}
async function refreshBoxes() {
  const g = await api('/api/gather', {staff: S.staff});
  S.gather = g; S.boxes = g.boxes; S.byGlyph = {};
  for (const b of S.boxes) S.byGlyph[b.glyph] = b;
}

// ═══════════════════════════════════════════════════════════════════════
// THE DRAWER — the stage views, OVER the crop
// ═══════════════════════════════════════════════════════════════════════

function openDrawer(view) {
  S.drawerOpen = true;
  S.drawerView = view || S.drawerView;
  $('drawer').classList.remove('hidden');
  document.querySelectorAll('#tabs button').forEach(b =>
    b.classList.toggle('on', b.dataset.view === S.drawerView));
  paintDrawer();
}
function closeDrawer() {
  S.drawerOpen = false;
  $('drawer').classList.add('hidden');
}

async function paintDrawer() {
  const host = $('drawerBody');
  const v = S.drawerView;
  if (v === 'actions') return paintActions(host);
  host.replaceChildren(el('div', {class: 'hint'}, 'loading…'));
  try {
    if (v === 'pick') await renderPick(host);
    else if (v === 'export') await renderExport(host);
    else await renderStage(host, v);
  } catch (e) {
    host.replaceChildren(el('div', {class: 'hint bad'}, String(e.message || e)));
  }
}

function paintActions(host) {
  const acts = (S.sidecar.actions || []).slice().reverse();
  host.replaceChildren(
    el('div', {class: 'card'},
      el('div', {class: 'h'}, el('b', {}, 'What I have said about this staff'),
        el('span', {class: 'dim tiny mono'}, S.sidecarPath)),
      el('div', {class: 'b'},
        el('div', {style: 'display:flex;gap:8px;margin-bottom:8px'},
          el('button', {class: 'primary', onclick: rerun},
            'Re-run the stages with these'),
          el('button', {onclick: undoLast}, 'Undo the last one')),
        el('div', {id: 'rerunOut', class: 'tiny'}),
        acts.length ? el('div', {} , ...acts.map(a => el('div', {class: 'act'},
          el('button', {class: 'x', title: 'take this back',
            onclick: () => undoOne(a.id)}, '×'),
          el('b', {}, a.id), ' ', el('span', {class: 'badge b-inferred'}, a.kind),
          el('div', {class: 'tiny mono'}, (a.glyph || a.verdict || '')
            + (a.category ? ' → ' + a.category : '')
            + (a.staff ? ' ⇢ ' + a.staff : '')
            + (a.of ? ' = ' + a.of : '')),
          a.bbox_page_px ? el('div', {class: 'tiny dim mono'},
            '[' + a.bbox_page_px.map(n => Number(n).toFixed(1)).join(', ') + ']')
            : null,
          a.note ? el('div', {class: 'tiny'}, '“' + a.note + '”') : null)))
          : el('div', {class: 'tiny dim'},
            'Nothing yet. Every answer is saved the moment you press Enter.'))));
}

async function renderPick(host) {
  const rows = S.staves.staves;
  host.replaceChildren(el('div', {class: 'card'},
    el('div', {class: 'h'}, el('b', {}, 'Every staff-system in the record'),
      el('span', {class: 'dim tiny'},
        `${rows.length} staves, ordered by ${S.staves.ordered_by}`)),
    el('div', {class: 'b'},
      el('div', {class: 'hint'},
        'HEADS LOST = notehead boxes the detector drew minus the notes the '
        + 'exporter wrote. The buckets are `export._place_notes`\' own, '
        + 'instrumented at run time — this page restates no refusal rule.'),
      el('div', {class: 'scroll', style: 'max-height:70vh'},
        el('table', {},
          el('thead', {}, el('tr', {}, ...['staff', 'page', 'sys', 'part',
            'clef', 'boxed', 'written', 'LOST'].map(h =>
              el('th', {class: /boxed|written|LOST/.test(h) ? 'num' : ''}, h)))),
          el('tbody', {}, ...rows.map(r => el('tr', {
            class: 'click' + (r.staff === S.staff ? ' sel' : ''),
            onclick: () => { pickStaff(r.staff); closeDrawer(); }},
            el('td', {class: 'mono tiny'}, r.staff),
            el('td', {class: 'num'}, r.page),
            el('td', {class: 'num'}, r.system),
            el('td', {}, r.part_name || '—'),
            el('td', {class: 'tiny'}, r.clef
              ? el('span', {}, outcomeBadge(r.clef.outcome), ' ',
                  short(r.clef.value)) : outcomeBadge(null)),
            el('td', {class: 'num'}, r.heads_boxed),
            el('td', {class: 'num'}, r.heads_written),
            el('td', {class: 'num'}, el('b', {}, r.heads_lost))))))))));
}

async function renderStage(host, stage) {
  const key = stage + '|' + S.staff;
  if (!S.stageCache[key]) S.stageCache[key] = await api('/api/stage',
    {staff: S.staff, stage});
  const v = S.stageCache[key];
  const head = el('div', {});

  if (stage === 'infer') {
    head.appendChild(el('div', {class: 'hint'}, v.note));
    head.appendChild(el('table', {},
      el('thead', {}, el('tr', {}, ...['rule', 'flag', 'on?', 'target',
        'forbids argmax'].map(h => el('th', {}, h)))),
      el('tbody', {}, ...Object.entries(v.gates).map(([r, g]) => el('tr', {},
        el('td', {class: 'mono tiny'}, r), el('td', {class: 'mono tiny'}, g.env),
        el('td', {}, g.on ? 'ON' : 'off'), el('td', {class: 'mono tiny'}, g.target),
        el('td', {}, String(g.forbids_argmax)))))));
    if (!v.inferences.length) {
      head.appendChild(el('div', {class: 'hint'},
        'REACH ZERO on this staff — no rule wrote anything here. That is a '
        + 'reach of zero, not agreement.'));
    }
    host.replaceChildren(el('div', {class: 'card'},
      el('div', {class: 'h'}, el('b', {}, 'INFER — what is most LIKELY, labelled'),
        el('span', {class: 'mono dim tiny'}, S.staff)),
      el('div', {class: 'b'}, head,
        ...v.inferences.map(step => verdictCard(step, true)))));
    return;
  }

  const glyphTable = el('table', {},
    el('thead', {}, el('tr', {}, ...['glyph', 'class', 'bar', 'verdicts',
      'quantities', 'outcomes', 'export'].map(h => el('th', {}, h)))),
    el('tbody', {}, ...v.glyphs.map(g => el('tr', {class: 'click',
      onclick: () => openSubject(g.glyph)},
      el('td', {class: 'mono tiny'}, g.glyph.split('/').slice(4).join('/')),
      el('td', {class: 'tiny'}, g.class),
      el('td', {class: 'num'}, g.bar ?? '—'),
      el('td', {class: 'num'}, g.n_verdicts),
      el('td', {class: 'tiny mono'}, g.quantities.join(' ')),
      el('td', {class: 'tiny'}, Object.entries(g.outcomes)
        .map(([k, n]) => `${k} ${n}`).join(', ') || '—'),
      el('td', {class: 'tiny'}, g.export)))));

  const cards = [];
  for (const bucket of v.staff_level) {
    const kids = [];
    if (!bucket.verdicts.length && !bucket.abstentions.length) {
      kids.push(el('div', {class: 'hint'},
        `DID NOT RUN on ${bucket.subject} — no ${stage.toUpperCase()} row at `
        + 'this subject at all (State.ABSENT). That is not the same as a '
        + 'reader looking and declining.'));
    }
    for (const a of bucket.abstentions) kids.push(abstentionCard(a, bucket.subject));
    for (const step of bucket.verdicts) kids.push(verdictCard(step, false));
    cards.push(el('div', {class: 'card'},
      el('div', {class: 'h'}, el('b', {class: 'mono tiny'}, bucket.subject),
        el('span', {class: 'dim tiny'},
          `${bucket.verdicts.length} verdicts · ${bucket.abstentions.length} abstentions`)),
      el('div', {class: 'b'}, ...kids)));
  }
  for (const c of v.cells) {
    cards.push(el('div', {class: 'card'},
      el('div', {class: 'h'}, el('b', {class: 'mono tiny'}, c.subject),
        el('span', {class: 'dim tiny'}, c.verdicts.length + ' verdicts')),
      el('div', {class: 'b'}, ...c.verdicts.map(s => verdictCard(s, false)))));
  }
  host.replaceChildren(
    el('div', {class: 'card'},
      el('div', {class: 'h'},
        el('b', {}, stage.toUpperCase() + (stage === 'adjudicate'
          ? ' — what does this ONE thing mean, on what evidence'
          : ' — what follows NECESSARILY from what we now know')),
        el('span', {class: 'mono dim tiny'}, S.staff)),
      el('div', {class: 'b'},
        el('div', {class: 'lbl'}, 'every glyph on this staff'),
        el('div', {class: 'scroll'}, glyphTable))),
    ...cards);
}

function abstentionCard(a, subject) {
  return el('div', {class: 'card'},
    el('div', {class: 'h'},
      el('span', {class: 'badge b-declined'}, 'abstained'),
      el('b', {class: 'mono tiny'}, a.quantity),
      el('span', {}, 'reason ', el('b', {}, a.reason)),
      el('span', {class: 'dim tiny'}, 'reader ' + (a.reader || '?')
        + ' · frame ' + (a.frame || '?'))),
    el('div', {class: 'two'},
      el('div', {},
        el('div', {class: 'lbl'}, 'what the reader saw'),
        Object.keys(a.detail || {}).length
          ? el('dl', {class: 'kv'}, ...Object.entries(a.detail).flatMap(
              ([k, val]) => [el('dt', {}, k), el('dd', {}, short(val))]))
          : el('div', {class: 'tiny dim'}, 'no detail on this row')),
      el('div', {},
        el('div', {class: 'lbl'}, 'what it decided'),
        el('div', {}, 'NOTHING — it looked and could not say '
          + `(State.DECLINED, reason "${a.reason}").`),
        // ⚠️ THE STAGE MUST BE A STAGE. The drawer's own tabs include `My
        // actions` and `Staves`, which are not stages, and a stance filed
        // under one is refused by the contract.
        agreeRow({stage: STAGE_TABS.includes(S.drawerView) ? S.drawerView
                    : 'adjudicate',
                  kind: 'agree', verdict: a.id,
                  quantity: a.quantity, outcome: 'abstained', subject}))));
}

function verdictCard(step, inferred) {
  const rows = (step.rows_read || []);
  const basis = (step.rows_basis || []);
  const sup = step.supersedes;
  return el('div', {class: 'card'},
    el('div', {class: 'h'},
      outcomeBadge(step.outcome),
      inferred ? el('span', {class: 'badge b-inferred'}, 'INFERRED') : null,
      el('b', {class: 'mono tiny'}, step.quantity),
      el('span', {}, '= ', el('b', {}, short(step.value))),
      el('span', {class: 'dim tiny'}, 'reason ', el('b', {}, step.reason || '—')),
      el('span', {class: 'grow'}),
      el('span', {class: 'tiny mono dim'}, step.id + ' · ' + step.decided_by)),
    el('div', {class: 'two'},
      el('div', {},
        el('div', {class: 'lbl'}, 'what it read'),
        el('div', {class: 'tiny dim', style: 'margin-bottom:6px'},
          `${step.used} used of ${step.considered} considered · basis `
          + `${step.basis} · ${step.correlated_groups} correlated group(s)`
          + (step.missing && step.missing.length
             ? ' · missing: ' + step.missing.join(', ') : '')
          + (step.declined && step.declined.length
             ? ' · declined: ' + step.declined.join(', ') : '')),
        rowsTable(rows.length ? rows : basis),
        (step.excluded && step.excluded.length)
          ? el('div', {class: 'tiny'}, 'excluded: '
              + step.excluded.map(e => e.join(' → ')).join(' | ')) : null),
      el('div', {},
        el('div', {class: 'lbl'}, 'what it decided'),
        el('dl', {class: 'kv'},
          el('dt', {}, 'outcome'), el('dd', {}, step.outcome),
          el('dt', {}, 'value'), el('dd', {}, short(step.value)),
          el('dt', {}, 'reason'), el('dd', {}, step.reason || '—'),
          el('dt', {}, 'decided_by'), el('dd', {}, step.decided_by)),
        (step.candidates && step.candidates.length)
          ? el('div', {},
              el('div', {class: 'lbl', style: 'margin-top:8px'}, 'candidates'),
              candidateTable(step.candidates)) : null,
        (inferred && step.prior_candidates && step.prior_candidates.length)
          ? el('div', {},
              el('div', {class: 'lbl', style: 'margin-top:8px'},
                'the narrowing it collapsed (' + (step.prior_outcome || '?') + ')'),
              candidateTable(step.prior_candidates)) : null,
        sup ? el('div', {class: 'hint'},
          `supersedes ${sup.id}: ${sup.prior_decider} said `
          + `${short(sup.prior_value)} [${sup.prior_outcome}] — `
          + `direction: ${sup.direction}`) : null,
        agreeRow({stage: STAGE_TABS.includes(S.drawerView) ? S.drawerView
                    : 'adjudicate',
                  kind: 'agree', verdict: step.id, quantity: step.quantity,
                  outcome: step.outcome, value: step.value,
                  subject: step.subject}))));
}

function candidateTable(cands) {
  return el('table', {},
    el('thead', {}, el('tr', {}, el('th', {}, 'candidate'),
      el('th', {class: 'num'}, 'support'))),
    el('tbody', {}, ...cands.map(c => el('tr', {},
      el('td', {}, short(c.value !== undefined ? c.value : c)),
      el('td', {class: 'num'}, c.support !== undefined ? String(c.support) : '—')))));
}

function rowsTable(rows) {
  if (!rows.length) {
    return el('div', {class: 'tiny dim'},
      'no rows — this verdict names none (an abstention with nothing to read '
      + 'is a reader that found nothing, not a reader that did not run).');
  }
  const trunc = rows.find(r => r.row === 'truncated');
  return el('div', {class: 'scroll', style: 'max-height:240px'},
    trunc ? el('div', {class: 'hint'},
      `showing the first ${trunc.n_shown} rows — ${trunc.n_more} more are on `
      + 'the verdict and are NOT shown here.') : null,
    el('table', {},
      el('thead', {}, el('tr', {}, ...['row', 'reader', 'quantity', 'value',
        'score', 'subject'].map(h => el('th', {}, h)))),
      el('tbody', {}, ...rows.filter(r => r.row !== 'truncated')
        .slice(0, 200).map(r => el('tr', {},
        el('td', {class: 'tiny'}, r.row),
        el('td', {class: 'tiny'}, r.reader || '—'),
        el('td', {class: 'tiny mono'}, r.quantity || '—'),
        el('td', {class: 'tiny'}, r.row === 'abstention'
          ? 'abstained: ' + (r.reason || '?') : short(r.value)),
        el('td', {class: 'num tiny'},
          r.score === null || r.score === undefined ? '—' : Number(r.score).toFixed(3)),
        el('td', {class: 'tiny mono'}, r.subject || '—'))))));
}

function agreeRow(base) {
  const note = el('input', {type: 'text', placeholder: 'why (optional)'});
  const send = kind => async () => {
    try {
      await post('/api/sidecar/action', {review_staff: S.staff, ...base, kind,
                                         note: note.value || ''});
      await loadSidecar();
      note.value = '';
      toast('saved');
    } catch (e) { toast(String(e.message || e), true); }
  };
  return el('div', {class: 'agreeRow'},
    el('button', {class: 'agree', onclick: send('agree')}, 'Agree'),
    el('button', {class: 'disagree', onclick: send('disagree')}, 'Disagree'),
    note);
}

async function renderExport(host) {
  const v = await api('/api/stage', {staff: S.staff, stage: 'export'});
  const heads = v.heads.filter(h => h.is_notehead);
  const table = el('table', {},
    el('thead', {}, el('tr', {}, ...['glyph', 'class', 'bar', 'state',
      'step', 'alter', 'octave', 'type', 'refused'].map(h => el('th', {}, h)))),
    el('tbody', {}, ...heads.map(h => el('tr', {class: 'click',
      onclick: () => openSubject(h.glyph)},
      el('td', {class: 'mono tiny'}, h.glyph.split('/').slice(4).join('/')),
      el('td', {class: 'tiny'}, h.class),
      el('td', {class: 'num'}, h.bar ?? '—'),
      el('td', {}, el('span', {class: 'badge b-' +
        (h.state === 'written' ? 'written' : h.state === 'refused'
          ? 'refused' : 'absent')}, h.state)),
      el('td', {}, h.note ? (h.note.step ?? '—') : '—'),
      el('td', {}, h.note ? (h.note.alter || '') : ''),
      el('td', {}, h.note ? (h.note.octave ?? '') : ''),
      el('td', {}, h.note ? (h.note.type ?? '') : ''),
      el('td', {class: 'tiny'}, h.refused.join(', '))))));
  const svgHost = el('div', {}, el('div', {class: 'tiny dim'}, 'rendering…'));
  host.replaceChildren(el('div', {class: 'card'},
    el('div', {class: 'h'},
      el('b', {}, 'EXPORT — written, or refused under a named bucket'),
      el('span', {class: 'dim tiny'},
        `${v.counts.heads_boxed} notehead boxes → ${v.counts.heads_written} written`)),
    el('div', {class: 'b'},
      el('div', {class: 'lbl'}, 'our render of these bars'), svgHost,
      el('div', {class: 'lbl', style: 'margin-top:10px'}, 'every head'),
      el('div', {class: 'scroll'}, table))));
  try {
    const r = await fetch('/api/render.svg?' + qs({staff: S.staff}));
    const ct = r.headers.get('content-type') || '';
    if (ct.includes('svg')) {
      svgHost.innerHTML = await r.text();
      svgHost.querySelectorAll('svg').forEach(s => {
        s.removeAttribute('height'); s.style.maxWidth = '100%';
      });
    } else {
      const j = await r.json();
      svgHost.replaceChildren(el('div', {class: 'hint bad'},
        'no render: ' + (j.reason || 'unknown') + ' — ABSTAINED rather than '
        + 'drawn as an empty stave.'));
    }
  } catch (e) {
    svgHost.replaceChildren(el('div', {class: 'hint bad'}, String(e.message || e)));
  }
}

async function openSubject(key) {
  const t = await api('/api/subject', {key});
  const st = t.stages;
  const body = el('div', {});
  body.appendChild(el('div', {class: 'tiny dim'},
    `${t.kind} · ${t.n_rows_at_subject} rows at this exact subject`));
  body.appendChild(el('div', {class: 'lbl', style: 'margin-top:10px'},
    'GATHER — ' + st.gather.state));
  body.appendChild(rowsTable([
    ...st.gather.observations.map(o => ({...o, row: 'observation'})),
    ...st.gather.abstentions.map(a => ({...a, row: 'abstention'}))]));
  for (const name of ['adjudicate', 'evaluate', 'infer']) {
    const b = st[name];
    body.appendChild(el('div', {class: 'lbl', style: 'margin-top:12px'},
      name.toUpperCase() + ' — ' + b.state
      + (b.did_not_run ? '  (DID NOT RUN on this subject)' : '')));
    if (!b.verdicts.length) {
      body.appendChild(el('div', {class: 'tiny dim'},
        'no verdict at this subject. State.ABSENT — nobody ran; it is not an '
        + 'abstention and must not be read as one.'));
    }
    for (const step of b.verdicts) body.appendChild(verdictCard(step, name === 'infer'));
  }
  body.appendChild(el('div', {class: 'lbl', style: 'margin-top:12px'}, 'EXPORT'));
  body.appendChild(el('div', {},
    el('span', {class: 'badge b-' + (st.export.state === 'written' ? 'written'
      : st.export.state === 'refused' ? 'refused' : 'absent')},
      st.export.state),
    ' ', st.export.buckets ? st.export.buckets.join(', ') : ''));
  $('modalTitle').textContent = key;
  $('modalBody').replaceChildren(body);
  $('modal').classList.remove('hidden');
}

async function rerun() {
  const out = $('rerunOut') || el('div', {});
  out.textContent = 'running…';
  try {
    const r = await post('/api/rerun', {staff: S.staff});
    if (!r.available) {
      out.replaceChildren(el('div', {class: 'hint bad'}, r.message));
      return;
    }
    out.replaceChildren(
      el('div', {class: r.returncode === 0 ? 'hint' : 'hint bad'},
        `exit ${r.returncode} — ${r.cmd}`),
      el('pre', {class: 'tiny',
        style: 'white-space:pre-wrap;max-height:220px;overflow:auto'},
        (r.stdout || '') + (r.stderr ? '\n[stderr]\n' + r.stderr : '')),
      ...(r.files || []).map(f => el('details', {},
        el('summary', {}, `${f.name} (${f.bytes} bytes)`),
        el('pre', {class: 'tiny',
          style: 'white-space:pre-wrap;max-height:300px;overflow:auto'},
          f.text || '(binary)'))));
  } catch (e) {
    out.replaceChildren(el('div', {class: 'hint bad'}, String(e.message || e)));
  }
}

boot().catch(e => {
  document.body.appendChild(el('div', {class: 'hint bad',
    style: 'position:absolute;top:60px;left:20px;right:20px;z-index:99'},
    'could not start: ' + (e.message || e)));
});
