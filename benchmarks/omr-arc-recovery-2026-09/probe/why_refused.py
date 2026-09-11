"""The refused arcs, partitioned by WHAT IS MISSING — with the stem rule live.

Four buckets, and they take different repairs, which is the whole reason for
splitting them (`detected_and_unrepresented` vs `decided_and_unwritten`, one
family further down):

* **NOTHING WAS READ** -- the arc's bars hold no gathered notehead at all.
  A DETECTION gap; named with a crop in FINDINGS §5.
* **HELD BACK BY THE EXPORTER** -- two or more gathered heads lie under the
  arc, but `_place_notes` declined them (no pitch, a narrowed duration,
  another staff's copy). The only bucket the exporter alone can close.
* **IN THE BAR, NOT UNDER THE ARC** -- heads were read and none is where the
  curve is. The cross-barline configuration lives here.
* **ONE HEAD ONLY** -- the bar genuinely holds one note under the curve.
"""
from __future__ import annotations

import collections
import json
import sys

from tools.omr import export as _legacy
from tools.omr.staged import export as E

sys.path.insert(0, "benchmarks/omr-arc-recovery-2026-09")
from arc_partition import heads_by_cell  # noqa: E402


def main(path: str, stems_on: bool = True) -> None:
    rec = E.Record(json.load(open(path)))
    parts, *_ = E.build(rec)
    heads = heads_by_cell(rec)
    stem_boxes = E._stem_boxes_by_cell(rec)

    t: "collections.Counter" = collections.Counter()
    for part in parts:
        measures, pma, kinds, spacings, tops, breaks = E._flatten_part(part)
        if not measures or not any(pma):
            continue
        cells = E._part_cells_in_order(part)
        probes = E._stem_probes(rec, part, stem_boxes) if stems_on else {}
        for segments in _legacy._merge_arcs_across_barlines(
                measures, pma, spacings, tops, breaks):
            covered = _legacy._noteheads_under(measures, segments,
                                               x_probes=probes)
            t["groups"] += 1
            if len(covered) >= 2:
                t["binds 2+ (written or chord-refused)"] += 1
                continue
            in_bar = under = 0
            for m_idx, (ax, _ay, aw, _ah) in segments:
                r_, c_ = cells[m_idx]
                pool = heads.get((r_.page, r_.system, r_.staff, c_)) or []
                boxed = [h for h in pool if h["page_box"]]
                in_bar += len(pool)
                if not boxed:
                    continue
                pad = _legacy._SLUR_ARC_PAD_NOTEHEADS * (
                    sum(h["page_box"][2] for h in boxed) / len(boxed))
                for h in boxed:
                    pb = h["page_box"]
                    xc = pb[0] + pb[2] / 2.0
                    if ax - pad <= xc <= ax + aw + pad:
                        under += 1
            if in_bar == 0:
                t["refused: NOTHING WAS READ in its bars"] += 1
            elif under >= 2:
                t["refused: heads under it, HELD BACK by the exporter"] += 1
            elif under <= 1 and in_bar > 0:
                t["refused: heads in the bar, NOT UNDER the arc"] += 1
    print(f"stem probes: {'ON' if stems_on else 'OFF'}")
    for k, v in t.most_common():
        print(f"  {k:48s} {v}")


if __name__ == "__main__":
    main(sys.argv[1], "--off" not in sys.argv)
