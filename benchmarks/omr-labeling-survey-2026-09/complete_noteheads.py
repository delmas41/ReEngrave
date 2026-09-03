"""Audited model completion for BLACK NOTEHEADS + augmentation dots — the top-up.

Round 3's closing measurement (`residual_background.py`) took uncovered ink on
the training cells from 68.1% to 35.9%, and then said what the residue IS:
**41% of it is black noteheads** — 200 detections — with slurs and ties next.

That is the most dangerous class to leave as background, because it is the
dominant one, and the coverage is wildly uneven across batches: the earlier
completion rounds boxed 80 black noteheads on Litolff but **ONE across all 25
cells of v7**, which never got a completion pass at all. One epoch tolerates
that (the 896 ship held dense recall at 0.941); thirty epochs is what turned
unlabeled rests into suppressed rests last time.

Same audited method as `complete_marks.py`, pointed at the density-prior
classes. The one difference that matters: overlap is checked against the
FULLY MERGED verdict — human boxes AND every earlier model completion AND this
round's marks — so a head already boxed by any round is never proposed twice.

    python3 .../complete_noteheads.py --device mps
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
FAMILY_FLOOR = {"notehead": 0.55, "dot": 0.60}

KEEP_EXACT = {"noteheadblackonline", "noteheadblackinspace", "augmentationdot"}
# Hollow heads are HUMAN-labelled; never propose one from the model.
HOLLOW_KEYS = ("noteheadhalf", "noteheadwhole", "noteheaddoublewhole")

def _norm(n): return "".join(c for c in (n or "").lower() if c.isalnum())

def family(name: str) -> str | None:
    k = _norm(name)
    if any(h in k for h in HOLLOW_KEYS): return None
    if k in ("noteheadblackonline", "noteheadblackinspace"): return "notehead"
    if k == "augmentationdot": return "dot"
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
# TWO GUARDS, both from the round-3 audit of these candidates, and both RULES
# rather than a hand list — each is justified by a dimension a notehead cannot
# vary in, so they generalise to the next batch.
#
# 1. SIZE. A notehead is about one staff space tall and never much wider than
#    it is tall. The audit's worst false positive was a SLUR ARC boxed at
#    394x170 px against a 100 px staff space — 3.9 spaces wide. Real candidates
#    in this run measure 0.5-1.5 spaces. The cut sits in the empty gap between.
# 2. THE TOP EDGE. `not_lr_edge` guards left and right only, which is exactly
#    how a solid block of bleed from the staff ABOVE gets through — the audit
#    caught one at y=0, in the same cell complete_cells_phase2.py already culls
#    by name for the same artifact. A cell is padded above the staff, so real
#    ink never starts at row 0.
MAX_W_SPACES = 2.0
MAX_H_SPACES = 1.6

def _staff_space(cell) -> float:
    """Staff space in canonical px, or 0.0 when the cell has no five-line geometry.

    ⚠️ The field is `staff_line_ys_canonical`. An earlier cut of this guard read
    `staff_line_ys`, which does not exist on MeasureCell, so getattr returned
    None, every cell "had no geometry", the guard abstained on all 169
    candidates and the 394x170 slur arc it was written to catch sailed through.
    Nothing failed; the only tell was `dropped_size == 0` in the summary. That
    is why the caller COUNTS abstentions — a guard that abstains silently is
    indistinguishable from a guard that passed.
    """
    ys = sorted(float(y) for y in (getattr(cell, "staff_line_ys_canonical", None) or []))
    return (ys[-1] - ys[0]) / 4 if len(ys) == 5 else 0.0

def size_ok(d, cell) -> bool:
    sp = _staff_space(cell)
    if sp <= 0: return True                      # no geometry -> abstain, do not guess
    return (d.width_canonical <= MAX_W_SPACES * sp
            and d.height_canonical <= MAX_H_SPACES * sp)

def touches_top(d, tol=2) -> bool:
    return d.y_canonical <= tol


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
    # (none yet — populated after the overlay audit)
    ('mahler1-p5-sys0-s7-m5', 'dynamicP', 947, 873, 109, 133),  # schleppen — pp inside the word
    ('mahler1-p1-sys0-s8-m5', 'dynamicP', 416, 1064, 146, 152),  # sempre — mpr
    ('mahler1-p1-sys0-s8-m5', 'dynamicM', 264, 1063, 164, 103),  # sempre — m
    ('mahler1-p2-sys0-s9-m6', 'dynamicP', 446, 1157, 143, 165),  # sempre — pr
    ('mahler5-p175-sys0-s5-m7', 'dynamicP', 628, 193, 145, 170),  # espress. — p
    ('mahler5-p176-sys1-s12-m0', 'dynamicF', 1324, 984, 121, 139),  # espress. — p
    ('mahler5-p178-sys2-s16-m2', 'dynamicM', 970, 1143, 153, 115),  # sempr — m
    ('mahler5-p177-sys1-s7-m6', 'dynamicM', 120, 0, 123, 83),  # dim. — im
    ('schehe-p3-sys0-s3-m0', 'dynamicF', 1012, 0, 108, 54),  # unidentified mark, conf 0.60
    ('lamer-p2-sys0-s5-m4', 'slur', 1273, 0, 735, 83),  # hairpin — two converging straight lines
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
    ap.add_argument("--out", default="benchmarks/omr-labeling-survey-2026-09/notehead_completion.json")
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
        comp = Path(b, "notehead-completion")
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
            # every box any round has already placed on this cell
            mv = Path("benchmarks/omr-labeling-survey-2026-09/phase3-merged")
            prior_boxes = []
            for cand in mv.glob(f"*/verdicts/{cid}.verdict.json"):
                pv = json.loads(cand.read_text())
                prior_boxes += [b2["bbox"] for b2 in (pv.get("added_detections") or [])]
                prior_boxes += [b2["model_bbox"] for b2 in (pv.get("detections") or [])
                                if b2.get("verdict") == "TP" and b2.get("model_bbox")]
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
                if touches_top(d):
                    grand["dropped_topedge"] = grand.get("dropped_topedge", 0) + 1; continue
                if _staff_space(cell) <= 0:
                    grand["size_abstain"] = grand.get("size_abstain", 0) + 1
                elif not size_ok(d, cell):
                    grand["dropped_size"] = grand.get("dropped_size", 0) + 1; continue
                if ink_fraction(cell, d) < MIN_INK:
                    grand["dropped_ink"] += 1; continue
                keep.append(d)
            # never propose a box over something a human already drew
            hb = [(h["x"], h["y"], h["w"], h["h"]) for h in prior_boxes] or \
                 [(h["bbox"]["x"], h["bbox"]["y"], h["bbox"]["w"], h["bbox"]["h"]) for h in existing]
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
