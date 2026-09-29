"""ROADMAP 2.6b — one-off check: `ROADMAP.md` names 'owned_by_another_staff
(6,008 Brahms heads)'; `extract_losers_2_6b.py` measures 3,590 for NOTEHEAD
category alone on the same (current, `f4168dfd`) record. Is the gap other
glyph categories also carrying a `glyph_owner` verdict naming another staff?

Answer: no single category or small combination lands on 6,008 either
(FINDINGS.md §12). Kept as the record of that check, not as a deliverable.

    python3 benchmarks/omr-owner-domain-2026-09/check_category_breakdown_2_6b.py
"""
from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from tools.omr.staged.record_io import load_record  # noqa: E402
from extract_losers_2_6b import REC_PATH, own_of  # noqa: E402


def main() -> int:
    t0 = time.time()
    rec = load_record(REC_PATH)["record"]
    print(f"loaded in {time.time() - t0:.1f}s")

    glyph_cat = {}
    for o in rec["observations"]:
        if o["quantity"] != "glyph_box":
            continue
        d = o.get("detail") or {}
        glyph_cat[o["subject"]] = d.get("category")

    sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    by_cat_all = Counter()
    by_cat_lost = Counter()
    for v in rec["verdicts"]:
        if v["quantity"] != "glyph_owner" or v["id"] in sup:
            continue
        if v["outcome"] != "decided":
            continue
        sub = v["subject"]
        cat = glyph_cat.get(sub, "UNKNOWN")
        by_cat_all[cat] += 1
        own = own_of(sub)
        winner = v["value"]
        if winner and winner != own:
            by_cat_lost[cat] += 1

    print("all decided glyph_owner verdicts by category:", by_cat_all)
    print()
    print("LOSERS (own staff != winner) by category:", by_cat_lost)
    print("total losers, all categories:", sum(by_cat_lost.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
