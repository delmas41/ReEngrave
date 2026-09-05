"""Audited model completion for the MARKS families — dynamics, slurs, ties.

Why this exists (measured 2026-09-03, `residual_background.json`): running the
production scan detector over the 198 cells that actually emit YOLO label files
and bucketing every detection by whether ANY labeling pass has covered its
class, **41.2% of the detected ink sits in classes nothing has ever boxed** —
377 detections across 142 of 198 cells. `NEXT_ITERATION.md` named rests and
accidentals as the gap; those are 73. **Dynamics (165) + slurs (99) + ties (26)
are 3.6x larger.** Unboxed trains as background, which is the exact mechanism
that made the 30-epoch cloud run suppress symbols.

Why the MODEL does these and the HUMAN does rests/accidentals: they were
spot-checked separately and they behave differently. Eight crops per class,
eyeballed — **dynamicP 8/8 real, dynamicF 8/8 real, slur 8/8 real**, while the
round-2 audit found model rests/accidentals FP-prone (restWhole on slur arcs,
accidentalDoubleSharp on trills). So each labeler takes the families it is
good at. `tie` measured ~60% and is kept only at a raised confidence floor;
clefs (~60%, three boxes landed on noteheads) are NOT here — they go to a
24-cell human mini-pass.

This is the same method that produced the black noteheads and augmentation
dots in v8-v12 (`complete_cells.py`, `complete_cells_phase2.py`), pointed at
different classes. Like those, it writes candidates + overlays for review and
**never touches verdicts/** — the human record is merged separately, after the
overlays are audited.

    python3 benchmarks/omr-labeling-survey-2026-09/complete_marks.py --device mps
"""
from __future__ import annotations
import argparse, json, glob, os, sys
from pathlib import Path
import numpy as np
import cv2

sys.path.insert(0, str(Path.cwd()))
from tools.omr.yolo_detector import YoloDetector
from tools.omr.annotate.build_template import _load_cell_from_manifest
from tools.omr.transcribe import _drop_clipped_notehead_fragments

WEIGHTS = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
           "deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt")

# Confidence floors are PER FAMILY, set from the spot check rather than shared:
# dynamics and slurs verified 8/8 at >=0.50, ties only ~60%, so ties must clear
# a higher bar to enter. A single global floor would either admit tie junk or
# throw away good dynamics.
CONF_FLOOR = 0.50
FAMILY_FLOOR = {"dynamic": 0.55, "slur": 0.60, "tie": 0.75}

DYNAMIC_PREFIXES = ("dynamic",)
KEEP_EXACT = {"slur", "tie"}

def _norm(n): return "".join(c for c in (n or "").lower() if c.isalnum())

def family(name: str) -> str | None:
    k = _norm(name)
    if k in ("slur",): return "slur"
    if k in ("tie",): return "tie"
    if k.startswith("dynamic"): return "dynamic"
    return None

def _iou(a, b) -> float:
    ax0, ay0, aw, ah = a; ax1, ay1 = ax0+aw, ay0+ah
    bx0, by0, bw, bh = b; bx1, by1 = bx0+bw, by0+bh
    iw = max(0, min(ax1,bx1)-max(ax0,bx0)); ih = max(0, min(ay1,by1)-max(ay0,by0))
    inter = iw*ih
    if inter <= 0: return 0.0
    ua = aw*ah + bw*bh - inter
    return inter/ua if ua > 0 else 0.0

def _center_in(inner, outer) -> bool:
    ix, iy, iw, ih = inner
    cx, cy = ix+iw/2, iy+ih/2
    ox, oy, ow, oh = outer
    return ox <= cx <= ox+ow and oy <= cy <= oy+oh

def not_lr_edge(d, W, tol=8) -> bool:
    return d.x_canonical > tol and (d.x_canonical + d.width_canonical) < W - tol

def cross_class_nms(dets, iou_thr=0.45):
    dets = sorted(dets, key=lambda d: -d.confidence)
    out = []
    for d in dets:
        db = (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)
        if any(_iou(db, (o.x_canonical, o.y_canonical, o.width_canonical, o.height_canonical)) > iou_thr
               for o in out):
            continue
        out.append(d)
    return out

def ink_fraction(cell, d) -> float:
    """Share of the box that is actually ink.

    A dynamic letter and a slur arc are both mostly white inside their box, but
    an EMPTY box is the signature of a hallucination on blank paper — the one
    failure mode an overlay reviewer is worst at spotting, because nothing is
    drawn there to disagree with.
    """
    img = cell.image
    g = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    x, y = max(0, d.x_canonical), max(0, d.y_canonical)
    x1, y1 = min(g.shape[1], x + d.width_canonical), min(g.shape[0], y + d.height_canonical)
    if x1 <= x or y1 <= y: return 0.0
    patch = g[y:y1, x:x1]
    return float((patch < 128).mean())

