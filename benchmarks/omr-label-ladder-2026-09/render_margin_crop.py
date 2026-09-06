"""Render one staff's margin region, so a label dispute is settled by the print.

The whole point of the ladder diagnosis is that "which count is larger" is not
evidence. This renders the ink the readers were looking at.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--staves", type=int, nargs="+", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    from PIL import Image
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves

    page = render_page(Path(args.pdf), args.page, dpi=args.dpi)
    pws = detect_staves(page)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(page.rgb)

    for staff in pws.staves:
        if staff.staff_index not in args.staves:
            continue
        ys = sorted(staff.line_ys)
        spacing = staff.nominal_line_spacing_px or (ys[-1] - ys[0]) / 4.0
        pad = int(2.5 * spacing)
        top = max(0, int(min(staff.line_ys)) - pad)
        bot = min(img.height, int(max(staff.line_ys)) + pad)
        # The margin is everything left of where the staff's own lines start.
        right = min(img.width, int(staff.x_start) + pad)
        left = max(0, right - int(26 * spacing))
        crop = img.crop((left, top, right, bot))
        path = out / f"p{args.page}-staff{staff.staff_index}-margin.png"
        crop.save(path)
        print(f"staff {staff.staff_index}: {path}  "
              f"({crop.width}x{crop.height} px, spacing {spacing:.1f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
