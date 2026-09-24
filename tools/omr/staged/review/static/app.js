/* ReEngrave stage review — lane B.
 *
 * Every view answers the same two questions in the same layout:
 *   WHAT DID THIS STAGE READ   |   WHAT DID IT DECIDE
 *
 * An abstention is drawn as an abstention with its reason word; a stage with
 * no row on a subject says DID NOT RUN (State.ABSENT) and is kept apart from
 * DECLINED (a reader looked and could not say).
 *
 * The ONE place crop pixels become page pixels is `cropToPage` below, and it
 * is the exact inverse of the server's `CropFrame.to_crop` — which is tested
 * both ways in `tools/omr/tests/test_stage_review.py`.
 */
'use strict';

const S = {
  session: null, staves: null, staff: null, view: 'pick',
  gather: null, cropImg: null, cropMeta: null,
  layers: {lines: true, cells: true, ink: false, human: true,
           notehead: true, rest: true, clef: true, key: true,
           accidental: true, other: false},
  sel: null, redrawFor: null, drag: null, addMode: false,
  sidecar: {actions: []}, sidecarPath: '', classes: null, labels: null,
  pageFilter: '', stageCache: {}, selTrace: null, pendingAdd: null,
};

const FAMILY_COLOUR = {
  notehead: '#c62828', rest: '#1565c0', clef: '#6a1b9a',
  key: '#00838f', accidental: '#ef6c00', other: '#757575',
};
const HUMAN = '#c0208a';

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
    else if (k === 'html') n.innerHTML = v;
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
function toast(msg, bad) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast' + (bad ? ' bad' : '');
  setTimeout(() => t.classList.add('hidden'), bad ? 9000 : 2600);
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

// ── the coordinate frame, both ways ─────────────────────────────────────
function cropToPage(cx, cy) {
  const c = S.gather.crop;
  return [cx / c.zoom + c.page_px[0], cy / c.zoom + c.page_px[1]];
}
function pageToCrop(x, y) {
  const c = S.gather.crop;
  return [(x - c.page_px[0]) * c.zoom, (y - c.page_px[1]) * c.zoom];
}

// ── boot ────────────────────────────────────────────────────────────────
async function boot() {
  S.session = await api('/api/session');
  document.getElementById('provenance').innerHTML =
    `record <span class="mono">${S.session.record.split('/').pop()}</span> ·
     dpi ${S.session.dpi} · commit
     <span class="mono">${(S.session.provenance.commit || '?').slice(0, 8)}</span>
     ${S.session.is_a_baseline ? '' :
       '· <b>DIRTY TREE — not a baseline (§4b)</b>'}`;
  S.classes = await api('/api/classes');
  // ⚠️ THE LABEL SET COMES FROM THE SERVER, WHICH TAKES IT FROM LANE (A)'s
  // `HUMAN_BOX_LABELS`. Sean's ask ends in "etc.", so a sixth answer is one
  // row in one Python table — never a button hard-coded here as well.
  S.labels = await api('/api/labels');
  wireKeys();
  const params = new URLSearchParams(location.search);
  const staff = params.get('staff') || S.session.default_staff;
  document.querySelectorAll('#tabs button').forEach(b => {
    b.addEventListener('click', () => setView(b.dataset.view));
  });
  document.getElementById('rerunBtn').addEventListener('click', rerun);
  document.getElementById('modalCancel').addEventListener('click', closeModal);
  if (staff) { await selectStaff(staff, params.get('view') || 'gather'); }
  else { await setView('pick'); }
}

async function selectStaff(staff, view) {
  S.staff = staff;
  S.stageCache = {};
  S.gather = null; S.cropImg = null; S.sel = null; S.redrawFor = null;
  document.getElementById('staffTitle').textContent = staff;
  history.replaceState(null, '', `?staff=${encodeURIComponent(staff)}`);
  await loadSidecar();
  await setView(view || 'gather');
}

async function setView(name) {
  S.view = name;
  document.querySelectorAll('#tabs button').forEach(b =>
    b.classList.toggle('on', b.dataset.view === name));
  const host = document.getElementById('view');
  if (name !== 'pick' && !S.staff) {
    host.replaceChildren(el('div', {class: 'hint'},
      'Pick a staff first.'));
    return;
  }
  host.replaceChildren(el('div', {class: 'hint'}, 'loading…'));
  try {
    if (name === 'pick') await renderPick(host);
    else if (name === 'gather') await renderGather(host);
    else if (name === 'export') await renderExport(host);
    else await renderStage(host, name);
  } catch (e) {
    host.replaceChildren(el('div', {class: 'hint bad'}, String(e.message || e)));
  }
}

// ═══════════════════════════════════════════════════════════════════════
// PICK
// ═══════════════════════════════════════════════════════════════════════
async function renderPick(host) {
  if (!S.staves) S.staves = await api('/api/staves');
  const pages = [...new Set(S.staves.staves.map(r => r.page))].sort((a, b) => a - b);
  const sel = el('select', {style: 'width:120px',
    onchange: e => { S.pageFilter = e.target.value; setView('pick'); }},
    el('option', {value: ''}, 'every page'),
    ...pages.map(p => el('option',
      {value: String(p), ...(String(p) === S.pageFilter ? {selected: ''} : {})},
      'page ' + p)));
  const rows = S.staves.staves.filter(
    r => !S.pageFilter || String(r.page) === S.pageFilter);
  const table = el('table', {},
    el('thead', {}, el('tr', {},
      ...['staff', 'page', 'sys', 'ord', 'part', 'clef',
          'heads boxed', 'written', 'LOST', 'refused by bucket']
        .map(h => el('th', {class: /boxed|written|LOST/.test(h) ? 'num' : ''}, h)))),
    el('tbody', {}, ...rows.map(r => el('tr', {
      class: 'click' + (r.staff === S.staff ? ' sel' : ''),
      onclick: () => selectStaff(r.staff, 'gather')},
      el('td', {class: 'mono'}, r.staff),
      el('td', {class: 'num'}, r.page),
      el('td', {class: 'num'}, r.system),
      el('td', {class: 'num'}, r.staff_ordinal),
      el('td', {}, r.part_name || '—'),
      el('td', {}, r.clef
        ? el('span', {}, outcomeBadge(r.clef.outcome), ' ',
            short(r.clef.value), ' ',
            el('span', {class: 'dim tiny'}, r.clef.reason || ''))
        : el('span', {class: 'badge b-absent'}, 'no verdict')),
      el('td', {class: 'num'}, r.heads_boxed),
      el('td', {class: 'num'}, r.heads_written),
      el('td', {class: 'num'}, el('b', {}, r.heads_lost)),
      el('td', {class: 'tiny'}, Object.entries(r.refused)
        .map(([k, v]) => `${k} ×${v}`).join(', ') || '—')))));
  host.replaceChildren(
    el('div', {class: 'card'},
      el('div', {class: 'h'},
        el('b', {}, 'Every staff-system in the record'),
        el('span', {class: 'dim'},
          `${S.staves.staves.length} staves, ordered by ${S.staves.ordered_by}`),
        el('span', {class: 'grow'}), sel),
      el('div', {class: 'b'},
        el('div', {class: 'hint'},
          'HEADS LOST = notehead boxes the detector drew minus the notes the '
          + 'exporter wrote. The buckets are `export._place_notes`\' own, '
          + 'instrumented at run time — this page restates no refusal rule.'),
        el('div', {class: 'scroll', style: 'max-height:62vh'}, table))));
}

