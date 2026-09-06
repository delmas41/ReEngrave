"""Render one page of one edition to PNG, so a human (or a vision model) can
read the PRINT rather than an encoding of it. Deliverable-3 support.

    python3 benchmarks/omr-headline-validity-2026-09/render_page.py \
        --row beethoven-sym5-mvt1-984073-p1 --dpi 150 --out-dir /tmp/x
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))
from tools.library.score_library import library_root  # noqa: E402

SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", required=True)
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--crop", nargs=4, type=float, default=None,
                    metavar=("X0", "Y0", "X1", "Y1"),
                    help="fractions of the page box, for a legible close-up")
    ap.add_argument("--name", default=None)
    args = ap.parse_args(argv)

    rows = json.loads((SCAN / "works.json").read_text())["rows"]
    row = next(r for r in rows if r["row_id"] == args.row)
    pdf = library_root() / row["edition"]["catalog_path"]
    idx = row["page"]["pdf_page_index"]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf) as doc:
        page = doc[idx]
        rect = page.rect
        clip = None
        if args.crop:
            x0, y0, x1, y1 = args.crop
            clip = fitz.Rect(rect.x0 + x0 * rect.width,
                             rect.y0 + y0 * rect.height,
                             rect.x0 + x1 * rect.width,
                             rect.y0 + y1 * rect.height)
        pm = page.get_pixmap(dpi=args.dpi, clip=clip)
        name = args.name or f"{args.row}-p{idx}-{args.dpi}dpi.png"
        pm.save(str(out / name))
        print(f"{out / name}  {pm.width}x{pm.height}  page rect {rect}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
