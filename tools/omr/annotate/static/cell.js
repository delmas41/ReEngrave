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
};

const $ = (id) => document.getElementById(id);
const canvas = $("overlay");
const ctx = canvas.getContext("2d");

// ---------------------------------------------------------------- load -----

async function load() {
  const [cell, verdictRes, classes, cats] = await Promise.all([
    fetch(`/api/cell/${cellId}`).then((r) => r.json()),
    fetch(`/api/cell/${cellId}/verdict`).then((r) => r.json()),
    fetch(`/api/classes`).then((r) => r.json()),
    fetch(`/api/categories`).then((r) => r.json()),
  ]);
  state.cell = cell;
  state.verdict = verdictRes.state;
  state.classes = classes;
  state.classByName = Object.fromEntries(classes.map((c) => [c.name, c]));
  state.categories = cats;

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
};

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
  if (isEmpty) {
    const li = document.createElement("li");
    li.className = "no-detections-hint";
    li.innerHTML = `<em>No detections in this cell.</em><br>
      The model found nothing at conf≥0.25 here (common on first measures,
      tempo-marking rows, or near-empty rests). Press <kbd>Tab</kbd> to
      move on, or click <strong>+ add missed detection</strong> below to
      label anything the model missed.`;
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
    drawBox(h.bbox, COLORS.added, h.id, state.selectedId === h.id, true);
  }
  if (state.mode === "draw-bbox" && state.drawStart && state.drawCur) {
    const x = Math.min(state.drawStart.x, state.drawCur.x);
    const y = Math.min(state.drawStart.y, state.drawCur.y);
    const w = Math.abs(state.drawCur.x - state.drawStart.x);
    const h = Math.abs(state.drawCur.y - state.drawStart.y);
    drawBox({ x, y, w, h }, "#1976d2", "», dragging", true, false, [4, 4]);
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

function applyClassCorrection(className) {
  if (!state.pickerFor) return;
  const cat = state.classByName[className]?.category || "structural";
  if (state.pickerFor.kind === "detection") {
    const { obj } = findItem(state.pickerFor.id);
    if (!obj) return;
    obj.verdict = "WRONG_CATEGORY";
    obj.human_corrected_class = className;
    obj.human_corrected_category = cat;
  } else if (state.pickerFor.kind === "added") {
    const { obj } = findItem(state.pickerFor.id);
    if (!obj) return;
    obj.human_class = className;
    obj.human_category = cat;
  } else if (state.pickerFor.kind === "new") {
    // Create a new added_detection from drawIntent.bbox
    const idx = state.verdict.added_detections.length;
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
  // Auto-advance to next pending detection for keyboard speed.
  if (state.pickerFor === null) {
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

  gridEl.innerHTML = "";
  for (const name of visible) {
    const cls = state.classByName[name];
    if (!cls) continue;
    const tile = document.createElement("div");
    tile.className = "archetype-tile";
    if (!cls.has_archetype) tile.classList.add("no-archetype");
    if (name === currentClass) tile.classList.add("selected");
    // When searching, also show the source category as a small tag so
    // the labeler knows where each match comes from.
    const catTag = state.pickerSearch
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

  // Empty-state message when search returns nothing.
  if (emptyEl) emptyEl.hidden = visible.length > 0;
}

// ---------------------------------------------------------------- draw -----

function enterDrawMode(intent) {
  state.mode = "draw-bbox";
  state.drawIntent = intent;
  state.drawStart = null;
  state.drawCur = null;
  $("overlay-hint").hidden = false;
  $("overlay-hint").textContent =
    intent.kind === "fix-bbox"
      ? "Click and drag on the image to redraw the bbox. Esc to cancel."
      : "Click and drag on the image to draw the new detection's bbox. Esc to cancel.";
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

canvas.addEventListener("mouseup", (evt) => {
  if (state.mode !== "draw-bbox" || !state.drawStart) return;
  state.drawCur = canvasToCanonical(evt);
  const x = Math.min(state.drawStart.x, state.drawCur.x);
  const y = Math.min(state.drawStart.y, state.drawCur.y);
  const w = Math.abs(state.drawCur.x - state.drawStart.x);
  const h = Math.abs(state.drawCur.y - state.drawStart.y);
  if (w < 3 || h < 3) {
    // Too small — likely a click; ignore and stay in draw mode.
    state.drawStart = null;
    state.drawCur = null;
    renderOverlay();
    return;
  }
  const bbox = clampBbox({ x, y, w, h });
  const intent = state.drawIntent;
  exitDrawMode();
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

  const key = evt.key.toLowerCase();
  if (key === "n") { selectAdjacent(1); evt.preventDefault(); return; }
  if (key === "p") { selectAdjacent(-1); evt.preventDefault(); return; }

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
  }
});

function goToCell(id) {
  // Flush save first so we don't lose pending edits.
  if (state.saveState === "idle" && state.saveTimer) {
    clearTimeout(state.saveTimer);
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
