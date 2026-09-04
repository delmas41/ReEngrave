"""Class-space survival in seconds, so a save_period=1 sweep can be screened.

Gate axis 3 (`probe_confidence_shift.py --gate`) reads the raw transcription
JSONs, which means a page of `scan_eval` per checkpoint — 2.5 minutes each, and
a method sweep with per-epoch checkpoints produces dozens. This asks the same
question directly of the DETECTOR, on 30 dense orchestral cells that are already
cut on disk and are in no admitted training version (`benchmarks/omr-phase2.5/`,
the held-out set `wtc_forgetting_eval` uses), so it costs seconds.

It is a SCREEN, not a gate: it sees the detector, not the pipeline, so it cannot
tell you what reaches the export. A checkpoint that survives here still has to
clear all three real axes.

    python3 .../probe_class_inventory.py --ckpts prod=<prod.pt> a=<a.pt> ...
    python3 .../probe_class_inventory.py --ckpts-dir runs/ --baseline prod=<prod.pt>
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
CELLS_JSON = MAIN / "benchmarks" / "omr-phase2.5" / "cells.json"
CELLS_DIR = MAIN / "benchmarks" / "omr-phase2.5" / "cells"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpts", nargs="*", default=[],
                    help="tag=path pairs. The FIRST is the baseline unless "
                         "--baseline is given.")
    ap.add_argument("--ckpts-dir", type=Path, default=None,
                    help="add every *.pt under this directory, tagged by "
                         "<run>/<file>.")
    ap.add_argument("--baseline", default=None, help="tag=path")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--floor", type=int, default=10,
                    help="only classes the baseline reads this often are "
                         "reported as collapsed.")
    ap.add_argument("--ratio", type=float, default=0.25)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    import cv2
    from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell

    class _Cell:
        def __init__(self, ys, image):
            self.staff_line_ys_canonical = ys
            self.image = image

    manifest = {e["cell_id"]: e for e in json.loads(CELLS_JSON.read_text())}
    cells = []
    for cid, e in sorted(manifest.items()):
        p = CELLS_DIR / f"{cid}.png"
        if not p.exists():
            continue
        img = cv2.imread(str(p))
        if img is None:
            continue
        cells.append(_Cell(e.get("staff_line_ys_canonical") or [], img))
    if not cells:
        print(f"no cells under {CELLS_DIR}", file=sys.stderr)
        return 2
    print(f"{len(cells)} held-out dense cells")

    specs = list(a.ckpts)
    if a.baseline:
        specs.insert(0, a.baseline)
    if a.ckpts_dir:
        for f in sorted(a.ckpts_dir.rglob("*.pt")):
            specs.append(f"{f.parent.parent.name}-{f.stem}={f}")
    if not specs:
        ap.error("nothing to probe")

    out = {}
    order = []
    for spec in specs:
        tag, _, path = spec.partition("=")
        if tag in out:
            continue
        det = YoloDetector(path, device=a.device)
        counts = collections.Counter()
        for c in cells:
            for d in det.detect(c, conf_threshold=a.conf, imgsz=imgsz_for_cell(c)):
                counts[d.smufl_name] += 1
        out[tag] = dict(counts)
        order.append(tag)
        print(f"  {tag:26s} {sum(counts.values()):5d} detections, "
              f"{len(counts):3d} classes")

    base_tag = order[0]
    base = out[base_tag]
    gated = sorted((c for c, n in base.items() if n >= a.floor),
                   key=lambda c: -base[c])
    w = max(len(t) for t in order)
    print(f"\n{'class':24s}" + "".join(f"{t:>{w+2}s}" for t in order))
    for c in gated:
        print(f"{c:24s}" + "".join(f"{out[t].get(c, 0):{w+2}d}" for t in order))
    print(f"\ncollapsed (< {a.ratio:.0%} of {base_tag}, floor {a.floor}):")
    for t in order[1:]:
        lost = [c for c in gated if out[t].get(c, 0) < base[c] * a.ratio]
        print(f"  {t:26s} {len(lost):2d} classes  {lost[:10]}")

    if a.out:
        a.out.write_text(json.dumps(
            {"cells": len(cells), "conf": a.conf, "baseline": base_tag,
             "counts": out}, indent=1) + "\n")
        print("->", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