// ═══════════════════════════════════════════════════════════════════════
// GATHER
// ═══════════════════════════════════════════════════════════════════════
async function renderGather(host) {
  S.gather = await api('/api/gather', {staff: S.staff});
  S.cropMeta = await api('/api/crop_meta', {staff: S.staff});
  const g = S.gather, ctl = (S.cropMeta.control) || {};
  const banner = el('div', {
    class: 'frameBanner ' + (ctl.ran === false ? 'unknown' : (ctl.ok ? 'ok' : 'bad'))},
    ctl.ran === false ? 'FRAME CONTROL NOT RUN — ' + (ctl.note || '')
      : (ctl.ok ? `frame control PASSED, contrast ${ctl.contrast} — ${ctl.note}`
                : `FRAME CONTROL FAILED (contrast ${ctl.contrast}) — ${ctl.note}`));

  const tools = el('div', {class: 'tools'},
    layerBox('lines', 'staff lines', '#0a8f4d'),
    layerBox('cells', 'cells + bar numbers', '#999'),
    ...g.families.map(f => layerBox(f, f, FAMILY_COLOUR[f])),
    layerBox('ink', 'Q.INK summary', '#3949ab'),
    layerBox('human', 'my actions', HUMAN),
    el('label', {class: 'addTool'},
      el('input', {type: 'checkbox', id: 'addTool',
        onchange: e => {
          S.addMode = e.target.checked;
          if (S.addMode) { S.pendingAdd = null; showBox(null); }
          toast(S.addMode ? 'Add tool ON — drag a rectangle'
                          : 'Add tool off');
        }}),
      el('b', {}, 'Add tool'),
      el('span', {class: 'tiny dim'}, ' (drag to draw a missing box)')),
    el('span', {class: 'grow'}),
    el('label', {}, 'display ',
      el('input', {type: 'range', min: '25', max: '200', value: '100',
        style: 'width:120px',
        oninput: e => {
          const c = document.getElementById('cropCanvas');
          c.style.width = (g.crop.width * e.target.value / 100) + 'px';
        }})));

  const canvas = el('canvas', {id: 'cropCanvas', width: g.crop.width,
                               height: g.crop.height});
  canvas.style.width = g.crop.width + 'px';
  const wrap = el('div', {class: 'cropWrap'}, canvas);

  const detail = el('div', {id: 'boxDetail'});
  const counts = g.counts;
  host.replaceChildren(
    el('div', {class: 'card'},
      el('div', {class: 'h'},
        el('b', {}, 'GATHER — what is on the page'),
        el('span', {class: 'mono dim'}, g.staff),
        el('span', {}, g.part_name || 'part not named'),
        el('span', {class: 'grow'}),
        el('span', {class: 'dim tiny'},
          `${counts.heads_boxed} notehead boxes · ${counts.boxes_all} boxes · `
          + `${counts.heads_written} written · ${counts.heads_lost} lost`)),
      banner, tools, wrap,
      el('div', {class: 'two gatherSplit'},
        el('div', {},
          el('div', {class: 'lbl'}, 'what this stage read'),
          gatherReadPane(g)),
        el('div', {},
          el('div', {class: 'lbl'}, 'what it decided'),
          el('div', {class: 'hint'},
            'GATHER decides nothing. It files what a reader saw — and what a '
            + 'reader looked for and could not see. The decisions are '
            + 'ADJUDICATE\'s, one tab along.'),
          detail))));

  const img = new Image();
  img.onload = () => { S.cropImg = img; drawCrop(); };
  img.onerror = () => toast('the crop image would not load', true);
  img.src = g.crop_url;
  wireCanvas(canvas);
  showBox(null);
}

function layerBox(key, label, colour) {
  return el('label', {},
    el('input', {type: 'checkbox', ...(S.layers[key] ? {checked: ''} : {}),
      onchange: e => { S.layers[key] = e.target.checked; drawCrop(); }}),
    el('span', {class: 'swatch', style: `border-color:${colour}`}), label);
}

function gatherReadPane(g) {
  const byFam = {};
  for (const b of g.boxes) byFam[b.family] = (byFam[b.family] || 0) + 1;
  const noPage = g.boxes.filter(b => !b.bbox_page_px).length;
  return el('div', {},
    el('dl', {class: 'kv'},
      el('dt', {}, 'Q.STAFF_LINES'), el('dd', {}, g.staff_lines.join(', ')),
      el('dt', {}, 'spacing'), el('dd', {}, g.spacing.toFixed(3) + ' px'),
      el('dt', {}, 'Q.CELL_BOX'), el('dd', {}, g.cells.length + ' cells, bars '
        + (g.cells[0] ? g.cells[0].bar : '?') + '–'
        + (g.cells.length ? g.cells[g.cells.length - 1].bar : '?')),
      el('dt', {}, 'detector boxes'), el('dd', {},
        Object.entries(byFam).map(([k, v]) => `${k} ${v}`).join(', ')),
      el('dt', {}, 'Q.INK'), el('dd', {},
        g.ink.length ? g.ink.map(i => i.n_components).reduce((a, b) => a + (b || 0), 0)
          + ' components over ' + g.ink.length + ' cells'
          : 'no Q.INK row on this staff')),
    noPage ? el('div', {class: 'hint'},
      `${noPage} box(es) carry NO page rectangle — DECLINED, not defaulted, so `
      + 'they cannot be drawn and cannot be redrawn.') : null,
    el('div', {class: 'tiny dim', style: 'margin-top:8px'}, g.ink_note));
}

