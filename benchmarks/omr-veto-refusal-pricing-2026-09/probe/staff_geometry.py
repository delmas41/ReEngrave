"""Phase-1 only: where does the staff detector put each staff on these pages?

The pricing question needs to know WHICH printed staff each detected staff is,
and on page 86 the detector reads 16 staves against 17 printed — so the slot map
alone cannot say which string staff was dropped. This dumps the detected staff
bands at the same dpi the composition harness ran at (600), so a crop of the
printed page at each band settles the identity by its own clef.

No YOLO, no margin reader: render + detect_staves only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.preprocessing import render_page          # noqa: E402
from tools.omr.staff_detector import detect_staves       # noqa: E402

PDF = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
           "symphony-5-op67/"
           "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
           "imslp984073.pdf")
PAGES = (56, 57, 63, 86)
DPI = 600


def main() -> None:
    out = {}
    for page_index in PAGES:
        pws = detect_staves(render_page(PDF, page_index, dpi=DPI))
        staves = [
            {"idx": s.staff_index, "system": s.system_index,
             "y0": float(min(s.line_ys)), "y1": float(max(s.line_ys)),
             "x0": float(s.x_start), "x1": float(s.x_end)}
            for s in pws.staves
        ]
        out[str(page_index)] = {
            "h": int(pws.page.binary.shape[0]),
            "w": int(pws.page.binary.shape[1]),
            "staves": staves,
        }
        from collections import Counter
        print(page_index, "staves", len(staves), "systems",
              sorted(Counter(s["system"] for s in staves).items()), flush=True)
    dest = Path(__file__).resolve().parents[1] / "out" / "staffgeom600.json"
    dest.write_text(json.dumps(out, indent=1))
    print("wrote", dest)


if __name__ == "__main__":
    main()
