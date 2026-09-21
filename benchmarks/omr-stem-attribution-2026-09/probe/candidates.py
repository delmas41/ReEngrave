"""What separates a CHORD's inner head from a head crossing a NEIGHBOUR's stem?

⚠️⚠️ THE NAIVE END RULE REINTRODUCES THE DOCUMENTED DOUBLE-STOP REGRESSION.
A chord is several heads on ONE stem and its INNER head sits legitimately
mid-stroke, so *"the head must be at an end"* refuses the middle note of every
chord. Any rule here has to tell those two apart, and this probe asks whether
anything in the record can.

Three candidate discriminators, measured rather than chosen:

  ENDPOINT   does one of the stroke's two ends lie inside the head's OWN
             vertical extent? -- the convention stated directly, no constant.
  ANCHORED   does the stroke's near end lie inside the extent of the GROUP of
             heads on it? -- the chord-aware form of the same claim.
  GAP        the vertical gap from this head to the nearest other head on the
             same stroke, in units of THIS HEAD'S OWN HEIGHT -- the note's own
             ruler, the unit `_attached_dots` and `_stem_joined` already use.

⚠️ It reports the CROSS-TAB against group size, because a discriminator that
looks clean pooled and inverts on chords is the trap. And it dumps the
candidate list so a crop pass can put the population to the print -- which is
the only thing that can turn any of this into truth.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reach import collect, overlap  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    stems, heads, _ = collect(args.record)

    # stem -> members; head -> its stems
    per_stem = defaultdict(list)
    for c, hs in heads.items():
        for sid, sb in stems.get(c, []):
            for subj, _hid, hb in hs:
                if overlap(sb, hb):
                    per_stem[sid].append((subj, hb))

    stem_box = {}
    for c, ss in stems.items():
        for sid, sb in ss:
            stem_box[sid] = sb

    rows = []
    for sid, members in per_stem.items():
        sb = stem_box[sid]
        sy0, sy1 = sb[1], sb[1] + sb[3]
        gtop = min(hb[1] for _s, hb in members)
        gbot = max(hb[1] + hb[3] for _s, hb in members)
        for subj, hb in members:
            hy0, hy1 = hb[1], hb[1] + hb[3]
            hh = max(hb[3], 1e-6)
            hcy = hy0 + hb[3] / 2.0
            frac = (hcy - sb[1]) / sb[3] if sb[3] > 0 else 0.5
            endpoint = (hy0 <= sy0 <= hy1) or (hy0 <= sy1 <= hy1)
            # near end of the stroke, and whether the GROUP reaches it
            near_top = abs(hcy - sy0) <= abs(hcy - sy1)
            anchored = (gtop <= sy0 <= gbot) if near_top else (gtop <= sy1 <= gbot)
            # gap in this head's own heights to the nearest other member
            gaps = []
            for s2, b2 in members:
                if s2 == subj:
                    continue
                g = max(0.0, max(b2[1] - hy1, hy0 - (b2[1] + b2[3])))
                gaps.append(g / hh)
            rows.append({
                "subject": subj, "stem": sid, "group": len(members),
                "frac": round(frac, 4), "endpoint": endpoint,
                "anchored": anchored,
                "nearest_gap_heads": round(min(gaps), 3) if gaps else None,
                "head_box": [round(x, 1) for x in hb],
                "stem_box": [round(x, 1) for x in sb],
            })

    def tab(pred_name, pred):
        c = Counter()
        for r in rows:
            g = "solo" if r["group"] == 1 else "chord_or_more"
            c[f"{g}/{pred_name}={pred(r)}"] += 1
        return dict(sorted(c.items()))

    mid = [r for r in rows if 0.25 < r["frac"] < 0.75]
    out = {
        "label": args.label or Path(args.record).name,
        "head_stem_pairs": len(rows),
        "solo": sum(1 for r in rows if r["group"] == 1),
        "in_a_group": sum(1 for r in rows if r["group"] > 1),
        "ENDPOINT_crosstab": tab("endpoint", lambda r: r["endpoint"]),
        "ANCHORED_crosstab": tab("anchored", lambda r: r["anchored"]),
        "mid_stroke_0.25": {
            "n": len(mid),
            "solo": sum(1 for r in mid if r["group"] == 1),
            "in_a_group": sum(1 for r in mid if r["group"] > 1),
            "solo_and_not_endpoint":
                sum(1 for r in mid if r["group"] == 1 and not r["endpoint"]),
            "group_and_not_anchored":
                sum(1 for r in mid if r["group"] > 1 and not r["anchored"]),
        },
        # The rule's candidate population under each formulation.
        "would_refuse": {
            "ENDPOINT_only": sum(1 for r in rows if not r["endpoint"]),
            "ENDPOINT_or_ANCHORED": sum(
                1 for r in rows if not r["endpoint"] and not r["anchored"]),
        },
        "gap_percentiles_for_grouped_heads": _pcts(
            [r["nearest_gap_heads"] for r in rows
             if r["nearest_gap_heads"] is not None]),
    }
    print(json.dumps(out, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps({**out, "rows": rows}, indent=1))
    return 0


def _pcts(vals):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return {}
    return {f"p{int(p * 100):02d}": round(v[min(len(v) - 1, int(p * len(v)))], 3)
            for p in (0.05, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)}


if __name__ == "__main__":
    raise SystemExit(main())
