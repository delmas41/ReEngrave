"""2.221 m0 (barlines system-wide): per system, which barline columns does the PAGE show, and which does the shared
measure extractor cut?  STAGED/LEGACY-neutral: reads `measure_extractor.detect_barlines` (shared; callers are the staged
pipeline `staged/pipeline.py` and LEGACY `transcribe.py`) and re-measures on the same 600 dpi binary.

For each system: candidate x columns = per-staff full-height rules (existing `_detect_barlines_per_staff`) U columns whose ink
runs straight through an inter-staff gap. Each candidate is classed by what its ink spans (Sean 2026-10-29: "sometimes the
barlines extend the length of the whole system"):
  through_system : every inter-staff gap of the system holds the rule
  through_group  : a run of >=2 staves is joined by the rule, not all
  per_staff      : no gap holds it; judged by how many staves show a full-height rule (majority / minority / half)
and compared with the columns `detect_barlines` accepted (cut).
Usage: barline_columns.py PDF PAGES OUT.json
"""
from __future__ import annotations
import json, sys
import numpy as np
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr import measure_extractor as me

XTOL = 12          # same cluster tolerance detect_barlines uses
GAP_RUN = 0.90     # share of a gap's rows that must carry ink on the rule (measured thin: see width check)


def gap_rule_columns(bin_img, upper, lower):
    """x columns where ink is present on >= GAP_RUN of the gap rows, and the run is thin (<= 0.7 sp)."""
    top, bot = upper.bottom_y + 1, lower.top_y
    if bot - top < 3:
        return []
    strip = bin_img[top:bot, :] < 128
    frac = strip.mean(axis=0)
    cols = np.where(frac >= GAP_RUN)[0]
    if cols.size == 0:
        return []
    sp = max(1.0, (upper.line_spacing_px + lower.line_spacing_px) / 2)
    runs, s = [], cols[0]
    for a, b in zip(cols[:-1], cols[1:]):
        if b != a + 1:
            runs.append((s, a)); s = b
    runs.append((s, cols[-1]))
    return [int(round((a + b) / 2)) for a, b in runs if (b - a + 1) <= 0.7 * sp]


def classify(system_staves, bin_img, accepted):
    st = sorted(system_staves, key=lambda s: s.top_y)
    n = len(st)
    obs = []                                  # (x, kind, staff_pos)
    for i, s in enumerate(st):
        for x in me._detect_barlines_per_staff(bin_img, s):
            obs.append((x, "rule", i))
    gaps = [gap_rule_columns(bin_img, st[i], st[i + 1]) for i in range(n - 1)]
    for i, g in enumerate(gaps):
        for x in g:
            obs.append((x, "gap", i))
    obs.sort()
    clusters = []
    for o in obs:
        if clusters and o[0] - clusters[-1][-1][0] <= XTOL:
            clusters[-1].append(o)
        else:
            clusters.append([o])
    for a in accepted:                        # a cut with no observation at all is still a cut
        if not any(abs(sum(o[0] for o in c) / len(c) - a) <= XTOL for c in clusters):
            clusters.append([(a, "cut_only", -1)])
    out = []
    for c in clusters:
        x = int(round(sum(o[0] for o in c) / len(c)))
        votes = sorted({o[2] for o in c if o[1] == "rule"})
        crossed = sorted({o[2] for o in c if o[1] == "gap"})
        # staff groups joined by a crossed gap
        joined, run = [], [0]
        for i in range(n - 1):
            if i in crossed:
                run.append(i + 1)
            else:
                joined.append(run); run = [i + 1]
        joined.append(run)
        biggest = max(len(r) for r in joined)
        if n >= 2 and len(crossed) == n - 1:
            span = "through_system"
        elif biggest >= 2:
            span = "through_group"
        else:
            span = "per_staff"
        if span == "per_staff":
            frac = len(votes) / n
            vote = "majority" if frac > 0.5 else ("half" if frac == 0.5 else "minority")
        else:
            vote = "n/a"
        cut = any(abs(a - x) <= XTOL for a in accepted)
        lacking = n - len(votes) if span != "per_staff" else None
        out.append(dict(x=x, span=span, vote=vote, votes=len(votes), n=n, crossed=len(crossed), cut=cut,
                        lacking=lacking, cut_only=(c[0][1] == "cut_only")))
    return out


def main():
    pdf, pages, outp = sys.argv[1], [int(p) for p in sys.argv[2].split(",")], sys.argv[3]
    res = []
    for p in pages:
        pws = detect_staves(render_page(pdf, p, dpi=600))
        me.detect_barlines(pws)
        b = pws.page.binary
        systems = {}
        for s in pws.staves:
            if len(s.line_ys) >= 5:
                systems.setdefault(s.system_index, []).append(s)
        for sidx, sts in sorted(systems.items()):
            acc = sorted(bl.x for bl in pws.barlines if bl.system_index == sidx)
            res.append(dict(page=p, system=sidx, n_staves=len(sts), cuts=acc, cols=classify(sts, b, acc)))
        print("page", p, len(systems), "systems", flush=True)
    json.dump(res, open(outp, "w"))


if __name__ == "__main__":
    main()
