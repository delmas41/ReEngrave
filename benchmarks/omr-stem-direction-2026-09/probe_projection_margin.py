"""IS THE REFERENCE THE THING THAT IS WRONG? The projection's own MARGIN says.

Sean, 2026-09-17: the stem convention is *"very consistent unless there are
multiple voices per staff"*. Measured against our own `stem_projection`
verdicts it reads 0.793 -- and 0.793 in bars the pipeline itself calls ONE
voice, which is not what "very consistent" looks like. Either the convention
is weaker on this plate than the engraving tradition says, or **the thing it
is being scored against is wrong about one head in five**.

⚠️ THIS PROBE ASKS THE SECOND QUESTION WITHOUT A PRINT, and it can, because
`transcribe._stem_direction` carries its own confidence in its arithmetic:

    above = (top of the heads)    - (top of the stem)
    below = (bottom of the stem)  - (bottom of the heads)
    up if above > below

A CORRECTLY attached stem overhangs on exactly ONE side: `above` is a stem's
length and `below` is about zero, or the reverse. A stem box that spans both
ways -- two stems merged by the CV rung, a barline fragment, a neighbouring
beamed group's stem whose box overlaps this head -- makes both terms large,
and `>` is then a COIN FLIP dressed as a reading.

So: split the decided heads by whether the convention agrees, and compare the
MARGIN. If the disagreements sit at a small margin, the projection is the
suspect and Sean's rule is vindicated; if they sit at a large one, the
projection is confident and the convention really is weaker here.

⚠️ RESTRICTED TO HEADS WITH EXACTLY ONE STEM AND NO OTHER HEAD ON IT. A double
stop's group is what the projection exists to handle, and mixing it in would
measure that repair rather than this question.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators.rhythm import (               # noqa: E402
    _boxes_overlap, _xywh_head)
from tools.omr.staged.record import Kind, Subject                # noqa: E402

MIDDLE_LINE = 4.0


def position_says(pos):
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
    ap.add_argument("--json", default=str(HERE / "out" / "projection-margin.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc

    pos_of, box_of, space_of = {}, {}, {}
    stems = collections.defaultdict(list)
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
        elif q == "stem":
            b = box4(o.get("value"))
            if b is not None:
                stems[o["subject"]].append(b)
        elif q == "cell_staff_space":
            try:
                space_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass

    decided = {v["subject"]: v["value"] for v in rec["verdicts"]
               if v["quantity"] == "stem_direction" and v["outcome"] == "decided"}

    def cell(k):
        return Subject.from_key(k).at(Kind.CELL).to_key()

    heads_in = collections.defaultdict(list)
    for sub in box_of:
        heads_in[cell(sub)].append(sub)

    rows = []
    for sub, want in decided.items():
        head = box_of.get(sub)
        pos = pos_of.get(sub)
        if head is None or pos is None:
            continue
        c = cell(sub)
        mine = [s for s in stems.get(c, ()) if _boxes_overlap(s, head)]
        if len(mine) != 1:
            continue
        s = mine[0]
        # ⚠️ ONE HEAD ON THIS STEM ONLY. The group case is the double stop.
        if sum(1 for o in heads_in[c]
               if box_of.get(o) and _boxes_overlap(s, box_of[o])) != 1:
            continue
        above = head[1] - s[1]
        below = (s[1] + s[3]) - (head[1] + head[3])
        space = space_of.get(c) or 0.0
        rows.append({
            "subject": sub, "projection": want,
            "convention": position_says(pos),
            "above": above, "below": below,
            # the LOSING side, in staff spaces: 0 for a clean stem, large for
            # one that overhangs both ways
            "loser_spaces": (min(above, below) / space) if space else None,
            "margin_spaces": (abs(above - below) / space) if space else None,
        })

    agree = [r for r in rows if r["projection"] == r["convention"]]
    dis = [r for r in rows if r["projection"] != r["convention"]]
    print(f"single-stem, single-head cases: {len(rows)}   "
          f"convention agrees {len(agree)}  disagrees {len(dis)}")
    if not rows:
        print("⚠️ NOTHING MEASURED — every figure below would be this "
              "probe's key.", file=sys.stderr)
        return 2

    out = {"n": len(rows), "agree": len(agree), "disagree": len(dis)}
    for name, group in (("convention AGREES", agree),
                        ("convention DISAGREES", dis)):
        vals = [r["loser_spaces"] for r in group if r["loser_spaces"] is not None]
        marg = [r["margin_spaces"] for r in group if r["margin_spaces"] is not None]
        if not vals:
            continue
        vals.sort()
        marg.sort()
        rec_out = {
            "n": len(vals),
            "loser_side_median_spaces": round(statistics.median(vals), 3),
            "loser_side_p90_spaces": round(vals[int(0.9 * len(vals))], 3),
            "margin_median_spaces": round(statistics.median(marg), 3),
            "share_loser_over_1_space": round(
                sum(1 for v in vals if v > 1.0) / len(vals), 3),
        }
        out[name] = rec_out
        print(f"\n── {name}  (n={len(vals)})")
        for k, v in rec_out.items():
            if k != "n":
                print(f"   {k:<30} {v}")

    # ⚠️ THE ACTIONABLE CUT, if there is one: refuse the projection where the
    # losing side is long enough to be a stem in its own right, and see what
    # the convention would then be scored against.
    print(f"\n── if the projection ABSTAINED where the losing side exceeds N "
          f"staff spaces")
    print(f"   {'N':>5} {'kept':>7} {'conv agrees on kept':>22}")
    sweep = {}
    for n_sp in (0.5, 1.0, 1.5, 2.0, 3.0):
        kept = [r for r in rows
                if r["loser_spaces"] is not None and r["loser_spaces"] <= n_sp]
        if not kept:
            continue
        ok = sum(1 for r in kept if r["projection"] == r["convention"])
        sweep[str(n_sp)] = {"kept": len(kept),
                            "convention_agrees": round(ok / len(kept), 4)}
        print(f"   {n_sp:>5} {len(kept):>7} {ok / len(kept):>22.3f}")
    out["sweep"] = sweep

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
