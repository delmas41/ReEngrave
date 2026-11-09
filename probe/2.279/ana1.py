"""2.279 analysis 1: sort the dropped real-note heads (probe_a rows) by what is left to decide them.

usage: python3 probe/2.279/ana1.py ROWS.jsonl [OUT_PATTERNS.json]

For duration_narrowed / chord_value_undecided: the candidate set, the reader's own ordering (and whether that ordering
is a measured likelihood or only a historical order), and whether the BAR (the partial bar's own `gap_quarters`, which is the
space the unread glyphs leave) lands on exactly one of the candidates. For no_pitch: the staff, its clef verdict, and its
instrument. Counts are heads (representatives of distinct ink), then events (stems).
"""
import collections
import itertools
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1])]
EPS = 1e-6


def event_key(r):
    mem = tuple(sorted([r["sub"]] + [s["sub"] for s in r["sibs"]]))
    return mem


def cand_beats(r):
    """candidates of the event: common to all members (a chord on one stem shares one value)."""
    cs = [c["beats"] for c in (r["dur"] or {}).get("cands", []) if c.get("beats") is not None]
    return cs


def top_by_reader(r):
    """The reader's own top candidate and what kind of claim that order is.
    beams_ambiguous: 'a stroke that certainly covers the note outranks one that merely might' (support 2.0 vs 1.0).
    beam_discounted_uncertain: historical order (eighth first) unless OMR_BARE_STEM_RANK; measured: unbeamed right 54/76."""
    cs = (r["dur"] or {}).get("cands", [])
    if not cs:
        return None, "none"
    sups = sorted({c["support"] for c in cs}, reverse=True)
    if len(sups) == 1:
        return None, "flat"
    best = [c for c in cs if c["support"] == sups[0]]
    if len(best) != 1:
        return None, "tie"
    reason = r["dur"]["reason"]
    if reason == "beams_ambiguous":
        return best[0]["beats"], "certain_outranks_possible"
    if reason == "beam_discounted_uncertain":
        return best[0]["beats"], "historical_order"
    return best[0]["beats"], "reader_order:" + str(reason)


# bar landing, per cell: events dropped in the cell vs the partial bar's gap
by_cell = collections.defaultdict(list)
for r in rows:
    if r["bucket"] in ("refused:duration_narrowed",):
        by_cell[tuple(r["cell"])].append(r)

land = {}   # sub -> (n_fills, set(values this event takes in a fill))
for cell, rs in by_cell.items():
    b = rs[0]["bar"]
    if not rs[0]["bar_status"].startswith("partial") or b is None or b.get("gap_quarters") is None or b.get("two_voice"):
        continue
    # other unread things in the same bar that are not these events make the gap uncertain
    ug = b.get("unread_glyphs") or []
    only_these = all(g == "duration_narrowed" for g in ug)
    evs = collections.OrderedDict()
    for r in rs:
        evs.setdefault(event_key(r), r)
    evl = list(evs.values())
    cl = [cand_beats(r) for r in evl]
    if any(not c for c in cl):
        continue
    gap = b["gap_quarters"]
    fills = [combo for combo in itertools.product(*cl) if abs(sum(combo) - gap) < EPS]
    for i, r in enumerate(evl):
        vals = {combo[i] for combo in fills}
        for m in rs:
            if event_key(m) == event_key(r):
                land[m["sub"]] = (len(fills), vals, only_these, len(evl))

print("== duration_narrowed ==")
nar = [r for r in rows if r["bucket"] == "refused:duration_narrowed"]
tab = collections.Counter()
for r in nar:
    top, kind = top_by_reader(r)
    L = land.get(r["sub"])
    if L is None:
        bar = "bar_n/a:" + r["bar_status"]
    else:
        nf, vals, only_these, nev = L
        if nf == 0:
            bar = "bar_fits_none"
        elif len(vals) == 1:
            v = next(iter(vals))
            if top is None:
                bar = "bar_picks_one(reader_flat)"
            elif abs(v - top) < EPS:
                bar = "bar_agrees_with_reader_top"
            else:
                bar = "bar_disagrees_with_reader_top"
        else:
            bar = "bar_ambiguous"
    tab[(r["dur"]["reason"], kind, bar)] += 1
for k, n in sorted(tab.items(), key=lambda kv: -kv[1]):
    print("%5d  %s" % (n, k))

print("== chord_value_undecided ==")
ch = [r for r in rows if r["bucket"] == "refused:chord_value_undecided"]
tab = collections.Counter()
for r in ch:
    heads = [r] + r["sibs"]
    vals = collections.Counter((h["dur"] or {}).get("beats") for h in heads if (h["dur"] or {}).get("outcome") == "decided")
    sv = r["stem_value"] or {}
    tab[(sv.get("outcome"), sv.get("reason"), tuple(sorted(vals.items(), key=lambda kv: str(kv[0]))))] += 1
for k, n in sorted(tab.items(), key=lambda kv: -kv[1])[:20]:
    print("%5d  %s" % (n, k))

print("== no_pitch ==")
npch = [r for r in rows if r["bucket"] == "refused:no_pitch"]
tab = collections.Counter((tuple(r["cell"][:3]), (r["clef"] or {}).get("outcome"), (r["clef"] or {}).get("reason")) for r in npch)
for k, n in sorted(tab.items(), key=lambda kv: -kv[1])[:12]:
    print("%5d  %s" % (n, k))
