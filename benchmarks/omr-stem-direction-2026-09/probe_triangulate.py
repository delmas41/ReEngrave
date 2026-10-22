"""THREE READINGS OF ONE FACT, AND NONE OF THEM IS A TRUTH.

The stem direction of a head can be read three ways, and they fail for
different reasons:

  PROJECTION  where the stem overhangs -- needs the stem to be attached right
  BEAM MATE   what a head on the SAME BEAM says -- needs a beam and a mate
  CONVENTION  Sean's rule: above the middle line is stem-down -- needs the
              bar to be ONE VOICE

⚠️⚠️ THE QUESTION THIS SETTLES. Scored against the projection, the convention
reads 0.793 -- and 0.793 in bars the pipeline calls one-voice, which is not
what *"very consistent"* looks like. But the projection is not a truth: it is
a reading, and on a scan a stem box can belong to a neighbour. So the two are
put to a THIRD reading that shares an input with neither -- the beam -- and
the question becomes: **where the projection and the convention disagree,
which one does the beam side with?**

⚠️ NOT A TRUTH EITHER, and the conclusion must be phrased as agreement rather
than accuracy. What it can establish is RELATIVE: if the beam sides with the
convention where the projection dissents, the projection is the weak reading;
if it sides with the projection, the convention does not hold on this plate.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators.rhythm import (               # noqa: E402
    _on_beam, _xywh_head)
from tools.omr.staged.record import Kind, Subject                # noqa: E402

MIDDLE_LINE = 4.0


def convention(pos):
    return "down" if pos <= MIDDLE_LINE else "up"


def box4(v):
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return None
    try:
        return tuple(float(t) for t in v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "triangulate.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc

    pos_of, box_of = {}, {}
    beams = collections.defaultdict(list)
    for o in rec["observations"]:
        q = o["quantity"]
        if q == "notehead_staff_position":
            try:
                pos_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass
        elif q == "glyph_box":
            b = _xywh_head(o.get("value"))
            if b is not None:
                box_of[o["subject"]] = b
        elif q == "beam_stroke":
            b = box4(o.get("value"))
            if b is not None:
                beams[Subject.from_key(o["subject"]).at(Kind.CELL)
                      .to_key()].append(b)

    proj = {v["subject"]: v["value"] for v in rec["verdicts"]
            if v["quantity"] == "stem_direction"
            and v["reason"] == "stem_projection"}

    def cell(k):
        return Subject.from_key(k).at(Kind.CELL).to_key()

    heads_in = collections.defaultdict(list)
    for sub in proj:
        heads_in[cell(sub)].append(sub)

    def beam_mate(sub):
        """What the OTHER heads on this head's beams say. None if silent."""
        head = box_of.get(sub)
        if head is None:
            return None
        votes = set()
        for b in beams.get(cell(sub), ()):
            if not _on_beam(head, b):
                continue
            for o in heads_in[cell(sub)]:
                if o == sub or box_of.get(o) is None:
                    continue
                if _on_beam(box_of[o], b):
                    votes.add(proj[o])
        if len(votes) != 1:
            return None
        return votes.pop()

    t = collections.Counter()
    for sub, p in proj.items():
        pos = pos_of.get(sub)
        if pos is None:
            continue
        c = convention(pos)
        m = beam_mate(sub)
        if m is None:
            t["beam silent"] += 1
            continue
        t["all three speak"] += 1
        if p == c:
            t["projection == convention"] += 1
            t["  and the beam agrees" if m == p
              else "  and the beam DISSENTS"] += 1
        else:
            t["projection != convention"] += 1
            if m == p:
                t["  the beam sides with the PROJECTION"] += 1
            elif m == c:
                t["  the beam sides with the CONVENTION"] += 1

    print("── three readings of one head")
    for k, n in t.most_common():
        print(f"   {n:6d}  {k}")

    both = t["  the beam sides with the PROJECTION"] + \
        t["  the beam sides with the CONVENTION"]
    if both:
        share = t["  the beam sides with the CONVENTION"] / both
        print(f"\nWHERE THEY DISAGREE, the beam sides with the CONVENTION "
              f"{t['  the beam sides with the CONVENTION']}/{both} = "
              f"{share:.3f}")
        print("⚠️ 0.5 would mean the beam cannot tell them apart; near 1.0 "
              "means the PROJECTION is the weak reading; near 0.0 means the "
              "convention does not hold on this plate.")
    Path(a.json).write_text(json.dumps(dict(t), indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
