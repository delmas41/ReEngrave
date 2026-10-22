"""The three waiting jobs' REACH numbers, read off a shared record.

Each of the three jobs that stopped on 2026-09-15 for want of a second
publisher needs a different population, and the point of a shared record's
receipt is that the next session can size its own question from the REPO
rather than by re-gathering 443 MB.

⚠️ These are REACH figures — how much of the population this record holds.
NOTHING here is an accuracy claim, and no glyph was checked against the print.
"""

from __future__ import annotations

import collections
import json
import sys


def main() -> int:
    d = json.load(open(sys.argv[1]))
    rec = d["record"]
    obs = rec["observations"]
    verdicts = rec["verdicts"]

    q = collections.Counter(o["quantity"] for o in obs)

    print("── ARC GRAMMAR (benchmarks/omr-arc-grammar-2026-09) ───────────")
    arcs = [o for o in obs if o["quantity"] == "arc_box"]
    print("  arc_box rows      : %d   (Litolff p1-3: 779)" % len(arcs))
    print("  Q.STEM rows       : %d   (Litolff: 1,920)" % q["stem"])
    print("  noteheads         : %d   (Litolff: 2,347)" % q["notehead_class"])
    kinds = collections.Counter(
        str(v.get("value")) for v in verdicts if v["quantity"] == "arc_kind")
    print("  arc_kind values   :", dict(kinds))

    print("\n── NOTE WHERE SILENCE (benchmarks/omr-note-where-silence-2026-09) ──")
    rests = [o for o in obs if o["quantity"] == "rest"]
    rc = collections.Counter(str(o.get("value")) for o in rests)
    print("  rest rows         : %d   (its two cuts were derived from"
          " Litolff's 395 whole rests)" % len(rests))
    print("  rest classes      :", dict(rc.most_common(8)))
    nh = collections.Counter(
        str(o.get("value")) for o in obs if o["quantity"] == "notehead_class")
    print("  notehead classes  :", dict(nh.most_common(8)))
    wr = sum(1 for v in verdicts
             if v["quantity"] == "notehead_is_a_whole_rest" and v.get("value"))
    print("  notehead_is_a_whole_rest TRUE: %d of %d"
          % (wr, sum(1 for v in verdicts
                     if v["quantity"] == "notehead_is_a_whole_rest")))

    print("\n── METER CARRY (the standing blocking objection) ──────────────")
    print("  meter_glyph rows  : %d" % q["meter_glyph"])
    print("  meter_template    : %d" % q["meter_template"])
    mv = [v for v in verdicts if v["quantity"] == "meter"]
    bad = 0
    for v in mv:
        val = v.get("value") or {}
        if not (val.get("numerator") == 6 and val.get("denominator") == 8):
            bad += 1
    print("  systems whose OPENING meter is NOT the printed 6/8: %d of %d"
          % (bad, len(mv)))

    print("\n── DURATION MARKS (this document is the mark-RICH arm) ────────")
    print("  flag rows         : %d   (CLAUDE.md records 371 here vs"
          " Litolff's 49)" % q["flag"])
    print("  aug_dot rows      : %d   (CLAUDE.md records 656 here vs"
          " Litolff's 35)" % q["aug_dot"])

    print("\n── WHAT THIS RECORD CANNOT ANSWER ─────────────────────────────")
    for name, litolff in (("fermata_mark", 67), ("ornament_mark", 6),
                          ("direction_word", 6), ("wedge_box", 0),
                          ("dynamic_letter", 485)):
        print("  %-16s %5d   (Litolff p1-3: %d)" % (name, q[name], litolff))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
