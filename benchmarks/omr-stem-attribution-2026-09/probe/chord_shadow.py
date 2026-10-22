"""Is a "SOLO" stroke really solo? — the claim the whole rule design rested on.

⚠️⚠️ THE RULE WAS SCOPED TO STROKES CARRYING EXACTLY ONE HEAD, on the
reasoning that a chord is then impossible and the documented double-stop
regression therefore unreachable BY CONSTRUCTION. Crop `G00` refutes that by
eye: a stem-down chord whose UPPER member's box does not quite overlap the
stroke, so the pair presents as solo and the lower member sits legitimately
mid-stroke.

This asks the record the same question without a crop. For every solo
(head, stroke) pair it looks for ANOTHER notehead in the same cell that is
aligned with the stroke in x and lies within the stroke's y-span -- a chord
partner the overlap test missed. If those exist, "solo" is not a chord
guarantee and the structural safety claim is false.

⚠️ x-alignment is tested against the HEAD's own width, not a tuned window: a
chord's members stand at the same x as each other, within a notehead.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reach import collect, end_gap, overlap  # noqa: E402


def solo_pairs_with_shadows(stems, heads):
    """Every SOLO (head, stroke) pair, with the chord partners overlap missed.

    ⚠️ FACTORED OUT SO THE TEST EXERCISES THE CODE THAT RUNS. The first
    version of the test re-derived this loop inline, which tests a COPY -- the
    shape this repo records as *a fixture that does not match GATHER tests the
    test*. That same test also built a fixture whose two heads BOTH overlapped
    the stroke, so the pair was never solo and the case it was named for was
    never reached; it went red and said so.
    """
    rows = []
    for c, hs in heads.items():
        for sid, sb in stems.get(c, []):
            members = [(s, hb) for s, _h, hb in hs if overlap(sb, hb)]
            if len(members) != 1:
                continue
            subj, hb = members[0]
            hh = max(hb[3], 1e-6)
            hcy = hb[1] + hb[3] / 2.0
            hcx = hb[0] + hb[2] / 2.0
            g = end_gap(hb, sb)
            shadows = []
            for s2, _h2, b2 in hs:
                if s2 == subj:
                    continue
                cx2 = b2[0] + b2[2] / 2.0
                cy2 = b2[1] + b2[3] / 2.0
                # same x within one head width, and inside the stroke's y-span
                if (abs(cx2 - hcx) <= max(hb[2], b2[2])
                        and sb[1] - hh <= cy2 <= sb[1] + sb[3] + hh):
                    shadows.append(
                        {"subject": s2,
                         "dy_head_heights": round((cy2 - hcy) / hh, 2)})
            rows.append({"subject": subj, "stem": sid,
                         "gap_head_heights": round(g, 3),
                         "n_chord_shadows": len(shadows),
                         "shadows": shadows})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--gap", type=float, default=0.8)
    ap.add_argument("--crops", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    stems, heads, _ = collect(a.record)
    rows = solo_pairs_with_shadows(stems, heads)

    far = [r for r in rows if r["gap_head_heights"] > a.gap]
    out = {
        "label": a.label or Path(a.record).name,
        "solo_pairs": len(rows),
        "solo_pairs_with_a_chord_shadow":
            sum(1 for r in rows if r["n_chord_shadows"]),
        "FAR_gap_cut": a.gap,
        "FAR_pairs": len(far),
        "FAR_with_a_chord_shadow": sum(1 for r in far if r["n_chord_shadows"]),
        "FAR_rows": sorted(far, key=lambda r: -r["gap_head_heights"]),
    }
    print(json.dumps({k: v for k, v in out.items() if k != "FAR_rows"},
                     indent=2))
    print("\nFAR pairs (the rule's whole population) and their chord shadows:")
    for r in out["FAR_rows"]:
        print(f"  gap={r['gap_head_heights']:5.2f}  shadows={r['n_chord_shadows']}  "
              f"{r['subject']}  {[s['dy_head_heights'] for s in r['shadows']]}")
    if a.out:
        Path(a.out).write_text(json.dumps({**out, "rows": rows}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
