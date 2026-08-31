"""Build a clef-locator sweep corpus for a score the layer has never been
measured on. The method that produced `beethoven5-clef-sweep.json`, written
down so a second edition costs an afternoon instead of a session.

The corpora this layer had before the sweep all shared a blind spot: none of
them contained a bass clef the locator was liable to call a C clef, so
`FALSE POSITIVES 0` meant "nothing here to get wrong" rather than "nothing got
got wrong". A sweep corpus removes that by construction — it is built from the
locator's OWN output, so every read it makes is in the corpus whether it is
right or not.

    # 1. collect every staff the locator LOCATES a C clef on, and render a
    #    crop of each staff's head so the glyph can be read by eye
    python3 benchmarks/omr-clef-geometry/sweep_located_clefs.py \
        --pdf ~/Documents/.../Mahler_5_.pdf \
        --first 2 --last 200 --every 3 \
        --out-dir /tmp/mahler5-sweep

    # 2. read the montages, then write {page, staff, c_clef, note} rows into a
    #    corpus JSON shaped like beethoven5-clef-sweep.json and point
    #    check_clef_precision.py --sweep-spec at it.

Two things about the crops, both of which cost the first attempt real time:

*   **Neither `staff.x_start` nor the header window's `x0` is enough alone, so
    the crop is the UNION of the two.** The window is deliberately biased LEFT
    (`staff_header.left_margin_spaces`) so a reader never loses the clef off
    the front, which means on an orchestral page it usually opens in the
    instrument name — and where the window is cut at the system's initial rule
    it can end before the clef, showing "Violoncelle" and nothing else.
    `x_start` is the longest ink run, which on a scan starts in the MUSIC, so
    a crop anchored there alone opens after the clef instead. Measured on
    Mahler 5 p.72, where an `x_start`-anchored crop showed the bracket and the
    first chord on two of the two staves the locator fired on.
*   **Include the real C clefs.** The temptation is to render only the reads
    that look wrong. A corpus of only failures scores a veto that fires on
    everything as perfect, which is the exact mistake the four older corpora
    made in the other direction.

Clustering (`ClefLocatorConfig.cluster_y_gap_spaces`) is ON here by default
regardless of what ships, because the corpus should cover every read the layer
is capable of making, not only the ones the current default happens to reach.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.clef_locator import (  # noqa: E402
    DEFAULT_LOCATOR_CONFIG,
    locate_clef,
)
from tools.omr.measure_extractor import (  # noqa: E402
    detect_barlines,
    extract_measures,
    resegment_fused_measures,
)
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402


def crop_staff_head(
    rgb: np.ndarray,
    staff,
    spacing: float,
    window: tuple[int, int, int, int],
    bbox_page: tuple[int, int, int, int] | None,
    left_spaces: float,
    right_spaces: float,
    pad_spaces: float,
) -> np.ndarray:
    """The head of one staff, wide enough to hold the clef and tall enough to
    show which line it sits on.

    Anchored on `staff.x_start` and then UNIONED with the header window, which
    is the pair of bounds that survives both failure modes. The window alone
    can end before the clef (`staff_header`'s "instrument names and no clef at
    all"); `x_start` alone can begin after it, because it is the longest ink
    run and on an orchestral scan that run starts in the music. Neither is
    reliable and the union of the two always contains the glyph.
    """
    h, w = rgb.shape[:2]
    x_anchor = int(staff.x_start)
    x0 = min(window[0], x_anchor - int(left_spaces * spacing))
    x1 = max(window[2], x_anchor + int(right_spaces * spacing))
    if bbox_page is not None:
        # Whatever the locator actually fired on has to be visible, even when
        # it is outside the window a clef would live in — that is the case
        # worth seeing.
        x0 = min(x0, bbox_page[0] - int(2 * spacing))
        x1 = max(x1, bbox_page[2] + int(2 * spacing))
    y0 = int(staff.line_ys[0] - pad_spaces * spacing)
    y1 = int(staff.line_ys[-1] + pad_spaces * spacing)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return np.full((10, 10, 3), 255, np.uint8)
    out = rgb[y0:y1, x0:x1].copy()
    if bbox_page is not None:
        bx0, by0, bx1, by1 = bbox_page
        cv2.rectangle(
            out, (bx0 - x0, by0 - y0), (bx1 - x0, by1 - y0), (0, 0, 255), 2
        )
    return out


def label_strip(text: str, width: int, height: int = 26) -> np.ndarray:
    strip = np.full((height, width, 3), 255, np.uint8)
    cv2.putText(strip, text, (4, height - 8), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (0, 0, 0), 1, cv2.LINE_AA)
    return strip


def montage(tiles: list[tuple[str, np.ndarray]]) -> np.ndarray:
    width = max(t.shape[1] for _, t in tiles)
    rows: list[np.ndarray] = []
    for text, tile in tiles:
        pad = np.full((tile.shape[0], width - tile.shape[1], 3), 255, np.uint8)
        rows.append(label_strip(text, width))
        rows.append(np.hstack([tile, pad]) if pad.shape[1] else tile)
        rows.append(np.full((6, width, 3), 200, np.uint8))
    return np.vstack(rows)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--first", type=int, default=2)
    ap.add_argument("--last", type=int, default=80)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--cluster-y-gap-spaces", type=float, default=1.0,
                    help="locator clustering for the sweep; 0 disables it")
    ap.add_argument("--per-montage", type=int, default=12)
    ap.add_argument("--left-spaces", type=float, default=6.0)
    ap.add_argument("--right-spaces", type=float, default=14.0)
    ap.add_argument("--pad-spaces", type=float, default=2.5)
    args = ap.parse_args()

    if not args.pdf.exists():
        print(f"no PDF at {args.pdf}", file=sys.stderr)
        return 1

    config = dataclasses.replace(
        DEFAULT_LOCATOR_CONFIG,
        cluster_y_gap_spaces=(args.cluster_y_gap_spaces or None),
    )

    crops_dir = args.out_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    montages_dir = args.out_dir / "montages"
    montages_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    tiles: list[tuple[str, np.ndarray]] = []
    n_pages = n_headers = 0
    for page_index in range(args.first, args.last + 1, args.every):
        try:
            page = render_page(args.pdf, page_index, dpi=args.dpi)
            pws = detect_barlines(detect_staves(page))
            # The same four steps `check_clef_precision.read_page` takes, in
            # the same order, so a corpus built here is scored by that harness
            # against the identical set of header cells.
            remove_staff_lines(resegment_fused_measures(pws, extract_measures(pws)))
        except Exception as exc:  # a page that Phase 1 cannot lay out
            print(f"  p{page_index}: skipped ({type(exc).__name__}: {exc})")
            continue
        cells = header_cells_for_page(pws)
        if not cells:
            continue
        n_pages += 1
        by_index = {s.staff_index: s for s in pws.staves}
        for staff_index, cell in sorted(cells.items()):
            n_headers += 1
            found = locate_clef(cell, config=config)
            if found is None:
                continue
            staff = by_index[staff_index]
            spacing = max(1.0, staff.line_spacing_px)
            inv = 1.0 / cell.upscale_factor if cell.upscale_factor else 1.0
            # `LocatedClef.bbox` is (x, y, w, h) in the cell's own canonical
            # pixels — connectedComponentsWithStats' order, not (x0, y0, x1,
            # y1). Reading it as a corner pair puts the marker on a sliver
            # left of the clef and makes a correct read look like a fluke.
            cx, cy, cw, ch = found.bbox
            bbox_page = (
                int(cell.bbox_page_px[0] + cx * inv),
                int(cell.bbox_page_px[1] + cy * inv),
                int(cell.bbox_page_px[0] + (cx + cw) * inv),
                int(cell.bbox_page_px[1] + (cy + ch) * inv),
            )
            crop = crop_staff_head(
                page.rgb, staff, spacing, cell.bbox_page_px, bbox_page,
                args.left_spaces, args.right_spaces, args.pad_spaces,
            )
            name = f"p{page_index}_s{staff_index}"
            cv2.imwrite(str(crops_dir / f"{name}.png"), crop)
            records.append({
                "page": page_index,
                "staff": staff_index,
                "read_as": found.read.name,
                "symmetry": found.symmetry,
                "crop": f"crops/{name}.png",
            })
            tiles.append((f"{name}  read {found.read.name}  sym {found.symmetry:.3f}",
                          crop))
        print(f"  p{page_index}: {len(cells)} headers, "
              f"{sum(1 for r in records if r['page'] == page_index)} located")

    for i in range(0, len(tiles), args.per_montage):
        chunk = tiles[i:i + args.per_montage]
        out = montages_dir / f"montage_{i // args.per_montage:02d}.png"
        cv2.imwrite(str(out), montage(chunk))

    (args.out_dir / "located.json").write_text(json.dumps({
        "pdf": str(args.pdf),
        "pages": [args.first, args.last, args.every],
        "dpi": args.dpi,
        "cluster_y_gap_spaces": args.cluster_y_gap_spaces,
        "header_cells": n_headers,
        "pages_measured": n_pages,
        "located": records,
    }, indent=1))
    print(f"\n{len(records)} located of {n_headers} header cells "
          f"over {n_pages} pages")
    print(f"crops in {crops_dir}, montages in {montages_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
