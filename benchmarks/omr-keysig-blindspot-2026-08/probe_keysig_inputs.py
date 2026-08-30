"""What is the detector actually SHOWN where a key signature is printed?

`benchmarks/omr-detection-probe-2026-08/findings.md` concluded that Beethoven 5
p.15's key-signature flats are undetected at conf 0.25, 0.10 and 0.05 alike, and
called that a genuine class-specific blindness rather than a scale artefact. Its
own method note says the thing to check first is what the model was shown — that
warning was written after two confident measurements turned out to describe the
instrument rather than the page.

So this probe does not ask "does the detector find flats". It dumps BOTH inputs
a key signature can be read from — the staff-start MEASURE cell (what the
detector reads) and the HEADER window (what the CV locator reads) — writes them
as PNGs to look at, and reports every class the detector returns on each, at a
sweep of confidences, with no filtering.

    python3 benchmarks/omr-keysig-blindspot-2026-08/probe_keysig_inputs.py \
        --pdf <score.pdf> --page 15 --dpi 600 --staves 0 1 2 3
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.transcribe import DEFAULT_WEIGHTS  # noqa: E402
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell  # noqa: E402

OUT = Path(__file__).resolve().parent / "crops"
KEY_CLASSES = ("keySharp", "keyFlat", "keyNatural")
ACCIDENTALS = ("accidentalSharp", "accidentalFlat", "accidentalNatural")


def report(tag: str, det, cell, confs: list[float]) -> None:
    png = OUT / f"{tag}.png"
    cv2.imwrite(str(png), cell.image)
    imgsz = imgsz_for_cell(cell)
    print(f"\n  {tag}  ({cell.image.shape[1]}x{cell.image.shape[0]} px, imgsz={imgsz})")
    for conf in confs:
        dets = det.detect(cell, conf_threshold=conf, imgsz=imgsz)
        by_class = Counter(d.smufl_name for d in dets)
        keys = {k: v for k, v in by_class.items() if k in KEY_CLASSES}
        accs = {k: v for k, v in by_class.items() if k in ACCIDENTALS}
        top = ", ".join(f"{k}x{v}" for k, v in by_class.most_common(6)) or "(nothing)"
        print(f"    conf {conf:<5} {len(dets):>4} dets | key={keys or '-'} "
              f"acc={accs or '-'} | top: {top}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--staves", type=int, nargs="*", default=None)
    ap.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    ap.add_argument("--confs", type=float, nargs="*", default=[0.25, 0.10, 0.05, 0.01])
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    page = render_page(Path(args.pdf), args.page, dpi=args.dpi)
    pws = detect_barlines(detect_staves(page))
    cells = extract_measures(pws)
    header_cells = header_cells_for_page(pws)
    det = YoloDetector(Path(args.weights), device="auto")

    first_cell = {}
    for c in cells:
        first_cell.setdefault(c.staff_index, c)

    staves = args.staves if args.staves is not None else sorted(first_cell)
    print(f"page {args.page}: {len(pws.staves)} staves, {len(cells)} cells, "
          f"{len(header_cells)} header cells; probing staves {staves}")

    for si in staves:
        print(f"\n=== staff {si} ===")
        if si in first_cell:
            report(f"s{si}_measure0", det, first_cell[si], args.confs)
        else:
            print("  (no measure cell)")
        if si in header_cells:
            report(f"s{si}_header", det, header_cells[si], args.confs)
        else:
            print("  (no header window measured)")

    print(f"\ncrops written to {OUT}")


if __name__ == "__main__":
    main()
