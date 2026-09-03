/*
 * Cell labeling page.
 *
 * State machine: state.cell, state.verdict, state.classes, state.categories.
 * The verdict is autosaved 1.2s after the last edit (debounced).
 *
 * Modes:
 *   normal      — clicking a bbox selects it; verdict buttons act on it.
 *   draw-bbox   — click-drag on the canvas to draw a new bbox; releases
 *                 either commit (if drawing for a Fix-bbox) or open the
 *                 picker (if drawing for "add missed detection").
 *
 * No build step: plain ES2017+ for evergreen browsers.
 */
"use strict";

const cellId = window.location.pathname.split("/").pop();

const state = {
  cell: null,            // /api/cell/<id> payload (no detections — comes via verdict)
  verdict: null,         // schema_v2 state
  classes: [],           // list of {name, category, archetype_url, has_archetype}
  classByName: {},
  categories: null,      // {order: [], members: {...}}
  selectedId: null,      // detection id ("D0" or "H0") or null
  pickerOpen: false,
  pickerTab: null,
  pickerFor: null,       // {kind: "detection"|"added"|"new", id?: string}
  pickerSearch: "",      // free-text filter applied across ALL categories
  mode: "normal",        // "normal" | "draw-bbox"
  drawIntent: null,      // {kind: "fix-bbox"|"add-missed", id?: string}
  drawStart: null,       // {x, y} in canonical coords
  drawCur: null,
  imageEl: null,         // the loaded HTMLImageElement
  scale: 1.0,            // canvas pixel per canonical pixel
  saveTimer: null,
  saveState: "idle",     // "idle"|"saving"|"saved"|"error"
  // Single-symbol pass mode. `pass` is /api/pass; inactive on any bench with
  // no batch_config.json, and then every branch below falls through to the
  // behavior that was here before.
  pass: null,
  passSlot: 0,           // index of the active palette slot (number keys)
  passOverride: false,   // escape hatch — full catalog, normal picker
};

const $ = (id) => document.getElementById(id);
const canvas = $("overlay");
const ctx = canvas.getContext("2d");

// ---------------------------------------------------------------- load -----

async function load() {
  const [cell, verdictRes, classes, cats, passCfg] = await Promise.all([
    fetch(`/api/cell/${cellId}`).then((r) => r.json()),
    fetch(`/api/cell/${cellId}/verdict`).then((r) => r.json()),
    fetch(`/api/classes`).then((r) => r.json()),
    fetch(`/api/categories`).then((r) => r.json()),
    fetch(`/api/pass`).then((r) => r.json()).catch(() => ({ active: false })),
  ]);
  state.cell = cell;
  state.verdict = verdictRes.state;
  state.classes = classes;
  state.classByName = Object.fromEntries(classes.map((c) => [c.name, c]));
  state.categories = cats;
  state.pass = passCfg && passCfg.active ? passCfg : null;
  renderPassBar();

  $("cell-title").textContent = cell.cell.cell_id;
  // Position breadcrumb — tells the labeler where on the page they are
  const samePage = cell.page_cells || [];
  const meIdx = samePage.findIndex((c) => c.is_current);
  $("cell-meta").innerHTML =
    `<span class="bc-overall">${cell.index + 1}/${cell.total}</span>` +
    ` · <span class="bc-source">${cell.cell.source_tag}</span>` +
    ` · <span class="bc-page">p${cell.cell.page}</span>` +
    ` · <span class="bc-system">sys${cell.cell.system_index}</span>` +
    ` · <span class="bc-staff">staff${cell.cell.staff_index}</span>` +
    ` · <span class="bc-measure">m${cell.cell.measure_index}` +
    (meIdx >= 0 ? ` (cell ${meIdx + 1}/${samePage.length} on page)` : "") +
    `</span>` +
    ` · <span class="bc-source-file muted">${verdictRes.source}</span>`;
  $("btn-prev").disabled = !cell.prev_id;
  $("btn-next").disabled = !cell.next_id;
  renderPageCellStrip(cell);

  await loadImage();
  renderDetectionList();
  renderHintsPanel();
  renderOverlay();
  selectFirstPending();
}

function loadImage() {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      state.imageEl = img;
      sizeCanvas();
      resolve();
    };
    img.src = `/api/cell/${cellId}/image`;
  });
}

function sizeCanvas() {
  const img = state.imageEl;
  if (!img) return;
  // Fit the image into the available vertical space; preserve aspect.
  const wrap = $("overlay-wrap");
  const maxH = wrap.clientHeight - 28;
  const maxW = wrap.clientWidth - 28;
  const scale = Math.min(maxH / img.naturalHeight, maxW / img.naturalWidth, 1.5);
  state.scale = scale;
  canvas.width = Math.round(img.naturalWidth * scale);
  canvas.height = Math.round(img.naturalHeight * scale);
}

// ------------------------------------------------------------ pass mode ----
//
// A pass restricts the palette to the symbol kind this sweep is for. With no
// batch_config.json on the bench, `state.pass` stays null and every helper
// here answers false, so the rest of the file behaves exactly as before.

// Is the restricted palette in force right now? False while the labeler has
// deliberately escaped to the full class list.
function passActive() {
  return !!state.pass && !state.passOverride;
}

function activeSlot() {
  if (!state.pass) return null;
  return state.pass.slots[state.passSlot] || null;
}

// Every class name the pass palette can produce (both halves of any pair).
function passClassNames() {
  if (!state.pass) return [];
  return state.pass.slots.flatMap((s) => s.classes.map((c) => c.name));
}

// Which slot owns a class — used to re-derive a variant when a box moves.
function slotForClass(className) {
  if (!state.pass) return null;
  return state.pass.slots.find((s) =>
    s.classes.some((c) => c.name === className)) || null;
}

function slotIsPair(slot) {
  return !!slot && slot.kind === "staff_position_pair";
}

// on_line / in_space, for the overlay tag and color. Only consulted in a
// pass, so a non-pass bench draws added boxes exactly as it always did.
function variantOf(className) {
  if (!className) return null;
  if (className.endsWith("OnLine")) return "on_line";
  if (className.endsWith("InSpace")) return "in_space";
  return null;
}

