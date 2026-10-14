"""ROADMAP 2.112 audit: every TEST set a verdict was judged on  x  every labelled training version.
Reads manifests / label dirs / records only.  python3 benchmarks/omr-test-leakage-2026-10/audit.py  -> leakage_audit.json"""
import json, re, sys, os
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import leakage_guard as g

REPO = g.REPO; MAIN = g.MAIN; HERE = Path(__file__).parent
ED = {"litolff": "imslp984073", "brahms": "imslp317803", "dvorak": "imslp405841", "schumann": None, "tchaikovsky": None}

# ---------------- training versions -------------------------------------------------------------
ROOTS = {"UL": MAIN / "data" / "user-labeled", "D25": MAIN / "data" / "user-labeled-distill25"}
D25_CAT = [l.strip() for l in (ROOTS["D25"] / "catalog-versions.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
UL_CAT = [l.strip() for l in (ROOTS["UL"] / "catalog-versions.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
HOLLOW_FT = ["v1-2026-05-18-orchestral", "v2-2026-06-08-beet5", "v3-2026-06-09-mahler5", "v4-2026-06-10-la-mer",
             "v7-2026-09-02-hollow", "v8-2026-09-02-hollow2-5pub"]   # weights-lineage.json: hollow-ft-2026-09-03 corpus
ROLE = {}  # version -> where it was trained
for v in D25_CAT: ROLE.setdefault(v, []).append("PRODUCTION scan graft features (distill25 mix, epoch0)")
for v in HOLLOW_FT: ROLE.setdefault(v, []).append("hollow-ft-2026-09-03 (teacher; production class rows)")
ROLE["v24-2026-10-13-hollow4-train"] = ["2.4b/2.110 arms only (not admitted)"]
ROLE["v23-2026-09-04-arcs-reconcile"] = ["experiment corpus (arcs); not admitted"]
for v in ("v5-2026-07-12-clef", "v6-2026-07-13-clef-diverse"): ROLE[v] = ["clef fine-tune (weights rejected, never deployed)"]
for v in ("v9-2026-09-03-hollow3-mahler1", "v10-2026-09-03-hollow3-elgar1", "v11-2026-09-03-hollow3-lamer", "v12-2026-09-03-hollow3-tchaikovsky1-lowres"):
    ROLE[v] = ["superseded by v19-v21 / ablation only; not in shipped weights"]

def training():
    T = {}
    for r, root in ROOTS.items():
        for vd in sorted(root.glob("v*-*")):
            if (vd / "images").is_dir():
                T[(r, vd.name)] = g.load_version(root, vd.name)
    return T

# ---------------- test sets ---------------------------------------------------------------------
def tile_cells(doc):
    t = json.load(open(REPO / "benchmarks/acceptance/judged-tiles.json"))["tiles"]
    keys = set(); pages = Counter()
    for x in t:
        if x["doc"] != doc or not x["subject"]: continue
        p = x["subject"].split("/")
        n = [int(a) for a in p[1:5]]
        keys.add((ED[doc], n[0], n[1], n[2], n[3])); pages[n[0]] += 1
    return keys, pages

def cells_from_manifest_rows(rows):
    return {(g.edition_key(r["pdf"]), int(r["page"]), r["system_index"], r["staff_index"], r["measure_index"]) for r in rows}

def build_tests():
    T = {}
    rows = json.load(open(REPO / "benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/cells.json"))
    T["TS1 Litolff 984073 idx1 hollow4 TEST (104 cells, 59 hand heads)"] = {"cells": cells_from_manifest_rows(rows), "heads": 59}
    hp = json.load(open(REPO / "data/hand-truth/pages/imslp317803/0.json"))
    T["TS2 Brahms 317803 idx0 hand truth (202 cells, 1352 boxes)"] = {"cells": {("imslp317803", 0, c["system"], c["staff"], c["measure"]) for c in hp["cells"] if c["kind"] == "measure"}, "boxes": 1352}
    T["TS3 Litolff 984073 idx1 WHOLE page (beet5-p1: GATE/SHIP hollow-payoff page, 12 staves)"] = {"pages": {("imslp984073", 1)}}
    ho = json.load(open(REPO / "data/hand-truth/held-out.json"))["pages"]
    T["TS4 held-out.json pages (Brahms 0,1; Litolff 2,3; Simrock 4)"] = {"pages": {(p["edition"], p["pdf_page_index"]) for p in ho}}
    sr = json.load(open(REPO / "data/hand-truth/INVENTORY.json"))["structure_truth"]
    T["TS5 20-row scan gate / structure-truth pages (Beethoven x2 editions, Brahms 0-3, Dvorak9 4-6, Mahler local 1-4, Bach)"] = {"pages": {(r["edition"] or "mahler--symphony-5--unidentified-scan-2016--local", r["pdf_page_index"]) for r in sr}}
    p25 = json.load(open(REPO / "benchmarks/omr-phase2.5/cells.json")); p25 = p25 if isinstance(p25, list) else p25["cells"]
    T["TS6 omr-phase2.5 '30 held-out dense cells' (forgetting axis + class-inventory screen)"] = {"cells": cells_from_manifest_rows(p25)}
    hr = json.load(open(REPO / "benchmarks/omr-labeling-survey-2026-09/held_out_rests.json"))["cells"]
    mi = g.manifest_index()
    T["TS7 held_out_rests (35 cells held out of the rest-specialist corpus; WITHDRAWN round 6)"] = {"cells": {g.key_of(c["cell_id"]) for c in hr if g.key_of(c["cell_id"])}}
    for doc, nm in (("litolff", "TS8 blind tiles Litolff"), ("brahms", "TS9 blind tiles Brahms")):
        k, pg = tile_cells(doc)
        T[f"{nm} (Sean-judged, {sum(pg.values())} tiles, pages {sorted(pg)})"] = {"cells": k}
    return T

def main():
    train = training(); tests = build_tests()
    tkeys = {}
    for (r, v), cells in train.items():
        d = defaultdict(list)
        for c in cells:
            if c.key: d[c.key].append(c.name)
        tkeys[(r, v)] = d
    out = {"training": {}, "matrix": {}}
    for (r, v), cells in train.items():
        pg = Counter(c.key[:2] for c in cells if c.key)
        out["training"][f"{r}/{v}"] = {"cells": len(cells), "unplaced_cells": sum(1 for c in cells if not c.key), "pages": len(pg),
                                       "role": ROLE.get(v, ["not in any recorded training run (on disk only)"])}
    for tn, ts in tests.items():
        row = {}
        tpages = ts.get("pages") or {k[:2] for k in ts["cells"]}
        for (r, v), d in tkeys.items():
            if "cells" in ts:
                cell_hits = sorted(k for k in ts["cells"] if k in d)
                page_hits = sum(len(l) for k, l in d.items() if k[:2] in tpages)
                if cell_hits or page_hits:
                    row[f"{r}/{v}"] = {"same_cell_key": len(cell_hits), "train_cells_on_test_pages": page_hits, "keys": [list(k) for k in cell_hits][:40]}
            else:
                n = sum(len(l) for k, l in d.items() if k[:2] in tpages)
                if n: row[f"{r}/{v}"] = {"train_cells_on_test_pages": n, "by_page": dict(Counter(f"{k[0]}:{k[1]}" for k, l in d.items() for _ in l if k[:2] in tpages))}
        out["matrix"][tn] = {"n_cells": len(ts.get("cells", [])), "n_pages": len(tpages), "overlaps": row}
    (HERE / "leakage_audit.json").write_text(json.dumps(out, indent=1))
    for tn, m in out["matrix"].items():
        print("\n" + tn, "| cells", m["n_cells"], "pages", m["n_pages"])
        for v, o in m["overlaps"].items():
            print("   ", v[:60].ljust(60), {k: v2 for k, v2 in o.items() if k not in ("keys",)})

if __name__ == "__main__":
    main()


def twins():
    """Litolff Beethoven 5 exists as two DIFFERENT scans (984073, 575951); structure_truth pairs 984073 idx p with 575951 idx p-1
    (same bars).  A training cell on one scan is the same engraved plate as a test page of the other (not a pixel/key match)."""
    tr = training(); res = {}
    gate = {"imslp984073": {1, 2, 3, 4}, "imslp575951": {0, 1, 2, 3}}
    for (r, v), cells in tr.items():
        if r != "D25": continue
        n = Counter()
        for c in cells:
            if not c.key: continue
            ed, pg = c.key[:2]
            if ed == "imslp984073" and (pg - 1) in gate["imslp575951"]: n[f"trained 984073:{pg} -> gate row 575951:{pg-1}"] += 1
            if ed == "imslp575951" and (pg + 1) in gate["imslp984073"]: n[f"trained 575951:{pg} -> gate row 984073:{pg+1}"] += 1
        if n: res[v] = dict(n)
    return res

if __name__ == "__main__":
    t = twins(); print("\nTWIN-SCAN (same plate, other scan):", json.dumps(t, indent=1))
    j = json.loads((HERE / "leakage_audit.json").read_text()); j["twin_scan"] = t
    (HERE / "leakage_audit.json").write_text(json.dumps(j, indent=1))
