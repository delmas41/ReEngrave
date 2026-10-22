"""CAN A BEAM NAME A STEM DIRECTION? Scored where the answer is already known.

⚠️ THE METHOD IS THE POINT. `adjudicate_stem_direction` decides 1,443 heads by
projecting the STEM it found, and abstains `no_stem` on 784 that should have
one. The decided population is a held-out answer for any rule that does not
read the stem -- so a beam rule can be SCORED before it is written, on heads
where a stem says what the truth is.

⚠️⚠️ AND THE TRANSFER IS NOT FREE, WHICH THIS PROBE CANNOT TEST. A head with
no stem is a head whose ink the CV rung could not read; the beams near it are
more likely to be broken too. So an accuracy measured on heads WITH a stem is
an UPPER BOUND on the same rule applied to heads without one, and every figure
here must be read as one.
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


def candidates(head, beams, *, require_centre_inside):
    """The beams this head might hang from, split above/below."""
    hx = head[0] + head[2] / 2.0
    above, below = [], []
    for b in beams:
        if require_centre_inside:
            if not (b[0] <= hx <= b[0] + b[2]):
                continue
        elif not (head[0] < b[0] + b[2] and b[0] < head[0] + head[2]):
            continue
        if b[1] + b[3] <= head[1]:
            above.append(b)
        elif b[1] >= head[1] + head[3]:
            below.append(b)
    return above, below


RULES = {
    # name: (require the head's x-CENTRE inside the beam's span?, only fire
    #        when the beams all sit on ONE side?)
    "overlap_any_side": (False, False),
    "overlap_unambiguous": (False, True),
    "centre_any_side": (True, False),
    "centre_unambiguous": (True, True),
}


def apply(rule, head, beams):
    centre, unambiguous = RULES[rule]
    above, below = candidates(head, beams, require_centre_inside=centre)
    if not above and not below:
        return None
    if unambiguous and above and below:
        return None
    if above and below:
        # nearest wins: the gap between the head and the beam
        da = min(head[1] - (b[1] + b[3]) for b in above)
        db = min(b[1] - (head[1] + head[3]) for b in below)
        return "up" if da <= db else "down"
    return "up" if above else "down"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "beam-rule.json"))
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
            beams[cell_of(o["subject"])].append(b)

    verdicts = [v for v in rec["verdicts"] if v["quantity"] == "stem_direction"]
    truth = [(v["subject"], v["value"]) for v in verdicts
             if v["outcome"] == "decided"]
    unknown = [v["subject"] for v in verdicts if v["reason"] == "no_stem"]
    print(f"\nheld-out answers (decided by the stem): {len(truth)}")
    print(f"heads with no stem at all:              {len(unknown)}")

    out = {}
    print(f"\n{'rule':<24} {'fires':>7} {'right':>7} {'wrong':>7} "
          f"{'accuracy':>9} {'on no_stem':>11}")
    print("-" * 70)
    for rule in RULES:
        right = wrong = 0
        for sub, want in truth:
            head = box_of.get(sub)
            if head is None:
                continue
            got = apply(rule, head, beams.get(cell_of(sub), ()))
            if got is None:
                continue
            right += got == want
            wrong += got != want
        fires = right + wrong
        acc = right / fires if fires else 0.0
        reach = sum(1 for sub in unknown
                    if box_of.get(sub) is not None
                    and apply(rule, box_of[sub],
                              beams.get(cell_of(sub), ())) is not None)
        out[rule] = {"fires": fires, "right": right, "wrong": wrong,
                     "accuracy": round(acc, 4), "reach_on_no_stem": reach}
        print(f"{rule:<24} {fires:>7} {right:>7} {wrong:>7} {acc:>9.3f} "
              f"{reach:>11}")

    # ⚠️ THE BASELINE THAT MAKES AN ACCURACY MEAN ANYTHING. Always answering
    # the commoner direction costs nothing and needs no ink; a rule that does
    # not beat it is not reading the page.
    base = collections.Counter(w for _, w in truth)
    top = base.most_common(1)[0]
    print(f"\nbaseline 'always {top[0]}': {top[1]}/{len(truth)} = "
          f"{top[1] / len(truth):.3f}")
    out["baseline"] = {"value": top[0], "accuracy": round(top[1] / len(truth), 4)}

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
