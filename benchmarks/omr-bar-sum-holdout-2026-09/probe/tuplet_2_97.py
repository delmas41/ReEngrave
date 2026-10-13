"""2.97: how many SETTLED bars hold tuplet evidence?  python3 tuplet_2_97.py ARM.pkl"""
import pickle
import sys

sys.path.insert(0, ".")
from tools.omr.staged import consequences as C  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Outcome, Q  # noqa: E402

log = pickle.load(open(sys.argv[1], "rb"))
bars = set()
for v in list(log._vrd.values()):
    cur = log.verdict(Q.DURATION, v.subject)
    if cur is None or cur.id != v.id or v.outcome is not Outcome.DECIDED:
        continue
    if v.decider == "infer:collapse_narrowed_by_bar" or (
            v.decider == "reconcile_duration" and (
                (v.detail or {}).get("chord_of") or (v.detail or {}).get("settled_alongside"))):
        s = v.subject
        bars.add((s.page, s.system, s.staff, s.cell))
n = 0
for k in bars:
    cell = R.cell(*k)
    notes = [q for q in C._standing(log, cell, Q.DURATION)]
    n += C._bar_has_tuplet(log, cell, notes)
print(len(bars), "settled bars;", n, "hold tuplet evidence")
