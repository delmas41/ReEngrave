"""Pre-label a batch at the PER-CELL inference size, not a fixed one.

⚠️ WHY THIS EXISTS RATHER THAN `run_yolo --imgsz N`. A measure cell is
CANONICALLY RESCALED before detection, so the right letterbox size is a property
of the cell, not a constant — `yolo_detector.imgsz_for_cell` computes it, and
`detect(..., imgsz=None)` asks for it. `run_yolo.py` types `--imgsz` as an int
with default 640 and has no way to express "per cell", so every batch it
pre-labels is detected at the wrong scale.

Run against the Simrock batch with a fixed 2048 it produced boxes that were
tiny slivers strung along the cell's left and right EDGES — on the barlines —
with essentially nothing on the noteheads: 38 boxes on a cell whose music is a
handful of notes. That is `project_detector_scale`'s documented failure ("note
over-detection was an inference-SCALE bug (imgsz on canonically-rescaled
cells)") reproduced exactly, on labeling input this time rather than on a
transcription.

Writes the same `detections/<cell>.json` shape run_yolo does, via the same
`_detections_to_dict`, so the annotate UI cannot tell the difference.

    python3 .../prelabel_percell.py --bench-dir benchmarks/omr-labeling-simrock-2026-09
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
from tools.omr.yolo_detector import YoloDetector
from tools.omr.annotate.build_template import _load_cell_from_manifest, _detections_to_dict
from tools.omr.transcribe import _drop_clipped_notehead_fragments

W = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
     "deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-dir", required=True)
    ap.add_argument("--weights", default=W)
    ap.add_argument("--conf", type=float, default=0.45)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--limit", type=int, default=0, help="only the first N cells (for a sample)")
    a = ap.parse_args()
    bench = Path(a.bench_dir)
    man = json.loads((bench / "cells.json").read_text())
    if a.limit: man = man[: a.limit]
    out = bench / "detections"; out.mkdir(parents=True, exist_ok=True)
    det = YoloDetector(a.weights, device=a.device); root = Path.cwd()
    tot = 0
    for i, e in enumerate(man):
        cid = e["cell_id"]
        try:
            cell = _load_cell_from_manifest(e, root)
            dets = det.detect(cell, conf_threshold=a.conf, imgsz=None)   # <- per cell
            dets, _ = _drop_clipped_notehead_fragments(dets, cell)
        except Exception as ex:
            print(f"  skip {cid}: {type(ex).__name__} {ex}"); continue
        (out / f"{cid}.json").write_text(json.dumps(_detections_to_dict(cid, dets), indent=2))
        tot += len(dets)
        if (i + 1) % 25 == 0: print(f"  {i+1}/{len(man)}  ({tot} boxes)", flush=True)
    print(f"wrote {len(man)} detection files, {tot} boxes, {tot/max(len(man),1):.1f}/cell")

if __name__ == "__main__":
    main()