function renderPassBar() {
  const bar = $("pass-bar");
  if (!bar) return;
  if (!state.pass) {
    bar.hidden = true;
    return;
  }
  bar.hidden = false;
  bar.classList.toggle("overridden", state.passOverride);
  bar.innerHTML = "";

  const name = document.createElement("span");
  name.className = "pass-name";
  name.textContent = state.passOverride
    ? `all classes (pass: ${state.pass.pass_name})`
    : `pass · ${state.pass.pass_name}`;
  bar.appendChild(name);

  // Feedback on revisit: has THIS cell already been swept by this pass? The
  // sweep is recorded on the way out, so a first visit shows nothing and a
  // return shows the tick — the labeler can see a cell is already counted
  // and does not need re-checking.
  if (state.verdict && Array.isArray(state.verdict.inspected_passes)
      && state.verdict.inspected_passes.includes(state.pass.pass_name)) {
    const swept = document.createElement("span");
    swept.className = "pass-swept";
    swept.textContent = "✓ swept";
    swept.title = "This cell has already been inspected for this pass.";
    bar.appendChild(swept);
  }

  if (!state.passOverride) {
    state.pass.slots.forEach((slot, i) => {
      const chip = document.createElement("button");
      chip.className = "pass-slot" + (i === state.passSlot ? " active" : "");
      const clickable = slot.click_box ? " · click" : "";
      chip.innerHTML =
        (state.pass.slots.length > 1
          ? `<span class="slot-key">${i + 1}</span>` : "") +
        `<span>${slot.label}</span>` +
        `<span class="slot-click">${clickable}</span>`;
      chip.title = slot.classes.map((c) => c.name).join(" / ");
      chip.addEventListener("click", () => selectSlot(i));
      bar.appendChild(chip);
    });
    const hint = document.createElement("span");
    hint.className = "pass-hint";
    const slot = activeSlot();
    hint.textContent = slot && slot.click_box
      ? "a → draw mode · click places a sized box · drag for a custom one"
      : "a → draw mode · drag a box; the class is assigned for you";
    bar.appendChild(hint);
  } else {
    const note = document.createElement("span");
    note.className = "pass-note";
    note.textContent = "full picker — boxes are NOT auto-assigned";
    bar.appendChild(note);
  }

  const esc = document.createElement("button");
  esc.className = "pass-escape";
  esc.textContent = state.passOverride
    ? `↩ back to “${state.pass.pass_name}”`
    : "⋯ all classes";
  esc.title = "Leave the restricted palette for one-off oddities";
  esc.addEventListener("click", togglePassOverride);
  bar.appendChild(esc);
}

function togglePassOverride() {
  state.passOverride = !state.passOverride;
  renderPassBar();
  if (state.pickerOpen) renderPicker();
  renderOverlay();
}

function selectSlot(i) {
  if (!state.pass || !state.pass.slots[i]) return;
  state.passSlot = i;
  renderPassBar();
  if (state.pickerOpen) renderPicker();
}

// Ask the server which class this y lands on. The staff grid lives in Python
// (tools/omr/annotate/server.py:snap_to_staff) so the tested code is the code
// that runs — the browser holds no second copy of the arithmetic.
async function snapAt(x, y, slotIndex) {
  try {
    const r = await fetch(
      `/api/cell/${cellId}/snap?x=${encodeURIComponent(x)}` +
      `&y=${encodeURIComponent(y)}&slot=${slotIndex}`);
    if (!r.ok) return null;
    const j = await r.json();
    return j.available ? j : null;
  } catch (e) {
    console.error("snap failed", e);
    return null;
  }
}

// Commit a box the pass assigned itself: no picker, no scrolling.
function addPassBox(bbox, className) {
  const cat = state.classByName[className]?.category || "notehead";
  const newId = `H${nextHId()}`;
  state.verdict.added_detections.push({
    id: newId,
    human_class: className,
    human_category: cat,
    bbox,
    notes: "",
  });
  state.selectedId = newId;
  markDirty();
  renderDetectionList();
  renderOverlay();
  renderDetail();
}

// A plain CLICK in a click-box slot: place a box of the class's own measured
// size, centered on the staff position the click snaps to.
async function placeClickBox(pt) {
  const slot = activeSlot();
  if (!slot || !slot.click_box) return false;
  const snap = await snapAt(pt.x, pt.y, slot.index);
  if (!snap || !snap.bbox) return false;
  addPassBox(clampBbox(snap.bbox), snap.class.name);
  return true;
}

// Move or resize a box that was already drawn. Model detections have had
// this since the start (Fix-bbox); drawn boxes had only delete-and-redraw,
// which is not good enough once geometry is choosing the class for you — a
// mis-snapped variant has to be nudgeable.
//
// Moving it across the staff grid RE-DERIVES the variant, so the class keeps
// matching where the box actually sits. Only within its own pass slot: a box
// whose class the pass does not own keeps the class it has.
async function reboxAdded(id, bbox, clickPt) {
  const { kind, obj } = findItem(id);
  if (kind !== "added" || !obj) return;
  const slot = slotForClass(obj.human_class);
  if (clickPt) {
    // Click-to-replace: same sized box, new position.
    if (!slot || !slot.click_box) return;
    const snap = await snapAt(clickPt.x, clickPt.y, slot.index);
    if (!snap || !snap.bbox) return;
    obj.bbox = clampBbox(snap.bbox);
    if (slotIsPair(slot)) obj.human_class = snap.class.name;
  } else {
    obj.bbox = bbox;
    if (slotIsPair(slot)) {
      const snap = await snapAt(bbox.x + bbox.w / 2, bbox.y + bbox.h / 2,
                                slot.index);
      if (snap) obj.human_class = snap.class.name;
    }
  }
  obj.human_category = state.classByName[obj.human_class]?.category
    || obj.human_category;
  markDirty();
  renderDetectionList();
  renderOverlay();
  renderDetail();
}

// A DRAG in a pass: the labeler chose the box, the geometry chooses the
// variant (for a pair) from where the box's center sits.
async function commitPassDrag(bbox) {
  const slot = activeSlot();
  if (!slot) return false;
  let className = slot.classes[0].name;
  if (slotIsPair(slot)) {
    const snap = await snapAt(bbox.x + bbox.w / 2, bbox.y + bbox.h / 2,
                              slot.index);
    if (snap) className = snap.class.name;
  }
  addPassBox(bbox, className);
  return true;
}

// ---------------------------------------------------------------- render ----

function verdictClass(v) {
  if (!v) return "v-pending";
  return `v-${v}`;
}

