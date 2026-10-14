"""ROADMAP 2.114 leak guard: 2.112's `leakage_guard.check_leak` for both test sets against the SECOND detector's training mix
(2.110's OLD arm: v1-v4 + v13-v22, read from BOTH roots -- `data/user-labeled-distill25` and `data/user-labeled`; the 2.110 filter only
REMOVED staffless cells, so the unfiltered mix is a superset and the check is conservative).
Test cells are cut by the product cutter (`cut_test_cells.py`, runs/2.114/test-cells/<tag>/): Litolff 984073 idx 1 = Sean's 104 TEST cells
(benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/cells.json), Brahms 317803 idx 0 = every cell of the page.
usage: python3 benchmarks/omr-second-detector-2026-10/leak_check.py [--out leak.json]
Exits 1 if the control cannot fail (the 2.112 audit found 9 same-key Litolff cells; finding none means the guard is looking at the wrong thing)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import leakage_guard as G

REPO = Path.cwd()
CUT = REPO / "runs/2.114/test-cells"


def test_cells(tag, edition, page, keep=None):
    meta = json.loads((CUT / tag / "cells.json").read_text())
    out = []
    for m in meta:
        k = (m["system_index"], m["staff_index"], m["measure_index"])
        if keep is not None and k not in keep:
            continue
        out.append(G.Cell(f"{tag}/{m['cell_id']}", CUT / tag / f"{m['cell_id']}.png", (edition, page, *k), "test", m["staff_line_ys_canonical"]))
    return out


def mix():
    d25, lab = G.MAIN / "data/user-labeled-distill25", G.MAIN / "data/user-labeled"
    vs = [l.strip() for l in (d25 / "catalog-versions.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
    cells = []
    for root in (d25, lab):
        for v in vs:
            cells += G.load_version(root, v)
    return vs, cells


def main():
    keep = {(r["system_index"], r["staff_index"], r["measure_index"])
            for r in json.loads((REPO / "benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/cells.json").read_text())}
    lit = test_cells("litolff984073_p1", "imslp984073", 1, keep)
    bra = test_cells("brahms317803_p0", "imslp317803", 0)
    vs, train = mix()
    print(f"mix: {len(vs)} versions {vs}; {len(train)} training cells (both roots); test: litolff {len(lit)} cells (of {len(keep)} in cells.json), brahms {len(bra)} cells")
    res = {"versions": vs, "train_cells": len(train)}
    for name, t in (("litolff", lit), ("brahms", bra)):
        r = G.check_leak(t, train)
        res[name] = {"test_cells": len(t), "exact": len(r["exact"]), "key": len(r["key"]), "near": len(r["near"]),
                     "key_cells": sorted({b for a, b in r["key"]}), "near_pairs": r["near"][:40], "exact_pairs": r["exact"]}
        print(f"[{name}] exact {len(r['exact'])}  same-key {len(r['key'])}  near>=0.90 {len(r['near'])}   leaked test cells (by key): {len(set(b for a, b in r['key']))}")
    if len(sys.argv) > 2 and sys.argv[1] == "--out":
        Path(sys.argv[2]).write_text(json.dumps(res, indent=1, default=str))
    if res["litolff"]["key"] == 0:
        print("CONTROL FAILED: the 2.112 audit found 9 same-key cells on Litolff idx 1; the guard found none")
        sys.exit(1)


main()
