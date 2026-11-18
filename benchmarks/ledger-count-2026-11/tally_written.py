"""ROADMAP 2.312 Part 0b/0c -- what became of every far head by geometry: counted by ledger, moved to another staff, written BLUE by the fallback, plain, or refused as a head.

    python3 benchmarks/ledger-count-2026-11/tally_written.py HEADS.json
"""
import collections
import json
import sys


def far(h):
    g = int(round(h["geom"]))
    return g <= -2 or g >= 10


def reason(h):
    r = ((h.get("ledger_refusal") or {}).get("detail") or {}).get("ledger_reason") or "?"
    return r.split(" (")[0]


GROUP = {"reowned_by_ledger_reading": "moved to the other staff by its ledger lines", "reowned": "moved to the other staff by its ledger lines",
         "position_and_clef_ledger_unread": "written BLUE (fallback, GUESSED)", "position_and_clef": "written PLAIN (fallback)",
         "position_and_clef_change": "written PLAIN (fallback, after a clef change)"}


def main(path):
    hs = json.load(open(path))
    f = [h for h in hs if far(h)]
    print("far heads by geometry:", len(f), " counted by ledger:", sum(1 for h in f if h["ledger_row"] is not None))
    c = collections.Counter()
    r = collections.Counter()
    for h in f:
        if h["ledger_row"] is not None:
            continue
        pv = h["pitch"] or {}
        g = GROUP.get(pv.get("reason"), "no pitch verdict (nothing written)" if not pv else str(pv.get("reason")))
        nan = h["not_a_note"]
        c[(g, "refused as a head" if (nan and nan[1] is True) else "")] += 1
        if g.startswith("moved"):
            continue
        r[(g, "refused as head" if (nan and nan[1] is True) else "a head", reason(h))] += 1
    for k, v in sorted(c.items()):
        print("  %4d  %s %s" % (v, k[0], k[1]))
    print("by what stopped the count (not counting heads moved to the other staff):")
    for k, v in sorted(r.items()):
        print("  %4d  %-50s %-15s %s" % (v, k[0], k[1], k[2]))


if __name__ == "__main__":
    main(sys.argv[1])
