"""Does this four-page gather reproduce the committed single-page one?

⚠️ WHY IT IS THE CONTROL THAT MATTERS. Everything this lane reports rests on a
gather THIS SESSION made. The 2026-09-18 lane committed a gather of the SAME
plate's page 1, from a different branch, four days earlier, in a separate
process with its own detector load. If the two disagree about the population,
every number here is about my run rather than about the document -- and a
detector's confidences are already recorded in this repo moving on
byte-identical code, so agreement was not a foregone conclusion.

It compares POPULATIONS (row counts per quantity) and then the exact SUBJECT
KEY SET for the ink rows, which is the stronger claim: a matching count with a
different key set would mean the same number of different things.

⚠️ It is DEAD if the single-page artefact is absent, and says so rather than
reporting a vacuous pass.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

QUANTITIES = ("ink", "glyph_box", "glyph_conf", "notehead_class", "stem",
              "cell_staff_space", "beam_stroke", "rest")


def rows(path):
    with open(path) as f:
        doc = json.load(f)
    log = doc["record"] if "record" in doc else doc
    return log["observations"]


def on_page(obs, page, q):
    return [o for o in obs
            if o.get("quantity") == q
            and (o.get("subject") or "").split("/")[1:2] == [page]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--four-page", required=True)
    ap.add_argument("--single-page", default=(
        "benchmarks/omr-ink-first-2026-09/out/"
        "brahms1-breitkopf-p2.gather.json"))
    ap.add_argument("--page", default="1",
                    help="the page coordinate the single-page gather holds. "
                         "⚠️ It is 1, not 2: that artefact is named for the "
                         "HUMAN page (1-based) and `--pages` is 0-based, so "
                         "its subjects read glyph/1/... . Joining on the name "
                         "rather than the coordinate would compare two "
                         "different pages and report a clean disagreement.")
    a = ap.parse_args()

    if not os.path.exists(a.single_page):
        print(f"DEAD: {a.single_page} is not here, so nothing is compared.")
        return 2

    four, single = rows(a.four_page), rows(a.single_page)
    print(f"four-page  : {a.four_page} ({len(four)} observations)")
    print(f"single-page: {a.single_page} ({len(single)} observations)")
    print(f"comparing page coordinate {a.page!r}\n")

    ok = True
    for q in QUANTITIES:
        s, f = len(on_page(single, a.page, q)), len(on_page(four, a.page, q))
        same = s == f
        ok = ok and same
        print(f"  {q:18} single {s:>6}   four {f:>6}   "
              f"{'IDENTICAL' if same else 'DIFFER %+d' % (f - s)}")

    ks = {o["subject"] for o in on_page(single, a.page, "ink")}
    kf = {o["subject"] for o in on_page(four, a.page, "ink")}
    print(f"\n  ink subject key SET identical: {ks == kf}"
          f"   (single-only {len(ks - kf)}, four-only {len(kf - ks)})")
    if not ks:
        print("  DEAD: no ink rows on that page in the single-page gather.")
        return 2
    ok = ok and (ks == kf)
    print(f"\n{'PASS' if ok else 'FAIL'}: the two independent gathers "
          f"{'agree about' if ok else 'DISAGREE about'} this page's population.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