const COLORS = {
  TP: "#2e7d32",
  FP: "#b00020",
  WRONG_CATEGORY: "#e67e22",
  WRONG_BBOX: "#8e24aa",
  unsure: "#555",
  null: "#888",
  added: "#1976d2",
  // Staff-position variants get their own colors in a pass, so a mis-snapped
  // box is visible on the image rather than only in the sidebar.
  added_on_line: "#1976d2",
  added_in_space: "#00897b",
};

// Label an added box in a pass with the variant the geometry chose.
function addedBoxStyle(h) {
  if (!state.pass) return { color: COLORS.added, label: h.id };
  const v = variantOf(h.human_class);
  if (v === "on_line") return { color: COLORS.added_on_line, label: `${h.id} ·line` };
  if (v === "in_space") return { color: COLORS.added_in_space, label: `${h.id} ·space` };
  return { color: COLORS.added, label: h.id };
}

function renderDetectionList() {
  const ul = $("detection-ul");
  ul.innerHTML = "";
  for (const d of state.verdict.detections) {
    const li = document.createElement("li");
    li.dataset.id = d.id;
    li.classList.add(verdictClass(d.verdict));
    if (state.selectedId === d.id) li.classList.add("selected");
    const cls = d.human_corrected_class || d.model_predicted_class || "?";
    const verdict = d.verdict || "pending";
    li.innerHTML = `<span>${d.id} ${cls}</span><span class="vbadge">${verdict}</span>`;
    li.addEventListener("click", () => selectDetection(d.id));
    ul.appendChild(li);
  }
  // Helpful hint if the model found no detections in this cell.
  const isEmpty = state.verdict.detections.length === 0
    && state.verdict.added_detections.length === 0;
  if (isEmpty && passActive()) {
    const slot = activeSlot();
    const li = document.createElement("li");
    li.className = "no-detections-hint";
    li.innerHTML = `<em>${state.pass.pass_name} — nothing drawn yet.</em><br>
      Press <kbd>a</kbd>, then ` +
      (slot && slot.click_box
        ? `<strong>click each ${slot.label}</strong> — the box is sized and
           classed for you`
        : `<strong>drag a box around each ${slot ? slot.label : "one"}</strong>`) +
      `. <kbd>Esc</kbd> stops, <kbd>Tab</kbd> goes to the next cell.
       Only this pass's symbols belong here; the rest of the cell is another
       pass's job.`;
    ul.appendChild(li);
  } else if (isEmpty) {
    const li = document.createElement("li");
    li.className = "no-detections-hint";
    li.innerHTML = `<em>No detections — draw them in.</em><br>
      Press <kbd>a</kbd> (or click <strong>+ add missed detection</strong>) to
      draw a box around each element and label it; the UI stays in draw mode
      so you can keep going. <kbd>Esc</kbd> stops, <kbd>Tab</kbd> goes to the
      next cell. <kbd>Del</kbd> removes the selected box. Anything you don't
      draw is treated as background.`;
    ul.appendChild(li);
  }
  $("det-count").textContent =
    `(${state.verdict.detections.filter((d) => d.verdict).length}/${state.verdict.detections.length})`;

  const aul = $("added-ul");
  aul.innerHTML = "";
  for (const h of state.verdict.added_detections) {
    const li = document.createElement("li");
    li.dataset.id = h.id;
    li.classList.add("v-WRONG_CATEGORY");  // reuse the orange/added color
    if (state.selectedId === h.id) li.classList.add("selected");
    li.innerHTML = `<span>${h.id} ${h.human_class || "?"}</span><span class="vbadge">added</span>`;
    li.addEventListener("click", () => selectDetection(h.id));
    aul.appendChild(li);
  }
  $("added-count").textContent = `(${state.verdict.added_detections.length})`;
}

function renderOverlay() {
  const img = state.imageEl;
  if (!img) return;
  const s = state.scale;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  for (const d of state.verdict.detections) {
    const b = d.human_bbox || d.model_bbox;
    if (!b) continue;
    drawBox(b, COLORS[d.verdict || "null"], d.id, state.selectedId === d.id);
  }
  for (const h of state.verdict.added_detections) {
    const style = addedBoxStyle(h);
    drawBox(h.bbox, style.color, style.label, state.selectedId === h.id, true);
  }
  renderHintsOverlay();
  if (state.mode === "draw-bbox" && state.drawStart && state.drawCur) {
    const x = Math.min(state.drawStart.x, state.drawCur.x);
    const y = Math.min(state.drawStart.y, state.drawCur.y);
    const w = Math.abs(state.drawCur.x - state.drawStart.x);
    const h = Math.abs(state.drawCur.y - state.drawStart.y);
    drawBox({ x, y, w, h }, "#1976d2", "», dragging", true, false, [4, 4]);
  }
}

// ---------------------------------------------------------------- hints ---
//
// Ghost markers from the reference-driven pre-fill (`mxl_verdicts`). A
// "missing" hint says the reference has a note here that the reading never
// found — its pitch and value are known, its x is ESTIMATED from the
// neighbours, so the marker is a dotted outline and a name, never a box the
// converter would export. An "extra" hint marks a note the reading found
// that the reference does not contain. Neither is a label; the human still
// draws or decides. Toggle with `h`.

const HINT_COLORS = { missing: "#8e6c00", extra: "#9e9e9e" };

function hintsFor() {
  const pre = state.cell && state.cell.prefill;
  return pre && Array.isArray(pre.hints) ? pre.hints : [];
}

