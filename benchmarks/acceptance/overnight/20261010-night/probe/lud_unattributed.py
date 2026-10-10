#!/usr/bin/env python3
"""lud_unattributed: the kept -> narrowed notes whose duration-verdict guard counters did NOT differ between the
nights. What GATHER readings changed on those same notes (the diff's own `changes` lines)?"""
import collections
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lud_bars  # noqa: E402

for doc in ("brahms1-breitkopf", "beethoven5-litolff"):
    rows = [r for r in csv.DictReader(open(HERE.parent / "undecided" / f"changed-notes-{doc}.csv"))
            if r["kind"] == "kept_to_narrowed" and r["what_changed"] == "no guard counter changed"]
    keys = {r["subject"]: r for r in rows}
    d = json.load(open(lud_bars.COMPARE / f"{doc}-first-two-stages.json"))
    c = collections.Counter()
    n_g = 0
    for p in d["changed_pairs"]:
        if p["b"] in keys:
            g = [re.sub(r":.*$", "", x) for x in p["changes"] if x.startswith("GATHER")]
            n_g += bool(g)
            for x in g or ["(no GATHER line)"]:
                c[x] += 1
    print(f"{doc}: {len(rows)} notes with no guard counter changed; {n_g} of them carry a GATHER change line")
    for k, n in c.most_common():
        print(f"   {n:4d}  {k}")
    by = collections.Counter(r["tonight_reason"] for r in rows)
    print("   tonight's reasons:", dict(by))
