"""2.97 A/B numbers: python3 stats_2_97.py LABEL ARM.pkl BASE_REPORT.json ARM_REPORT.json
 - held bars before/after, released / newly held, notes reaching the file
 - bars the arm SETTLED, by part (single / chord / columns), heads settled
 - the control that must be 0: a settled value NOT among the superseded
   verdict's own candidates."""
import collections
import json
import pickle
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
from tools.omr.staged.record import Outcome, Q  # noqa: E402



def part_of(v):
    if v.decider == "reconcile_duration":
        if (v.detail or {}).get("chord_of"):
            return "chord"
        if (v.detail or {}).get("settled_alongside"):
            return "single"
        return None
    if v.decider == "infer:collapse_narrowed_by_bar":
        return "columns" if (v.detail or {}).get("bar_unknown_events", 1) >= 2 else "single"
    return None


label, pk, brep, arep = sys.argv[1:5]
log = pickle.load(open(pk, "rb"))
b, a = json.load(open(brep)), json.load(open(arep))


def held(r):
    return {(h["page"], h["system"], h["staff"], h["cell"]) for h in r["bars_held_out_sum"]["held"]}


hb, ha = held(b), held(a)
print(label, "held", len(hb), "->", len(ha), "released", len(hb - ha), "newly held", len(ha - hb))
print(" bars_held_out_sum.bars", b["bars_held_out_sum"]["bars"], "->", a["bars_held_out_sum"]["bars"])
print(" notes in file", b["written"]["notes"], "->", a["written"]["notes"])
print(" duration_narrowed not written", b["notes_not_written"].get("duration_narrowed"), "->",
      a["notes_not_written"].get("duration_narrowed"))
bars = collections.defaultdict(set)
heads = collections.Counter()
outside = 0
for v in list(log._vrd.values()):
    cur = log.verdict(Q.DURATION, v.subject)
    if cur is None or cur.id != v.id or v.outcome is not Outcome.DECIDED:
        continue
    p = part_of(v)
    if p is None:
        continue
    s = v.subject
    bars[p].add((s.page, s.system, s.staff, s.cell))
    heads[p] += 1
    old = log._vrd.get(v.supersedes)
    cands = [c.value.get("beats") for c in (old.candidates if old else [])
             if isinstance(c.value, dict)]
    if old is not None and old.outcome is Outcome.NARROWED and \
            (v.value or {}).get("beats") not in cands:
        outside += 1
rel = hb - ha
for p in ("single", "chord", "columns"):
    print(" part", p, "bars settled", len(bars[p]), "heads", heads[p],
          "of which bars released from the held list", len(bars[p] & rel))
print(" settled value NOT among its own candidates (must be 0):", outside)
