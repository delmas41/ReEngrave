#!/usr/bin/env python3
"""DO THE TRUE AND FALSE SCORE POPULATIONS SEPARATE? Derived from the two
committed `score_frames` runs rather than counted by hand.

The TRUE population is `brahms1-p045`'s HEADER readings — a movement start whose
print was LOOKED AT (page 46, *Adagio*, a common-time `C` on every staff), so the
right answer is known without a truth file. The FALSE population is the same
frame on the nine CONTINUATION pages, where no meter is printed anywhere.

If an absolute floor could separate them, a score-based arbiter would at least
be conceivable. This reports the widest empty interval, and how many FALSE
readings sit at or above the weakest TRUE one.

⚠️ POSITIVE CONTROL: both populations must be non-empty and the TRUE one must
be all `C`. A zero overlap computed over an empty population is not a result,
and `--check` fails on it — never on a threshold.

    python3 .../probe/overlap.py            # the table
    python3 .../probe/overlap.py --check    # non-zero if either side is empty
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import statistics

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "out"

WITH_P045 = OUT / "score-frames.json"
NINE = OUT / "score-frames-nine.json"
TRUE_PAGE = "brahms1-p045"
TRUE_RAW = "C"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--population", default="header")
    args = ap.parse_args()

    if not WITH_P045.exists() or not NINE.exists():
        print(f"DEAD: run score_frames.py twice first — {WITH_P045.name} and "
              f"{NINE.name} are the inputs")
        return 2

    a = json.loads(WITH_P045.read_text())
    b = json.loads(NINE.read_text())
    pop = args.population
    if pop != "header":
        # ⚠️ `--population head_last` RUNS AND IS NOT A TRUTH COMPARISON, which
        # is worth refusing loudly rather than leaving as a footnote: p.45
        # prints its meter in the HEADER, so that page's LAST-cell readings are
        # false too and the "TRUE" label is simply wrong there. Printed, and
        # `--check` refuses it, because a probe that answers a question it was
        # not asked is the shape this repo already pays for.
        print(f"⚠️ `{pop}` HAS NO TRUE POPULATION — p.45 prints its meter in "
              f"the header, so its `{pop}` readings are FALSE as well. The "
              f"table below compares two false populations and is NOT an "
              f"overlap result.")

    true_rows = [r for r in a["rows"]
                 if r["page"] == TRUE_PAGE and r["population"] == pop]
    false_rows = [r for r in b["rows"] if r["population"] == pop]

    print(f"POPULATION: {pop}   floor {a['floor']}")
    print(f"  TRUE  ({TRUE_PAGE}, a movement start printing `{TRUE_RAW}`) "
          f"n={len(true_rows)}   spellings "
          f"{collections.Counter(r['raw'] for r in true_rows).most_common(3)}")
    print(f"  FALSE (nine continuation pages)                     "
          f"n={len(false_rows)}   spellings "
          f"{collections.Counter(r['raw'] for r in false_rows).most_common(3)}")
    if not true_rows or not false_rows:
        print("DEAD: one population is empty — no overlap figure is meaningful")
        return 2

    t = sorted(r["score"] for r in true_rows)
    f = sorted(r["score"] for r in false_rows)
    above = [s for s in f if s >= t[0]]
    print(f"  TRUE  min {t[0]:.4f}  median {statistics.median(t):.4f}  "
          f"max {t[-1]:.4f}")
    print(f"  FALSE min {f[0]:.4f}  median {statistics.median(f):.4f}  "
          f"max {f[-1]:.4f}")
    if f[-1] < t[0]:
        print(f"  ⚠️ THEY SEPARATE — an EMPTY INTERVAL {f[-1]:.4f} .. {t[0]:.4f}")
    else:
        print(f"  ⚠️⚠️ THEY OVERLAP: {len(above)} of {len(false_rows)} FALSE "
              f"readings score at or above the weakest TRUE one ({t[0]:.4f}), "
              f"the highest at {f[-1]:.4f}. **No absolute floor separates "
              f"them.**")

    if args.check:
        if pop != "header":
            print(f"DEAD: --check is only meaningful for `header`; `{pop}` has "
                  f"no true population on this corpus")
            return 2
        wrong = [r for r in true_rows if r["raw"] != TRUE_RAW]
        if wrong:
            print(f"DEAD: the TRUE population is not all `{TRUE_RAW}` "
                  f"({len(wrong)} rows differ) — it is not a clean truth")
            return 2
        print("CHECK OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