function renderHintsOverlay() {
  if (state.hideHints) return;
  const s = state.scale;
  for (const h of hintsFor()) {
    const b = h.bbox;
    if (!b) continue;
    const color = HINT_COLORS[h.kind] || "#888";
    const cx = (b.x + b.w / 2) * s;
    const cy = (b.y + b.h / 2) * s;
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([2, 3]);
    if (h.kind === "missing") {
      // An ellipse the size of a notehead, at the staff position the pitch
      // names — the y is exact, the x is a guess and the dashes say so.
      ctx.beginPath();
      ctx.ellipse(cx, cy, Math.max(4, (b.w / 2) * s), Math.max(3, (b.h / 2) * s), 0, 0, Math.PI * 2);
      ctx.stroke();
    } else {
      ctx.beginPath();
      ctx.moveTo(cx - 6, cy - 6); ctx.lineTo(cx + 6, cy + 6);
      ctx.moveTo(cx + 6, cy - 6); ctx.lineTo(cx - 6, cy + 6);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.font = "10px ui-monospace, monospace";
    ctx.fillStyle = color;
    ctx.fillText(`? ${h.label}`, b.x * s, Math.max(10, b.y * s - 3));
    ctx.restore();
  }
}

function renderHintsPanel() {
  const panel = $("hints-panel");
  const ul = $("hints-ul");
  if (!panel || !ul) return;
  const pre = state.cell && state.cell.prefill;
  const hints = hintsFor();
  if (!pre) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const head = $("hints-head");
  if (head) {
    const al = pre.alignment || {};
    const meas = pre.measure_number != null ? `m${pre.measure_number} · ` : "";
    head.textContent =
      `${meas}${pre.status}` +
      (pre.reason ? ` — ${pre.reason}` : "") +
      (al.matched != null ? ` · matched ${al.matched}/${Math.max(al.n_truth || 0, al.n_pred || 0)}` : "") +
      (pre.n_tp || pre.n_wrong_category
        ? ` · confirmed ${pre.n_tp || 0}, relabelled ${pre.n_wrong_category || 0}` : "");
  }
  ul.innerHTML = "";
  for (const h of hints) {
    const li = document.createElement("li");
    li.className = `hint hint-${h.kind}`;
    li.textContent = (h.kind === "missing" ? "missing: " : "extra: ") + h.label +
      (h.class ? ` (${h.class})` : "") + (h.x_estimated ? " · x approx." : "");
    ul.appendChild(li);
  }
  if (!hints.length) {
    const li = document.createElement("li");
    li.className = "muted";
    li.textContent = "nothing missing, nothing extra";
    ul.appendChild(li);
  }
}

function drawBox(b, color, label, selected = false, dashed = false, dashPat = null) {
  const s = state.scale;
  ctx.lineWidth = selected ? 2.5 : 1.2;
  ctx.strokeStyle = color;
  ctx.setLineDash(dashed ? (dashPat || [3, 3]) : []);
  ctx.strokeRect(b.x * s + 0.5, b.y * s + 0.5, b.w * s, b.h * s);
  ctx.setLineDash([]);
  if (selected) {
    ctx.fillStyle = color + "33";
    ctx.fillRect(b.x * s, b.y * s, b.w * s, b.h * s);
  }
  if (label) {
    const lx = b.x * s;
    const ly = b.y * s - 2;
    ctx.font = "10px ui-monospace, monospace";
    ctx.fillStyle = color;
    ctx.fillText(label, lx, Math.max(10, ly));
  }
}

// ---------------------------------------------------------------- detail ---

function findItem(id) {
  if (!id) return { kind: null, obj: null };
  for (const d of state.verdict.detections) {
    if (d.id === id) return { kind: "detection", obj: d };
  }
  for (const h of state.verdict.added_detections) {
    if (h.id === id) return { kind: "added", obj: h };
  }
  return { kind: null, obj: null };
}

function selectDetection(id) {
  state.selectedId = id;
  state.pickerOpen = false;
  $("picker").hidden = true;
  renderDetectionList();
  renderOverlay();
  renderDetail();
}

function selectFirstPending() {
  const pend = state.verdict.detections.find((d) => !d.verdict);
  if (pend) {
    selectDetection(pend.id);
  } else if (state.verdict.detections.length) {
    selectDetection(state.verdict.detections[0].id);
  }
}

function selectAdjacent(delta) {
  const flat = [
    ...state.verdict.detections.map((d) => d.id),
    ...state.verdict.added_detections.map((h) => h.id),
  ];
  if (!flat.length) return;
  let idx = flat.indexOf(state.selectedId);
  if (idx === -1) idx = 0;
  idx = (idx + delta + flat.length) % flat.length;
  selectDetection(flat[idx]);
}

function renderDetail() {
  const { kind, obj } = findItem(state.selectedId);
  if (!obj) {
    $("empty-detail").hidden = false;
    $("detail").hidden = true;
    return;
  }
  $("empty-detail").hidden = true;
  $("detail").hidden = false;

  if (kind === "detection") {
    $("detail-id").textContent = `${obj.id} (model: ${obj.model_predicted_class || "?"})`;
    $("d-model-class").textContent = obj.model_predicted_class || "?";
    $("d-model-cat").textContent = obj.model_predicted_category || "?";
    $("d-conf").textContent = obj.confidence?.toFixed(3) ?? "—";
    $("d-verdict").textContent = obj.verdict || "(pending)";
    $("d-corrected").textContent = obj.human_corrected_class || "—";
    $("d-notes").value = obj.notes || "";
    const bb = obj.human_bbox || obj.model_bbox;
    setCrop(bb);
    document.querySelectorAll(".verdict-buttons button").forEach((b) => {
      b.classList.toggle("active", b.dataset.verdict === obj.verdict);
    });
  } else if (kind === "added") {
    $("detail-id").textContent = `${obj.id} (human-added)`;
    $("d-model-class").textContent = "(human-added)";
    $("d-model-cat").textContent = obj.human_category || "?";
    $("d-conf").textContent = "—";
    $("d-verdict").textContent = "added";
    $("d-corrected").textContent = obj.human_class || "?";
    $("d-notes").value = obj.notes || "";
    setCrop(obj.bbox);
    document.querySelectorAll(".verdict-buttons button").forEach((b) => {
      b.classList.toggle("active", false);
    });
  }
}

function setCrop(bb) {
  if (!bb || bb.w <= 0 || bb.h <= 0) {
    $("crop").src = "";
    return;
  }
  $("crop").src =
    `/api/cell/${cellId}/crop?x=${bb.x}&y=${bb.y}&w=${bb.w}&h=${bb.h}&pad=24`;
}

// ---------------------------------------------------------------- mutation -

function setVerdict(id, verdict) {
  const { kind, obj } = findItem(id);
  if (!obj || kind !== "detection") return;
  obj.verdict = verdict;
  if (verdict !== "WRONG_CATEGORY") {
    obj.human_corrected_class = null;
    obj.human_corrected_category = null;
  }
  if (verdict !== "WRONG_BBOX") {
    obj.human_bbox = null;
  }
  markDirty();
  renderDetectionList();
  renderOverlay();
  renderDetail();
}

function deleteSelected() {
  const id = state.selectedId;
  if (!id) return;
  const { kind, obj } = findItem(id);
  if (kind === "added") {
    const i = state.verdict.added_detections.findIndex((h) => h.id === id);
    if (i >= 0) state.verdict.added_detections.splice(i, 1);
  } else if (kind === "detection" && obj) {
    // Can't remove a model detection — reset its verdict back to pending.
    obj.verdict = null;
    obj.human_corrected_class = null;
    obj.human_corrected_category = null;
    obj.human_bbox = null;
  } else {
    return;
  }
  state.selectedId = null;
  markDirty();
  renderDetectionList();
  renderOverlay();
  renderDetail();
}

function applyClassCorrection(className) {
  if (!state.pickerFor) return;
  const forKind = state.pickerFor.kind;
  const cat = state.classByName[className]?.category || "structural";
  if (forKind === "detection") {
    const { obj } = findItem(state.pickerFor.id);
    if (!obj) return;
    obj.verdict = "WRONG_CATEGORY";
    obj.human_corrected_class = className;
    obj.human_corrected_category = cat;
  } else if (forKind === "added") {
    const { obj } = findItem(state.pickerFor.id);
    if (!obj) return;
    obj.human_class = className;
    obj.human_category = cat;
  } else if (forKind === "new") {
    // Create a new added_detection from the freshly-drawn bbox.
    const newId = `H${nextHId()}`;
    state.verdict.added_detections.push({
      id: newId,
      human_class: className,
      human_category: cat,
      bbox: state.pickerFor.bbox,
      notes: "",
    });
    state.selectedId = newId;
  }
  state.pickerOpen = false;
  state.pickerFor = null;
  $("picker").hidden = true;
  markDirty();
  renderDetectionList();
  renderOverlay();
  renderDetail();
  if (forKind === "new") {
    // Rapid-draw loop: jump straight back into draw mode for the next
    // element so you can label a whole measure without re-clicking. Esc stops.
    enterDrawMode({ kind: "add-missed" });
  } else {
    // Auto-advance to next pending detection for keyboard speed.
    advanceToNextPending();
  }
}

function nextHId() {
  // Find the highest existing H<n> and add 1.
  let max = -1;
  for (const h of state.verdict.added_detections) {
    const m = /^H(\d+)$/.exec(h.id);
    if (m) max = Math.max(max, parseInt(m[1], 10));
  }
  return max + 1;
}

function advanceToNextPending() {
  const cur = state.verdict.detections.findIndex((d) => d.id === state.selectedId);
  for (let i = cur + 1; i < state.verdict.detections.length; i++) {
    if (!state.verdict.detections[i].verdict) {
      selectDetection(state.verdict.detections[i].id);
      return;
    }
  }
  // Wrap to start
  for (let i = 0; i <= cur && i < state.verdict.detections.length; i++) {
    if (!state.verdict.detections[i].verdict) {
      selectDetection(state.verdict.detections[i].id);
      return;
    }
  }
}

// ---------------------------------------------------------------- picker ---

function openPicker(forKind, forId, hint) {
  state.pickerOpen = true;
  state.pickerFor = { kind: forKind, id: forId };
  if (hint && hint.bbox) state.pickerFor.bbox = hint.bbox;
  // When the picker opens for a freshly-drawn "add missed detection" box,
  // there's no selected detection yet — so #detail is still hidden, and
  // the picker (which is nested inside #detail) would be invisible. Force
  // the right panel open in that case.
  if (forKind === "new") {
    $("empty-detail").hidden = true;
    $("detail").hidden = false;
  }
  $("picker").hidden = false;
  if (!state.pickerTab) state.pickerTab = state.categories.order[0];
  renderPicker();
}

function closePicker() {
  state.pickerOpen = false;
  state.pickerFor = null;
  state.pickerSearch = "";  // reset filter so next open is clean
  const inp = $("picker-search-input");
  if (inp) inp.value = "";
  $("picker").hidden = true;
}

function renderPicker() {
  const tabsEl = $("picker-tabs");
  const gridEl = $("picker-grid");
  const emptyEl = $("picker-empty");
  const searchInput = $("picker-search-input");
  const escapeEl = $("picker-escape");

  // In a pass the palette is just this sweep's classes: no tabs to choose
  // between and nothing to search through. The escape hatch is a button.
  const restricted = passActive();
  const searchRow = document.querySelector(".picker-search");
  if (tabsEl) tabsEl.hidden = restricted;
  if (searchRow) searchRow.hidden = restricted;
  if (escapeEl) escapeEl.hidden = !state.pass;
  if (restricted) {
    const names = passClassNames();
    let currentClass = null;
    const { obj } = findItem(state.pickerFor?.id);
    if (obj) currentClass = obj.human_corrected_class || obj.human_class
      || obj.model_predicted_class;
    renderPickerTiles(gridEl, names, currentClass, false);
    if (emptyEl) emptyEl.hidden = names.length > 0;
    return;
  }

  // Reflect current search value in the input (in case it was set
  // programmatically by openPicker or hotkey).
  if (searchInput && searchInput.value !== state.pickerSearch) {
    searchInput.value = state.pickerSearch;
  }

  // Tabs: render as before, but visually dim them when a search is
  // active (since search overrides the tab filter).
  tabsEl.innerHTML = "";
  state.categories.order.forEach((cat, i) => {
    const b = document.createElement("button");
    b.textContent = `${i + 1}. ${cat}`;
    if (cat === state.pickerTab) b.classList.add("active");
    if (state.pickerSearch) b.classList.add("dimmed");
    b.addEventListener("click", () => {
      state.pickerTab = cat;
      // Clicking a tab clears search — the labeler likely wants to
      // browse within the chosen tab again.
      state.pickerSearch = "";
      renderPicker();
    });
    tabsEl.appendChild(b);
  });

  // Decide what's displayed:
  //   - If a search query is non-empty, show ALL classes (across every
  //     category) whose name contains the query (case-insensitive).
  //   - Else, show the members of the currently selected category tab.
  let visible;
  if (state.pickerSearch) {
    const q = state.pickerSearch.toLowerCase();
    visible = state.classes
      .filter((c) => c.name.toLowerCase().includes(q))
      .map((c) => c.name);
  } else {
    visible = state.categories.members[state.pickerTab] || [];
  }

  // What class is currently set on the detection? Highlight its tile.
  let currentClass = null;
  if (state.pickerFor?.kind === "detection") {
    const { obj } = findItem(state.pickerFor.id);
    currentClass = obj?.human_corrected_class || obj?.model_predicted_class;
  } else if (state.pickerFor?.kind === "added") {
    const { obj } = findItem(state.pickerFor.id);
    currentClass = obj?.human_class;
  }

  renderPickerTiles(gridEl, visible, currentClass, !!state.pickerSearch);

  // Empty-state message when search returns nothing.
  if (emptyEl) emptyEl.hidden = visible.length > 0;
}

function renderPickerTiles(gridEl, names, currentClass, showCatTag) {
  gridEl.innerHTML = "";
  for (const name of names) {
    const cls = state.classByName[name];
    if (!cls) continue;
    const tile = document.createElement("div");
    tile.className = "archetype-tile";
    if (!cls.has_archetype) tile.classList.add("no-archetype");
    if (name === currentClass) tile.classList.add("selected");
    // When searching, also show the source category as a small tag so
    // the labeler knows where each match comes from.
    const catTag = showCatTag
      ? `<div class="cat-tag">${cls.category || "?"}</div>`
      : "";
    tile.innerHTML = `
      <img src="${cls.archetype_url || ""}" alt="${name}">
      <div class="name">${name}</div>
      ${catTag}
    `;
    tile.addEventListener("click", () => applyClassCorrection(name));
    gridEl.appendChild(tile);
  }
}

// ---------------------------------------------------------------- draw -----

function enterDrawMode(intent) {
  state.mode = "draw-bbox";
  state.drawIntent = intent;
  state.drawStart = null;
  state.drawCur = null;
  $("overlay-hint").hidden = false;
  const slot = passActive() ? activeSlot() : null;
  if (intent.kind === "fix-bbox" || intent.kind === "fix-added-bbox") {
    $("overlay-hint").textContent =
      slot && slot.click_box && intent.kind === "fix-added-bbox"
        ? "Click to move the box, or drag to resize it. Esc to cancel."
        : "Click and drag on the image to redraw the bbox. Esc to cancel.";
  } else if (slot) {
    $("overlay-hint").textContent = slot.click_box
      ? `${slot.label}: click each one (or drag for a custom box). Esc stops.`
      : `${slot.label}: drag a box around each one. Esc stops.`;
  } else {
    $("overlay-hint").textContent =
      "Click and drag on the image to draw the new detection's bbox. Esc to cancel.";
  }
  document.querySelector(".col-overlay").classList.add("drawing");
  canvas.focus();
}

function exitDrawMode() {
  state.mode = "normal";
  state.drawIntent = null;
  state.drawStart = null;
  state.drawCur = null;
  $("overlay-hint").hidden = true;
  document.querySelector(".col-overlay").classList.remove("drawing");
  renderOverlay();
}

function canvasToCanonical(evt) {
  const rect = canvas.getBoundingClientRect();
  const x = (evt.clientX - rect.left) / state.scale;
  const y = (evt.clientY - rect.top) / state.scale;
  return { x: Math.round(x), y: Math.round(y) };
}

function clampBbox(b) {
  const img = state.imageEl;
  const x = Math.max(0, Math.min(b.x, img.naturalWidth - 1));
  const y = Math.max(0, Math.min(b.y, img.naturalHeight - 1));
  const w = Math.max(1, Math.min(b.w, img.naturalWidth - x));
  const h = Math.max(1, Math.min(b.h, img.naturalHeight - y));
  return { x, y, w, h };
}

canvas.addEventListener("mousedown", (evt) => {
  const p = canvasToCanonical(evt);
  if (state.mode === "draw-bbox") {
    state.drawStart = p;
    state.drawCur = p;
    renderOverlay();
    return;
  }
  // Normal: click to select the topmost detection under the point
  let hit = null;
  for (const d of state.verdict.detections) {
    const b = d.human_bbox || d.model_bbox;
    if (b && p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h) {
      hit = d.id;
    }
  }
  for (const h of state.verdict.added_detections) {
    const b = h.bbox;
    if (b && p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h) {
      hit = h.id;
    }
  }
  if (hit) selectDetection(hit);
});

canvas.addEventListener("mousemove", (evt) => {
  if (state.mode === "draw-bbox" && state.drawStart) {
    state.drawCur = canvasToCanonical(evt);
    renderOverlay();
  }
});

canvas.addEventListener("mouseup", async (evt) => {
  if (state.mode !== "draw-bbox" || !state.drawStart) return;
  state.drawCur = canvasToCanonical(evt);
  const x = Math.min(state.drawStart.x, state.drawCur.x);
  const y = Math.min(state.drawStart.y, state.drawCur.y);
  const w = Math.abs(state.drawCur.x - state.drawStart.x);
  const h = Math.abs(state.drawCur.y - state.drawStart.y);
  if (w < 3 || h < 3) {
    // A click, not a drag. In a click-box pass that IS the label: one click
    // places a correctly-sized box on the staff position it snaps to, and
    // draw mode stays on for the next one. Otherwise (as before) ignore it.
    const clickPt = state.drawStart;
    const clickIntent = state.drawIntent;
    state.drawStart = null;
    state.drawCur = null;
    if (passActive() && activeSlot()?.click_box) {
      if (clickIntent.kind === "add-missed") {
        await placeClickBox(clickPt);
        renderOverlay();
        return;
      }
      if (clickIntent.kind === "fix-added-bbox") {
        exitDrawMode();
        await reboxAdded(clickIntent.id, null, clickPt);
        return;
      }
    }
    renderOverlay();
    return;
  }
  const bbox = clampBbox({ x, y, w, h });
  const intent = state.drawIntent;
  exitDrawMode();
  if (intent.kind === "fix-added-bbox") {
    await reboxAdded(intent.id, bbox, null);
    return;
  }
  if (intent.kind === "add-missed" && passActive()) {
    // A drag in a pass is still auto-assigned — the labeler chose the box,
    // not the class.
    await commitPassDrag(bbox);
    enterDrawMode({ kind: "add-missed" });
    return;
  }
  if (intent.kind === "fix-bbox") {
    const { obj } = findItem(intent.id);
    if (obj) {
      // For "fix-bbox", we set verdict=WRONG_BBOX and store the new bbox;
      // the class stays the model's prediction unless the labeler also
      // hits Fix-class afterward.
      obj.verdict = "WRONG_BBOX";
      obj.human_bbox = bbox;
      markDirty();
      renderDetectionList();
      renderOverlay();
      renderDetail();
    }
  } else if (intent.kind === "add-missed") {
    openPicker("new", null, { bbox });
  }
});

// ---------------------------------------------------------------- save ----

function markDirty() {
  setSaveState("idle");
  if (state.saveTimer) clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(save, 1200);
}

function setSaveState(s) {
  state.saveState = s;
  const el = $("save-indicator");
  el.className = "save-indicator " + s;
  const labels = { idle: "idle", saving: "saving…", saved: "saved", error: "ERROR" };
  el.textContent = labels[s] || s;
}

async function save() {
  setSaveState("saving");
  try {
    const r = await fetch(`/api/cell/${cellId}/verdict`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(state.verdict),
    });
    if (!r.ok) {
      const err = await r.text();
      console.error("save failed:", err);
      setSaveState("error");
      return;
    }
    setSaveState("saved");
  } catch (e) {
    console.error(e);
    setSaveState("error");
  }
}

