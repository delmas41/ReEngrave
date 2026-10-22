"""ROADMAP 2.84 -- the population: articulation boxes that sit where a ledger
line would, measured off a saved record (GATHER rows only; nothing decided).

    python3 benchmarks/omr-tenuto-ledger-2026-10/probe/census.py REC.json \
        [--pages 0,1] [--out census.json]

For every `Q.ARTICULATION_MARK` glyph: its class, its staff step (page px,
`family_precision._ledger_geometry`, the ledger decision's own ruler), how
far beyond the band, the offset from the nearest rung step, and every
notehead box in the SAME cell that x-overlaps it (`_heads_on_the_rung`, the
ledger decision's own head test) with its SIGNED outward distance
(+ = farther from the staff than the mark).

Buckets (facts, not a verdict):
  inside_band          the mark's centre is between line 1 and line 5
  head_beyond          outside the band, an x-overlapping head stands ON the
                       mark's box or farther out -- where a ledger stands
  heads_staffward_only outside, every x-overlapping head is staffward of it --
                       where an articulation stands
  no_head              outside, no x-overlapping head in the cell
  no_geometry          no staff step or no cell staff space
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import adjudicate, adjudicators  # noqa: F401,E402
from tools.omr.staged.adjudicate import Evidence  # noqa: E402
from tools.omr.staged.adjudicators import family_precision as FP  # noqa: E402
from tools.omr.staged.record import Kind, Q, Scope, Subject  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review.rerun import rebuild_gather  # noqa: E402


def log_pos(log, sub):
    rows = log.rows(Q.NOTEHEAD_STAFF_POSITION, sub)
    if not rows:
        return None
    try:
        return float(rows[-1].value)
    except (TypeError, ValueError):
        return None


def local_rung_offset(pos):
    """Spaces from the nearest rung step beyond the band, in the CELL's own
    grid (top line 0, positive DOWN, rungs at -2, -4, ... and 10, 12, ...);
    None inside the band."""
    if -0.0 <= pos <= 8.0:
        return None
    beyond = (-pos if pos < 0 else pos - 8.0) / 2.0
    return round(abs(beyond - round(beyond)), 3)


def head_facts(ev, box_row, space, step):
    """Every x-overlapping head, signed outward distance in spaces."""
    _n, x_r, y_r, w_r, h_r = box_row.value
    mid = y_r + h_r / 2.0
    sign = -1.0 if step > FP._BAND_TOP_STEP else (1.0 if step < 0 else None)
    out = []
    cell = ev.subject.at(Kind.CELL)
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        v = r.value
        if not isinstance(v, (list, tuple)) or len(v) != 5:
            continue
        if not FP._is_notehead_class(v[0]):
            continue
        _hn, hx, hy, hw, hh = v
        if min(hx + hw, x_r + w_r) - max(hx, x_r) <= 0.0:
            continue
        dy = ((hy + hh / 2.0) - mid) / space
        on = min(hy + hh, y_r + h_r) - max(hy, y_r) > 0.0
        pos = log_pos(ev.log, r.subject)
        local = None
        if pos is not None:
            half = space / 2.0
            top_y = (hy + hh / 2.0) - pos * half
            local = round((mid - top_y) / half, 3)
        out.append({"head": r.subject.to_key(), "class": v[0], "head_pos": pos,
                    "mark_pos_local": local,
                    "outward": None if sign is None else round(sign * dy, 3),
                    "on_box": on})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--pages", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    pages = None if a.pages is None else {int(p) for p in a.pages.split(",")}
    data = load_record(a.record)
    rec = data.get("record", data)
    keep = {Q.ARTICULATION_MARK, Q.GLYPH_BOX, Q.STAFF_LINES, Q.STAFF_SPACING,
            Q.CELL_STAFF_SPACE, Q.NOTEHEAD_STAFF_POSITION}
    rec = {"observations": [o for o in rec.get("observations") or ()
                            if o["quantity"] in keep],
           "abstentions": []}
    log, _ = rebuild_gather(rec)
    spec = adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER]
    rows = []
    for row in log.all_rows():
        if getattr(row, "quantity", None) != Q.ARTICULATION_MARK:
            continue
        if not hasattr(row, "value"):
            continue
        sub = row.subject
        if pages is not None and sub.at(Kind.PAGE).page not in pages:
            continue
        ev = Evidence(log, sub, spec)
        box = FP._glyph_box_row(ev)
        rec_row = {"subject": sub.to_key(), "class": row.value}
        if box is None:
            rec_row["bucket"] = "no_geometry"
            rows.append(rec_row)
            continue
        rec_row["page_box"] = (box.detail or {}).get("bbox_page_px")
        space = FP._cell_staff_space(ev)
        step, _ = FP._ledger_geometry(ev, box)
        if step is None or space is None:
            rec_row["bucket"] = "no_geometry"
            rows.append(rec_row)
            continue
        beyond = FP._beyond_spaces(step)
        rec_row.update(step=round(step, 3), beyond=round(beyond, 3),
                       rung_offset=(None if FP._rung_offset_spaces(step) is None
                                    else round(FP._rung_offset_spaces(step), 3)),
                       w_spaces=round(box.value[3] / space, 3),
                       h_spaces=round(box.value[4] / space, 3))
        heads = head_facts(ev, box, space, step)
        rec_row["heads"] = heads
        locs = [h["mark_pos_local"] for h in heads
                if h["mark_pos_local"] is not None]
        if locs:
            lp = sorted(locs)[len(locs) // 2]
            rec_row["pos_local"] = lp
            rec_row["rung_offset_local"] = local_rung_offset(lp)
        if beyond <= 0:
            b = "inside_band"
        elif not heads:
            b = "no_head"
        elif any(h["on_box"] or (h["outward"] or 0) > 0 for h in heads):
            b = "head_beyond"
        else:
            b = "heads_staffward_only"
        rec_row["bucket"] = b
        rows.append(rec_row)
    c = collections.Counter((r["bucket"], r["class"]) for r in rows)
    for (b, k), n in sorted(c.items()):
        print(f"{b:22s} {k:28s} {n}")
    print("total", len(rows))
    if a.out:
        Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
