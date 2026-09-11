"""The two geometric repairs the crops name, apart and together.

The refused population is dominated by ONE printed configuration, read off
`crops/REFUSED-slur-p2s1st0c10.png` and `-c12.png`: a bar holding one chord at
its start, and a slur drawn from THAT chord to the chord at the start of the
NEXT bar. Such a curve fails `_noteheads_under` at BOTH ends and for two
different reasons:

* **its own chord** is outside the arc's ink, because the curve is drawn from
  STEM TOP to STEM TOP and a stem stands at the SIDE of its notehead -- the
  `_beam_levels` fault, already measured in this repo at 0.35-0.47 notehead
  widths and repaired there by joining the note to the beam BY ITS STEM;
* **the next bar's chord** is in a bar the arc has no segment in, and the
  arc's continuation fragment there is ~0 px wide -- because the chord sits at
  the bar's very start -- so `_merge_arcs_across_barlines` has nothing to join
  to and the chain breaks.

Each repair alone leaves the arc binding ONE head, which is still refused. So
they are measured apart AND together; this probe exists because the separate
numbers would under-state both.

⚠️ NOTHING IS REPAIRED HERE. This measures reach on the record, and prints the
distribution the cross-barline window would have to sit on -- so that a
constant, if one is ever proposed, is read off a gap rather than chosen.
"""
from __future__ import annotations

import collections
import json
import sys
from typing import Dict, List, Optional, Tuple

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q

sys.path.insert(0, "benchmarks/omr-arc-recovery-2026-09")
from arc_partition import heads_by_cell  # noqa: E402
sys.path.insert(0, "benchmarks/omr-arc-recovery-2026-09/probe")
from stem_reach import cell_x_maps  # noqa: E402


def stem_x_of_heads(rec, maps) -> Dict[str, float]:
    stems: Dict[str, List[Tuple[float, float, float]]] = collections.defaultdict(list)
    for o in rec.obs_of(Q.STEM):
        m = maps.get(o["subject"])
        v = o["value"]
        if m is None or not isinstance(v, (list, tuple)) or len(v) < 4:
            continue
        a, b = m
        cx0, cx1 = float(v[0]), float(v[0]) + float(v[2])
        stems[o["subject"]].append(
            ((a * cx0 + b + a * cx1 + b) / 2.0, cx0, cx1))
    out: Dict[str, float] = {}
    for o in rec.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        s = E._parse_subject(sub)
        if s["glyph"] is None or not rec.obs(Q.NOTEHEAD_CLASS, sub):
            continue
        v = o["value"]
        if not isinstance(v, (list, tuple)) or len(v) < 5:
            continue
        key = f"cell/{s['page']}/{s['system']}/{s['staff']}/{s['cell'] or 0}"
        hx0, hx1 = float(v[1]), float(v[1]) + float(v[3])
        for px, cx0, cx1 in stems.get(key, ()):
            if cx0 <= hx1 and cx1 >= hx0:
                out[sub] = px
                break
    return out