// ---------------------------------------------------------------- hotkeys --

document.addEventListener("keydown", (evt) => {
  // Skip if user is typing in a text field
  if (evt.target.tagName === "TEXTAREA" || evt.target.tagName === "INPUT") return;

  if (evt.key === "Escape") {
    if (state.mode === "draw-bbox") {
      exitDrawMode();
      return;
    }
    if (state.pickerOpen) {
      closePicker();
      return;
    }
    // Also close the page-context overlay on Esc
    const pcOverlay = document.getElementById("page-context-overlay");
    if (pcOverlay && !pcOverlay.hidden) {
      hidePageContext();
      return;
    }
  }

  if (state.pickerOpen) {
    // In a restricted pass the numbers pick the CLASS, not a category tab —
    // there are no tabs, and the palette is short enough to be numbered.
    if (passActive()) {
      const k = parseInt(evt.key, 10);
      const names = passClassNames();
      if (!isNaN(k) && k >= 1 && k <= names.length) {
        applyClassCorrection(names[k - 1]);
        evt.preventDefault();
      }
      return;
    }
    // "/" → focus the search box. Works whether the picker is open via a
    // detection-fix-class flow or a draw-new flow.
    if (evt.key === "/") {
      const inp = $("picker-search-input");
      if (inp) {
        inp.focus();
        inp.select();
        evt.preventDefault();
      }
      return;
    }
    // Number keys jump tabs while the picker is open
    const n = parseInt(evt.key, 10);
    if (!isNaN(n) && n >= 1 && n <= state.categories.order.length) {
      // If a search filter is active, clearing it is more intuitive than
      // re-rendering both the tab + the filter (since search overrides tabs).
      state.pickerSearch = "";
      const inp = $("picker-search-input");
      if (inp) inp.value = "";
      state.pickerTab = state.categories.order[n - 1];
      renderPicker();
      evt.preventDefault();
      return;
    }
    return;
  }

  if (evt.key === "Tab") {
    evt.preventDefault();
    if (evt.shiftKey) {
      if (state.cell.prev_id) goToCell(state.cell.prev_id);
    } else {
      if (state.cell.next_id) goToCell(state.cell.next_id);
    }
    return;
  }

  // System / staff navigation within the same page:
  //   ] = next system on same page (different system_index)
  //   [ = prev system on same page
  //   } = next staff group on same page (different system_index or staff_index)
  //   { = prev staff group on same page
  if (evt.key === "]") {
    if (state.cell.next_system_id) { goToCell(state.cell.next_system_id); evt.preventDefault(); return; }
  }
  if (evt.key === "[") {
    if (state.cell.prev_system_id) { goToCell(state.cell.prev_system_id); evt.preventDefault(); return; }
  }
  if (evt.key === "}") {
    if (state.cell.next_staff_id) { goToCell(state.cell.next_staff_id); evt.preventDefault(); return; }
  }
  if (evt.key === "{") {
    if (state.cell.prev_staff_id) { goToCell(state.cell.prev_staff_id); evt.preventDefault(); return; }
  }

  // Delete / Backspace → remove the selected drawn box (or clear a model
  // detection's verdict back to pending).
  if (evt.key === "Delete" || evt.key === "Backspace") {
    if (state.selectedId) { deleteSelected(); evt.preventDefault(); return; }
  }

  // Number keys select the pass slot (1..n) while the picker is closed —
  // "which symbol am I drawing now". Nothing bound them before pass mode.
  if (passActive() && state.pass.slots.length > 1) {
    const k = parseInt(evt.key, 10);
    if (!isNaN(k) && k >= 1 && k <= state.pass.slots.length) {
      selectSlot(k - 1);
      evt.preventDefault();
      return;
    }
  }

  const key = evt.key.toLowerCase();
  if (key === "n") { selectAdjacent(1); evt.preventDefault(); return; }
  if (key === "p") { selectAdjacent(-1); evt.preventDefault(); return; }

  // "a" → draw a brand-new ground-truth box (no selection needed). After the
  // class is picked the UI re-enters draw mode so you can keep drawing.
  if (key === "a") { enterDrawMode({ kind: "add-missed" }); evt.preventDefault(); return; }

  if (!state.selectedId) return;
  const { kind } = findItem(state.selectedId);

  if (key === "t" && kind === "detection") {
    setVerdict(state.selectedId, "TP");
    advanceToNextPending();
    evt.preventDefault();
  } else if (key === "f" && kind === "detection") {
    setVerdict(state.selectedId, "FP");
    advanceToNextPending();
    evt.preventDefault();
  } else if (key === "h") {
    // Reference hints on/off. They are markers, not boxes; hiding them never
    // changes the verdict.
    state.hideHints = !state.hideHints;
    renderOverlay();
  } else if (key === "u" && kind === "detection") {
    setVerdict(state.selectedId, "unsure");
    advanceToNextPending();
    evt.preventDefault();
  } else if (key === "c") {
    openPicker(kind, state.selectedId);
    evt.preventDefault();
  } else if (key === "b" && kind === "detection") {
    enterDrawMode({ kind: "fix-bbox", id: state.selectedId });
    evt.preventDefault();
  } else if (key === "b" && kind === "added") {
    // Redraw a box you drew. In a pair slot the variant re-derives from
    // wherever the new box lands.
    enterDrawMode({ kind: "fix-added-bbox", id: state.selectedId });
    evt.preventDefault();
  }
});

