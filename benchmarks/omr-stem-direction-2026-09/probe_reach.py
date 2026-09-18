"""WHAT IS THE `no_stem` POPULATION, AND WHAT EVIDENCE STANDS BESIDE IT?

⚠️ REACH BEFORE ACCURACY, and here reach has to be SPLIT before it is even a
number. `adjudicate_stem_direction` abstains `no_stem` when the CV rung read
no stem meeting the head -- and **a whole note HAS no stem**, so part of this
population is the decision being right. A rule aimed at the whole of it would
be aimed mostly at correct abstentions.

It reads a committed record and decides nothing. Three questions:

  1. how big is `no_stem`, and what notehead CLASSES is it made of?
  2. does a BEAM stand over or under those heads? A beam is a stem-direction
     declaration in ink: it joins stem TIPS, so a stroke above the head means
     the stem points up and one below means down. That is a READING, not a
     convention, and it is the only evidence here that could be ADJUDICATE's.
  3. do OTHER heads in the same bar carry a decided direction? ⚠️ This is the
     dangerous one and is measured in order to be REFUSED: handing a head the
     bar's majority would make `adjudicate_event`'s divisi guard and
     `split_events_into_voices` unable to ever separate anything, because the
     quantity they read would have been filled in from the answer they are
     trying to find.
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

# ⚠️⚠️ IMPORTED, NOT RESTATED, AND THE FIRST DRAFT PAID FOR RESTATING IT.
# `Q.GLYPH_BOX` is `(smufl_name, x, y, w, h)` -- the NAME comes first -- and
# this probe read `value[:4]`, floated the name, threw, and built an EMPTY box
# map. Every geometric question then answered 0, and the control that would
# have caught it printed nothing at all, which is itself the tell. The helper
# exists in `rhythm.py` with a docstring saying it is spelled once "so a
# second reader of the same row cannot get it wrong"; this is that second
# reader, getting it wrong by not importing it.
from tools.omr.staged.adjudicators.rhythm import _xywh_head   # noqa: E402
from tools.omr.staged.record import Kind, Subject              # noqa: E402


def cell_of(key: str) -> str:
    """The CELL subject a row's subject sits in.

    ⚠️⚠️ NOT `key.rsplit("/", 1)[0]`, AND THIS PROBE MADE THAT MISTAKE TWICE.
    A subject key carries its KIND in the first segment, so chopping the last
    segment off `glyph/1/0/2/4/1` yields `glyph/1/0/2/4` -- which is not
    `cell/1/0/2/4` and matches nothing. The two dicts never met and every
    geometric question answered a clean, believable ZERO. `Subject.at` is the
    only thing that knows how a key is shaped.
    """
    return Subject.from_key(key).at(Kind.CELL).to_key()


def xywh(v):
    """A CV line row as `(x, y, w, h)`, or None. Those really are 4-tuples."""
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return None
    try:
        return tuple(float(t) for t in v)
    except (TypeError, ValueError):
        return None


def overlaps_x(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "reach.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print(f"record provenance: {doc.get('provenance')}")

    obs = rec["observations"]
    by_q = collections.defaultdict(list)
    for o in obs:
        by_q[o["quantity"]].append(o)

    cls_of = {o["subject"]: str(o["value"]) for o in by_q.get("notehead_class", [])}
    box_of = {}
    for o in by_q.get("glyph_box", []):
        b = _xywh_head(o.get("value"))
        if b is not None:
            box_of[o["subject"]] = b

    # ⚠️⚠️ A BEAM ROW IS FILED ON THE **CELL**, NOT ON A GLYPH, and the first
    # run of this probe stripped a segment off it as if it were a glyph
    # subject. That keyed the beams by STAFF while the heads were keyed by
    # CELL, the two dicts never met, and the probe reported `has_a_beam_over_
    # or_under: 0 of 784` -- a clean, believable zero that was the KEY and not
    # the page. The `clefG`/`gClef` fault, one family over.
    beams = collections.defaultdict(list)
    for o in by_q.get("beam_stroke", []):
        b = xywh(o.get("value"))
        if b is not None:
            beams[cell_of(o["subject"])].append(b)

    verdicts = [v for v in rec["verdicts"] if v["quantity"] == "stem_direction"]
    tally = collections.Counter((v["outcome"], v["reason"]) for v in verdicts)
    print("\n── stem_direction verdicts")
    for k, n in tally.most_common():
        print(f"   {n:6d}  {k[0]:<10} {k[1]}")

    decided_in_cell = collections.defaultdict(list)
    for v in verdicts:
        if v["outcome"] == "decided":
            decided_in_cell[cell_of(v["subject"])].append(v["value"])

    no_stem = [v for v in verdicts if v["reason"] == "no_stem"]
    by_class = collections.Counter(cls_of.get(v["subject"], "?") for v in no_stem)
    print(f"\n── the {len(no_stem)} `no_stem` heads, by DETECTED class")
    for c, n in by_class.most_common():
        # ⚠️ A WHOLE NOTE HAS NO STEM. Those abstentions are the decision
        # being RIGHT, and a rule aimed at them would be aimed at nothing.
        note = "  <- correct: a whole note carries no stem" if "Whole" in c else ""
        print(f"   {n:6d}  {c}{note}")

    stemmed = [v for v in no_stem if "Whole" not in cls_of.get(v["subject"], "")]
    print(f"\n── of those, {len(stemmed)} are heads that SHOULD carry a stem")

    ev = collections.Counter()
    rows = []
    for v in stemmed:
        sub = v["subject"]
        cell = cell_of(sub)
        head = box_of.get(sub)
        above = below = 0
        if head is not None:
            for b in beams.get(cell, ()):
                if not overlaps_x(head, b):
                    continue
                if b[1] + b[3] <= head[1]:
                    above += 1
                elif b[1] >= head[1] + head[3]:
                    below += 1
        others = decided_in_cell.get(cell, [])
        ev["has_a_beam_over_or_under"] += 1 if (above or below) else 0
        ev["beam_says_one_way_only"] += 1 if bool(above) != bool(below) else 0
        ev["another_head_in_the_bar_is_decided"] += 1 if others else 0
        ev["the_bar_is_unanimous"] += 1 if others and len(set(others)) == 1 else 0
        ev["no_evidence_of_either_kind"] += 1 if not (above or below or others) else 0
        rows.append({"subject": sub, "class": cls_of.get(sub),
                     "beams_above": above, "beams_below": below,
                     "others_in_bar": len(others),
                     "bar_unanimous": bool(others) and len(set(others)) == 1})

    # ⚠️ THE POSITIVE CONTROL FOR THE BEAM GEOMETRY. If heads whose direction
    # WAS decided show no beam either, the zero above is this probe's frame
    # and not the page -- and the two are indistinguishable without it.
    ctrl = collections.Counter()
    for v in verdicts:
        if v["outcome"] != "decided":
            continue
        head = box_of.get(v["subject"])
        if head is None:
            continue
        cell = cell_of(v["subject"])
        hit = [b for b in beams.get(cell, ()) if overlaps_x(head, b)]
        ctrl["decided_heads_examined"] += 1
        ctrl["decided_head_under_a_beam"] += 1 if hit else 0
        for b in hit:
            if b[1] + b[3] <= head[1]:
                ctrl["beam_above_a_%s_head" % v["value"]] += 1
            elif b[1] >= head[1] + head[3]:
                ctrl["beam_below_a_%s_head" % v["value"]] += 1
    print("\n── CONTROL: the same geometry on heads that DID decide")
    print(f"   glyph boxes read: {len(box_of)}   beam_stroke rows: "
          f"{sum(len(v) for v in beams.values())} over {len(beams)} cells")
    if not box_of:
        print("⚠️ NOT ONE GLYPH BOX PARSED — every geometric zero below is "
              "this probe's frame and not the page.", file=sys.stderr)
    for k, n in ctrl.most_common():
        print(f"   {n:6d}  {k}")

    print("\n── what stands beside them")
    for k, n in ev.most_common():
        pct = 100.0 * n / max(1, len(stemmed))
        print(f"   {n:6d}  ({pct:5.1f}%)  {k}")

    out = {"verdicts": {f"{k[0]}/{k[1]}": n for k, n in tally.items()},
           "no_stem_total": len(no_stem),
           "no_stem_by_class": dict(by_class),
           "should_carry_a_stem": len(stemmed),
           "evidence": dict(ev), "control": dict(ctrl), "rows": rows}
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    if not stemmed:
        print("\n⚠️ NOTHING TO REACH. An inert probe and a page with no such "
              "head are the same zero here.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
