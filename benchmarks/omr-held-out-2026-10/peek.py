"""peek at rows of one record: python3 peek.py REC quantity [decider-substr] [n]"""
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

R = load_record(sys.argv[1])["record"]
q = sys.argv[2]
sub = sys.argv[3] if len(sys.argv) > 3 else ""
n = int(sys.argv[4]) if len(sys.argv) > 4 else 5
k = 0
for sec in ("verdicts", "observations", "abstentions"):
    for r in R[sec]:
        if r["quantity"] == q and sub in str(r.get("decider", r.get("reader", "")) or "") + str(r.get("reason", "")):
            r = dict(r)
            for big in ("considered", "basis", "correlated", "used", "missing", "declined", "excluded"):
                r.pop(big, None)
            print(sec, json.dumps(r, default=str)[:900])
            k += 1
            if k >= n:
                sys.exit()