// Record that the current pass has SWEPT this cell. Returns whether it added
// anything, so the caller knows a save is now owed. A no-op off a pass bench,
// so non-pass navigation still writes nothing it did not already.
//
// Stamped on the way OUT, not on open: it means "looked and moved on", which
// is the signal a single-symbol sweep produces on a cell holding none of its
// symbols — and it is what makes 48/48-inspected provable from the verdicts
// dir instead of one file per drawn cell. Gated on `state.pass` (a config
// exists), not passActive(): the escape hatch is a within-pass UI state, and
// the cell was still inspected for this pass.
function stampInspectedForPass() {
  if (!state.pass || !state.verdict) return false;
  const name = state.pass.pass_name;
  if (!Array.isArray(state.verdict.inspected_passes)) {
    state.verdict.inspected_passes = [];
  }
  if (state.verdict.inspected_passes.includes(name)) return false;
  state.verdict.inspected_passes.push(name);
  return true;
}

function goToCell(id) {
  // Stamp the sweep, then flush anything owed before the full-page reload —
  // a stamp or a pending debounced edit must reach disk or it is lost.
  const stamped = stampInspectedForPass();
  const hadTimer = state.saveTimer != null;
  if (state.saveTimer) { clearTimeout(state.saveTimer); state.saveTimer = null; }
  if (stamped || hadTimer) {
    save().finally(() => {
      window.location.href = `/cells/${id}`;
    });
  } else {
    window.location.href = `/cells/${id}`;
  }
}

