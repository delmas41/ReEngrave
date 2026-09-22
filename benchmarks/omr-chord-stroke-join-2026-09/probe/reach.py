"""REACH FIRST: how many heads abstain `no_stem` while a chord partner of
theirs is joined to a stroke that reaches them?

⚠️ THE CONVENTION, STATED BEFORE THE CODE. A chord is several noteheads
sharing ONE stem: the engraver draws one vertical stroke and stacks the heads
on it at one x, so only the OUTERMOST head sits at the stroke's end. Sean,
2026-09-20, on a strip the software had filed as a fault: *"it is an octave of
C's and the stem belongs to both."*

⚠️ THE CLAIM UNDER TEST is that `_stems_on` -- strict box overlap, no
tolerance -- DROPS such members, so a chord's inner or offset head reads
`no_stem` while its partner reads a direction off the same ink.

⚠️ THE FAILURE MUST BE IN X, AND THAT IS FORCED RATHER THAN ASSUMED: a head
whose box overlaps the stroke in BOTH axes is joined by definition, so any
head lying inside the stroke's y-span and not joined fails the x test. The
probe reports the x gap so the claim can be falsified rather than believed.

⚠️ NOTHING IS FITTED. The candidate join is head-against-head in x
(`x_overlap`) plus head-against-stroke in y (`y_overlap`) -- both the SHIPPED
predicate on boxes already on the record. The ruler for *"the same x"* is the
heads' own widths.
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


def _percentiles(vals, ps=(0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99)):
    if not vals:
        return {}
    v = sorted(vals)
    return {f"p{int(p * 100):02d}": round(v[min(len(v) - 1, int(p * len(v)))], 4)
            for p in ps}


def unjoined_members(stems_c, heads_c):
    """Every (head, stroke) the widened join would ADD, in one cell.

    A row is written for each head H with NO stroke of its own that
      (a) overlaps stroke S in y, and
      (b) stands at the x of some head H2 that IS joined to S.

    ⚠️ (a) AND (b) ARE BOTH NEEDED AND NEITHER IS A TOLERANCE. Without (a) a
    head anywhere in the bar could be recruited; without (b) the rule would be
    *"any head inside a stroke's reach"*, which is the successive-note case.
    """
    rows = []
    for h in heads_c:
        hb = h.value
        if _stems_on(hb, stems_c):
            continue                      # it already has a stem of its own
        for s in stems_c:
            sb = s.value
            if not y_overlap(hb, sb):
                continue
            mates = [o for o in heads_c
                     if o is not h and _boxes_overlap(o.value, sb)
                     and x_overlap(hb, o.value)]
            if not mates:
                continue
            hw = max(hb[2], 1e-6)
            gap = max(0.0, max(sb[0] - (hb[0] + hb[2]), hb[0] - (sb[0] + sb[2])))
            rows.append({
                "head": h.subject,
                "stem": s.id,
                "n_mates": len(mates),
                "mates": [m.subject for m in mates],
                "x_gap_head_widths": round(gap / hw, 3),
                "dy_head_heights": round(
                    ((hb[1] + hb[3] / 2.0)
                     - (mates[0].value[1] + mates[0].value[3] / 2.0))
                    / max(hb[3], 1e-6), 3),
            })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    stems, heads, _b, n_obs = collect(a.record)

    n_heads = sum(len(v) for v in heads.values())
    n_stems = sum(len(v) for v in stems.values())

    no_stem = 0
    has_stem = 0
    multi = 0
    for c, hs in heads.items():
        ss = stems.get(c, [])
        for h in hs:
            mine = _stems_on(h.value, ss)
            if not mine:
                no_stem += 1
            else:
                has_stem += 1
                if len(mine) > 1:
                    multi += 1

    rows = []
    for c, hs in heads.items():
        ss = stems.get(c, [])
        if not ss:
            continue
        rows.extend(unjoined_members(ss, hs))

    reached_heads = sorted({r["head"] for r in rows})
    touched_strokes = sorted({r["stem"] for r in rows})
    ambiguous = sorted({r["head"] for r in rows
                        if sum(1 for q in rows if q["head"] == r["head"]) > 1})

    out = {
        "label": a.label or Path(a.record).name,
        "record": a.record,
        "observations_streamed": n_obs,
        "noteheads": n_heads,
        "stem_rows": n_stems,
        "counts_today": {"no_stem": no_stem, "has_stem": has_stem,
                         "multi_stem": multi},
        "REACH": {
            "candidate_pairs": len(rows),
            "heads_reached": len(reached_heads),
            "heads_reached_share_of_no_stem":
                round(len(reached_heads) / no_stem, 4) if no_stem else None,
            "strokes_touched": len(touched_strokes),
            "heads_with_MORE_THAN_ONE_candidate_stroke": len(ambiguous),
        },
        "x_gap_head_widths": _percentiles([r["x_gap_head_widths"] for r in rows]),
        "x_gap_max": max([r["x_gap_head_widths"] for r in rows], default=None),
        "dy_head_heights": _percentiles(
            [abs(r["dy_head_heights"]) for r in rows]),
    }
    print(json.dumps(out, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps({**out, "rows": rows}, indent=1))
    if not rows:
        print("DEAD: the widened join reaches nothing on this record",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
