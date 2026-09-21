"""Is the head at an END of the stroke? -- measured in the HEAD'S OWN HEIGHT.

⚠️⚠️ THIS REPLACES THE `frac` STATISTIC, WHICH THE CROPS REFUTED. `frac` is
the head centre's position along the stroke as a FRACTION of the stroke's
length, and it conflates two different things:

    a head part-way along a LONG stroke          -- the fault, if it exists
    a head at the end of a SHORT stroke fragment -- harmless

because when the stroke is barely longer than the head, a head sitting at its
end scores frac ~0.3 by arithmetic alone. Measured on the 24 crops: every
`MID` pair had a stroke of 1.39-2.20 head-heights and every `END` pair
2.42-4.63, while the distance from the head's centre to the nearer end was
0.45-0.64 and 0.14-0.32 head-heights respectively -- i.e. ALL of them were at
an end, and `frac` had manufactured a population out of stroke length.

The scale-free question is: **how far is the head's centre from the nearer end
of the stroke, in units of its own height?** A head at an end scores about
0.5, because a stem leaves the head at its top or bottom edge and the centre
is half a height away. A head genuinely crossed part-way by a neighbour's
stroke scores much more.

⚠️ Reported SOLO and GROUPED apart. A chord's inner head is legitimately far
from an end, so pooling them would hide the only population the rule may act
on and invent a tail in the only one it may not touch.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reach import collect, end_gap as _end_gap, overlap  # noqa: E402


def _stats(vals):
    v = sorted(vals)
    if not v:
        return {}
    def q(p):
        return round(v[min(len(v) - 1, int(p * len(v)))], 3)
    return {"n": len(v), "min": round(v[0], 3), "p05": q(.05), "p25": q(.25),
            "p50": q(.50), "p75": q(.75), "p90": q(.90), "p95": q(.95),
            "p99": q(.99), "max": round(v[-1], 3)}


def _hist(vals, hi=4.0, nbins=20):
    out = [0] * (nbins + 1)
    for v in vals:
        out[min(nbins, int(v / hi * nbins))] += 1
    rows = [[round(i * hi / nbins, 2), round((i + 1) * hi / nbins, 2), out[i]]
            for i in range(nbins)]
    rows.append([hi, None, out[nbins]])
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    stems, heads, _ = collect(a.record)
    solo, grouped, rows = [], [], []
    by_group = defaultdict(list)
    for c, hs in heads.items():
        for sid, sb in stems.get(c, []):
            members = [(s, hb) for s, _h, hb in hs if overlap(sb, hb)]
            if not members:
                continue
            for subj, hb in members:
                hh = max(hb[3], 1e-6)
                gap = _end_gap(hb, sb)
                rec = {"subject": subj, "stem": sid, "group": len(members),
                       "gap_head_heights": round(gap, 4),
                       "stroke_in_head_heights": round(sb[3] / hh, 3)}
                rows.append(rec)
                by_group[len(members)].append(gap)
                (solo if len(members) == 1 else grouped).append(gap)

    out = {
        "label": a.label or Path(a.record).name,
        "pairs": len(rows),
        "SOLO_gap_head_heights": _stats(solo),
        "GROUPED_gap_head_heights": _stats(grouped),
        "solo_histogram": _hist(solo),
        "grouped_histogram": _hist(grouped),
        "by_group_size": {str(k): _stats(v) for k, v in sorted(by_group.items())},
        # How many SOLO pairs sit further from an end than a head at an end
        # possibly could? A head at an end scores ~0.5; these cuts are
        # reported as a CURVE, not chosen.
        "solo_beyond": {f"{t:.1f}": sum(1 for g in solo if g > t)
                        for t in (0.75, 1.0, 1.25, 1.5, 2.0, 3.0)},
        "grouped_beyond": {f"{t:.1f}": sum(1 for g in grouped if g > t)
                           for t in (0.75, 1.0, 1.25, 1.5, 2.0, 3.0)},
    }
    print(json.dumps({k: v for k, v in out.items()
                      if not k.endswith("histogram")}, indent=2))
    print("\nSOLO histogram (gap in head-heights; a head AT an end ~0.5)")
    mx = max(r[2] for r in out["solo_histogram"]) or 1
    for lo, hi, n in out["solo_histogram"]:
        lbl = f"{lo:4.2f}..{hi:4.2f}" if hi is not None else f">{lo:4.2f}    "
        print(f"  {lbl} {n:5d} {'#' * int(50 * n / mx)}")
    print("\nGROUPED histogram")
    mx = max(r[2] for r in out["grouped_histogram"]) or 1
    for lo, hi, n in out["grouped_histogram"]:
        lbl = f"{lo:4.2f}..{hi:4.2f}" if hi is not None else f">{lo:4.2f}    "
        print(f"  {lbl} {n:5d} {'#' * int(50 * n / mx)}")
    if a.out:
        Path(a.out).write_text(json.dumps({**out, "rows": rows}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