// ── drawing ─────────────────────────────────────────────────────────────
function drawCrop() {
  const canvas = document.getElementById('cropCanvas');
  if (!canvas || !S.cropImg) return;
  const g = S.gather, x = canvas.getContext('2d');
  x.clearRect(0, 0, canvas.width, canvas.height);
  x.drawImage(S.cropImg, 0, 0);

  if (S.layers.lines) {
    x.strokeStyle = '#0a8f4d'; x.lineWidth = 1;
    for (const y of g.staff_lines) {
      const [, cy] = pageToCrop(0, y);
      x.beginPath(); x.moveTo(0, cy); x.lineTo(canvas.width, cy); x.stroke();
    }
  }
  if (S.layers.cells) {
    x.strokeStyle = '#bbb'; x.lineWidth = 1; x.font = '12px monospace';
    x.fillStyle = '#888';
    for (const c of g.cells) {
      const a = pageToCrop(c.box[0], c.box[1]);
      const b = pageToCrop(c.box[2], c.box[3]);
      x.beginPath(); x.moveTo(a[0], 0); x.lineTo(a[0], canvas.height);
      x.moveTo(b[0], 0); x.lineTo(b[0], canvas.height); x.stroke();
      x.fillText(c.bar === null ? ('cell ' + c.index) : String(c.bar),
                 a[0] + 4, 13);
    }
  }
  if (S.layers.ink) {
    x.font = '11px monospace'; x.fillStyle = '#3949ab';
    for (const i of g.ink) {
      const c = g.cells.find(cc => cc.index === i.cell);
      if (!c) continue;
      const a = pageToCrop(c.box[0], c.box[1]);
      x.fillText('ink ' + (i.n_components ?? '?'), a[0] + 4, canvas.height - 5);
    }
  }
  // ⚠️ EVERY LABEL THE HUMAN HAS PUT ON A MACHINE BOX, keyed by glyph. The
  // machine's box STAYS VISIBLE under every one of them — a correction is a
  // witness beside the machine's row, never an erasure of it.
  const deleted = new Set(actionsOfKind('delete_box').map(a => a.glyph));
  const redrawn = new Map(actionsOfKind('redraw_box')
    .map(a => [a.glyph, a.bbox_page_px]));
  const relabelled = new Map(actionsOfKind('relabel_box')
    .map(a => [a.glyph, a.category]));
  const owned = new Map(actionsOfKind('own_box').map(a => [a.glyph, a.staff]));
  const dup = new Map(actionsOfKind('dup_box').map(a => [a.glyph, a.of]));
  const unsure = new Set(actionsOfKind('unsure_box').map(a => a.glyph));
  for (const b of g.boxes) {
    if (!b.bbox_page_px || !S.layers[b.family]) continue;
    const p = boxToCrop(b.bbox_page_px);
    const isSel = !!(S.sel && S.sel.glyph === b.glyph);
    // ⚠️ THE OTHERS ARE DIMMED, NOT HIDDEN. A selection that removed its
    // neighbours would hide exactly the context a cross-staff or duplicate
    // judgement needs.
    x.globalAlpha = (!S.sel || isSel) ? 1 : 0.35;
    x.lineWidth = isSel ? 3.5 : 1.5;
    x.strokeStyle = FAMILY_COLOUR[b.family] || '#777';
    x.strokeRect(p[0], p[1], p[2] - p[0], p[3] - p[1]);
    if (isSel) {
      x.strokeStyle = '#111'; x.lineWidth = 1;
      x.setLineDash([3, 3]);
      x.strokeRect(p[0] - 4, p[1] - 4, p[2] - p[0] + 8, p[3] - p[1] + 8);
      x.setLineDash([]);
    }
    if (b.written) {
      x.strokeStyle = '#1b7f3b'; x.lineWidth = 1.5;
      x.strokeRect(p[0] - 2, p[1] - 2, p[2] - p[0] + 4, p[3] - p[1] + 4);
    }
    if (S.layers.human && relabelled.has(b.glyph)) {
      // the OLD class struck through, the human's new one beside it
      x.font = '11px monospace';
      const oldW = x.measureText(b.class).width;
      x.fillStyle = '#777';
      x.fillText(b.class, p[0], p[1] - 4);
      x.strokeStyle = '#777'; x.lineWidth = 1;
      x.beginPath();
      x.moveTo(p[0], p[1] - 7.5); x.lineTo(p[0] + oldW, p[1] - 7.5); x.stroke();
      x.fillStyle = HUMAN;
      x.fillText('→ ' + relabelled.get(b.glyph), p[0] + oldW + 4, p[1] - 4);
      x.strokeStyle = HUMAN; x.lineWidth = 2;
      x.strokeRect(p[0] - 1, p[1] - 1, p[2] - p[0] + 2, p[3] - p[1] + 2);
    }
    if (S.layers.human && owned.has(b.glyph)) {
      x.fillStyle = HUMAN; x.font = '11px monospace';
      x.fillText('⇢ ' + owned.get(b.glyph), p[0], p[3] + 12);
      x.strokeStyle = HUMAN; x.lineWidth = 2;
      x.setLineDash([2, 3]);
      x.strokeRect(p[0] - 1, p[1] - 1, p[2] - p[0] + 2, p[3] - p[1] + 2);
      x.setLineDash([]);
    }
    if (S.layers.human && unsure.has(b.glyph)) {
      x.fillStyle = HUMAN; x.font = 'bold 13px monospace';
      x.fillText('?', p[2] + 3, p[1] + 11);
    }
    if (S.layers.human && (deleted.has(b.glyph) || dup.has(b.glyph))) {
      // ⚠️ THE MACHINE'S BOX STAYS VISIBLE, struck through — a correction is a
      // witness beside the machine's row, never an erasure of it.
      x.strokeStyle = HUMAN; x.lineWidth = 2;
      x.beginPath();
      x.moveTo(p[0], p[1]); x.lineTo(p[2], p[3]);
      x.moveTo(p[2], p[1]); x.lineTo(p[0], p[3]); x.stroke();
    }
    if (S.layers.human && redrawn.has(b.glyph)) {
      const q = boxToCrop(redrawn.get(b.glyph));
      x.strokeStyle = HUMAN; x.lineWidth = 2; x.setLineDash([5, 3]);
      x.strokeRect(q[0], q[1], q[2] - q[0], q[3] - q[1]);
      x.setLineDash([]);
    }
  }
  x.globalAlpha = 1;
  if (S.layers.human) {
    x.strokeStyle = HUMAN; x.lineWidth = 2;
    for (const a of actionsOfKind('add_box')) {
      const p = boxToCrop(a.bbox_page_px);
      x.strokeRect(p[0], p[1], p[2] - p[0], p[3] - p[1]);
      x.fillStyle = HUMAN; x.font = '11px monospace';
      x.fillText(a.category, p[0], p[1] - 3);
    }
  }
  if (S.drag) {
    x.strokeStyle = HUMAN; x.lineWidth = 2; x.setLineDash([4, 3]);
    x.strokeRect(Math.min(S.drag.x0, S.drag.x1), Math.min(S.drag.y0, S.drag.y1),
      Math.abs(S.drag.x1 - S.drag.x0), Math.abs(S.drag.y1 - S.drag.y0));
    x.setLineDash([]);
  }
}
function boxToCrop(b) {
  const a = pageToCrop(b[0], b[1]), c = pageToCrop(b[2], b[3]);
  return [a[0], a[1], c[0], c[1]];
}
function actionsOfKind(kind) {
  return (S.sidecar.actions || []).filter(a => a.kind === kind);
}

