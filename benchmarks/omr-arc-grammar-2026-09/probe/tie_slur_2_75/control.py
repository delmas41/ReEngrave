"""CONTROL: a replay on the OLD code must reproduce the record's own arc_kind
verdicts (N of N), or every before/after below measures the harness.

usage: control.py record.json rows_from_old_code.json
"""
import json
import sys

from tools.omr.staged import record_io

rec = record_io.load_record(sys.argv[1])["record"]
own = {v["subject"]: (v["outcome"], v["value"]) for v in rec["verdicts"]
       if v["quantity"] == "arc_kind"}
rows = json.load(open(sys.argv[2]))
same = sum(1 for r in rows if own.get(r["sub"]) == (r["outcome"], r["kind"]))
print("replay on old code reproduces %d of %d arc_kind verdicts" % (same, len(rows)))
bad = [r["sub"] for r in rows if own.get(r["sub"]) != (r["outcome"], r["kind"])][:5]
print("first mismatches:", bad)
sys.exit(0 if same == len(rows) else 1)
