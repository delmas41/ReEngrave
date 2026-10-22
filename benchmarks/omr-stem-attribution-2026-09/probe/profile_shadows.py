"""How much of the PROFILE reader's far-from-an-end population is a CHORD?

⚠️ COMPUTED RATHER THAN EYEBALLED, ON PURPOSE. The profile reader's
far-from-an-end population on Breitkopf is 124 pairs, and its crops are the
densest passages on the plate -- the stratum my own crop pass is worst at (6 of
8 `cannot_tell` on the far easier shipped population, and I got 2 of 24 tiles
wrong at sheet magnification). An eye that unreliable should not be the
instrument for 124 tiles.

So this asks the same question `chord_shadow.py` asks of the shipped strokes:
of the pairs an end rule would refuse, how many have another notehead aligned
in x and inside the stroke's y-span -- i.e. look like a chord the overlap test
did not join?

It reuses the crop manifest, which already carries every FAR pair's stroke box,
so it needs no second cell re-cut.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reach import collect  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--crops", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    _stems, heads, _ = collect(a.record)
    by_cell = {}
    for c, hs in heads.items():
        by_cell[c] = [(s, hb) for s, _h, hb in hs]
    box = {s: hb for c, hs in heads.items() for s, _h, hb in hs}

    man = json.load(open(a.crops))
    rows = []
    for r in man["index"]:
        hb = box.get(r["subject"])
        if hb is None:
            continue
        sb = r["stem_box_canonical"]
        hh = max(hb[3], 1e-6)
        hcx, hcy = hb[0] + hb[2] / 2.0, hb[1] + hb[3] / 2.0
        shadows = []
        for s2, b2 in by_cell.get(r["cell"], []):
            if s2 == r["subject"]:
                continue
            cx2, cy2 = b2[0] + b2[2] / 2.0, b2[1] + b2[3] / 2.0
            if (abs(cx2 - hcx) <= max(hb[2], b2[2])
                    and sb[1] - hh <= cy2 <= sb[1] + sb[3] + hh):
                shadows.append(round((cy2 - hcy) / hh, 2))
        rows.append({"tile": r["tile"], "stratum": r["stratum"],
                     "gap": r["gap_head_heights"],
                     "n_chord_shadows": len(shadows), "dy": shadows})

    far = [r for r in rows if r["stratum"] == "FAR"]
    with_sh = [r for r in far if r["n_chord_shadows"]]
    out = {
        "label": a.label,
        "FAR_pairs": len(far),
        "FAR_with_a_chord_shadow": len(with_sh),
        "FAR_share_with_a_chord_shadow": (round(len(with_sh) / len(far), 4)
                                          if far else None),
        "FAR_without": len(far) - len(with_sh),
        "END_control": sum(1 for r in rows if r["stratum"] == "END"),
        "rows": rows,
    }
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