// ── canvas interaction ──────────────────────────────────────────────────
function wireCanvas(canvas) {
  const at = e => {
    const r = canvas.getBoundingClientRect();
    const k = canvas.width / r.width;
    return [(e.clientX - r.left) * k, (e.clientY - r.top) * k];
  };
  let down = null;
  canvas.addEventListener('mousedown', e => {
    const [cx, cy] = at(e); down = [cx, cy];
    S.drag = {x0: cx, y0: cy, x1: cx, y1: cy};
  });
  canvas.addEventListener('mousemove', e => {
    if (!down) return;
    const [cx, cy] = at(e); S.drag.x1 = cx; S.drag.y1 = cy; drawCrop();
  });
  window.addEventListener('mouseup', e => {
    if (!down) return;
    const [cx, cy] = at(e);
    const moved = Math.abs(cx - down[0]) > 6 && Math.abs(cy - down[1]) > 6;
    const box = [Math.min(down[0], cx), Math.min(down[1], cy),
                 Math.max(down[0], cx), Math.max(down[1], cy)];
    down = null; S.drag = null;
    if (moved) drawnBox(box); else clickedAt(cx, cy);
    drawCrop();
  });
}

function clickedAt(cx, cy) {
  const [px, py] = cropToPage(cx, cy);
  let best = null;
  for (const b of S.gather.boxes) {
    if (!b.bbox_page_px || !S.layers[b.family]) continue;
    const [x0, y0, x1, y1] = b.bbox_page_px;
    if (px < x0 || px > x1 || py < y0 || py > y1) continue;
    const area = (x1 - x0) * (y1 - y0);
    if (!best || area < best.area) best = {b, area};
  }
  // ⚠️ "this one duplicates THAT one": the second click names the twin, and
  // the row is filed on the box that was SELECTED, never on the twin.
  if (S.dupFor && best) {
    const src = S.dupFor; S.dupFor = null;
    if (best.b.glyph === src.glyph) {
      return toast('a box cannot duplicate itself', true);
    }
    fileLabel(src, 'dup_box', {of: best.b.glyph},
              document.getElementById('labelNote'));
    return;
  }
  showBox(best ? best.b : null);
}

function drawnBox(cropBox) {
  const page = [...cropToPage(cropBox[0], cropBox[1]),
                ...cropToPage(cropBox[2], cropBox[3])];
  if (S.redrawFor) {
    const g = S.redrawFor; S.redrawFor = null;
    openAction({stage: 'gather', kind: 'redraw_box', glyph: g.glyph,
                bbox_page_px: page, prior_bbox_page_px: g.bbox_page_px,
                crop_px: cropBox},
      `Redraw ${g.glyph} (${g.class})`, null);
    return;
  }
  if (!S.addMode) {
    // ⚠️ A DRAG IS NOT A BOX UNLESS HE ASKED FOR ONE. Before the Add tool
    // existed, every stray drag on the crop opened an "add a box" dialog,
    // which is half of what made the page awkward to use.
    return toast('turn on the Add tool to draw a new box');
  }
  addPending(page, cropBox);
}

// ── the Add tool: a pending box, classed BEFORE it is saved ──────────────
// ⚠️⚠️ NOTHING IS WRITTEN UNTIL A CLASS IS CHOSEN. A human box with no name
// is `Q.INK`, which GATHER already files and this tool may not manufacture —
// lane (A) refuses an `add_box` with no `category`, so a viewer that saved
// first and asked later would be writing actions the ingest throws away.
function addPending(page, cropBox) {
  const cell = cellUnder(page);
  S.pendingAdd = {page, cropBox, cell};
  const host = document.getElementById('boxDetail');
  const search = el('input', {type: 'text', id: 'relabelSearch',
    placeholder: 'search the canonical class list…',
    oninput: () => paintPendingList()});
  const note = el('input', {type: 'text', id: 'labelNote',
    placeholder: 'why — in your words (optional)'});
  S.sel = null;
  host.replaceChildren(el('div', {class: 'panel'},
    el('div', {class: 'panelHead'},
      el('b', {}, 'a box the detector missed'),
      el('span', {class: 'grow'}),
      el('button', {class: 'tiny', onclick: () => {
        S.pendingAdd = null; showBox(null);
      }}, 'cancel ⎋')),
    el('dl', {class: 'kv'},
      el('dt', {}, 'page box'), el('dd', {},
        page.map(v => v.toFixed(1)).join(', ')),
      el('dt', {}, 'cell'), el('dd', {}, cell ||
        'inside no single Q.CELL_BOX — LEFT OUT rather than guessed, and '
        + 'lane (A) will refuse the action and say so')),
    el('div', {class: 'lbl', style: 'margin-top:10px'},
      'what is it? (nothing is saved until you choose)'),
    note, search,
    el('div', {id: 'relabelList', class: 'classList'})));
  drawCrop();
  paintPendingList();
}

function paintPendingList() {
  const host = document.getElementById('relabelList');
  if (!host || !S.pendingAdd) return;
  const q = (document.getElementById('relabelSearch').value || '')
    .trim().toLowerCase();
  const kids = [];
  for (const [fam, names] of Object.entries(S.classes.by_family)) {
    const hits = names.filter(n => !q || n.toLowerCase().includes(q));
    if (!hits.length) continue;
    kids.push(el('div', {class: 'famHead'}, fam));
    for (const n of hits.slice(0, 40)) {
      kids.push(el('button', {class: 'classBtn', onclick: async () => {
        const p = S.pendingAdd;
        S.pendingAdd = null;
        try {
          await addAction({stage: 'gather', kind: 'add_box',
                           bbox_page_px: p.page, crop_px: p.cropBox,
                           ...(p.cell ? {cell: p.cell} : {}),
                           category: n,
                           note: (document.getElementById('labelNote') || {})
                                   .value || ''});
          showBox(null);
        } catch (e) { toast(String(e.message || e), true); }
      }}, n));
    }
  }
  host.replaceChildren(...kids);
}

function cellUnder(page) {
  const cx = (page[0] + page[2]) / 2, cy = (page[1] + page[3]) / 2;
  const hits = S.gather.cells.filter(c =>
    cx >= c.box[0] && cx <= c.box[2] && cy >= c.box[1] && cy <= c.box[3]);
  if (hits.length !== 1) return null;
  const p = S.staff.split('/');
  return `cell/${p[1]}/${p[2]}/${p[3]}/${hits[0].index}`;
}

