"""Guard 4, measured: does a one-line percussion rule reach further into the
margins than the five-line staves it sits among?

`extract_measures` hands `_measure_x_boundaries` the system's staves, and that
function takes a MEDIAN over `x_start` and a MAX over `x_end`. If a percussion
rule's extent differs from its neighbours', admitting it to that list moves
every five-line staff's measure boundaries — which would make the whole change
non-additive. The synthetic test pins the mechanism; this measures the premise
on the real pages.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page                    # noqa: E402
from tools.omr.staff_detector import detect_staves                 # noqa: E402
from tools.omr.measure_extractor import _measure_x_boundaries, detect_barlines
from tools.library.score_library import library_root               # noqa: E402

HERE = Path(__file__).parent
MAHLER = ("editions/mahler/symphony-5/"
          "mahler--symphony-5--unidentified-scan-2016--local.pdf")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", nargs="*", type=int, default=[1, 2, 3, 4])
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args(argv)

    pdf = library_root() / MAHLER
    rows = []
    for pidx in args.pages:
        page = render_page(str(pdf), pidx, dpi=args.dpi)
        pws = detect_staves(page)
        five = [s for s in pws.staves if len(s.line_ys) >= 5]
        one = [s for s in pws.staves if len(s.line_ys) < 5]
        if not five or not one:
            continue
        detect_barlines(pws)
        bls = [b for b in pws.barlines]
        xb_five = _measure_x_boundaries(bls, five)
        xb_all = _measure_x_boundaries(bls, five + one)
        rec = {
            "page": pidx, "page_w": int(page.binary.shape[1]),
            "five_line": {"n": len(five),
                          "x_start_median": statistics.median(
                              s.x_start for s in five),
                          "x_start_min": min(s.x_start for s in five),
                          "x_end_max": max(s.x_end for s in five)},
            "one_line": {"n": len(one),
                         "x_start": [s.x_start for s in one],
                         "x_end": [s.x_end for s in one]},
            "boundaries_five_line_only": xb_five,
            "boundaries_if_rules_voted": xb_all,
            "boundaries_identical": xb_five == xb_all,
        }
        rows.append(rec)
        print(json.dumps({k: rec[k] for k in
                          ("page", "page_w", "five_line", "one_line",
                           "boundaries_identical")}), flush=True)
        if not rec["boundaries_identical"]:
            print(f"   first boundary  five-line-only {xb_five[0]}   "
                  f"if rules voted {xb_all[0]}", flush=True)
    dst = HERE / "margin-reach.json"
    dst.write_text(json.dumps({"rows": rows}, indent=1) + "\n")
    moved = sum(1 for r in rows if not r["boundaries_identical"])
    print(f"\n{moved} of {len(rows)} pages would have their measure boundaries "
          f"MOVED by letting the rules vote")
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
