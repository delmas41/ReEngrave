"""ROADMAP 2.313 -- re-adjudicate a saved gather on THIS tree (cwd) and write the record (ADJUDICATE..INFER; the gather rows are kept).

    PYTHONPATH=. python3 benchmarks/landing-check-2026-11/readj.py GATHER.record.json OUT.record.json

The same call `lane_report --from adjudicate` makes (`review.rerun.rebuild_gather` + `run_stages`), on one saved record. Run it from a tree
without a landing to get that landing's OFF arm when the landing has no switch (the r14 flag rules).
"""
import json
import sys

from tools.omr.staged.record_io import load_record
from tools.omr.staged.review import rerun as RR

result = load_record(sys.argv[1])
rec = result["record"] if "record" in result else result
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
json.dump({"record": log.to_json(), "summary": log.summary(), "provenance": result.get("provenance")}, open(sys.argv[2], "w"), default=str)
print("re-adjudicated", sys.argv[1].split("/")[-1], "->", sys.argv[2].split("/")[-1], "on", __import__("os").getcwd().split("/")[-1])