// ═══════════════════════════════════════════════════════════════════════
// THE SELECTION PANEL — ROADMAP 3.4c
//
// Sean, 2026-09-23, after his first minutes on the page: *"it works now but
// the UI is awkward — I need to be able to select a box and re-label it"*,
// and *"and to label boxes as nothing or belongs to another staff etc."*
//
// So the panel asks ONE question — WHAT IS THIS? — and every answer is a
// sidecar action the stages can read. The answers come from `/api/labels`,
// which serves lane (A)'s own table; nothing here knows the list.
// ═══════════════════════════════════════════════════════════════════════

function showBox(b) {
  S.sel = b;
  S.selTrace = null;
  const host = document.getElementById('boxDetail');
  if (!host) return;
  if (!b) {
    host.replaceChildren(el('div', {class: 'tiny dim'},
      'Click a box to select it, or turn on the Add tool and drag a '
      + 'rectangle to add one the detector missed.'));
    drawCrop();
    return;
  }
  host.replaceChildren(boxPanel(b));
  drawCrop();
  // the verdicts already on this box, fetched once per selection
  api('/api/subject', {key: b.glyph}).then(t => {
    if (!S.sel || S.sel.glyph !== b.glyph) return;
    S.selTrace = t;
    const slot = document.getElementById('selVerdicts');
    if (slot) slot.replaceChildren(verdictsOnSelection(t));
  }).catch(e => {
    const slot = document.getElementById('selVerdicts');
    if (slot) slot.replaceChildren(el('div', {class: 'hint bad'},
      String(e.message || e)));
  });
}

function boxPanel(b) {
  const mine = (S.sidecar.actions || []).filter(a => a.glyph === b.glyph);
  return el('div', {class: 'panel'},
    el('div', {class: 'panelHead'},
      el('b', {}, b.class),
      el('span', {class: 'dim tiny'}, '(' + b.category + ')'),
      el('span', {class: 'grow'}),
      el('button', {class: 'tiny', title: 'Esc',
        onclick: () => showBox(null)}, 'deselect ⎋')),
    el('dl', {class: 'kv'},
      el('dt', {}, 'glyph'), el('dd', {}, b.glyph),
      el('dt', {}, 'confidence'), el('dd', {},
        b.conf === null || b.conf === undefined ? '—'
          : Number(b.conf).toFixed(3)),
      el('dt', {}, 'size'), el('dd', {}, b.size_spaces
        // ⚠️ STAFF SPACES, the unit every measured rule is stated in — the
        // notehead width floor is 1.0 SPACES, not 37 px.
        ? b.size_spaces.map(v => v.toFixed(2)).join(' × ') + ' staff spaces'
        : 'DECLINED — this row carries no page rectangle'),
      el('dt', {}, 'bar / cell'), el('dd', {}, `${b.bar ?? '?'} / ${b.cell}`),
      el('dt', {}, 'page box'), el('dd', {},
        b.bbox_page_px ? b.bbox_page_px.map(v => v.toFixed(1)).join(', ')
                       : 'DECLINED — no page rectangle on this row'),
      el('dt', {}, 'export'), el('dd', {},
        b.written ? el('span', {class: 'badge b-written'}, 'written')
          : (b.refused.length
             ? el('span', {class: 'badge b-refused'},
                 'refused: ' + b.refused.join(', '))
             : el('span', {class: 'badge b-absent'}, 'never asked')))),
    mine.length ? el('div', {class: 'hint'},
      'you have already said: '
      + mine.map(a => a.kind + (a.category || a.staff || a.of
          ? ' ' + (a.category || a.staff || a.of) : '')).join(' · ')) : null,
    el('div', {class: 'lbl', style: 'margin-top:12px'}, 'what is this?'),
    labelActions(b),
    el('div', {class: 'lbl', style: 'margin-top:12px'},
      'what the stages already said about it'),
    el('div', {id: 'selVerdicts'}, el('div', {class: 'tiny dim'}, 'loading…')));
}

function labelActions(b) {
  const search = el('input', {type: 'text', id: 'relabelSearch',
    placeholder: 'search the canonical class list…',
    oninput: () => paintClassList(b)});
  const list = el('div', {id: 'relabelList', class: 'classList'});
  const note = el('input', {type: 'text', id: 'labelNote',
    placeholder: 'why — in your words (optional, and the most useful part)'});

  const rows = [];
  for (const entry of (S.labels.labels || [])) {
    if (entry.kind === 'relabel_box') {
      rows.push(el('div', {class: 'labelRow'},
        el('div', {class: 'labelName'}, entry.label,
          el('span', {class: 'key'}, entry.keys)),
        search, list));
      continue;
    }
    if (entry.kind === 'own_box') {
      rows.push(el('div', {class: 'labelRow'},
        el('div', {class: 'labelName'}, entry.label,
          el('span', {class: 'key'}, entry.keys)),
        ownButtons(b, note)));
      continue;
    }
    if (entry.kind === 'dup_box') {
      rows.push(el('div', {class: 'labelRow'},
        el('div', {class: 'labelName'}, entry.label,
          el('span', {class: 'key'}, entry.keys)),
        el('div', {class: 'tiny dim'},
          'click the box it duplicates, then press = there'),
        el('button', {onclick: () => {
          S.dupFor = b;
          toast('now click the box this one duplicates');
        }}, 'pick the twin…')));
      continue;
    }
    rows.push(el('div', {class: 'labelRow'},
      el('button', {class: entry.kind === 'delete_box' ? 'disagree' : '',
        onclick: () => fileLabel(b, entry.kind, {}, note)},
        entry.label, el('span', {class: 'key'}, entry.keys))));
  }
  rows.push(el('div', {class: 'labelRow'},
    el('button', {onclick: () => {
      S.redrawFor = b;
      toast('now drag the rectangle you would have drawn');
    }}, 'Redraw this box', el('span', {class: 'key'}, 'r')),
    el('button', {onclick: () => openSubject(b.glyph)}, 'Trace this glyph')));
  const wrap = el('div', {}, note, ...rows);
  setTimeout(() => paintClassList(b), 0);
  return wrap;
}

function paintClassList(b) {
  const host = document.getElementById('relabelList');
  if (!host) return;
  const q = (document.getElementById('relabelSearch').value || '')
    .trim().toLowerCase();
  const kids = [];
  for (const [fam, names] of Object.entries(S.classes.by_family)) {
    const hits = names.filter(n => !q || n.toLowerCase().includes(q));
    if (!hits.length) continue;
    kids.push(el('div', {class: 'famHead'}, fam));
    for (const n of hits.slice(0, 40)) {
      kids.push(el('button', {
        class: 'classBtn' + (n === b.class ? ' cur' : ''),
        title: n === b.class ? 'the class the detector already gave it' : '',
        onclick: () => fileLabel(b, 'relabel_box', {category: n},
                                 document.getElementById('labelNote'))}, n));
    }
  }
  if (!kids.length) {
    kids.push(el('div', {class: 'tiny dim'},
      'no canonical class matches — the list is the 157 from '
      + '`class_aliases.canonical`, and this tool may not invent a name'));
  }
  host.replaceChildren(...kids);
}

