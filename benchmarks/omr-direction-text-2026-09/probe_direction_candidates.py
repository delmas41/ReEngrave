"""What does the CV half propose, and what does the OCR make of it?

Two numbers this separates that the pooled metric cannot:

- **candidate recall** — a word the CV never proposes is a word no reader can
  find, and that is a different failure from one the OCR got wrong;
- **the gate's cost** — every candidate the lexicon refuses is a crop the OCR
  was paid to read, and every one it accepts wrongly is charged its own
  character count.

    # candidates only — no OCR, no venv needed, seconds per page
    python3 benchmarks/omr-direction-text-2026-09/probe_direction_candidates.py \\
        benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.pdf \\
        --crops-dir /tmp/cands

    # and read them
    python3 benchmarks/omr-direction-text-2026-09/probe_direction_candidates.py \\
        benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.pdf --read

`--crops-dir` writes each candidate as its own PNG plus a contact sheet, which
is the only way to tell a candidate that was never a word from a word the
cropping cut in half. Both failures look like "OCR returned nothing".
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.omr.direction_text import (crop_for, find_candidates,     # noqa: E402
                                      read_directions)
from tools.omr.transcribe import DEFAULT_WEIGHTS, transcribe         # noqa: E402


def contact_sheet(crops: list[np.ndarray], path: Path,
                  max_height: int = 2400) -> None:
    """One image of every crop, stacked, so a page is read in one look."""
    if not crops:
        return
    width = max(c.shape[1] for c in crops)
    rows = []
    for crop in crops:
        pad = np.full((crop.shape[0], width - crop.shape[1], 3), 255, np.uint8)
        rows.append(np.hstack([crop, pad]))
        rows.append(np.full((5, width, 3), 110, np.uint8))
    sheet = np.vstack(rows)
    if sheet.shape[0] > max_height:
        scale = max_height / sheet.shape[0]
        sheet = cv2.resize(sheet, (int(width * scale), max_height))
    cv2.imwrite(str(path), sheet)


def run(pdf: Path, *, read: bool, crops_dir: Path | None,
        weights: str, dpi: int | None) -> None:
    # The candidates are defined by SUBTRACTING the detections, so the page has
    # to be transcribed first; there is no cheaper input that carries them.
    opts = {"dpi": dpi} if dpi is not None else {}
    result = transcribe(pdf_path=pdf, pages=[0], weights=weights,
                        contextual=False, progress=False, **opts)
    page_dict = result["pages"][0]

    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves

    page = render_page(pdf, 0, dpi=(dpi or 600))
    pws = detect_staves(page)
    spacing = float(np.median([s.line_spacing_px for s in pws.staves]))

    candidates = find_candidates(pws, page_dict)
    print(f"\n=== {pdf.name}: {len(pws.staves)} staves, "
          f"{len(candidates)} candidates")
    for i, c in enumerate(candidates):
        x0, y0, x1, y1 = c.bbox_page
        print(f"  {i:3d}  staff {c.staff_index:2d} m{c.measure_index} "
              f"{c.placement:5s}  {(x1 - x0) / spacing:5.1f} x "
              f"{(y1 - y0) / spacing:4.1f} spaces  n={c.n_components}")

    if crops_dir is not None:
        crops_dir.mkdir(parents=True, exist_ok=True)
        crops = [crop_for(page, c, spacing) for c in candidates]
        for i, (c, crop) in enumerate(zip(candidates, crops)):
            cv2.imwrite(str(crops_dir / f"{pdf.stem}-c{i:03d}-s{c.staff_index:02d}"
                                        f"-m{c.measure_index}-{c.placement}.png"), crop)
        contact_sheet(crops, crops_dir / f"{pdf.stem}-sheet.png")
        print(f"  wrote {len(crops)} crops + a contact sheet to {crops_dir}")

    if read:
        directions, info = read_directions(pws, page_dict)
        print(f"  read {info['n_read']} / {info['n_candidates']}, "
              f"accepted {info['n_accepted']}")
        for d in directions:
            print(f"    staff {d.staff_index:2d} m{d.measure_index} "
                  f"{d.placement:5s} {d.category:10s} {d.text!r}")
        if info["rejected"]:
            print(f"    refused by the lexicon: {info['rejected']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="+", type=Path)
    ap.add_argument("--read", action="store_true",
                    help="also OCR the candidates and gate them (needs .venv-surya)")
    ap.add_argument("--crops-dir", type=Path, default=None)
    ap.add_argument("--weights", default=DEFAULT_WEIGHTS)
    ap.add_argument("--dpi", type=int, default=None)
    args = ap.parse_args(argv)
    for pdf in args.pdfs:
        run(pdf, read=args.read, crops_dir=args.crops_dir,
            weights=args.weights, dpi=args.dpi)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
