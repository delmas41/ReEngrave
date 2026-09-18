"""WHICH NOTEHEAD CLASS CARRIES THE CONTAMINATION?

The 22 boxes the width floor MISSES are not scattered: 13 of them are classed
`noteheadWhole*` -- five Litolff `staff_line_gap`s and eight Breitkopf
time-signature digit counters, every one of them a whole-class box. So the
question stops being "how wide is a notehead" and becomes "which class is the
detector using as a dustbin", which is answerable per class on the whole
population without the print.

⚠️ THIS CORROBORATES THE CROP PASS FROM A DIFFERENT DIRECTION. Its §5 found
16 of 17 whole-class heads CLASS-false by looking at the plate. This reaches
the same conclusion from the record's own geometry, with no crop. Two
instruments, one conclusion; neither is the other's evidence.

⚠️ AND IT IS WHY `[L4]` CANNOT BE SETTLED FROM THE CLASS LABEL. *A whole
notehead is wider than a black one* predicts 1.688 vs 1.180 spaces, a 43%
difference. Measured on the class, the gap is absent and the SIGN is
sometimes reversed -- but a class that is mostly not whole notes cannot
falsify a claim about whole notes. The entry stays untested and the CLASS is
what this reports.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
FLOOR = 1.0


def q(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(p * len(s)))] if s else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    out = {"floor": FLOOR}
    for pub in ("litolff", "breitkopf"):
        rows = json.loads(
            (BENCH / "out" / f"{pub}-widths.json").read_text())["rows"]
        per = {}
        for cls in sorted({r["cls"] for r in rows}):
            v = [r for r in rows if r["cls"] == cls]
            dec = [r for r in v if r["outcome"] == "decided"]
            thin = [r for r in v if r["w_page"] < FLOOR]
            per[cls] = {
                "n": len(v),
                "decided": len(dec),
                "share_decided": round(len(dec) / len(v), 4),
                "under_floor": len(thin),
                "share_under_floor": round(len(thin) / len(v), 4),
                "w_median": round(q([r["w_page"] for r in v], .5), 3),
                "h_median": round(q([r["h_page"] for r in v], .5), 3),
                "w_median_decided": (round(q([r["w_page"] for r in dec], .5), 3)
                                     if dec else None),
            }
        fam = {}
        for k in ("Black", "Half", "Whole"):
            v = [r for r in rows if k in r["cls"]]
            dec = [r for r in v if r["outcome"] == "decided"]
            fam[k] = {"n": len(v), "decided": len(dec),
                      "share_decided": round(len(dec) / len(v), 4) if v else None,
                      "under_floor": sum(1 for r in v if r["w_page"] < FLOOR),
                      "w_median": round(q([r["w_page"] for r in v], .5), 3)
                      if v else None,
                      "w_median_decided": round(
                          q([r["w_page"] for r in dec], .5), 3) if dec else None}
        out[pub] = {"by_class": per, "by_family": fam}

    Path(a.json).write_text(json.dumps(out, indent=1))
    for pub in ("litolff", "breitkopf"):
        print(f"== {pub}")
        print(f"   {'class':<24} {'n':>5} {'decided':>8} {'%dec':>7} "
              f"{'<1.0':>6} {'w med':>7} {'h med':>7}")
        for cls, c in out[pub]["by_class"].items():
            print(f"   {cls:<24} {c['n']:>5} {c['decided']:>8} "
                  f"{c['share_decided']:>6.1%} {c['under_floor']:>6} "
                  f"{c['w_median']:>7.3f} {c['h_median']:>7.3f}")
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
