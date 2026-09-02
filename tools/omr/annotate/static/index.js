// Cell-list page. Loads /api/cells once and renders a filterable table.
// Clicking a row navigates to /cells/<cell_id>.

(async () => {
  const tbody = document.getElementById("cell-tbody");
  const summary = document.getElementById("bench-summary");
  const filterStatus = document.getElementById("filter-status");
  const filterSearch = document.getElementById("filter-search");
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

  function render() {
    tbody.innerHTML = "";
    let shown = 0;
    let totalDecided = 0;
    let totalDetections = 0;
    let totalDone = 0;
    for (const c of cells) {
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
  render();
})();
