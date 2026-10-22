// Cell-list page. Loads /api/cells once and renders a filterable table.
// Clicking a row navigates to /cells/<cell_id>.

(async () => {
  const tbody = document.getElementById("cell-tbody");
  const summary = document.getElementById("bench-summary");
  const filterStatus = document.getElementById("filter-status");
  const filterSearch = document.getElementById("filter-search");
  const sortOrder = document.getElementById("sort-order");
  const counts = document.getElementById("counts");

  const [bench, cells] = await Promise.all([
    fetch("/api/bench").then((r) => r.json()),
    fetch("/api/cells").then((r) => r.json()),
  ]);

  summary.textContent =
    `${bench.n_cells} cells · ${bench.n_classes} classes · ` +
    (bench.pass_name ? `pass: ${bench.pass_name} · ` : ``) +
    `bench: ${bench.root}`;

  function statusFor(c) {
    if (c.schema_version === "corrupt") return "corrupt";
    if (!c.has_verdict) return "untouched";
    if (c.schema_version === 1) return "schema_v1";
    // "done" = nothing left pending AND the cell has been dealt with — either
    // a decided model detection, a drawn box, or (in a pass) an explicit sweep
    // that found none of this pass's symbols. Without the last clause an
    // inspected-empty cell reads "pending" forever, which is the coverage gap
    // this whole marker closes.
    const inspected = (c.inspected_passes || []).length > 0;
    if (c.n_pending === 0 && (c.n_detections > 0 || c.n_added > 0 || inspected)) {
      return "done";
    }
    if (c.n_decided > 0 || c.n_added > 0 || (c.inspected_passes || []).length) {
      return "in-progress";
    }
    return "pending";
  }

  function rowMatches(c) {
    const status = statusFor(c);
    const want = filterStatus.value;
    if (want === "pending" && c.n_pending === 0) return false;
    if (want === "untouched" && status !== "untouched") return false;
    if (want === "done" && status !== "done") return false;
    if (want === "schema_v1" && status !== "schema_v1") return false;
    const q = filterSearch.value.trim().toLowerCase();
    if (q && !c.cell_id.toLowerCase().includes(q)) return false;
    return true;
  }

  // Queue mode. "What is left for me" on a cell is its pending detections
  // plus the reference hints (notes the reference names that the reading
  // never found — each one is a box the human may have to draw). A cell the
  // pre-fill ABSTAINED on counts every detection as left, because nothing
  // there was decided by anyone. Ties fall back to batch order so the queue
  // is stable between reloads.
  function workLeft(c) {
    const hints = c.n_hints_missing || 0;
    if (c.prefill_status === "abstained") return c.n_detections + hints + 0.5;
    return c.n_pending + hints;
  }

  function ordered() {
    const idx = new Map(cells.map((c, i) => [c.cell_id, i]));
    const mode = sortOrder ? sortOrder.value : "manifest";
    if (mode === "manifest") return cells;
    const key = mode === "hints" ? (c) => c.n_hints || 0 : workLeft;
    return [...cells].sort((a, b) => key(b) - key(a) || idx.get(a.cell_id) - idx.get(b.cell_id));
  }

  function render() {
    tbody.innerHTML = "";
    let shown = 0;
    let totalDecided = 0;
    let totalDetections = 0;
    let totalDone = 0;
    for (const c of ordered()) {
      totalDecided += c.n_decided;
      totalDetections += c.n_detections;
      const status = statusFor(c);
      if (status === "done") totalDone += 1;
      if (!rowMatches(c)) continue;
      shown += 1;
      const tr = document.createElement("tr");
      tr.dataset.cellId = c.cell_id;
      tr.dataset.status = status;
      tr.innerHTML = `
        <td><a href="/cells/${c.cell_id}">${c.cell_id}</a></td>
        <td>${c.source_tag || ""}</td>
        <td>${c.page ?? ""}</td>
        <td>${c.system_index ?? ""}/${c.staff_index ?? ""}/${c.measure_index ?? ""}</td>
        <td>${c.n_detections}</td>
        <td>${c.n_decided}/${c.n_detections}</td>
        <td>${c.n_added}</td>
        <td title="${c.prefill_status ? `pre-fill: ${c.prefill_status}` : `no pre-fill`}">${
          c.prefill_status ? (c.n_hints_missing || 0) : ""
        }${c.prefill_status === "abstained" ? " ⚠" : ""}</td>
        <td><span class="status-badge status-${status}">${status}</span></td>
      `;
      tbody.appendChild(tr);
    }
    const totalAdded = cells.reduce((s, c) => s + c.n_added, 0);
    counts.textContent =
      `showing ${shown}/${cells.length} · ` +
      `${totalDone}/${cells.length} cells done · ${totalAdded} boxes drawn` +
      (totalDetections > 0 ? ` · decided ${totalDecided}/${totalDetections} detections` : ``);
  }

  filterStatus.addEventListener("change", render);
  filterSearch.addEventListener("input", render);
  if (sortOrder) sortOrder.addEventListener("change", render);
  render();
})();
