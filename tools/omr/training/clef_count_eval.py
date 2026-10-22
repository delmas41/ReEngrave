"""Held-out clef-detection eval.

The catalog-val mAP is meaningless on these small canonical cells (the model
over-detects phantom noteheads → mAP≈0 for ANY model). This eval sidesteps that
and measures the actual disease directly: on cells that each contain exactly one
clef (the m0 cell of a staff), does the model DETECT the clef, and get the TYPE
right? The production model reads real orchestral pages as all-treble because it
detects ≈0 clefs — this quantifies that, and gives a fine-tune something real to
beat.

Ground truth (optional) is read from labeling verdicts: each cell's human-labeled
clef class. Cells without a verdict still count toward the detection rate.

CLI:
    python3 -m tools.omr.training.clef_count_eval \
        --weights omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
        --cells-dir benchmarks/omr-labeling-2026-07-12-clef/cells \
        --verdicts-dir benchmarks/omr-labeling-2026-07-12-clef/verdicts \
        --imgsz 1280 --conf 0.20
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import Counter
from pathlib import Path

# Map DSv2 / labeling clef class names → a canonical clef token.
_CLEF_CANON = {
    "clefG": "treble", "gClef": "treble",
    "clefCAlto": "alto", "cClefAlto": "alto",
    "clefCTenor": "tenor", "cClefTenor": "tenor",
    "clefF": "bass", "fClef": "bass",
    "clefUnpitchedPercussion": "perc", "unpitchedPercussionClef1": "perc",
    "clefGChange": "treble", "clefCAltoChange": "alto",
    "clefCTenorChange": "tenor", "clefFChange": "bass",
    "clefC": "alto",  # bare C clef → alto (default position)
}
_CLEF_TOKENS = {"treble", "alto", "tenor", "bass", "perc"}


def _canon(name: str | None) -> str | None:
    if not name:
        return None
    return _CLEF_CANON.get(name)


def load_ground_truth(verdicts_dir: str | None) -> dict[str, str]:
    """cell_id → canonical clef token, from labeling verdicts."""
    gt: dict[str, str] = {}
    if not verdicts_dir:
        return gt
    for f in glob.glob(os.path.join(verdicts_dir, "*.json")):
        d = json.load(open(f))
        cid = d.get("cell_id") or Path(f).name.split(".")[0]
        for det in d.get("added_detections", []) + d.get("detections", []):
            if det.get("human_category") == "clef" or _canon(det.get("human_class")):
                tok = _canon(det.get("human_class"))
                if tok:
                    gt[cid] = tok
                    break
    return gt


def clef_indices(names: dict[int, str]) -> dict[int, str]:
    """model class-index → canonical clef token, for clef classes only."""
    return {i: _canon(n) for i, n in names.items() if _canon(n) in _CLEF_TOKENS}


def evaluate(weights: str, cells_dir: str, verdicts_dir: str | None,
             imgsz: int, conf: float, device: str) -> dict:
    from ultralytics import YOLO
    import warnings
    warnings.filterwarnings("ignore")

    model = YOLO(weights)
    names = {int(i): n for i, n in model.names.items()}
    clef_idx = clef_indices(names)
    gt = load_ground_truth(verdicts_dir)

    cells = sorted(p for p in glob.glob(os.path.join(cells_dir, "*.png"))
                   if not p.endswith("_nostaff.png"))
    rows = []
    for cp in cells:
        cid = Path(cp).stem
        r = model.predict(cp, imgsz=imgsz, conf=conf, device=device, verbose=False)[0]
        clefs = [(_canon(names[int(b.cls)]), float(b.conf))
                 for b in r.boxes if int(b.cls) in clef_idx]
        clefs.sort(key=lambda x: -x[1])
        top = clefs[0] if clefs else (None, 0.0)
        rows.append({"cell": cid, "expected": gt.get(cid),
                     "detected": top[0], "conf": round(top[1], 3),
                     "n_clef_dets": len(clefs)})
    return {"names_have_clef_classes": sorted(set(clef_idx.values())),
            "n_cells": len(rows), "rows": rows}


def render_report(rep: dict, weights: str) -> str:
    rows = rep["rows"]
    n = rep["n_cells"]
    got_any = sum(1 for r in rows if r["detected"])
    L = ["=" * 70, f"  clef-count eval — {Path(weights).name}", "=" * 70,
         f"cells: {n}   |   clef detected on: {got_any}/{n}  ({got_any/n:.0%})", ""]

    L.append("DETECTED clef-type distribution:")
    dist = Counter(r["detected"] or "(none)" for r in rows)
    for tok, c in dist.most_common():
        L.append(f"    {tok:<8} {c}")
    L.append("")

    labeled = [r for r in rows if r["expected"]]
    if labeled:
        correct = sum(1 for r in labeled if r["detected"] == r["expected"])
        miss = sum(1 for r in labeled if not r["detected"])
        L.append(f"TYPE ACCURACY (on {len(labeled)} cells with ground truth):")
        L.append(f"    right type: {correct}/{len(labeled)}  ({correct/len(labeled):.0%})"
                 f"   |   missed entirely: {miss}")
        # per-expected-type recall
        by_type: dict[str, list] = {}
        for r in labeled:
            by_type.setdefault(r["expected"], []).append(r)
        L.append("    by true clef type (detected-right / total):")
        for tok in ["treble", "bass", "alto", "tenor", "perc"]:
            grp = by_type.get(tok, [])
            if grp:
                ok = sum(1 for r in grp if r["detected"] == tok)
                L.append(f"        {tok:<8} {ok}/{len(grp)}"
                         + ("" if ok == len(grp) else "   ← MISSED"))
        L.append("")
        L.append("    misses / wrong (true → detected):")
        for r in labeled:
            if r["detected"] != r["expected"]:
                L.append(f"        {r['cell']:<28} {r['expected']} → {r['detected'] or '(none)'}")
    L.append("=" * 70)
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--cells-dir", required=True, help="Dir of clef cell PNGs.")
    ap.add_argument("--verdicts-dir", default=None, help="Labeling verdicts → ground truth.")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--conf", type=float, default=0.20)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    rep = evaluate(args.weights, args.cells_dir, args.verdicts_dir,
                   args.imgsz, args.conf, args.device)
    print(render_report(rep, args.weights))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(rep, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
