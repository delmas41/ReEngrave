"""Is the same-cell duplicate really the NMS parameters? Ask the detector.

⚠️ READING THE CODE IS NOT MEASURING IT. `gather.py` calls
`detector.detect(cell, conf_threshold=..., imgsz=...)` and passes neither
`iou_threshold` nor `agnostic_nms`, so it takes `YoloDetector.detect`'s own
defaults (0.7, False) where `transcribe()` passes (0.5, True). That is a claim
about what the detector then DOES, and this runs both parameter sets over the
same cells of the same page and counts the overlapping same-family boxes each
produces.

It is a ONE-PAGE, FEW-CELL probe and it is not a pricing: it says whether the
mechanism is what the code reading says, nothing about what changing it costs.
The pricing is two full re-gathers (FINDINGS §6).
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.pipeline import prepare_pages  # noqa: E402
from tools.omr.transcribe import _bbox_iou_xywh  # noqa: E402
from tools.omr.yolo_detector import YoloDetector  # noqa: E402

NOTEHEAD = "notehead"


def overlapping(dets, iou=0.3):
    """Pairs of same-CATEGORY detections overlapping more than `iou`."""
    out = []
    for i in range(len(dets)):
        for j in range(i + 1, len(dets)):
            a, b = dets[i], dets[j]
            if a.category != b.category:
                continue
            ba = [a.x_canonical, a.y_canonical, a.width_canonical,
                  a.height_canonical]
            bb = [b.x_canonical, b.y_canonical, b.width_canonical,
                  b.height_canonical]
            v = _bbox_iou_xywh(ba, bb)
            if v > iou:
                out.append((a, b, v))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--cells", type=int, default=40)
    ap.add_argument("--conf", type=float, default=0.25)
    args = ap.parse_args(argv)

    # ⚠️ THE PIPELINE'S OWN PREPARATION, called rather than re-derived, so the
    # cells this probe hands the detector are the cells GATHER hands it.
    prepared = prepare_pages(args.pdf, [args.page], dpi=600)
    pws, all_cells = prepared[0]
    cells = list(all_cells)[:args.cells]
    print(f"page {args.page}: {len(pws.staves)} staves, "
          f"{len(all_cells)} cells, probing {len(cells)}")

    det = YoloDetector(args.weights)
    arms = {
        "staged (gather.py: detector defaults 0.7 / agnostic=False)":
            dict(iou_threshold=0.7, agnostic_nms=False),
        "legacy (transcribe(): 0.5 / agnostic=True)":
            dict(iou_threshold=0.5, agnostic_nms=True),
    }
    for label, kw in arms.items():
        n_det = 0
        pairs = collections.Counter()
        classes = collections.Counter()
        for c in cells:
            d = det.detect(c, conf_threshold=args.conf, **kw)
            n_det += len(d)
            for a, b, _v in overlapping(d):
                pairs[a.category] += 1
                if a.smufl_name != b.smufl_name:
                    classes["different_class"] += 1
                else:
                    classes["same_class"] += 1
        print(f"\n{label}")
        print(f"  detections            {n_det}")
        print(f"  overlapping pairs     {sum(pairs.values())}  {dict(pairs)}")
        print(f"  ... class agreement   {dict(classes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