MIN_INK = 0.02

# ---------------------------------------------------------------------------
# AUDIT 2026-09-03 — all 192 candidates of the first run were cropped and
# eyeballed. Precision is high (dynamics ~89%, slurs ~90%) and the errors are
# ONE systematic family: **a letter lifted out of a printed word**. `sempre`,
# `espress.`, `dim.`, `schleppen`, `Bewegung` each donate an `m`, `p` or `g`
# that the detector calls a dynamic. Culling them is not optional politeness —
# those letters SHOULD train as background (they are text, and `textDynamic`
# exists for the dynamic words), so boxing them teaches the opposite.
#
# ⚠️ A GENERIC FILTER FOR THIS WAS BUILT AND REFUTED — do not rebuild it.
# The idea: a dynamic is short and isolated, a word-letter sits in a long run
# of same-height ink, so measure the horizontal ink run through the box after a
# letter-gap closing and threshold on run-width / box-width. Measured against
# this audit, the distributions OVERLAP and there is no usable cut:
#
#     dynamics  KEEP run-width p50 1.86, max 8.16 · CULL p50 3.98, max 8.41
#       thr 3.0 -> culls 14/17 bad but LOSES 31/133 good
#       thr 4.0 -> culls  8/17 bad,       loses 24/133 good
#     slurs     no separation at all — every threshold culls 0 of 4 bad
#
# The reason is that a real dynamic is usually NOT isolated: it abuts staff
# lines, noteheads and hairpins, and a `pp`/`ff` ligature is wide on its own.
# So the culls are an explicit, content-keyed list — the same shape
# complete_cells_phase2.py uses — stable across re-runs because it keys on the
# cell and the box, never on an index.
EXPLICIT_CULL = [
    ('schehe-p4-sys1-s14-m1', 'dynamicP', 514, 0, 115, 92),  # staircase of clipped edge ink, not a 'p' (round-3 audit)
    ('mahler1-p5-sys0-s7-m5', 'dynamicP', 947, 873, 109, 133),  # schleppen — pp inside the word
    ('mahler1-p5-sys1-s17-m0', 'dynamicP', 849, 793, 100, 110),  # sempre — pr
    ('mahler1-p1-sys0-s8-m5', 'dynamicP', 416, 1064, 146, 152),  # sempre — mpr
    ('mahler1-p5-sys1-s17-m0', 'dynamicM', 736, 795, 117, 78),  # sempre — m
    ('mahler1-p1-sys0-s8-m5', 'dynamicM', 264, 1063, 164, 103),  # sempre — m
    ('mahler1-p2-sys0-s9-m6', 'dynamicM', 284, 1155, 170, 117),  # sempre — p
    ('mahler1-p2-sys0-s9-m6', 'dynamicP', 446, 1157, 143, 165),  # sempre — pr
    ('mahler5-p178-sys2-s16-m2', 'dynamicP', 1099, 1139, 156, 174),  # sempre — p
    ('mahler5-p175-sys0-s5-m7', 'dynamicP', 628, 193, 145, 170),  # espress. — p
    ('mahler1-p3-sys0-s11-m5', 'dynamicP', 432, 1138, 160, 181),  # espr. — esp
    ('mahler5-p176-sys1-s12-m0', 'dynamicF', 1324, 984, 121, 139),  # espress. — p
    ('mahler5-p177-sys1-s7-m6', 'dynamicM', 329, 0, 184, 78),  # dim. — im
    ('mahler5-p178-sys2-s16-m2', 'dynamicM', 970, 1143, 153, 115),  # sempr — m
    ('dvorak9-p8-sys1-s23-m0', 'dynamicF', 996, 980, 103, 206),  # tr (trill), not a dynamic
    ('mahler5-p177-sys1-s7-m6', 'dynamicM', 120, 0, 123, 83),  # dim. — im
    ('mahler5-p178-sys1-s10-m1', 'dynamicP', 270, 209, 149, 170),  # Bewegung — g
    ('schehe-p3-sys0-s3-m0', 'dynamicF', 1012, 0, 108, 54),  # unidentified mark, conf 0.60
    ('mahler5-p178-sys2-s16-m2', 'slur', 439, 360, 427, 131),  # hairpin/wedge, not an arc
    ('lamer-p2-sys0-s5-m4', 'slur', 1273, 0, 735, 83),  # hairpin — two converging straight lines
    ('mahler5-p178-sys2-s17-m3', 'slur', 160, 1313, 295, 81),  # ambiguous, not a clear arc
    ('beet5hr-p51-sys0-s7-m4', 'slur', 320, 1208, 1677, 135),  # ambiguous flat line over ff
]
_CULL_INDEX = {(c[0], c[1]): [] for c in EXPLICIT_CULL}
for _c in EXPLICIT_CULL:
    _CULL_INDEX[(_c[0], _c[1])].append((_c[2], _c[3], _c[4], _c[5]))