// ---------------------------------------------------------------- wire ----

// Render a horizontal strip of all cells on the current page so the
// labeler can see where they are and jump between same-page cells with
// a click. Strip is grouped visually by (system, staff).
function renderPageCellStrip(cell) {
  const strip = document.getElementById("page-cell-strip");
  if (!strip) return;
  const cells = cell.page_cells || [];
  if (cells.length <= 1) {
    strip.hidden = true;
    return;
  }
  strip.hidden = false;
  strip.innerHTML = "";
  // Group by (system_index, staff_index) so visually consecutive cells
  // from the same staff line cluster together.
  let lastGroup = null;
  for (const c of cells) {
    const groupKey = `s${c.system_index}-${c.staff_index}`;
    if (groupKey !== lastGroup) {
      const sep = document.createElement("span");
      sep.className = "page-strip-sep";
      sep.textContent = `sys${c.system_index}.staff${c.staff_index}:`;
      strip.appendChild(sep);
      lastGroup = groupKey;
    }
    const chip = document.createElement("a");
    chip.className = "page-strip-chip" + (c.is_current ? " current" : "");
    chip.textContent = `m${c.measure_index}`;
    chip.href = `/cells/${encodeURIComponent(c.cell_id)}`;
    chip.title = c.cell_id;
    chip.addEventListener("click", (evt) => {
      evt.preventDefault();
      goToCell(c.cell_id);
    });
    strip.appendChild(chip);
  }
}

