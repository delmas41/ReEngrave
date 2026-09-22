"""Two questions the reach probe does not answer.

**(1) WOULD THE WIDENED JOIN CHANGE ANY DIRECTION THAT IS ALREADY DECIDED?**
`_project` builds the group whose span decides a stroke's direction from the
heads that OVERLAP it, so a chord member the overlap test dropped is also
missing from the group. `_stem_direction` compares how far the stroke
projects above the group's top against how far below its bottom -- so dropping
the member at one extreme biases it toward the other. This asks, per stroke,
whether adding the stemless chord shadows FLIPS the answer.

⚠️ IT USES THE SHIPPED `_stem_direction`, imported through the shipped
`_project`'s own import, so the arithmetic is the decision's.

**(2) DOES THE BEAM-MATE TIER ALREADY ANSWER THE HEADS THE JOIN WOULD REACH?**
A head the join rescues may already be getting a direction from
`_direction_from_a_beam_mate`, in which case the repair moves a REASON and not
a value. That tier needs `Q.BEAM_STROKE`, so the beams are streamed too.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    _boxes_overlap, _stems_on, collect, x_overlap, y_overlap,
)
from tools.omr import transcribe as _legacy  # noqa: E402
from tools.omr.staged.adjudicators.rhythm import _on_beam  # noqa: E402


class _Shim:
    __slots__ = ("x_canonical", "y_canonical", "width_canonical",
                 "height_canonical")

    def __init__(self, x, y, w, h):
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h


def _dir(stroke, boxes):
    return _legacy._stem_direction(_Shim(*stroke), [_Shim(*b) for b in boxes])


def extra_members(sb, stems_c, heads_c):
    """The stemless heads the widened join would add to THIS stroke.

    ⚠️ IT TAKES THE CELL'S HEADS AND RE-DERIVES THE JOINED SET. An earlier
    signature also took the caller's `joined` list AND recomputed it, so the
    parameter was declared and never read -- the inert-declaration shape this
    repo records a dozen times, in a probe this time. Deleted rather than
    wired, because the two could disagree.
    """
    joined = [h for h in heads_c if _boxes_overlap(sb, h.value)]
    # ⚠️ NO `if not joined: return []` GUARD, AND IT WAS DELETED RATHER THAN
    # TESTED AROUND. A mutation arm removing it SURVIVED, and the reason is
    # that it cannot change an answer: with `joined` empty the `any(...)`
    # below is False for every head, so the function already returns `[]`.
    # A guard in front of an assignment that cannot change the outcome is an
    # equivalent mutant, and this repo's rule is to delete the code.
    out = []
    for h in heads_c:
        if any(h is j for j in joined):
            continue
        if _stems_on(h.value, stems_c):
            continue
        if not y_overlap(h.value, sb):
            continue
        if any(x_overlap(h.value, j.value) for j in joined):
            out.append(h)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    stems, heads, beams, _n = collect(a.record, want_beams=True)

    strokes_with_extras = 0
    flips = []
    rescued, rescued_on_a_beam = [], []
    for c, hs in heads.items():
        ss = stems.get(c, [])
        if not ss:
            continue
        bs = beams.get(c, [])
        for s in ss:
            sb = s.value
            joined = [h for h in hs if _boxes_overlap(sb, h.value)]
            if not joined:
                continue
            extra = extra_members(sb, ss, hs)
            if not extra:
                continue
            strokes_with_extras += 1
            before = _dir(sb, [h.value for h in joined])
            after = _dir(sb, [h.value for h in joined + extra])
            if before != after:
                flips.append({"stem": s.id, "before": before, "after": after,
                              "n_joined": len(joined), "n_extra": len(extra),
                              "extra": [h.subject for h in extra]})
            for h in extra:
                rescued.append(h.subject)
                # would the beam-mate tier already have answered this head?
                on = [b for b in bs if _on_beam(h.value, b.value)]
                if on:
                    rescued_on_a_beam.append(h.subject)

    out = {
        "label": a.label or Path(a.record).name,
        "strokes_gaining_a_member": strokes_with_extras,
        "strokes_whose_DIRECTION_FLIPS": len(flips),
        "heads_rescued": len(set(rescued)),
        "heads_rescued_that_STAND_ON_A_BEAM":
            len(set(rescued_on_a_beam)),
        "flips": flips,
    }
    print(json.dumps(out, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
