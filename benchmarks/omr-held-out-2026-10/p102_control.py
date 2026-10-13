"""ROADMAP 2.102: unrefused heads still decided a hollow half (the tile control).

    python3 benchmarks/omr-held-out-2026-10/p102_control.py REC
"""
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

r = load_record(sys.argv[1])["record"]
refused = {v["subject"] for v in r["verdicts"]
           if v["quantity"] == "notehead_is_not_a_notehead"
           and v["outcome"] == "decided" and v["value"] is True}
n = 0
for v in r["verdicts"]:
    if (v["quantity"] == "duration" and v["decider"] == "adjudicate_duration"
            and v["reason"] == "hollow_head_bare_stem" and v["subject"] not in refused):
        n += 1
        if n <= 6:
            print(v["subject"])
print("unrefused hollow_head_bare_stem halves:", n)
