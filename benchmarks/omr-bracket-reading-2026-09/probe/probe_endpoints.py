"""Does a bracket END, or did the ink just STOP?

The reader's failure mode is the mirror of the incumbent's.  Incidental ink can
only push a crossing count UP, so the barline-stop rule fails by MERGING blocks
(measured elsewhere: boundary recall 0.523, precision 0.920).  A rule broken by
a bad scan splits one stroke into two, so the bracket reader fails by
SPLITTING — it manufactures a boundary where the printed bracket runs straight
through.

A printed bracket TERMINATES at the outer staff line of its block, with a
terminal that overshoots slightly.  A break in the ink stops wherever the scan
lost it.  This measures both populations directly: for every stroke, the signed
distance from each end to the nearest staff boundary line (the top line of its
first covered staff, the bottom line of its last), in staff spacings.

If the two populations separate, the reader gets an endpoint gate for free and
its splitting failure closes.  If they do not, that is the finding and the
reader stays a second opinion rather than a replacement.

    probe_endpoints.py --pages-per-edition 8 --out out/endpoints.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.preprocessing import render_page              # noqa: E402
from tools.omr.staff_detector import detect_staves           # noqa: E402
from tools.omr.bracket_reader import (                       # noqa: E402
    strokes_at_left_edge, covered_staves, is_rule)

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
WORKS = Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/"
             "omr-scan-e2e-2026-09/works.json")

# Bach / Peters is the only edition in the corpus whose printed bracket blocks
# are known independently AND constant across the movement: three choirs of
# three, hand-verified from the print (crop out/crops/bach-p8-s0.png) and
# agreeing with `benchmarks/omr-structural-parts-2026-09`'s hand adjudication
# of the same edition's p1 (3,3,3,1,2).  So on Bach a stroke ending at gap
# 2, 5 or 8 is a TERMINUS and any other end is a BREAK — a ground truth for
# this question that costs no new labelling.
BACH_TRUE_BOUNDARIES = {2, 5, 8}


def _flare(binary, st, spacing: float, end: str) -> float:
    """How much wider the stroke is at `end` than along its body.

    A printed bracket TERMINATES in a serif that flares outward; ink that
    merely stopped does not.  Measured as (widest ink row within half a staff
    spacing of the end) / (median ink row over the stroke's body), both taken
    in a window a little wider than the stroke itself so a flare has room to
    show.  1.0 means no flare.
    """
    import numpy as _np
    pad = int(round(2.0 * spacing))
    x0 = max(0, st.x_left - pad)
    x1 = min(binary.shape[1], st.x_right + pad + 1)
    y0, y1 = st.y_top, st.y_bot
    if y1 <= y0 or x1 <= x0:
        return float("nan")
    ink = (binary[y0:y1 + 1, x0:x1] < 128)
    widths = ink.sum(axis=1).astype(float)
    body = float(_np.median(widths)) or 1.0
    k = max(2, int(round(0.5 * spacing)))
    tip = widths[:k] if end == "top" else widths[-k:]
    return round(float(tip.max()) / body, 3)


def scan_editions() -> list[tuple[str, Path]]:
    rows = json.loads(WORKS.read_text())["rows"]
    seen: dict[str, Path] = {}
    for r in rows:
        cp = r["edition"]["catalog_path"]
        seen.setdefault(cp.split("/")[1], LIB / cp)
    return sorted(seen.items())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-per-edition", type=int, default=8)
    ap.add_argument("--first-page", type=int, default=2)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    recs = []
    for tag, pdf in scan_editions():
        if tag != "bach":
            continue
        for pg in range(args.first_page,
                        args.first_page + args.pages_per_edition):
            try:
                pi = render_page(str(pdf), pg, dpi=args.dpi)
                staves = sorted(detect_staves(pi).staves, key=lambda s: s.top_y)
            except Exception as exc:                          # noqa: BLE001
                print(f"{tag} p{pg}: FAILED {exc}", flush=True)
                continue
            by_sys: dict[int, list] = defaultdict(list)
            for s in staves:
                by_sys[s.system_index].append(s)
            for si, members in sorted(by_sys.items()):
                if len(members) != 12:
                    continue
                sp = statistics.median([s.line_spacing_px for s in members])
                strokes, _g = strokes_at_left_edge(pi.binary, members)
                for st in strokes:
                    if not is_rule(st):
                        continue
                    cov = covered_staves(st, members)
                    if not cov:
                        continue
                    top_ref = members[cov[0]].top_y
                    bot_ref = members[cov[-1]].bottom_y
                    # a stroke's LOWER end at gap g means it ended after staff g
                    recs.append({
                        "page": pg, "system": si,
                        "covers": cov,
                        "top_gap": cov[0] - 1,       # -1 = system top
                        "bot_gap": cov[-1],          # n-1 = system bottom
                        "d_top": round((st.y_top - top_ref) / sp, 3),
                        "d_bot": round((st.y_bot - bot_ref) / sp, 3),
                        "flare_top": _flare(pi.binary, st, sp, "top"),
                        "flare_bot": _flare(pi.binary, st, sp, "bot"),
                        "thickness": st.thickness_spacings,
                        "x_centre": st.x_centre,
                    })
    Path(args.out).write_text(json.dumps(recs, indent=1))

    def bucket(kind: str, field: str) -> tuple[list[float], list[float]]:
        term, brk = [], []
        for r in recs:
            if kind == "bot":
                g, d = r["bot_gap"], r[field]
                if g == 11:                    # the system's own bottom
                    continue
            else:
                g, d = r["top_gap"], r[field]
                if g == -1:                    # the system's own top
                    continue
            if d != d:                         # NaN
                continue
            (term if g in BACH_TRUE_BOUNDARIES else brk).append(d)
        return term, brk

    def report(title: str, term: list[float], brk: list[float]) -> None:
        print(f"-- {title} --")
        for name, vals in (("TERMINUS (ends at a true boundary)", term),
                           ("BREAK    (ends anywhere else)     ", brk)):
            if not vals:
                print(f"   {name}  n=0")
                continue
            vs = sorted(vals)
            print(f"   {name}  n={len(vs):3d}  "
                  f"min {vs[0]:+.2f}  p10 {vs[len(vs)//10]:+.2f}  "
                  f"med {statistics.median(vs):+.2f}  "
                  f"p90 {vs[-max(1, len(vs)//10)]:+.2f}  max {vs[-1]:+.2f}")
        if term and brk:
            lo, hi = min(term), max(term)
            inside = sum(lo <= b <= hi for b in brk)
            print(f"   termini span [{lo:+.2f},{hi:+.2f}]; "
                  f"{inside}/{len(brk)} breaks fall inside that span "
                  f"({inside/len(brk):.3f})")
        print()

    print("Bach / Peters, 12-staff systems.  True bracket boundaries: "
          f"{sorted(BACH_TRUE_BOUNDARIES)} (blocks 3|3|3)")
    print(f"{len(recs)} rule strokes\n")
    for kind, ref in (("top", "first staff TOP line"),
                      ("bot", "last staff BOTTOM line")):
        t, b = bucket(kind, "d_top" if kind == "top" else "d_bot")
        report(f"{kind} end: distance to its block's {ref} (staff spacings)",
               t, b)
    for kind in ("top", "bot"):
        t, b = bucket(kind, "flare_top" if kind == "top" else "flare_bot")
        report(f"{kind} end: TERMINAL FLARE (widest tip row / body row)", t, b)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
