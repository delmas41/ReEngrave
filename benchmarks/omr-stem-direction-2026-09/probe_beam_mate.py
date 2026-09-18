"""A BEAM IS ONE PHYSICAL OBJECT, SO EVERY STEM ON IT POINTS THE SAME WAY.

⚠️ THE CLAIM IS NOT GEOMETRIC AND THAT IS WHY IT IS WORTH MEASURING SEPARATELY.
`probe_beam_rule.py` asks *where is the beam relative to this head* and tops
out at 0.829 -- a rule at 1-in-6 wrong, fed to a divisi guard whose own
docstring says an UNKNOWN is better than a confident wrong answer. This asks a
different question: *does another head on THE SAME BEAM already have an
answer?* A beam joins stem TIPS, so two heads hanging from one stroke have
stems pointing the same way -- a fact about the engraving rather than a
measurement of where ink fell.

⚠️ SCORED LEAVE-ONE-OUT. For a head whose direction IS decided, the witnesses
are the OTHER decided heads on its beam; the head itself is never its own
witness, which would score the rule against its own input.

⚠️ AND AN UPPER BOUND AGAIN: a head with no stem is a head whose ink the CV
rung could not read, so the beam beside it is likelier broken too.
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

from tools.omr.staged.adjudicators.rhythm import _xywh_head    # noqa: E402
from tools.omr.staged.record import Kind, Subject              # noqa: E402


def cell_of(key):
    return Subject.from_key(key).at(Kind.CELL).to_key()


def box4(v):
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return None
    try:
        return tuple(float(t) for t in v)
    except (TypeError, ValueError):
        return None


def on_beam(head, beam):
    """Is this head's x-CENTRE inside the beam's span?"""
    hx = head[0] + head[2] / 2.0
    return beam[0] <= hx <= beam[0] + beam[2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "beam-mate.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print(f"record provenance: {doc.get('provenance')}")

    by_q = collections.defaultdict(list)
    for o in rec["observations"]:
        by_q[o["quantity"]].append(o)
    box_of = {}
    for o in by_q.get("glyph_box", []):
        b = _xywh_head(o.get("value"))
        if b is not None:
            box_of[o["subject"]] = b
    beams = collections.defaultdict(list)
    for o in by_q.get("beam_stroke", []):
        b = box4(o.get("value"))
        if b is not None:
            beams[cell_of(o["subject"])].append((o["id"], b))

    verdicts = [v for v in rec["verdicts"] if v["quantity"] == "stem_direction"]
    decided = {v["subject"]: v["value"] for v in verdicts
               if v["outcome"] == "decided"}
    no_stem = [v["subject"] for v in verdicts if v["reason"] == "no_stem"]

    heads_in_cell = collections.defaultdict(list)
    for sub in list(decided) + no_stem:
        if sub in box_of:
            heads_in_cell[cell_of(sub)].append(sub)

    def witnesses(sub, *, exclude_self):
        """`{beam id: [direction of every OTHER decided head on it]}`."""
        head = box_of[sub]
        out = {}
        for bid, b in beams.get(cell_of(sub), ()):
            if not on_beam(head, b):
                continue
            mates = [decided[o] for o in heads_in_cell[cell_of(sub)]
                     if o in decided and (o != sub or not exclude_self)
                     and on_beam(box_of[o], b)]
            if mates:
                out[bid] = mates
        return out

    def answer(sub, *, exclude_self, unanimous):
        w = witnesses(sub, exclude_self=exclude_self)
        votes = [d for mates in w.values() for d in mates]
        if not votes:
            return None
        if unanimous and len(set(votes)) != 1:
            return None
        return collections.Counter(votes).most_common(1)[0][0]

    print(f"\n{'rule':<28} {'fires':>7} {'right':>7} {'wrong':>7} "
          f"{'accuracy':>9} {'on no_stem':>11}")
    print("-" * 74)
    out = {}
    for name, unanimous in (("beam_mate_majority", False),
                            ("beam_mate_unanimous", True)):
        right = wrong = 0
        for sub, want in decided.items():
            if sub not in box_of:
                continue
            got = answer(sub, exclude_self=True, unanimous=unanimous)
            if got is None:
                continue
            right += got == want
            wrong += got != want
        reach = sum(1 for sub in no_stem if sub in box_of
                    and answer(sub, exclude_self=True,
                               unanimous=unanimous) is not None)
        fires = right + wrong
        acc = right / fires if fires else 0.0
        out[name] = {"fires": fires, "right": right, "wrong": wrong,
                     "accuracy": round(acc, 4), "reach_on_no_stem": reach}
        print(f"{name:<28} {fires:>7} {right:>7} {wrong:>7} {acc:>9.3f} "
              f"{reach:>11}")

    base = collections.Counter(decided.values()).most_common(1)[0]
    print(f"\nbaseline 'always {base[0]}': {base[1] / len(decided):.3f}")
    out["baseline"] = {"value": base[0],
                       "accuracy": round(base[1] / len(decided), 4)}

    # ⚠️ WHY THE REACH IS WHAT IT IS, reported rather than left to be guessed.
    funnel = collections.Counter()
    for sub in no_stem:
        funnel["no_stem heads"] += 1
        if sub not in box_of:
            continue
        funnel["with a box"] += 1
        cell_beams = beams.get(cell_of(sub), ())
        if not cell_beams:
            continue
        funnel["in a cell holding a beam"] += 1
        if not any(on_beam(box_of[sub], b) for _, b in cell_beams):
            continue
        funnel["standing ON a beam"] += 1
        w = witnesses(sub, exclude_self=True)
        if not w:
            continue
        funnel["with a decided mate on it"] += 1
        votes = [d for m in w.values() for d in m]
        if len(set(votes)) == 1:
            funnel["whose mates AGREE"] += 1
    print("\n── the funnel")
    for k, n in funnel.items():
        print(f"   {n:6d}  {k}")
    out["funnel"] = dict(funnel)

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