def is_culled(d, cid, tol=6) -> bool:
    """True if this box is on the audited cull list (matched by position)."""
    key = (cid, getattr(d, "smufl_name", ""))
    for (x, y, w, h) in _CULL_INDEX.get(key, ()):
        if (abs(d.x_canonical - x) <= tol and abs(d.y_canonical - y) <= tol
                and abs(d.width_canonical - w) <= tol and abs(d.height_canonical - h) <= tol):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps"])
    ap.add_argument("--weights", default=WEIGHTS)
    ap.add_argument("--batches", nargs="*", default=None)
    ap.add_argument("--out", default="benchmarks/omr-labeling-survey-2026-09/marks_completion.json")
    args = ap.parse_args()

    batches = args.batches or (
        ["benchmarks/omr-labeling-hollow-2026-08"]
        + sorted(glob.glob("benchmarks/omr-labeling-hollow2-2026-09-*"))
        + sorted(glob.glob("benchmarks/omr-labeling-hollow3-2026-09-*")))
    det = YoloDetector(args.weights, device=args.device)
    root = Path.cwd()
    summary = {"weights": args.weights, "conf_floor": CONF_FLOOR,
               "family_floor": FAMILY_FLOOR, "min_ink": MIN_INK, "batches": {}}
    grand = {"cells": 0, "kept": 0, "dropped_overlap": 0, "dropped_ink": 0, "dropped_conf": 0, "dropped_cull": 0}

    for b in batches:
        name = os.path.basename(b)
        mf = Path(b, "cells.json")
        if not mf.exists(): continue
        manifest = {e["cell_id"]: e for e in json.loads(mf.read_text())}
        comp = Path(b, "marks-completion")
        (comp / "candidates").mkdir(parents=True, exist_ok=True)
        per = {"cells": 0, "kept": 0, "by_family": {}}
        for vf in sorted(glob.glob(os.path.join(b, "verdicts", "*.verdict.json"))):
            v = json.loads(Path(vf).read_text())
            cid = v["cell_id"]
            entry = manifest.get(cid)
            if entry is None: continue
            png = Path(b, "cells", f"{cid}.png")
            if not png.exists(): continue
            # Only cells that already carry a human box become training data,
            # so only those can suffer the background problem.
            existing = list(v.get("added_detections") or [])
            if not existing: continue
            try:
                cell = _load_cell_from_manifest(entry, root)
            except Exception as ex:
                print(f"  skip {cid}: {type(ex).__name__} {ex}"); continue
            H, W = cell.image.shape[:2]
            dets = det.detect(cell, conf_threshold=CONF_FLOOR, imgsz=None)
            dets, _ = _drop_clipped_notehead_fragments(dets, cell)
            keep = []
            for d in dets:
                fam = family(getattr(d, "smufl_name", ""))
                if fam is None: continue
                if d.confidence < FAMILY_FLOOR[fam]:
                    grand["dropped_conf"] += 1; continue
                if not not_lr_edge(d, W): continue
                if ink_fraction(cell, d) < MIN_INK:
                    grand["dropped_ink"] += 1; continue
                keep.append(d)
            # never propose a box over something a human already drew
            hb = [(h["bbox"]["x"], h["bbox"]["y"], h["bbox"]["w"], h["bbox"]["h"]) for h in existing]
            filt = []
            for d in keep:
                db = (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)
                if any(_iou(db, x) > 0.25 or _center_in(db, x) for x in hb):
                    grand["dropped_overlap"] += 1; continue
                if is_culled(d, cid):
                    grand["dropped_cull"] += 1; continue
                filt.append(d)
            filt = cross_class_nms(filt)
            per["cells"] += 1; grand["cells"] += 1
            cand = [{"smufl_name": d.smufl_name, "category": d.category,
                     "family": family(d.smufl_name), "confidence": round(float(d.confidence), 4),
                     "ink": round(ink_fraction(cell, d), 4),
                     "bbox": {"x": d.x_canonical, "y": d.y_canonical,
                              "w": d.width_canonical, "h": d.height_canonical}}
                    for d in filt]
            for c in cand:
                per["by_family"][c["family"]] = per["by_family"].get(c["family"], 0) + 1
            per["kept"] += len(cand); grand["kept"] += len(cand)
            (comp / "candidates" / f"{cid}.json").write_text(
                json.dumps({"cell_id": cid, "candidates": cand}, indent=1))
        summary["batches"][name] = per
        print(f"{name:56s} cells={per['cells']:3d} kept={per['kept']:4d} {per['by_family']}")
    summary["grand"] = grand
    Path(args.out).write_text(json.dumps(summary, indent=1))
    print(f"\n{grand}\nwrote {args.out}")
    print("NOTHING was written to verdicts/ — audit the overlays, then merge.")

if __name__ == "__main__":
    main()
