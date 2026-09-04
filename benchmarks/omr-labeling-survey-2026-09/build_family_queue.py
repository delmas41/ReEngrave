"""Build the adjudication queue that makes a specialist corpus honest.

Round 6 measured why every specialist kills its own class: the corpora accuse
their own symbol. 58% of the ties the teacher can see in the ties corpus are
unboxed (slurs 61%, hollow 28%), and each unboxed one trains as a hard negative
against exactly the class the specialist exists for.

This writes a standard annotate batch per family that contains BOTH sides:

* the human's existing family boxes, as detections pre-marked TP — so the
  export after triage is the COMPLETE family labeling, not a delta to merge;
* the teacher's family detections that no human box overlaps, as PENDING —
  the queue. `t` makes one a label, `f` makes it background. For ties that is
  ~143 boxes: an hour at the UI, not a campaign.

The images are not written (they are gitignored everywhere); run
`recut_cells --bench-dir <out>` before serving, as with any checked-out batch.

    python3 .../build_family_queue.py --family ties \
        --out benchmarks/omr-queue-ties-2026-09
    python3 -m tools.omr.annotate.recut_cells --bench-dir benchmarks/omr-queue-ties-2026-09
    python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-queue-ties-2026-09

After triage, convert with `verdicts_to_yolo_labels` and rebuild the family
corpus from THIS batch alone — every decided cell is complete for the family by
construction, so `build_specialist_versions.py` is not needed for it.

⚠️ The batch_config palette is the family only, and each cell opens in draw
mode so a symbol BOTH the human and the teacher missed can still be added —
the queue lowers the residue, it cannot prove it zero.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import shutil
import sys
import os
from pathlib import Path

sys.path.insert(0, os.getcwd())

REPO = Path.cwd()
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
TEACHER = MAIN / "omr-weights" / "deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"

FAMILIES = {
    "ties": {"classes": ["tie"], "label": "tie"},
    "slurs": {"classes": ["slur"], "label": "slur"},
    "rests": {"classes": ["restWhole", "restHalf", "restQuarter", "rest8th",
                          "rest16th", "restHBar"], "label": "rest"},
    "accidentals": {"classes": ["accidentalFlat", "accidentalNatural",
                                "accidentalSharp"], "label": "accidental"},
    "hollow": {"classes": ["noteheadHalfOnLine", "noteheadHalfInSpace",
                           "noteheadWholeOnLine", "noteheadWholeInSpace"],
               "label": "hollow notehead"},
}


def iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    return inter / (aw * ah + bw * bh - inter) if inter > 0 else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True, choices=sorted(FAMILIES))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--spec-root", type=Path, default=None,
                    help="specialist corpus (default data/specialist-<family>)")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--iou", type=float, default=0.20)
    ap.add_argument("--device", default="mps")
    a = ap.parse_args()

    fam = FAMILIES[a.family]
    want = set(fam["classes"])
    spec = a.spec_root or (REPO / "data" / f"specialist-{a.family}")
    names = json.loads((REPO / "tools/omr/training/deepscoresv2_208_classes.json")
                       .read_text())

    # cell_id -> manifest entry, from every batch on disk
    mans: dict[str, dict] = {}
    for m in glob.glob("benchmarks/**/*cells.json", recursive=True):
        try:
            for e in json.loads(Path(m).read_text()):
                mans.setdefault(e["cell_id"], e)
        except Exception:
            continue

    from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell
    import cv2

    class _Cell:
        def __init__(s, ys, im):
            s.staff_line_ys_canonical = ys
            s.image = im

    det = YoloDetector(str(TEACHER), device=a.device)

    if a.out.exists():
        print(f"REFUSING to overwrite {a.out} — it may hold verdicts")
        return 1
    (a.out / "detections").mkdir(parents=True)
    (a.out / "verdicts").mkdir()

    manifest_rows = []
    n_tp = n_pending = 0
    for lab in sorted(spec.glob("v*/labels/*.txt")):
        cid = lab.stem
        entry = mans.get(cid)
        if entry is None:
            print(f"  WARN no manifest entry for {cid} — skipped")
            continue
        img_p = lab.parent.parent / "images" / f"{cid}.png"
        img = cv2.imread(str(img_p))
        if img is None:
            continue
        h, w = img.shape[:2]
        human = []
        for line in lab.read_text().splitlines():
            p = line.split()
            if len(p) == 5:
                i = int(p[0])
                cx, cy, bw, bh = (float(x) for x in p[1:])
                human.append((names[i] if i < len(names) else f"cls{i}",
                              (cx - bw / 2) * w, (cy - bh / 2) * h, bw * w, bh * h))
        ys = entry.get("staff_line_ys_canonical") or []
        cell = _Cell(ys, img)
        dets = []
        did = 0
        for cls, x, y, bw, bh in human:      # the human's boxes, pre-decided
            dets.append({"id": f"D{did}", "model_class": cls,
                         "model_category": "queue",
                         "model_bbox": {"x": int(x), "y": int(y),
                                        "w": int(bw), "h": int(bh)},
                         "confidence": 1.0})
            did += 1
        n_human = did
        hb = [(x, y, bw, bh) for _c, x, y, bw, bh in human]
        for d in det.detect(cell, conf_threshold=a.conf, imgsz=imgsz_for_cell(cell)):
            if d.smufl_name not in want:
                continue
            box = (d.x_canonical, d.y_canonical,
                   d.width_canonical, d.height_canonical)
            bcx, bcy = box[0] + box[2] / 2, box[1] + box[3] / 2
            if any(iou(box, b) > a.iou
                   or (b[0] <= bcx <= b[0] + b[2] and b[1] <= bcy <= b[1] + b[3])
                   for b in hb):
                continue
            dets.append({"id": f"D{did}", "model_class": d.smufl_name,
                         "model_category": "queue",
                         "model_bbox": {"x": d.x_canonical, "y": d.y_canonical,
                                        "w": d.width_canonical,
                                        "h": d.height_canonical},
                         "confidence": round(d.confidence, 3),
                         "notes": "teacher: unmatched by any human box"})
            did += 1
        if did == n_human == 0:
            continue                         # nothing to decide, nothing to keep
        (a.out / "detections" / f"{cid}.json").write_text(json.dumps(
            {"cell_id": cid, "detections": dets}, indent=1))
        # pre-mark the human's boxes TP so triage is only the queue
        (a.out / "verdicts" / f"{cid}.verdict.json").write_text(json.dumps(
            {"cell_id": cid, "schema_version": 2,
             "detections": [{"id": f"D{i}", "verdict": "TP"}
                            for i in range(n_human)],
             "added_detections": [],
             "notes": "human family boxes pre-confirmed by build_family_queue"},
            indent=1))
        n_tp += n_human
        n_pending += did - n_human
        manifest_rows.append(entry)

    (a.out / "cells.json").write_text(json.dumps(manifest_rows, indent=1))
    (a.out / "batch_config.json").write_text(json.dumps(
        {"pass_name": f"{a.family}-reconcile",
         "note": f"adjudicate the teacher's unmatched {fam['label']} boxes: "
                 f"t = real, f = not. Draw any {fam['label']} BOTH missed.",
         "classes": fam["classes"]}, indent=1))
    print(f"{len(manifest_rows)} cells, {n_tp} human boxes pre-marked TP, "
          f"{n_pending} teacher candidates PENDING -> {a.out}")
    print(f"next: python3 -m tools.omr.annotate.recut_cells --bench-dir {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
