"""What scale does the detector actually want to be shown?

The pipeline upscales every measure cell so its staff span is
`CANONICAL_STAFF_SPAN_PX` (400 px), then runs YOLO at `imgsz=2048`. Those two
choices were made independently and multiply: a cell 1200 px tall goes into the
model at ~1.7x again, so the model sees a staff space of 100-200 px. The weights
were fine-tuned on DeepScoresV2 *pages*, where a staff space is a couple of dozen
pixels. `imgsz=2048` "matching the weights' fine-tuning resolution" is true of a
page and false of a canonical cell.

This probe holds one cell fixed and varies only `imgsz`, reported not as a pixel
budget but as the quantity that actually matters:

    space_in = canonical_staff_space * imgsz / longest_side_of_cell

i.e. the staff space the model is shown. Truth is exact — the e2e fixtures are
authored, so every measure's note count is known — so the sweep scores counts,
not just plausibility.

    python3 -m benchmarks.omr_detector_scale.probe_detector_scale     # (see --help)

Two numbers per row are worth watching together:

  ratio     detected noteheads / true noteheads, summed over every measure
  medW/sp   median notehead box width in staff spaces. A notehead is about
            1.25 spaces wide, so this says whether the boxes are notehead-
            shaped at all. When it collapses the model has stopped finding
            noteheads and started finding fragments of them.
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

from tools.omr import measure_extractor as me
from tools.omr import preprocessing as pre
from tools.omr import staff_detector as sd
from tools.omr.training.e2e_fixtures import render
from tools.omr.yolo_detector import YoloDetector


DEFAULT_WEIGHTS = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
    "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
)

# Note counts per (fixture, staff, measure), read off `tools/omr/training/
# e2e_fixtures.py`. Staff order is top-to-bottom, which is the order the
# fixtures insert their parts.
TRUTH: dict[str, dict[int, list[int]]] = {
    "melody": {0: [4, 4, 4, 2, 8, 2]},
    "keyboard": {0: [4, 8, 2, 4], 1: [2, 4, 1, 2]},
    "ensemble": {0: [8, 4, 2, 4], 1: [4, 2, 4, 1],
                 2: [2, 1, 4, 1], 3: [1, 2, 4, 1]},
}

TARGETS = [12, 16, 20, 24, 30, 38, 50, 70, 100, 150]


def canonical_staff_space(cell) -> float:
    """The staff space in the cell's own canonical frame, from the cell itself
    rather than from the page — this is the number the model is shown."""
    ys = cell.staff_line_ys_canonical
    if len(ys) < 2:
        return 0.0
    return (ys[-1] - ys[0]) / (len(ys) - 1)


def imgsz_for_space(cell, target_space: float) -> int:
    """The imgsz that shows the model a staff space of `target_space`."""
    space = canonical_staff_space(cell)
    if space <= 0:
        return 2048
    long_side = max(cell.image.shape[0], cell.image.shape[1])
    raw = target_space * long_side / space
    return max(64, min(2048, int(round(raw / 32)) * 32))


def sweep(work: Path, weights: Path, targets: list[int]) -> list[dict]:
    det = YoloDetector(weights)
    rows: list[dict] = []
    for name, truth_by_staff in TRUTH.items():
        _, pdf = render(name, work)
        page = pre.render_page(str(pdf), 0, dpi=600)
        pws = me.detect_barlines(sd.detect_staves(page))
        for cell in me.extract_measures(pws):
            per_staff = truth_by_staff.get(cell.staff_index)
            if per_staff is None or cell.measure_index >= len(per_staff):
                continue
            space = canonical_staff_space(cell)
            for target in targets:
                imgsz = imgsz_for_space(cell, target)
                dets = det.detect(cell, conf_threshold=0.25, imgsz=imgsz,
                                  iou_threshold=0.5, agnostic_nms=True)
                nh = [d for d in dets if d.category == "notehead"]
                rows.append({
                    "fixture": name,
                    "staff": cell.staff_index,
                    "measure": cell.measure_index,
                    "truth": per_staff[cell.measure_index],
                    "target_space": target,
                    "imgsz": imgsz,
                    "canonical_space": round(space, 1),
                    "got": len(nh),
                    "median_width_spaces": (
                        round(st.median([d.width_canonical / space for d in nh]), 2)
                        if nh and space else None
                    ),
                    "median_conf": (
                        round(st.median([d.confidence for d in nh]), 2) if nh else None
                    ),
                })
    return rows


def report(rows: list[dict], targets: list[int]) -> None:
    print(f"{'space_in':>9} {'imgsz(med)':>11} {'got':>6} {'truth':>6} "
          f"{'ratio':>7} {'exact':>9} {'medW/sp':>8} {'conf':>6}")
    for target in targets:
        r = [x for x in rows if x["target_space"] == target]
        if not r:
            continue
        got = sum(x["got"] for x in r)
        truth = sum(x["truth"] for x in r)
        exact = sum(1 for x in r if x["got"] == x["truth"])
        widths = [x["median_width_spaces"] for x in r if x["median_width_spaces"]]
        confs = [x["median_conf"] for x in r if x["median_conf"]]
        print(f"{target:>9} {int(st.median([x['imgsz'] for x in r])):>11} "
              f"{got:>6} {truth:>6} {got / truth:>7.2f} "
              f"{str(exact) + '/' + str(len(r)):>9} "
              f"{(st.median(widths) if widths else 0):>8.2f} "
              f"{(st.median(confs) if confs else 0):>6.2f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    ap.add_argument("--work-dir", type=Path, default=Path("/tmp/detector-scale"))
    ap.add_argument("--targets", type=int, nargs="*", default=TARGETS)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    args.work_dir.mkdir(parents=True, exist_ok=True)
    rows = sweep(args.work_dir, args.weights, args.targets)
    report(rows, args.targets)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=1) + "\n")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
