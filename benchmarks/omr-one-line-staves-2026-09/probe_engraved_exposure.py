"""Does the ENGRAVED eleven-work benchmark contain a one-line staff at all?

If it does not, `OMR_ONE_LINE_STAVES` is byte-identical there by construction
and a full engraved run measures nothing. If it does, the flag can move the
headline benchmark and the run is mandatory.

Two questions, asked separately because they are different:

  PRINTED   does the fixture's own LilyPond source set `line-count = #1`?
            That is what the truth says the page shows.
  DETECTED  does `staff_detector` come back with a `len(line_ys) < 5` staff?
            That is what the flag would admit.

The first is free. The second costs one phase-1 pass per fixture PDF.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page                    # noqa: E402
from tools.omr.staff_detector import detect_staves                 # noqa: E402
from tools.omr.accuracy_record import BENCHMARK_WORKS              # noqa: E402

# Fixtures are build products and are regenerated into the work-dir on each
# run; the committed default location is the main checkout's.
FIX = Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/"
           "omr-orchestral-e2e/fixtures")
OUT = Path(__file__).parent


def main() -> int:
    rows = []
    for work in BENCHMARK_WORKS:
        ly = FIX / f"{work}.ly"
        pdf = FIX / f"{work}.pdf"
        rec: dict = {"work": work}
        if ly.is_file():
            src = ly.read_text(errors="replace")
            rec["printed_one_line"] = len(
                re.findall(r"line-count\s*=\s*#1\b", src))
            rec["percussion_clef"] = src.count('\\clef "percussion"')
        if not pdf.is_file():
            rec["error"] = "no fixture pdf"
            rows.append(rec)
            print(json.dumps(rec))
            continue
        page = render_page(str(pdf), 0, dpi=600)
        pws = detect_staves(page)
        one = [s for s in pws.staves if len(s.line_ys) < 5]
        rec.update({
            "detected_staves": len(pws.staves),
            "detected_one_line": len(one),
            "one_line": [{"staff_index": s.staff_index,
                          "y": int(s.line_ys[0]),
                          "x_start": int(s.x_start), "x_end": int(s.x_end),
                          "spacing": s.nominal_line_spacing_px} for s in one],
        })
        rows.append(rec)
        print(json.dumps(rec), flush=True)
    dst = OUT / "engraved-exposure.json"
    dst.write_text(json.dumps({"rows": rows}, indent=1) + "\n")
    print("\nprinted one-line staves:",
          sum(r.get("printed_one_line", 0) for r in rows))
    print("detected one-line staves:",
          sum(r.get("detected_one_line", 0) for r in rows))
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
