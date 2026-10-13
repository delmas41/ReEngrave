"""ROADMAP 2.97 -- why does reconcile_duration not land a bar whose only
unwritten head is ONE narrowed note?  Loads a pickled Log (run_2_97.py's 4th
arg), and for every cell with a narrowed non-rest duration whose meter is
DECIDED, replays reconcile_duration's landing search with diagnostics.

   python3 why_2_97.py LOG.pickle OUT.json
"""
import collections
import json
import pickle
import sys

sys.path.insert(0, ".")
from tools.omr.staged import consequences as C  # noqa: E402
from tools.omr.staged.record import Kind, Outcome, Q, Subject  # noqa: E402

log = pickle.load(open(sys.argv[1], "rb"))


def diagnose(cell):
    meter = log.verdict(Q.METER, cell.at(Kind.SYSTEM))
    if meter is None or meter.outcome is not Outcome.DECIDED:
        return {"why": "meter_not_decided"}
    expected = C._bar_beats_at(meter, cell)
    if expected is None:
        return {"why": "no_meter_in_force"}
    notes, set_aside = [], 0
    for v in C._standing(log, cell, Q.DURATION):
        if v.outcome not in (Outcome.DECIDED, Outcome.NARROWED):
            continue
        if C._left_the_bar(log, v.subject) is None:
            notes.append(v)
        else:
            set_aside += 1
    narrowed = [n for n in notes if n.outcome is Outcome.NARROWED
                and not C._is_rest(n)]
    if not narrowed:
        return {"why": "no_narrowed_note"}
    cur = {v.id: (v.value if v.outcome is Outcome.DECIDED
                  else (v.candidates[0].value if v.candidates else None))
           for v in notes}
    if any(c is None for c in cur.values()):
        return {"why": "a_note_has_no_value"}
    total = C._event_totals(log, cell, notes, cur)
    if total is None:
        return {"why": "no_event_grouping"}
    land = []
    for n in notes:
        if C._is_rest(n):
            continue
        now = cur[n.id]
        if float(now.get("beats") or 0.0) != float(now.get("written") or -1.0):
            continue
        for o in C._admitted(n):
            if n.outcome is Outcome.DECIDED and o.get("beam_levels") == now.get("beam_levels"):
                continue
            moved = total - float(now.get("beats") or 0) + float(o.get("beats") or 0)
            if abs(moved - expected) < 1e-6:
                land.append((n.outcome.value, n.subject.glyph,
                             o.get("beats")))
    # does a landing exist through the narrowed notes' candidates ALONE, all
    # other notes held at their decided value (the 2.96 definition)?
    return {"why": "landings", "expected": expected, "total": total,
            "narrowed": len(narrowed), "set_aside": set_aside,
            "landings": land, "fits_now": abs(total - expected) < 1e-6}


cells = collections.OrderedDict()
for v in list(log._vrd.values()):
    if v.quantity != Q.DURATION or v.outcome is not Outcome.NARROWED:
        continue
    cur_v = log.verdict(Q.DURATION, v.subject)
    if cur_v is not None and cur_v.id == v.id:
        c = v.subject.at(Kind.CELL)
        cells[c.to_key()] = c
out = {}
cnt = collections.Counter()
for k, c in cells.items():
    d = diagnose(c)
    out[k] = d
    key = d["why"]
    if key == "landings":
        key += ":" + ("fits_now" if d["fits_now"] else "short" if d["total"] < d["expected"] else "long")
        key += ":%d_landings" % min(len(d["landings"]), 3)
        key += ":%s" % ("decided_moved" if any(l[0] == "decided" for l in d["landings"]) else "narrowed_only")
    cnt[key] += 1
for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
    print(v, k)
json.dump(out, open(sys.argv[2], "w"), indent=1, default=str)
