#!/usr/bin/env python3
"""Mine pages where our system grouping and LEGATO's disagree.

`findings.md` put connectivity grouping at 12/14 pages, against ground truth
read off the left brackets by eye. Fourteen pages is what hand-labelling buys,
and the two failures are both MERGES — a real break that something crosses —
which is exactly the case a bracket count is slowest to find.

`guangyangmusic/legato-1.5-YOLO` is a single-class `system` detector, 25.9M
params, trained on 1,024 annotated pages spanning single-staff to orchestral.
It is NOT ground truth: it is a model, trained by other people on data we cannot
see, and on a scan it has never met it can be wrong in ways its own val set
never showed. What it is, is CHEAP — so it can look at hundreds of pages and say
which handful are worth a human's eye.

That is the whole design: **a miner, not a label source.** Every disagreement it
reports still has to be adjudicated by looking at the page. What changes is that
we look at six pages instead of six hundred.

COMPARE PARTITIONS, NOT COUNTS. Two groupings can both say "2 systems" and
disagree about which staves are in which — and a merge paired with a split is
precisely the failure mode the gap heuristic used to produce. So each of our
staves is assigned to whichever LEGATO box contains its centre, and the two
partitions of the SAME staves are compared.

    python3 benchmarks/omr-system-grouping-2026-08/legato_crosscheck.py \
        --weights ~/path/legato-1.5-YOLO.pt --limit 40

The weights are AGPL-3.0 (inherited from ultralytics), which is why this lives
in benchmarks/ and nothing in tools/omr imports it.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

HERE = Path(__file__).resolve().parent
CORPUS = "/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp"
LOOSE = ("/Users/seanjohnson/Documents/Gradus-Assets/Scores/"
         "Scores For Gradus/PDF Scores")
BEET5 = ("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/"
         "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf")


def our_partition(staves) -> dict[int, int]:
    """`{staff_index: system_index}` as the pipeline sees it."""
    return {s.staff_index: s.system_index for s in staves}


def legato_partition(model, page_rgb, staves, *, imgsz: int, conf: float):
    """`{staff_index: legato_box_id}`, plus the boxes themselves.

    A staff whose centre falls in no box gets `-1`. That is a signal in itself —
    LEGATO missing a staff we found is as interesting as the two disagreeing
    about where a boundary is.
    """
    from PIL import Image

    result = model.predict(Image.fromarray(page_rgb), imgsz=imgsz, conf=conf,
                           verbose=False)[0]
    boxes = []
    for box in result.boxes:
        x0, y0, x1, y1 = (float(v) for v in box.xyxy[0].tolist())
        boxes.append({"y0": y0, "y1": y1, "x0": x0, "x1": x1,
                      "conf": float(box.conf[0])})
    boxes.sort(key=lambda b: b["y0"])

    assignment = {}
    for staff in staves:
        centre = (staff.top_y + staff.bottom_y) / 2.0
        hit = -1
        for i, box in enumerate(boxes):
            if box["y0"] <= centre <= box["y1"]:
                hit = i
                break
        assignment[staff.staff_index] = hit
    return assignment, boxes


def classify(ours: dict[int, int], theirs: dict[int, int]) -> str:
    """How the two partitions differ, over the staves LEGATO placed at all.

    Named from OUR point of view: `we_merge` means LEGATO splits a group we
    hold together, which is the failure mode `findings.md` says is left.
    """
    shared = [i for i in ours if theirs.get(i, -1) >= 0]
    if not shared:
        return "no_overlap"

    # Same partition iff the two labellings agree on every PAIR of staves.
    we_merge = we_split = False
    for a_i in range(len(shared)):
        for b_i in range(a_i + 1, len(shared)):
            a, b = shared[a_i], shared[b_i]
            same_ours = ours[a] == ours[b]
            same_theirs = theirs[a] == theirs[b]
            if same_ours and not same_theirs:
                we_merge = True
            elif same_theirs and not same_ours:
                we_split = True
    if we_merge and we_split:
        return "boundary_moved"
    if we_merge:
        return "we_merge"
    if we_split:
        return "we_split"
    return "agree"


def cases(limit: int) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for pdf in sorted(glob.glob(f"{CORPUS}/*/pdfs/*/score.pdf")):
        out += [(pdf, p) for p in (10, 20, 30, 40, 50, 59, 70)]
    if Path(BEET5).is_file():
        out += [(BEET5, p) for p in range(5, 80, 5)]
    for name in sorted(glob.glob(f"{LOOSE}/*.pdf")):
        out += [(name, p) for p in (2, 10, 20)]
    return out[:limit] if limit else out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True, type=Path)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--imgsz", type=int, default=800,
                    help="LEGATO was trained at 800; larger is not better")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", type=Path, default=HERE / "legato-crosscheck.json")
    args = ap.parse_args()

    from ultralytics import YOLO
    model = YOLO(str(args.weights))

    tally = collections.Counter()
    rows = []
    for pdf, page_index in cases(args.limit):
        try:
            page = render_page(pdf, page_index, dpi=args.dpi)
            staves = sorted(detect_staves(page).staves, key=lambda s: s.top_y)
        except Exception as exc:                              # noqa: BLE001
            print(f"  skip {Path(pdf).name} p{page_index}: "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        if not staves:
            continue

        ours = our_partition(staves)
        theirs, boxes = legato_partition(model, page.rgb, staves,
                                         imgsz=args.imgsz, conf=args.conf)
        verdict = classify(ours, theirs)
        tally[verdict] += 1

        n_ours = len(set(ours.values()))
        unplaced = sum(1 for v in theirs.values() if v < 0)
        rows.append({
            "pdf": pdf, "page_index": page_index, "verdict": verdict,
            "staves": len(staves), "our_systems": n_ours,
            "legato_systems": len(boxes), "staves_legato_missed": unplaced,
            "our_sizes": sorted(collections.Counter(ours.values()).values(),
                                reverse=True),
            "legato_sizes": sorted(collections.Counter(
                v for v in theirs.values() if v >= 0).values(), reverse=True),
            "boxes": boxes,
        })
        flag = "" if verdict == "agree" else "  <-- LOOK"
        print(f"  {Path(pdf).name[:34]:34s} p{page_index:<3d} "
              f"staves {len(staves):2d}  ours {n_ours}  legato {len(boxes)}  "
              f"missed {unplaced:2d}  {verdict}{flag}")

    args.out.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"\n{sum(tally.values())} pages")
    for verdict, n in tally.most_common():
        print(f"  {verdict:16s} {n:4d}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