function ownButtons(b, note) {
  const staves = (S.gather.system_staves || []);
  const i = staves.findIndex(r => r.is_this_one);
  const above = i > 0 ? staves[i - 1] : null;
  const below = (i >= 0 && i < staves.length - 1) ? staves[i + 1] : null;
  const pick = el('select', {},
    el('option', {value: ''}, 'another staff of this system…'),
    ...staves.filter(r => !r.is_this_one).map(r => el('option',
      {value: r.staff}, `${r.staff}  ${r.part_name || '(unnamed)'}`)));
  return el('div', {},
    el('div', {style: 'display:flex;gap:6px;flex-wrap:wrap'},
      // ⚠️ ABSENT, NOT DISABLED-AND-LYING: the top staff of a system has no
      // staff above it, and the honest page shows no button rather than one
      // that files a subject the record does not hold.
      above ? el('button', {onclick: () => fileLabel(b, 'own_box',
        {staff: above.staff}, note)},
        '↑ ' + (above.part_name || above.staff),
        el('span', {class: 'key'}, '↑')) : null,
      below ? el('button', {onclick: () => fileLabel(b, 'own_box',
        {staff: below.staff}, note)},
        '↓ ' + (below.part_name || below.staff),
        el('span', {class: 'key'}, '↓')) : null),
    el('div', {style: 'display:flex;gap:6px;margin-top:5px'}, pick,
      el('button', {onclick: () => {
        if (!pick.value) return toast('pick a staff first', true);
        fileLabel(b, 'own_box', {staff: pick.value}, note);
      }}, 'file')),
    (!above && !below) ? el('div', {class: 'tiny dim'},
      'this system has only one staff in the record') : null);
}

async function fileLabel(b, kind, extra, noteEl) {
  try {
    await addAction({stage: 'gather', kind, glyph: b.glyph, ...extra,
                     note: (noteEl && noteEl.value) || ''});
    if (noteEl) noteEl.value = '';
    // ⚠️ THE BOX STAYS SELECTED. He may want to say two things about one
    // box (*not a notehead*, AND *it belongs to the staff below*), and a
    // panel that closed itself would make the second click find nothing.
    const fresh = (S.gather.boxes || []).find(x => x.glyph === b.glyph);
    showBox(fresh || b);
  } catch (e) { toast(String(e.message || e), true); }
}

function verdictsOnSelection(t) {
  const st = t.stages;
  const rows = [];
  for (const name of ['adjudicate', 'evaluate', 'infer']) {
    const bucket = st[name];
    for (const step of bucket.verdicts) {
      rows.push({stage: name, quantity: step.quantity,
                 outcome: step.outcome, value: step.value,
                 reason: step.reason, decider: step.decided_by});
    }
    if (!bucket.verdicts.length) {
      rows.push({stage: name, quantity: '—', outcome: null,
                 value: null,
                 reason: 'DID NOT RUN on this subject (State.ABSENT) — not an '
                         + 'abstention, and it must not be read as one',
                 decider: '—'});
    }
  }
  return el('div', {class: 'scroll', style: 'max-height:240px'},
    el('table', {},
      el('thead', {}, el('tr', {}, ...['stage', 'quantity', 'outcome',
        'value', 'reason'].map(h => el('th', {}, h)))),
      el('tbody', {}, ...rows.map(r => el('tr', {},
        el('td', {class: 'tiny'}, r.stage),
        el('td', {class: 'tiny mono'}, r.quantity),
        el('td', {}, r.outcome ? outcomeBadge(r.outcome)
          : el('span', {class: 'badge b-absent'}, 'none')),
        el('td', {class: 'tiny'}, short(r.value)),
        el('td', {class: 'tiny'}, r.reason || '—'))))));
}

// ── the keyboard ────────────────────────────────────────────────────────
// ⚠️ EVERY BINDING IS A LABEL THE SERVER DECLARES, looked up by `keys` in
// `/api/labels` rather than hard-coded — except Esc, which is not a label.
function wireKeys() {
  window.addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const tag = (e.target.tagName || '').toLowerCase();
    const typing = tag === 'input' || tag === 'textarea' || tag === 'select';
    if (e.key === 'Escape') {
      if (!document.getElementById('modal').classList.contains('hidden')) {
        return closeModal();
      }
      S.redrawFor = null; S.dupFor = null; S.addMode = false;
      showBox(null);
      const t = document.getElementById('addTool');
      if (t) t.checked = false;
      return;
    }
    if (typing || !S.sel || S.view !== 'gather') return;
    const b = S.sel, note = document.getElementById('labelNote');
    const go = (kind, extra) => {
      e.preventDefault(); fileLabel(b, kind, extra || {}, note);
    };
    if (e.key === 'd' || e.key === '0') return go('delete_box');
    if (e.key === 'u') return go('unsure_box');
    if (e.key === 'r') {
      e.preventDefault(); S.redrawFor = b;
      return toast('now drag the rectangle you would have drawn');
    }
    if (e.key === '=') {
      e.preventDefault(); S.dupFor = b;
      return toast('now click the box this one duplicates');
    }
    if (e.key === 'l') {
      e.preventDefault();
      const s = document.getElementById('relabelSearch');
      if (s) { s.focus(); s.select(); }
      return;
    }
    if (e.key === 'n') {
      e.preventDefault();
      if (note) note.focus();
      return;
    }
    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      const staves = (S.gather.system_staves || []);
      const i = staves.findIndex(r => r.is_this_one);
      const t = e.key === 'ArrowUp'
        ? (i > 0 ? staves[i - 1] : null)
        : ((i >= 0 && i < staves.length - 1) ? staves[i + 1] : null);
      if (!t) return toast('this system has no staff that way', true);
      return go('own_box', {staff: t.staff});
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════
// ADJUDICATE / EVALUATE / INFER
// ═══════════════════════════════════════════════════════════════════════
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
        el('td', {class: 'mono'}, r), el('td', {class: 'mono'}, g.env),
        el('td', {}, g.on ? 'ON' : 'off'), el('td', {class: 'mono'}, g.target),
        el('td', {}, String(g.forbids_argmax)))))));
    if (!v.inferences.length) {
      head.appendChild(el('div', {class: 'hint'},
        'REACH ZERO on this staff — no rule wrote anything here. That is a '
        + 'reach of zero, not agreement.'));
    }
    host.replaceChildren(el('div', {class: 'card'},
      el('div', {class: 'h'}, el('b', {}, 'INFER — what is most LIKELY, labelled'),
        el('span', {class: 'mono dim'}, S.staff)),
      el('div', {class: 'b'}, head,
        ...v.inferences.map(step => verdictCard(step, true)))));
    return;
  }

  // staff-level first, then per-cell, then the glyph table
  const glyphTable = el('table', {},
    el('thead', {}, el('tr', {}, ...['glyph', 'class', 'bar',
      'verdicts', 'quantities', 'outcomes', 'export']
      .map(h => el('th', {}, h)))),
    el('tbody', {}, ...v.glyphs.map(g => el('tr', {class: 'click',
      onclick: () => openSubject(g.glyph)},
      el('td', {class: 'mono'}, g.glyph.split('/').slice(4).join('/')),
      el('td', {}, g.class),
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
      el('div', {class: 'h'}, el('b', {}, bucket.subject),
        el('span', {class: 'dim'},
          `${bucket.verdicts.length} verdicts · ${bucket.abstentions.length} abstentions`)),
      el('div', {class: 'b'}, ...kids)));
  }
  for (const c of v.cells) {
    cards.push(el('div', {class: 'card'},
      el('div', {class: 'h'}, el('b', {}, c.subject),
        el('span', {class: 'dim'}, c.verdicts.length + ' verdicts')),
      el('div', {class: 'b'}, ...c.verdicts.map(s => verdictCard(s, false)))));
  }
  host.replaceChildren(
    el('div', {class: 'card'},
      el('div', {class: 'h'},
        el('b', {}, stage.toUpperCase() + (stage === 'adjudicate'
          ? ' — what does this ONE thing mean, on what evidence'
          : ' — what follows NECESSARILY from what we now know')),
        el('span', {class: 'mono dim'}, S.staff)),
      el('div', {class: 'b'},
        el('div', {class: 'lbl'}, 'every glyph on this staff'),
        el('div', {class: 'scroll'}, glyphTable))),
    ...cards);
}

