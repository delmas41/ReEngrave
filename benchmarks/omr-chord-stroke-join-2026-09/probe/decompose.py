"""Reproduce the sibling lane's `solo_pairs_with_a_chord_shadow` (73 / 98),
then DECOMPOSE it -- because that figure is not a reach.

⚠️⚠️ A SHADOW IS NOT A MISSING JOIN. `chord_shadow.py` asks whether a stroke
claimed by exactly one head has ANOTHER head at its x inside its y-span. It
does NOT ask whether that other head is stemless. A shadow that already
carries a stroke of its own is not a chord member the overlap test dropped --
it is a second voice, or a neighbour, or a head whose own stem was read
perfectly well.

So this splits the 73 / 98 into:
  * shadow already has a stroke of its own   -- nothing to repair
  * shadow is STEMLESS                       -- the only repairable population

⚠️ The sibling's two windows are RESTATED here rather than imported, because
the point is to reproduce a published number with its own conventions: the x
test is a CENTRE distance within one head width (looser than box overlap) and
the y test is the shadow's CENTRE inside the stroke's span expanded by one
head height. Both are marked at their site. The restatement is checked by the
number coming out equal to the published one.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import _boxes_overlap, _stems_on, collect  # noqa: E402


def shadows(stems_c, heads_c):
    """The sibling lane's solo-pair rows, with one column added."""
    rows = []
    for s in stems_c:
        sb = s.value
        members = [h for h in heads_c if _boxes_overlap(sb, h.value)]
        if len(members) != 1:
            continue
        me = members[0]
        hb = me.value
        hh = max(hb[3], 1e-6)
        hcx = hb[0] + hb[2] / 2.0
        hcy = hb[1] + hb[3] / 2.0
        sh = []
        for o in heads_c:
            if o is me:
                continue
            b2 = o.value
            cx2, cy2 = b2[0] + b2[2] / 2.0, b2[1] + b2[3] / 2.0
            # the sibling's windows, restated verbatim
            if (abs(cx2 - hcx) <= max(hb[2], b2[2])
                    and sb[1] - hh <= cy2 <= sb[1] + sb[3] + hh):
                sh.append({
                    "subject": o.subject,
                    "dy_head_heights": round((cy2 - hcy) / hh, 2),
                    # ⚠️ THE COLUMN THE SIBLING DID NOT HAVE
                    "shadow_is_stemless": not _stems_on(b2, stems_c),
                })
        rows.append({"head": me.subject, "stem": s.id,
                     "n_chord_shadows": len(sh), "shadows": sh})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    stems, heads, _b, _n = collect(a.record)
    rows = []
    for c, hs in heads.items():
        ss = stems.get(c, [])
        if ss:
            rows.extend(shadows(ss, hs))

    with_any = [r for r in rows if r["n_chord_shadows"]]
    stemless_shadow = [r for r in with_any
                       if any(s["shadow_is_stemless"] for s in r["shadows"])]
    n_shadow_rows = sum(r["n_chord_shadows"] for r in rows)
    n_stemless = sum(1 for r in rows for s in r["shadows"]
                     if s["shadow_is_stemless"])
    close = sum(1 for r in rows for s in r["shadows"]
                if s["shadow_is_stemless"] and abs(s["dy_head_heights"]) <= 2.0)

    out = {
        "label": a.label or Path(a.record).name,
        # the two published figures, re-derived
        "solo_pairs": len(rows),
        "solo_pairs_with_a_chord_shadow": len(with_any),
        # the decomposition
        "shadow_rows_total": n_shadow_rows,
        "shadow_rows_where_the_shadow_IS_STEMLESS": n_stemless,
        "shadow_rows_stemless_AND_within_2_head_heights": close,
        "solo_pairs_with_a_STEMLESS_shadow": len(stemless_shadow),
    }
    print(json.dumps(out, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps({**out, "rows": rows}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