def main(path: str) -> None:
    rec = E.Record(json.load(open(path)))
    parts, *_ = E.build(rec)
    heads = heads_by_cell(rec)
    maps, _resid = cell_x_maps(rec)
    stem_x = stem_x_of_heads(rec, maps)

    tally: "collections.Counter" = collections.Counter()
    edge_gaps: List[float] = []
    for part in parts:
        measures, pma, kinds, spacings, tops, breaks = E._flatten_part(part)
        if not measures or not any(pma):
            continue
        cells = E._part_cells_in_order(part)

        def pool_of(m_idx):
            r_, c_ = cells[m_idx]
            return [h for h in (heads.get((r_.page, r_.system, r_.staff, c_)) or [])
                    if h["page_box"] and h["fate"] == "written"]

        for segments in _legacy._merge_arcs_across_barlines(
                measures, pma, spacings, tops, breaks):
            covered = _legacy._noteheads_under(measures, segments)
            base = len(covered)

            def count(with_stems: bool, with_cross: bool) -> int:
                seen = set()
                probes: List[Tuple[int, float, float]] = []
                for m_idx, (ax, _ay, aw, _ah) in segments:
                    probes.append((m_idx, ax, ax + aw))
                if with_cross:
                    sp = spacings[segments[-1][0]] or 0.0
                    tol = _legacy._SLUR_BOUNDARY_SPACES * sp
                    lm, lb = segments[0]
                    rm, rb = segments[-1]
                    rbar = measures[rm].get("bbox_page_px")
                    if rbar and sp and (float(rbar[2]) - (rb[0] + rb[2])) <= tol \
                            and rm + 1 < len(measures) and rm + 1 not in breaks:
                        nb = measures[rm + 1].get("bbox_page_px")
                        if nb:
                            probes.append((rm + 1, float(nb[0]),
                                           float(nb[0]) + CROSS_WINDOW * sp))
                    lbar = measures[lm].get("bbox_page_px")
                    if lbar and sp and (lb[0] - float(lbar[0])) <= tol \
                            and lm - 1 >= 0 and lm not in breaks:
                        pb_ = measures[lm - 1].get("bbox_page_px")
                        if pb_:
                            probes.append((lm - 1,
                                           float(pb_[2]) - CROSS_WINDOW * sp,
                                           float(pb_[2])))
                for m_idx, x0, x1 in probes:
                    pool = pool_of(m_idx)
                    if not pool:
                        continue
                    pad = _legacy._SLUR_ARC_PAD_NOTEHEADS * (
                        sum(h["page_box"][2] for h in pool) / len(pool))
                    for h in pool:
                        pbx = h["page_box"]
                        xs = [pbx[0] + pbx[2] / 2.0]
                        if with_stems and h["subject"] in stem_x:
                            xs.append(stem_x[h["subject"]])
                        if any(x0 - pad <= x <= x1 + pad for x in xs):
                            seen.add(h["subject"])
                return len(seen)

            tally["now"] += base >= 2
            tally["stems"] += count(True, False) >= 2
            tally["cross"] += count(False, True) >= 2
            tally["both"] += count(True, True) >= 2
            tally["groups"] += 1

            # The distribution the cross window sits on: for an arc whose ink
            # reaches its bar's RIGHT edge with no continuation, how far into
            # the next bar is its first written head?
            sp = spacings[segments[-1][0]] or 0.0
            rm, rb = segments[-1]
            rbar = measures[rm].get("bbox_page_px")
            if (rbar and sp and (float(rbar[2]) - (rb[0] + rb[2]))
                    <= _legacy._SLUR_BOUNDARY_SPACES * sp
                    and rm + 1 < len(measures) and rm + 1 not in breaks):
                nb = measures[rm + 1].get("bbox_page_px")
                pool = pool_of(rm + 1)
                if nb and pool:
                    d = min((h["page_box"][0] + h["page_box"][2] / 2.0
                             - float(nb[0])) for h in pool)
                    edge_gaps.append(d / sp)

    print(f"merged groups {tally['groups']}")
    print(f"  binding 2+ now                 {tally['now']}")
    print(f"  + the STEM rule alone          {tally['stems']}")
    print(f"  + the CROSS-BARLINE rule alone {tally['cross']}")
    print(f"  + BOTH                         {tally['both']}")
    edge_gaps.sort()
    print(f"\nfor an arc reaching its bar's RIGHT edge with no continuation:")
    print(f"  distance from the barline to the next bar's first written head")
    print(f"  n={len(edge_gaps)} (staff spaces)")
    hist: "collections.Counter" = collections.Counter()
    for g in edge_gaps:
        hist[round(min(g, 8.0) * 2) / 2] += 1
    for k in sorted(hist):
        print(f"   {k:5.1f} {hist[k]:4d} {'#' * min(60, hist[k])}")


CROSS_WINDOW = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0

if __name__ == "__main__":
    main(sys.argv[1])
