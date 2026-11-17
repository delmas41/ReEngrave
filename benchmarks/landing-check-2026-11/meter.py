"""ROADMAP 2.313 -- how many bars of the counted pages have a meter in force, per record (reads only).

    PYTHONPATH=. python3 benchmarks/landing-check-2026-11/meter.py PAGE REC.record.json [...]
"""
import collections
import sys

from tools.omr.staged.record_io import load_record

page = sys.argv[1]
for n in sys.argv[2:]:
    rec = load_record(n)["record"]
    c = collections.Counter()
    for v in rec["verdicts"]:
        q = v["quantity"]
        if q in ("meter", "bar_length", "meter_carried", "time_signature") or "meter" in q:
            if "/%s/" % page in v["subject"] or v["subject"].split("/")[1:2] == [page]:
                c[(q, v.get("outcome"))] += 1
    print(n.split("/")[-1], dict(c))
