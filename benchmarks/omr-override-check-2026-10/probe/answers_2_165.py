"""ROADMAP 2.165 -- record Sean's answers to out/print/2.165-review (2026-10-17) and score each tile base vs on.

    python3 .../answers_2_165.py      (reads out/2.165/tiles-key.json; writes the review dir's manifest.json + answers.json)

Statuses per arm (STAGED, the standing duration of the tiled glyph in each whole-record replay):
  right      -- a value written (READ or GUESSED) equal to Sean's
  wrong      -- a value written that is not Sean's, or ANY value written on a non-note (slash, flag, clef)
  narrowed_holding / narrowed_missing -- not written (UNREAD), its candidates hold / do not hold Sean's value
  held_out   -- not written (UNREAD) with no candidate to compare (abstained, or a stem_heads_disagree hold-out),
                or, for a non-note, not written at all (the right outcome for a non-note)"""
import collections
import json
from pathlib import Path

VERBATIM = ("K- 1.trem slash 2.2 3.flag 4.2 half notes a third apart in one box 5.2 6.8 7.8 8.8 9.dot 4 10.2 11. Trem "
            "slash 12.8 13.dot4 14.8 15.4 16.part of a c clef 17. Flag 18. Trem slash 19.2 20.2 21.trem slash 22.4 23.8 "
            "24.8  25. Dot 4")
SEAN = {1: "trem slash", 2: "2", 3: "flag", 4: "2 half notes a third apart in one box", 5: "2", 6: "8", 7: "8", 8: "8",
        9: "dot 4", 10: "2", 11: "trem slash", 12: "8", 13: "dot 4", 14: "8", 15: "4", 16: "part of a c clef",
        17: "flag", 18: "trem slash", 19: "2", 20: "2", 21: "trem slash", 22: "4", 23: "8", 24: "8", 25: "dot 4"}
BEATS = {"2": 2.0, "4": 1.0, "8": 0.5, "dot 4": 1.5, "2 half notes a third apart in one box": 2.0}
NON_NOTE = {n for n, a in SEAN.items() if a not in BEATS}

OUT = Path("out/print/2.165-review")
key = json.load(open("out/2.165/tiles-key.json"))


def status(b, sean):
    if b is None:
        return "held_out"
    written = b["cls"] in ("READ", "GUESSED") and b.get("beats") is not None
    if sean is None:                                   # not a note
        return "wrong" if written else "held_out"
    if written:
        return "right" if abs(float(b["beats"]) - sean) < 1e-6 else "wrong"
    if b.get("cands"):
        return "narrowed_holding" if any(abs(c - sean) < 1e-6 for c in b["cands"]) else "narrowed_missing"
    return "held_out"


rows, by_cause = [], collections.defaultdict(collections.Counter)
for r in key:
    n = r["n"]
    sean = BEATS.get(SEAN[n])
    sb, so = status(r["base"], sean), status(r["on"], sean)
    rows.append(dict(n=n, doc=r["doc"], glyph=r["glyph"], role=r["role"], cause=r["cause"], sean=SEAN[n],
                     not_a_note=n in NON_NOTE, base=r["base"], on=r["on"], verdict_base=sb, verdict_on=so))
    by_cause[r["cause"]][(sb, so)] += 1
json.dump(dict(question=json.load(open(OUT / "manifest.json")).get("question"),
               tiles=[dict(n=r["n"], doc=r["doc"], glyph=r["glyph"]) for r in key]),
          open(OUT / "manifest.json", "w"), indent=1)
json.dump(dict(answered="2026-10-17", verbatim=VERBATIM,
               question="What is the written value of the note in the blue box? Say 'not a note' if it is not one.",
               tiles=rows), open(OUT / "answers.json", "w"), indent=1)
for r in rows:
    print("%2d %-7s %-40s Sean=%-12s base=%-17s on=%-17s %s" % (r["n"], r["doc"], r["cause"], r["sean"][:12],
                                                               r["verdict_base"], r["verdict_on"],
                                                               "NON-NOTE" if r["not_a_note"] else ""))
print()
for c, m in sorted(by_cause.items()):
    print(c, dict(m))
tot = collections.Counter((r["verdict_base"], r["verdict_on"]) for r in rows)
print("ALL", dict(tot))
print("notes", dict(collections.Counter((r["verdict_base"], r["verdict_on"]) for r in rows if not r["not_a_note"])))
print("non-notes", dict(collections.Counter((r["verdict_base"], r["verdict_on"]) for r in rows if r["not_a_note"])))
