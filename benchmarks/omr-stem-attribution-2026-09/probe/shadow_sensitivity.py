"""How much does the chord-shadow count depend on its own y tolerance?

⚠️⚠️ WRITTEN BECAUSE THE PRINT CAUGHT THE PROBE BEING ONE-SIDED. Tile `G86` of
the profile crop pass is unmistakably a DYAD — two dotted hollow heads on
ledger lines sharing an up-stem — and `chord_shadow.py` reported ZERO shadows
for it. The partner is in the record (`glyph/0/0/5/4/2`), at the same x to
8.5 px; it failed only the y test, by **19.5 px** — 0.27 head-heights past the
stroke's end plus the one-head-height tolerance.

So the shadow count is a LOWER BOUND on how much of the far-from-an-end
population is really a chord, and *"36 shadow-free profile candidates"* is an
upper bound on the misattribution candidates rather than a count of them.

This reports the whole curve instead of picking a tolerance. ⚠️ It is a
SENSITIVITY REPORT, not a calibration: no value is proposed, and the shipped
`chord_shadow.py` is left at 1.0 so its published numbers stand as taken.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reach import collect, end_gap, overlap  # noqa: E402

TOLS = (0.5, 1.0, 1.5, 2.0, 3.0)


def shadows(hb, sb, hs, subj, tol_heights):
    hh = max(hb[3], 1e-6)
    t = tol_heights * hh
    hcx, hcy = hb[0] + hb[2] / 2.0, hb[1] + hb[3] / 2.0
    n = 0
    for s2, b2 in hs:
        if s2 == subj:
            continue
        cx2, cy2 = b2[0] + b2[2] / 2.0, b2[1] + b2[3] / 2.0
        if (abs(cx2 - hcx) <= max(hb[2], b2[2])
                and sb[1] - t <= cy2 <= sb[1] + sb[3] + t):
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--crops", default="",
                    help="a crop manifest (the PROFILE strokes); "
                         "omit to use the record's own Q.STEM rows")
    ap.add_argument("--gap", type=float, default=1.0)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    stems, heads, _ = collect(a.record)
    by_cell = {c: [(s, hb) for s, _h, hb in hs] for c, hs in heads.items()}
    box = {s: hb for c, hs in heads.items() for s, _h, hb in hs}

    pairs = []
    if a.crops:
        for r in json.load(open(a.crops))["index"]:
            if r["stratum"] != "FAR":
                continue
            hb = box.get(r["subject"])
            if hb is None:
                continue
            pairs.append((r["subject"], r["cell"], hb,
                          tuple(r["stem_box_canonical"])))
    else:
        for c, hs in heads.items():
            for sid, sb in stems.get(c, []):
                members = [(s, hb) for s, _h, hb in hs if overlap(sb, hb)]
                if len(members) != 1:
                    continue
                subj, hb = members[0]
                if end_gap(hb, sb) > a.gap:
                    pairs.append((subj, c, hb, sb))

    curve = {}
    for t in TOLS:
        n = sum(1 for subj, c, hb, sb in pairs
                if shadows(hb, sb, by_cell.get(c, []), subj, t))
        curve[f"{t:.1f}"] = {"with_a_shadow": n,
                             "without": len(pairs) - n,
                             "share": round(n / len(pairs), 4) if pairs else None}

    out = {"label": a.label, "source": "profile" if a.crops else "record",
           "gap_cut": a.gap, "FAR_pairs": len(pairs),
           "by_y_tolerance_in_head_heights": curve}
    print(json.dumps(out, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