$("btn-prev").addEventListener("click", () => state.cell?.prev_id && goToCell(state.cell.prev_id));
$("btn-next").addEventListener("click", () => state.cell?.next_id && goToCell(state.cell.next_id));
$("btn-add-fn").addEventListener("click", () => {
  enterDrawMode({ kind: "add-missed" });
});
$("picker-close").addEventListener("click", closePicker);
$("picker-escape-btn")?.addEventListener("click", togglePassOverride);

// Picker search — type to filter archetypes across every category.
(function wirePickerSearch() {
  const input = $("picker-search-input");
  const clear = $("picker-search-clear");
  if (!input) return;
  input.addEventListener("input", (evt) => {
    state.pickerSearch = evt.target.value.trim();
    renderPicker();
  });
  // Esc inside the search input: clear it (don't close the whole picker).
  input.addEventListener("keydown", (evt) => {
    if (evt.key === "Escape") {
      if (state.pickerSearch) {
        state.pickerSearch = "";
        input.value = "";
        renderPicker();
        evt.preventDefault();
        evt.stopPropagation();
      } else {
        input.blur();
      }
    }
  });
  clear.addEventListener("click", () => {
    state.pickerSearch = "";
    input.value = "";
    input.focus();
    renderPicker();
  });
})();

// Page-context overlay: clicking the topbar button reveals the rendered
// source PDF page in a right-side sidebar so the labeler can see the
// musical context that the cropped cell may have stripped away.
function showPageContext() {
  // The cell ID lives at state.cell.cell.cell_id — state.cell IS the full
  // /api/cell/{id} response, which wraps the cell entry under a `cell` key.
  const cid = state.cell?.cell?.cell_id || cellId;
  if (!cid) return;
  const overlay = $("page-context-overlay");
  const img = $("page-context-img");
  const title = $("page-context-title");
  const btn = $("btn-show-page");
  img.src = `/api/cell/${encodeURIComponent(cid)}/page`;
  title.textContent = `Source page · ${cid}`;
  overlay.hidden = false;
  btn.classList.add("active");
}
function hidePageContext() {
  $("page-context-overlay").hidden = true;
  $("btn-show-page").classList.remove("active");
}
$("btn-show-page").addEventListener("click", () => {
  const overlay = $("page-context-overlay");
  if (overlay.hidden) showPageContext();
  else hidePageContext();
});
$("page-context-close").addEventListener("click", hidePageContext);

document.querySelectorAll(".verdict-buttons button").forEach((b) => {
  b.addEventListener("click", () => {
    if (!state.selectedId) return;
    const { kind } = findItem(state.selectedId);
    const v = b.dataset.verdict;
    if (v === "WRONG_CATEGORY") {
      openPicker(kind, state.selectedId);
    } else if (v === "WRONG_BBOX") {
      if (kind === "detection") {
        enterDrawMode({ kind: "fix-bbox", id: state.selectedId });
      } else if (kind === "added") {
        enterDrawMode({ kind: "fix-added-bbox", id: state.selectedId });
      }
    } else {
      setVerdict(state.selectedId, v);
      advanceToNextPending();
    }
  });
});

$("d-notes").addEventListener("input", (evt) => {
  const { obj } = findItem(state.selectedId);
  if (!obj) return;
  obj.notes = evt.target.value;
  markDirty();
});

window.addEventListener("resize", () => {
  sizeCanvas();
  renderOverlay();
});

load().catch((err) => {
  console.error(err);
  $("cell-title").textContent = "ERROR: " + err.message;
});
