"""ROADMAP 2.4b step 3 -- build Sean's hollow-head labelling batch from a pool of CUT cells.

    # 1. cut a pool (machine time; same cutter as hollow2: random sample, the PIPELINE's own padding)
    python3 benchmarks/omr-labeling-hollow2-2026-09/cut_candidate_cells.py \
        --out-dir out/hollow4-pool --plan "tag=PDF:PAGE1:N,..." --dpi 600
    # 2. score + detect + select (this file)
    python3 benchmarks/omr-labeling-hollow4-2026-10/build_batch.py --pool out/hollow4-pool \
        --out benchmarks/omr-labeling-hollow4-2026-10/batch --keep 96

What it does, per pooled cell: runs the PRODUCTION scan weights at conf 0.10 and counts hollow-class boxes (and any
notehead-class boxes), then keeps cells in three strata (`--keep` total):
  DETECTED   (~55%) production draws a hollow-class box at >= 0.10 -- real heads, and the bars around them
  NEIGHBOUR  (~35%) a same-staff adjacent bar of a DETECTED cell -- where a head beside a found one is missed
  EMPTY      (~10%) notehead boxes but no hollow box -- so "nothing here" is a real label
Round-robin across editions. `--blind` (used for both batches) writes EMPTY detection files: Sean draws every head himself.
`--test-page` keeps every cell of the pooled page holding any notehead-sized counter or notehead box (the TEST batch).
The 5 held-out hand-truth pages are refused; the gate page (Litolff idx 1) is refused except with --test-page.
The hollow2 `hollow_score` ranker is NOT used to select: it failed its print check (beam gaps, flag holes, ff bowls).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "omr-labeling-hollow2-2026-09"))

from hollow_score import score_cell  # noqa: E402

REPO = Path.cwd()
PROD = REPO / "omr-weights" / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
HOLLOW = ("noteheadHalfOnLine", "noteheadHalfInSpace", "noteheadWholeOnLine", "noteheadWholeInSpace",
          "noteheadHalfOnLineSmall", "noteheadHalfInSpaceSmall", "noteheadWhole")

#: (imslp id, 0-based pdf page) the plan reserves as TEST truth -- never labelled for training.
#: `data/hand-truth/held-out.json` is the source; this is read from it, plus the gate page.
GATE_PAGES = {("984073", 1)}   # Litolff p1: the plan's "31 -> toward 68" gate page


def held_out() -> set[tuple[str, int]]:
    d = json.loads((REPO / "data/hand-truth/held-out.json").read_text())
    return {(p["edition"].replace("imslp", ""), p["pdf_page_index"]) for p in d["pages"]} | GATE_PAGES


def imslp_of(pdf: str) -> str:
    return pdf.rsplit("--imslp", 1)[-1].split(".")[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", type=Path, required=True, help="a cut_candidate_cells output dir")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--keep", type=int, default=96)
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--max-score", type=int, default=6)
    ap.add_argument("--floor", type=float, default=0.10, help="pre-fill confidence floor")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--seed", type=int, default=20261011)
    ap.add_argument("--score-only", action="store_true")
    ap.add_argument("--blind", action="store_true",
                    help="write EMPTY detection files (draw from scratch). The test batch uses this: its truth "
                         "must be Sean's own eyes, not the detector's boxes he confirmed.")
    ap.add_argument("--test-page", action="store_true",
                    help="build the TEST batch: keep EVERY cell of the pooled page(s), no strata, and allow the "
                         "plan's gate page (Litolff idx 1). Such a batch is test truth and is never converted "
                         "into a training version.")
    a = ap.parse_args()

    cells = json.loads((a.pool / "cells.json").read_text())
    ho = held_out() - (GATE_PAGES if a.test_page else set())
    kept = []
    for c in cells:
        if (imslp_of(c["pdf"]), c["page"]) in ho:
            print("REFUSED held-out page:", c["cell_id"])
            continue
        kept.append(c)
    cells = kept
    print(f"{len(cells)} pooled cells")

    from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell
    import cv2

    class _Cell:
        def __init__(s, ys, im):
            s.staff_line_ys_canonical = ys
            s.image = im

    det = YoloDetector(str(PROD), device=a.device)
    rows = []
    for i, c in enumerate(cells):
        n_ctr, _ = score_cell(c, REPO) if (REPO / (c.get("nostaff_png_path") or c["cell_png_path"])).exists() \
            else score_cell({**c, "nostaff_png_path": None,
                             "cell_png_path": str(a.pool / "cells" / f"{c['cell_id']}.png")}, REPO)
        img_p = REPO / c["cell_png_path"]
        if not img_p.exists():
            img_p = a.pool / "cells" / f"{c['cell_id']}.png"
        img = cv2.imread(str(img_p))
        if img is None:
            continue
        cell = _Cell(c.get("staff_line_ys_canonical") or [], img)
        alld = det.detect(cell, conf_threshold=a.floor, imgsz=imgsz_for_cell(cell))
        n_head = sum(1 for d in alld if d.smufl_name.startswith("notehead"))
        ds = [d for d in alld if d.smufl_name in HOLLOW]
        n10 = len(ds)
        n25 = sum(1 for d in ds if d.confidence >= 0.25)
        rows.append({"cell": c, "counters": n_ctr, "n10": n10, "n25": n25, "n_head10": n_head,
                     "dets": [{"cls": d.smufl_name, "x": d.x_canonical, "y": d.y_canonical,
                               "w": d.width_canonical, "h": d.height_canonical,
                               "conf": round(float(d.confidence), 3)} for d in ds]})
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(cells)} scored", flush=True)

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "pool-scores.json").write_text(json.dumps(
        [{"cell_id": r["cell"]["cell_id"], "counters": r["counters"], "n10": r["n10"], "n25": r["n25"],
          "n_head10": r["n_head10"]}
         for r in rows], indent=1))
    # THE RANKER IS NOT A SELECTOR (print check 2026-10-11, scratch contact sheet of 12 cells): on these editions
    # its "counters" are beam gaps, flag holes, the bowls of ff / cresc. -- ~0 of 12 cells held a hollow head.
    # Strata are therefore built from the PRODUCTION DETECTOR: D = it draws a hollow-class box at conf >= 0.10;
    # N = a same-staff NEIGHBOUR bar of a D cell (long notes recur, and a head missed beside a found one is
    # the 2.53 shape); E = no hollow box but notehead-class boxes (hard negatives, ~10%).
    key = lambda r: (r["cell"]["source_tag"], r["cell"]["system_index"], r["cell"]["staff_index"])  # noqa: E731
    Dset = {(key(r), r["cell"]["measure_index"]) for r in rows if r["n10"] >= 1}
    D = [r for r in rows if r["n10"] >= 1]
    N = [r for r in rows if r["n10"] == 0 and ((key(r), r["cell"]["measure_index"] - 1) in Dset or
                                               (key(r), r["cell"]["measure_index"] + 1) in Dset)]
    C = [r for r in rows if r["n10"] == 0 and r["n_head10"] > 0 and r not in N]
    A, B = D, N
    print(f"strata in the pool: DETECTED {len(D)}  NEIGHBOUR {len(N)}  EMPTY-ish {len(C)}  of {len(rows)}")
    if a.score_only:
        return 0
    rnd = random.Random(a.seed)
    if a.test_page:
        A = [r for r in rows if r["counters"] > 0 or r["n_head10"] > 0]
        B = [r for r in rows if r not in A]

    def take(pool, k, by_edition=True):
        """Round-robin across editions so no press dominates."""
        by = collections.defaultdict(list)
        for r in pool:
            by[imslp_of(r["cell"]["pdf"])].append(r)
        for v in by.values():
            rnd.shuffle(v)
        out = []
        while len(out) < k and any(by.values()):
            for k2 in sorted(by):
                if by[k2] and len(out) < k:
                    out.append(by[k2].pop())
        return out

    if a.test_page:
        # every cell that holds a notehead-sized counter or ANY notehead-class box at conf >= 0.10; a cell
        # with neither is a rest-only / empty bar. Control: the count of heads Sean draws is compared with
        # the 68 half notes the reference prints on this page (DURATIONS.md).
        pick = list(A)
    else:
        nC = int(round(a.keep * 0.1))
        pick = take(C, nC)
        pick += take(D, int(round(a.keep * 0.55)))
        have = {r["cell"]["cell_id"] for r in pick}
        pick += take([r for r in N if r["cell"]["cell_id"] not in have], a.keep - len(pick))
        have = {r["cell"]["cell_id"] for r in pick}
        if len(pick) < a.keep:
            pick += take([r for r in D if r["cell"]["cell_id"] not in have], a.keep - len(pick))
    print(f"kept {len(pick)} cells")

    if (a.out / "cells.json").exists() or (a.out / "verdicts").exists():
        print(f"REFUSING to overwrite {a.out} -- it may hold verdicts")
        return 1
    (a.out / "detections").mkdir(parents=True, exist_ok=True)
    (a.out / "verdicts").mkdir()
    man, hints = [], []
    for r in sorted(pick, key=lambda r: (r["cell"]["source_tag"], r["cell"]["system_index"],
                                        r["cell"]["staff_index"], r["cell"]["measure_index"])):
        c = dict(r["cell"])
        cid = c["cell_id"]
        dets = [] if a.blind else [{"id": f"D{i}", "smufl_name": d["cls"], "category": "structural",
                 "x": d["x"], "y": d["y"], "w": d["w"], "h": d["h"], "confidence": d["conf"]}
                for i, d in enumerate(r["dets"])]
        (a.out / "detections" / f"{cid}.json").write_text(json.dumps({"cell_id": cid, "detections": dets}, indent=1))
        stratum = "TEST" if a.test_page else ("DETECTED" if r["n10"] >= 1 else ("NEIGHBOUR" if r in N else "EMPTY"))
        c.update({"hollow_candidates": r["counters"], "prod_hollow_conf10": r["n10"], "prod_hollow_conf25": r["n25"],
                  "stratum": stratum})
        man.append(c)
        hints.append(f"{cid}\tcounters={r['counters']}\tprod@0.10={r['n10']}\tprod@0.25={r['n25']}\t{stratum}")
    (a.out / "cells.json").write_text(json.dumps(man, indent=1))
    (a.out / "HOLLOW_HINTS.txt").write_text("\n".join(hints) + "\n")
    cfg = Path(__file__).parent / "batch_config.json"
    if cfg.resolve() != (a.out / "batch_config.json").resolve():
        shutil.copy(cfg, a.out / "batch_config.json")
    # pool PNGs: a bench dir needs its own cells/ (gitignored); copy only the kept ones
    (a.out / "cells").mkdir(exist_ok=True)
    for c in man:
        for key in ("cell_png_path", "nostaff_png_path"):
            p = c.get(key)
            if not p:
                continue
            src = REPO / p
            if not src.exists():
                src = a.pool / "cells" / Path(p).name
            if src.exists():
                shutil.copy(src, a.out / "cells" / Path(p).name)
            dst = (a.out / "cells" / Path(p).name).resolve()
            try:
                c[key] = str(dst.relative_to(REPO))
            except ValueError:
                c[key] = str(dst)
    (a.out / "cells.json").write_text(json.dumps(man, indent=1))
    strat = collections.Counter(c["stratum"] for c in man)
    eds = collections.Counter(imslp_of(c["pdf"]) for c in man)
    print("strata:", dict(strat), " editions:", dict(eds))
    print("pending pre-fills:", sum(len(r["dets"]) for r in pick))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
