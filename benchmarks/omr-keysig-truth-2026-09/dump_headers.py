#!/usr/bin/env python3
"""Write every staff's HEADER CROP as a PNG, so the window can be looked at.

    python3 benchmarks/omr-keysig-truth-2026-09/dump_headers.py --page 2

Both readers work on `staff_header`'s crop and neither can see past it, so a
window that misses the signature makes the locator abstain (no run) and the
template answer `0` (a clean window) — two different-looking failures with one
cause, upstream of both. The only way to tell that from a genuinely empty
header is to look at the crop.

Build products; `benchmarks/**/crops/` is gitignored.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

PDF = ("library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
       "imslp984073.pdf")


def main(argv: list[str]) -> int:
    import cv2
    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr.staff_header import header_cells_for_page

    pages = [int(argv[argv.index("--page") + 1])] if "--page" in argv else [1]
    out = pathlib.Path(argv[argv.index("--out") + 1]) if "--out" in argv \
        else HERE / "crops"
    out.mkdir(parents=True, exist_ok=True)

    for pws, _cells in prepare_pages(str(ROOT / PDF), pages):
        p = pws.page.page_index
        local = _system_local(pws.staves)
        header = header_cells_for_page(pws)
        for st in pws.staves:
            s, i = local[st.staff_index]
            crop = header.get(st.staff_index)
            if crop is None:
                print(f"p{p}/s{s}/{i:02d}: NO HEADER CELL")
                continue
            img = crop.image
            name = out / f"p{p}-s{s}-{i:02d}.png"
            cv2.imwrite(str(name), img)
            print(f"p{p}/s{s}/{i:02d}: {img.shape[1]}x{img.shape[0]} -> {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
