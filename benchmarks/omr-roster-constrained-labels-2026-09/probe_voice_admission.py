#!/usr/bin/env python3
"""Does any work that HAS singers fail to admit the voice family?

The veto's whole population is the voice family — 20,935 of the cross-product
firings — so the one way it can do real damage is a roster that drops the
singers of a work that has them: every vocal staff of an opera would then be
stripped of its name. This asks the question directly, over all 223 catalogued
works, and it needs no page and no OMR.

An INDEPENDENT signal is used on purpose: the work's IMSLP page TITLE and its
`Instrumentation` field, not the parsed roster the veto reads. A work whose
title says *Mass*, *Requiem*, *opera*, *Lieder*, *chorus* is a vocal work
whatever the parse made of it.

    python3 benchmarks/omr-roster-constrained-labels-2026-09/probe_voice_admission.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import work_roster as W                      # noqa: E402

#: Words that mean "this work has singers", read off the title and the raw
#: instrumentation fields — never off the parsed roster.
#:
#: ⚠️ `bass`, `alto` and `tenor` are DELIBERATELY ABSENT. The first cut held
#: them and flagged 39 works, most of them for `bass clarinet` and `bass drum`
#: — the detector's own false alarms, which would have buried the four real
#: ones. A screen for a rare fault has to be specific or its output is noise.
VOCAL_WORDS = re.compile(
    r"(?<![a-z])(mass|messe|missa|requiem|oratorio|cantata|kantate|opera|oper|"
    r"operetta|lieder|chorus|choir|coro|choral|chorale|"
    r"vocal|voice|voices|soprano|sopran|baritone|bariton|singstimme|"
    r"stabat|magnificat|te deum|motet|passion|passione|vespers|cast|narrator"
    r")(?![a-z])")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=BENCH / "voice-admission.json")
    args = ap.parse_args(argv)

    catalog = json.loads((ROOT / "data" / "score-library" / "catalog.json").read_text())
    rows, misses = [], []
    for wid, work in sorted(catalog["works"].items()):
        entry = work.get("instrumentation") or {}
        roster = W.work_roster(wid)
        if roster is None:
            continue
        title = (entry.get("imslp_page") or "") + " " + wid.replace("--", " ")
        raw = " ".join(str(v) for v in (entry.get("raw") or {}).values())
        looks_vocal = bool(VOCAL_WORDS.search((title + " " + raw).lower()))
        admits = roster.admits_family("voice")
        rows.append({"work_id": wid, "looks_vocal": looks_vocal,
                     "admits_voice": admits, "complete": roster.complete})
        if looks_vocal and not admits and roster.complete:
            misses.append((wid, entry.get("imslp_page", ""),
                           raw[:120].replace("\n", " ")))

    n = len(rows)
    vocal = sum(r["looks_vocal"] for r in rows)
    admits = sum(r["admits_voice"] for r in rows)
    print(f"{n} works with a roster; {vocal} look vocal by title/field; "
          f"{admits} admit the voice family")
    print(f"\n{len(misses)} would be VETOED WRONGLY (look vocal, roster admits "
          f"no voice, parse complete):")
    for wid, page, raw in misses:
        print(f"  {wid:44} {page[:52]}")
        print(f"      raw: {raw}")
    args.out.write_text(json.dumps(
        {"n": n, "looks_vocal": vocal, "admits_voice": admits,
         "misses": [m[0] for m in misses], "rows": rows}, indent=1) + "\n")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