function abstentionCard(a, subject) {
  return el('div', {class: 'card'},
    el('div', {class: 'h'},
      el('span', {class: 'badge b-declined'}, 'abstained'),
      el('b', {class: 'mono'}, a.quantity),
      el('span', {}, 'reason ', el('b', {}, a.reason)),
      el('span', {class: 'dim'}, 'reader ' + (a.reader || '?')
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
        agreeRow({stage: S.view, kind: 'agree', verdict: a.id,
                  quantity: a.quantity, outcome: 'abstained',
                  subject}))));
}

function verdictCard(step, inferred) {
  const rows = (step.rows_read || []);
  const basis = (step.rows_basis || []);
  const sup = step.supersedes;
  return el('div', {class: 'card'},
    el('div', {class: 'h'},
      outcomeBadge(step.outcome),
      inferred ? el('span', {class: 'badge b-inferred'}, 'INFERRED') : null,
      el('b', {class: 'mono'}, step.quantity),
      el('span', {}, '= ', el('b', {}, short(step.value))),
      el('span', {class: 'dim'}, 'reason ', el('b', {}, step.reason || '—')),
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
          el('dt', {}, 'decided_by'), el('dd', {}, step.decided_by),
          step.margin !== null && step.margin !== undefined
            ? el('dt', {}, 'margin') : null,
          step.margin !== null && step.margin !== undefined
            ? el('dd', {}, String(step.margin)) : null),
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
        agreeRow({stage: S.view === 'pick' ? 'adjudicate' : S.view,
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
  return el('div', {class: 'scroll', style: 'max-height:260px'},
    trunc ? el('div', {class: 'hint'},
      `showing the first ${trunc.n_shown} rows — ${trunc.n_more} more are on `
      + 'the verdict and are NOT shown here; the counts above are the whole '
      + 'basis.') : null,
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
        el('td', {class: 'tiny mono'}, r.subject || '—')))),
      rows.length > 200 ? el('tfoot', {}, el('tr', {},
        el('td', {colspan: '6'}, `…${rows.length - 200} more rows`))) : null));
}

function agreeRow(base) {
  const note = el('input', {type: 'text', placeholder: 'why (optional)'});
  const send = kind => async () => {
    try {
      await addAction({...base, kind, note: note.value || ''});
      note.value = '';
    } catch (e) { toast(String(e.message || e), true); }
  };
  return el('div', {class: 'agreeRow'},
    el('button', {class: 'agree', onclick: send('agree')}, 'Agree'),
    el('button', {class: 'disagree', onclick: send('disagree')}, 'Disagree'),
    note);
}

