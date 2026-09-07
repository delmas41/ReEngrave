"""Crop every multi-bar component and draw BOTH placements on it, to be looked at.

The 2-bar reading is an inference from a counting method. Nobody had cropped
the components and looked, and the audit that preceded this branch said so
explicitly. This makes that cheap: one PNG per multi-bar component, the
component's own ink at 4x, with the fabricated bands in one colour and the
measured bands in another.

    python3 benchmarks/omr-beam-bar-bands-2026-09/dump_crops.py \
        --rows dvorak-sym9-mvt1-405834-p6 mahler-sym5-mvt1-local-p3 --out-dir /tmp/crops

Exits non-zero on a missing input or an empty result set.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.line_detection import (  # noqa: E402
    _attached_stem_count, _binary_ink, _staff_line_spacing, _stacked_bar_bands,
    detect_stems,
)
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.measure_extractor import (  # noqa: E402
    detect_barlines, extract_measures, majority_bars_by_system,
    resegment_fused_measures,
)
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402

ROWS = REPO / "benchmarks/omr-scan-e2e-2026-09/works.json"
LIB = Path(os.environ.get("OMR_LIBRARY_ROOT",
                          "/Users/seanjohnson/Desktop/ReEngrave/library"))
PAD = 14
SCALE = 4


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="+", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--dpi", type=int, default=600)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    if not ROWS.is_file():
        print(f"FATAL: {ROWS} missing", file=sys.stderr); raise SystemExit(2)
    rows = {r["row_id"]: r for r in json.loads(ROWS.read_text())["rows"]}

    written = 0
    for row_id in a.rows:
        if row_id not in rows:
            print(f"FATAL: unknown row {row_id}", file=sys.stderr); raise SystemExit(2)
        r = rows[row_id]
        pdf = LIB / r["edition"]["catalog_path"]
        if not pdf.is_file():
            print(f"FATAL: missing {pdf}", file=sys.stderr); raise SystemExit(2)
        page = render_page(pdf, int(r["page"]["pdf_page_index"]), dpi=a.dpi)
        pws = detect_barlines(detect_staves(page))
        cells = extract_measures(pws)
        cells = resegment_fused_measures(
            pws, cells, expected_bars_by_system=majority_bars_by_system(cells))
        remove_staff_lines(cells)

        for ci, cell in enumerate(cells):
            src = cell.image_no_staff if cell.image_no_staff is not None else cell.image
            if src is None or src.size == 0:
                continue
            sp = _staff_line_spacing(cell)
            if sp <= 1.0:
                continue
            stems = detect_stems(cell)
            opened = cv2.morphologyEx(
                _binary_ink(src), cv2.MORPH_OPEN,
                cv2.getStructuringElement(cv2.MORPH_RECT,
                                          (max(3, int(round(sp * 1.5))), 1)))
            num, labels, stats, _ = cv2.connectedComponentsWithStats(opened, 8)
            anchors = [s for s in stems if s.height_canonical >= sp * 2.8]
            for i in range(1, num):
                x, y, w, h, area = (int(v) for v in stats[i][:5])
                if (w < int(round(sp * 1.5)) or h < max(2, int(round(sp * 0.10)))
                        or h > max(3, int(round(sp * 2.5)))
                        or area < max(6, sp) or w / max(1, h) < 2.0):
                    continue
                if _attached_stem_count(labels, i, anchors, x, y, w, h,
                                        sp, sp * 1.0, sp * 2.5) < 2:
                    continue
                n_bars, bands = _stacked_bar_bands(labels, i, x, y, w, h)
                if n_bars < 2:
                    continue
                # The ORIGINAL cell image, not the opened mask: the opening is
                # what the detector reasons over, but a human judging "are there
                # two bars here" must see the print.
                y0, y1 = max(0, y - PAD), min(src.shape[0], y + h + PAD)
                x0, x1 = max(0, x - PAD), min(src.shape[1], x + w + PAD)
                crop = cv2.cvtColor(src[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
                crop = cv2.resize(crop, None, fx=SCALE, fy=SCALE,
                                  interpolation=cv2.INTER_NEAREST)
                sub_h = max(1, h // n_bars)
                fab = [(int(y + k * (h / n_bars)), int(sub_h)) for k in range(n_bars)]
                mea = ([(int(y + t), max(1, int(b - t + 1))) for t, b in bands]
                       if bands else fab)
                for (by, bh), col in [(p, (0, 0, 255)) for p in fab] + \
                                     [(p, (0, 170, 0)) for p in mea]:
                    cv2.rectangle(crop,
                                  ((x - x0) * SCALE, (by - y0) * SCALE),
                                  ((x + w - x0) * SCALE, (by + bh - y0) * SCALE),
                                  col, 1)
                name = (f"{row_id}__cell{ci}__comp{i}__n{n_bars}"
                        f"__sp{int(sp)}__h{h}.png")
                cv2.imwrite(str(a.out_dir / name), crop)
                written += 1

    print(f"wrote {written} crops to {a.out_dir}  (RED = fabricated even division, "
          f"GREEN = measured bands)")
    if not written:
        print("FATAL: no multi-bar components found — nothing to look at",
              file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
