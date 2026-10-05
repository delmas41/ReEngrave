#!/usr/bin/env python3
"""lane-through-head-on (2026-10-04): how many IN-STAFF heads does the
through-head rule fire on when the REAL reader is run over them?

`reader_absolute_position` (the far-head reader, rung search outside the
staff) is run on every in-staff head of the two pages with the rule OFF and
ON (control: E4's flags); any head whose answer changes, or whose reason names
the rule, is listed.  (`score_chord_split_1004.py` also prints the UPPER bound
of the bare evidence function, which counts every staff line crossing a head
-- a staff line IS a thin flat line through the head -- and is why the
evidence function must only ever be called from the far-head path.)
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import score_combined_1004 as c  # noqa: E402
import score_exclusion as se  # noqa: E402
import score_standard_box as sb  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402

for d in ts.DOCS:
    D = sb.build(d)
    n = diff = rule = err = 0
    rows = []
    for h0 in D["heads_in"]:
        n += 1
        h = dict(h0, gray=D["pages"].get(h0["page"]), boxes=D["nh"].get(h0["page"], []),
                 acc=D["acc"].get(h0["page"], []))
        try:
            a = se.read(h, **c.EXC)
            b = se.read(h, **c.EXC, through_head_on_rung=True)
        except Exception as e:  # noqa: BLE001
            if err == 0: print("first error:", repr(e))
            err += 1
            continue
        if a != b:
            diff += 1
            rows.append((h["subject"], a, b))
        if "runs through the head" in str(b[1]):
            rule += 1
    print(f"{d}: in-staff heads {n}; read changed {diff}; reason names the rule {rule}; reader errors {err}")
    for r in rows[:20]:
        print("   ", r)
