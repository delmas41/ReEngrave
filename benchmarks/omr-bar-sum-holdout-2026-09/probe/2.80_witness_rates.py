"""2.80: how often does the missed-rest witness answer clear / unexplained over
EVERY cell of a record (not just the few it is asked about)? A witness that
says 'unexplained' on nearly every bar is a blanket refusal, not a witness.

    python3 .../2.80_witness_rates.py REC.json
"""
import collections
import sys

sys.path.insert(0, ".")
from tools.omr.staged import consequences as C, record as R  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun  # noqa: E402

doc = load_record(sys.argv[1])
rec = doc["record"] if "record" in doc else doc
log, _ = rerun.rebuild_gather(rec)
rerun.run_stages(log)
cnt = collections.Counter()
left_hist = collections.Counter()
n_cells = 0
for o in rec["observations"]:
    if o["quantity"] != R.Q.CELL_INK_PIECES:
        continue
    cell = R.Subject.from_key(o["subject"])
    n_cells += 1
    ans, left = C._missed_rest_witness(log, cell)
    cnt[ans] += 1
    if left is not None:
        left_hist[min(left, 6)] += 1
print("cells with a pieces row:", n_cells, dict(cnt))
print("unexplained pieces per cell (6 = 6+):", dict(sorted(left_hist.items())))