// ═══════════════════════════════════════════════════════════════════════
// EXPORT
// ═══════════════════════════════════════════════════════════════════════
async function renderExport(host) {
  const v = await api('/api/stage', {staff: S.staff, stage: 'export'});
  const heads = v.heads.filter(h => h.is_notehead);
  const rests = v.heads.filter(h => !h.is_notehead);
  const table = el('table', {},
    el('thead', {}, el('tr', {}, ...['glyph', 'class', 'bar', 'state',
      'step', 'alter', 'octave', 'type', 'dots', 'refused', ''].map(
        h => el('th', {}, h)))),
    el('tbody', {}, ...heads.map(h => el('tr', {},
      el('td', {class: 'mono tiny', onclick: () => openSubject(h.glyph),
        style: 'cursor:pointer'}, h.glyph.split('/').slice(4).join('/')),
      el('td', {class: 'tiny'}, h.class),
      el('td', {class: 'num'}, h.bar ?? '—'),
      el('td', {}, el('span', {class: 'badge b-' +
        (h.state === 'written' ? 'written' : h.state === 'refused'
          ? 'refused' : 'absent')}, h.state)),
      el('td', {}, h.note ? (h.note.step ?? '—') : '—'),
      el('td', {}, h.note ? (h.note.alter || '') : ''),
      el('td', {}, h.note ? (h.note.octave ?? '') : ''),
      el('td', {}, h.note ? (h.note.type ?? '') : ''),
      el('td', {class: 'num'}, h.note ? (h.note.dots ?? '') : ''),
      el('td', {class: 'tiny'}, h.refused.join(', ')),
      el('td', {}, el('div', {class: 'agreeRow'},
        el('button', {class: 'agree', onclick: () => addAction(
          {stage: 'export', kind: 'agree', verdict: h.glyph,
           quantity: 'written_note', outcome: h.state, note: ''})}, '✓'),
        el('button', {class: 'disagree', onclick: () => addAction(
          {stage: 'export', kind: 'disagree', verdict: h.glyph,
           quantity: 'written_note', outcome: h.state,
           note: prompt('what is wrong with this head?') || ''})}, '✗')))))));

  const svgHost = el('div', {}, el('div', {class: 'tiny dim'}, 'rendering…'));
  host.replaceChildren(
    el('div', {class: 'card'},
      el('div', {class: 'h'},
        el('b', {}, 'EXPORT — written, or refused under a named bucket'),
        el('span', {class: 'mono dim'}, S.staff),
        el('span', {}, `part ${v.part_id || '—'} (${v.part_name || '?'}), `
          + `measures ${v.measures[0]}–${v.measures[1]}`),
        el('span', {class: 'grow'}),
        el('span', {class: 'dim tiny'},
          `${v.counts.heads_boxed} notehead boxes → `
          + `${v.counts.heads_written} written`)),
      el('div', {class: 'two'},
        el('div', {},
          el('div', {class: 'lbl'}, 'what this stage read'),
          el('div', {class: 'tiny'},
            `${heads.length} notehead rows and ${rests.length} other glyph rows `
            + 'on this staff, with their pitch, duration and ownership verdicts. '
            + 'The refusal ladder is `export._place_notes`\' own — '
            + 'not-a-notehead → whole-rest ink → no pitch → duration → '
            + 'ownership → identity, first test failed wins.'),
          el('div', {class: 'scroll', style: 'margin-top:8px'}, table)),
        el('div', {},
          el('div', {class: 'lbl'}, 'what it decided — our render of these bars'),
          svgHost))));

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

// ═══════════════════════════════════════════════════════════════════════
// the per-subject trace (every stage, one subject)
// ═══════════════════════════════════════════════════════════════════════
async function openSubject(key) {
  const t = await api('/api/subject', {key});
  const st = t.stages;
  const body = el('div', {});
  body.appendChild(el('div', {class: 'tiny dim'},
    `${t.kind} · ${t.n_rows_at_subject} rows at this exact subject`));
  body.appendChild(el('div', {class: 'lbl', style: 'margin-top:10px'},
    'GATHER — ' + st.gather.state));
  body.appendChild(rowsTable([...st.gather.observations.map(o => ({...o, row: 'observation'})),
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
    ' ', st.export.buckets ? st.export.buckets.join(', ') : '',
    st.export.note && typeof st.export.note === 'string'
      ? el('div', {class: 'tiny dim'}, st.export.note) : null,
    st.export.note && typeof st.export.note === 'object'
      ? el('dl', {class: 'kv'}, ...Object.entries(st.export.note).flatMap(
          ([k, v]) => [el('dt', {}, k), el('dd', {}, short(v))])) : null));
  openModalRaw(key, body, null);
}

// ═══════════════════════════════════════════════════════════════════════
// the sidecar
// ═══════════════════════════════════════════════════════════════════════
async function loadSidecar() {
  const r = await api('/api/sidecar', {staff: S.staff});
  S.sidecar = r.sidecar; S.sidecarPath = r.path;
  paintSidecar();
}
function paintSidecar() {
  document.getElementById('sidecarCount').textContent =
    (S.sidecar.actions || []).length;
  document.getElementById('sidecarPath').textContent = S.sidecarPath;
  const host = document.getElementById('sidecarList');
  host.replaceChildren(...(S.sidecar.actions || []).slice().reverse().map(a =>
    el('div', {class: 'act'},
      el('button', {class: 'x', title: 'take this back',
        onclick: () => undo(a.id)}, '×'),
      el('b', {}, a.id), ' ', el('span', {class: 'badge b-' +
        (a.kind === 'agree' ? 'read' : a.kind === 'disagree' ? 'abstained'
          : a.kind === 'unsure_box' ? 'declined' : 'inferred')}, a.kind),
      el('div', {class: 'tiny mono'}, a.stage + ' · '
        + (a.glyph || a.verdict || (a.category || ''))
        + (a.kind === 'relabel_box' ? ' → ' + a.category : '')
        + (a.kind === 'own_box' ? ' ⇢ ' + a.staff : '')
        + (a.kind === 'dup_box' ? ' = ' + a.of : '')),
      a.bbox_page_px ? el('div', {class: 'tiny dim mono'},
        '[' + a.bbox_page_px.map(v => v.toFixed(1)).join(', ') + ']') : null,
      a.note ? el('div', {class: 'tiny'}, '“' + a.note + '”') : null)));
  if (!(S.sidecar.actions || []).length) {
    host.replaceChildren(el('div', {class: 'tiny dim'},
      'Nothing yet. Every action is saved the moment you make it.'));
  }
}
async function addAction(action) {
  const r = await post('/api/sidecar/action', {staff: S.staff, ...action});
  S.sidecar = r.sidecar; S.sidecarPath = r.path;
  paintSidecar(); drawCrop();
  toast('saved ' + r.action.id);
  return r.action;
}
async function undo(id) {
  const r = await post('/api/sidecar/undo', {staff: S.staff, id});
  S.sidecar = r.sidecar; paintSidecar(); drawCrop();
}
async function rerun() {
  const out = document.getElementById('rerunOut');
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
      el('pre', {class: 'tiny', style: 'white-space:pre-wrap;max-height:200px;overflow:auto'},
        (r.stdout || '') + (r.stderr ? '\n[stderr]\n' + r.stderr : '')),
      ...(r.files || []).map(f => el('details', {},
        el('summary', {}, `${f.name} (${f.bytes} bytes)`),
        el('pre', {class: 'tiny', style: 'white-space:pre-wrap;max-height:300px;overflow:auto'},
          f.text || '(binary)'))));
  } catch (e) {
    out.replaceChildren(el('div', {class: 'hint bad'}, String(e.message || e)));
  }
}

// ═══════════════════════════════════════════════════════════════════════
// the modal
// ═══════════════════════════════════════════════════════════════════════
let _modalOk = null;
function openModalRaw(title, body, onOk) {
  document.getElementById('modalTitle').textContent = title;
  document.getElementById('modalBody').replaceChildren(body);
  const ok = document.getElementById('modalOk');
  ok.classList.toggle('hidden', !onOk);
  _modalOk = onOk;
  ok.onclick = async () => {
    if (!_modalOk) return closeModal();
    try { await _modalOk(); closeModal(); }
    catch (e) { toast(String(e.message || e), true); }
  };
  document.getElementById('modal').classList.remove('hidden');
}
function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  _modalOk = null;
}
function openAction(base, title, extra, finish) {
  const note = el('textarea', {placeholder:
    'what you see on the plate, in your words — this is the part a session turns into a fix'});
  openModalRaw(title, el('div', {}, extra || null,
    el('div', {class: 'lbl', style: 'margin-top:10px'}, 'note'), note),
    async () => {
      let a = {...base, note: note.value || ''};
      if (finish) a = finish(a);
      await addAction(a);
    });
}

boot().catch(e => {
  document.getElementById('view').replaceChildren(
    el('div', {class: 'hint bad'}, 'could not start: ' + (e.message || e)));
});
