"""2.97: settlements that survive Sean's evidence rule, by part and by the
evidence each eighth-or-shorter settlement cites.  python3 evidence_2_97.py ARM.pkl"""
import collections
import pickle
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record import Outcome, Q  # noqa: E402

log = pickle.load(open(sys.argv[1], "rb"))
heads = collections.Counter()
bars = collections.defaultdict(set)
ev = collections.Counter()
for v in list(log._vrd.values()):
    cur = log.verdict(Q.DURATION, v.subject)
    if cur is None or cur.id != v.id or v.outcome is not Outcome.DECIDED:
        continue
    d = v.detail or {}
    if v.decider == "infer:collapse_narrowed_by_bar":
        part = "columns" if d.get("bar_unknown_events", 1) >= 2 else "single(INFER)"
    elif v.decider == "reconcile_duration" and d.get("chord_of"):
        part = "chord"
    else:
        continue
    s = v.subject
    bars[part].add((s.page, s.system, s.staff, s.cell))
    heads[part] += 1
    lv = int((v.value or {}).get("beam_levels") or 0)
    if lv > 0:
        ev[(part, tuple(d.get("eighth_evidence") or ()))] += 1
    else:
        ev[(part, "longer/zero-level")] += 1
for p in heads:
    print(p, "bars", len(bars[p]), "heads", heads[p])
for k, n in sorted(ev.items(), key=str):
    print("  ", k, n)
