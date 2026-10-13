"""ROADMAP 2.97 -- the SHAPE of every held bar that holds a narrowed head, on a
pickled Log (run_2_97.py's 4th arg) and its export report.

   python3 shape_2_97.py LOG.pickle REPORT.json OUT.json

Per held bar with >= 1 narrowed non-rest duration (a standing verdict):
  meter    : decided / abstained:<reason> / none
  printed  : does the meter reach a printed reading by `used` alone (2.81's test)
  shape    : '1 head' | '1 chord of N' | 'K events' (K narrowed events)
  landings : joint assignments of the narrowed events' OWN candidate lengths
             that land the bar, every other note held at its standing value
  cause    : why reconcile_duration (one note) could not have landed it
"""
import collections
import itertools
import json
import pickle
import sys
from fractions import Fraction

sys.path.insert(0, ".")
from tools.omr.staged import consequences as C  # noqa: E402
from tools.omr.staged import inferences as I  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Kind, Outcome, Q  # noqa: E402

log = pickle.load(open(sys.argv[1], "rb"))
rep = json.load(open(sys.argv[2]))
held = rep["bars_held_out_sum"]["held"]


def fr(x):
    return Fraction(float(x)).limit_denominator(1000)


def shape(cell):
    meter = log.verdict(Q.METER, cell.at(Kind.SYSTEM))
    mstate = "none" if meter is None else (
        "decided" if meter.outcome is Outcome.DECIDED
        else "%s:%s" % (meter.outcome.value, meter.reason))
    printed = None
    expected = None
    if meter is not None and meter.outcome is Outcome.DECIDED:
        expected = C._bar_beats_at(meter, cell)
        printed = I._printed_meter_roots(log, meter, cell) is not None
    notes = []
    for v in C._standing(log, cell, Q.DURATION):
        if v.outcome not in (Outcome.DECIDED, Outcome.NARROWED):
            continue
        if C._left_the_bar(log, v.subject) is not None:
            continue
        notes.append(v)
    narrowed = [n for n in notes if n.outcome is Outcome.NARROWED
                and not C._is_rest(n)]
    if not narrowed:
        return None
    grouping = log.verdict(Q.EVENT, cell)
    out = {"meter": mstate, "printed": printed, "expected": expected,
           "narrowed_heads": len(narrowed),
           "reasons": sorted({n.reason for n in narrowed})}
    if grouping is None or grouping.outcome is not Outcome.DECIDED:
        out["shape"] = "no_event_grouping"
        return out
    by_glyph = {v.subject.glyph: v for v in notes}
    fixed = Fraction(0)
    unknown = []
    seen = set()
    for ev in (grouping.value or {}).get("events", ()):
        ms = [by_glyph[g] for g in ev.get("glyphs", ()) if g in by_glyph]
        if not ms:
            continue
        seen.update(m.id for m in ms)
        nar = [m for m in ms if m.outcome is Outcome.NARROWED]
        if not nar:
            fixed += collections.Counter(
                fr(m.value.get("beats") or 0) for m in ms).most_common(1)[0][0]
            continue
        opts = [frozenset(fr(c.value.get("beats")) for c in m.candidates
                          if isinstance(c.value, dict)
                          and c.value.get("beats") is not None) for m in nar]
        unknown.append({"heads": len(ms), "narrowed": len(nar),
                        "mixed": len(nar) != len(ms),
                        "same": len(set(opts)) == 1,
                        "opts": sorted(set.intersection(*map(set, opts)))
                        if opts else []})
    for v in notes:
        if v.id not in seen and v.outcome is Outcome.NARROWED:
            unknown.append({"heads": 1, "narrowed": 1, "mixed": False,
                            "same": True, "opts": sorted(
                                {fr(c.value.get("beats")) for c in v.candidates
                                 if isinstance(c.value, dict)})})
        elif v.id not in seen:
            fixed += fr(v.value.get("beats") or 0)
    k = len(unknown)
    if k == 1 and unknown[0]["heads"] == 1:
        out["shape"] = "1 head"
    elif k == 1:
        out["shape"] = "1 chord of %d" % unknown[0]["heads"]
    else:
        out["shape"] = "%d events" % k
    out["any_mixed"] = any(u["mixed"] for u in unknown)
    out["any_not_same"] = any(not u["same"] for u in unknown)
    if expected is not None and k <= 12:
        tgt = fr(expected)
        n = 0
        for combo in itertools.product(*[u["opts"] or [Fraction(0)] for u in unknown]):
            if fixed + sum(combo) == tgt:
                n += 1
        out["landings"] = n
    return out


rows = {}
cnt = collections.Counter()
for h in held:
    c = R.cell(h["page"], h["system"], h["staff"], h["cell"])
    s = shape(c)
    if s is None:
        continue
    rows["%d/%d/%d/%d" % (h["page"], h["system"], h["staff"], h["cell"])] = s
    key = (s["meter"] if not s["meter"].startswith("abstained") else "abstained",
           s.get("printed"), s["shape"] if s["shape"].count(" ") < 2 and not s["shape"].endswith("events") else "events:" + s["shape"],
           "unique" if s.get("landings") == 1 else ("none" if s.get("landings") == 0 else ("many" if s.get("landings") else "?")))
    cnt[key] += 1
for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
    print(v, k)
print("held bars with a narrowed head:", len(rows), "of", len(held))
json.dump(rows, open(sys.argv[3], "w"), indent=1, default=str)
