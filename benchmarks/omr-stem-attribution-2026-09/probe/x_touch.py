"""The OTHER failure mode: the boxes GRAZE and the head never touches the ink.

⚠️⚠️ WRITTEN BECAUSE THE PRINT FOUND ONE. Tile `G02` of the far-from-an-end
crop pass sits in the CONTROL stratum at a gap of 0.19 head heights -- as
"at an end" as anything on the sheet -- and is nonetheless a real
misattribution: the stroke stands above and to the RIGHT of the head and
belongs to the NEXT note of the beamed run; the two boxes merely graze in x.

That is a HORIZONTAL failure and the end-gap statistic is blind to it by
construction. So a rule built on the end gap alone is not merely low-reach, it
is provably incomplete -- and this measures the population the other statistic
would reach, so the next session has a number rather than a hunch.

⚠️ NOTHING HERE IS PROPOSED AS A RULE. There is one print-settled instance.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reach import collect, overlap  # noqa: E402


def _stats(v):
    v = sorted(v)
    if not v:
        return {}
    def q(p):
        return round(v[min(len(v) - 1, int(p * len(v)))], 4)
    return {"n": len(v), "min": round(v[0], 4), "p01": q(.01), "p05": q(.05),
            "p25": q(.25), "p50": q(.50), "p75": q(.75), "max": round(v[-1], 4)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--crops", default="", help="a crop manifest to annotate")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    stems, heads, _ = collect(a.record)
    solo, grouped = [], []
    per_pair = {}
    for c, hs in heads.items():
        for sid, sb in stems.get(c, []):
            members = [(s, hb) for s, _h, hb in hs if overlap(sb, hb)]
            if not members:
                continue
            for subj, hb in members:
                # how much of the STROKE's width lies inside the head's x-span
                ov = (min(sb[0] + sb[2], hb[0] + hb[2])
                      - max(sb[0], hb[0]))
                frac_of_stroke = ov / max(sb[2], 1e-6)
                frac_of_head = ov / max(hb[2], 1e-6)
                rec = {"x_overlap_px": round(ov, 2),
                       "frac_of_stroke_width": round(frac_of_stroke, 4),
                       "frac_of_head_width": round(frac_of_head, 4)}
                per_pair[(subj, sid)] = rec
                (solo if len(members) == 1 else grouped).append(frac_of_stroke)

    out = {"label": a.label or Path(a.record).name,
           "SOLO_frac_of_stroke_width": _stats(solo),
           "GROUPED_frac_of_stroke_width": _stats(grouped),
           "solo_below": {f"{t:.2f}": sum(1 for x in solo if x < t)
                          for t in (0.05, 0.10, 0.20, 0.30, 0.50)},
           "solo_n": len(solo)}

    if a.crops:
        man = json.load(open(a.crops))
        rows = []
        for r in man["index"]:
            k = (r["subject"], r["stem"])
            rows.append({"tile": r["tile"], "stratum": r["stratum"],
                         "gap_head_heights": r["gap_head_heights"],
                         **per_pair.get(k, {})})
        out["crops"] = rows

    print(json.dumps(out, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
