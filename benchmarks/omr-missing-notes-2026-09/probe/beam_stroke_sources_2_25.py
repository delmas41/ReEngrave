"""ROADMAP 2.25 -- for every note whose duration counts >= 1 beam level,
which STROKES were counted, and does each coincide with a ledgerLine box, a
CV ledger rung (`Q.LEDGER_RUNG_INK`) of THIS head, a wedge box, an arc
(slur/tie) box, or ink standing outside this cell's OWN staff band (through
the 4-space pad)?

PATH: STAGED. Reads ONE saved record once (`record_io.load_record`),
rebuilds its GATHER rows into a `Log` (`review.rerun.rebuild_gather`), and
for every `Q.DURATION` verdict whose OWN recorded `detail.beam_evidence ==
"read"` (>= 1 beam level actually counted) re-derives the counted strokes
through the SAME live helpers `adjudicate_duration` calls today (2.18/2.18b
already applied) -- `_own_stem_side`, `_on_stem_side`, `_join_tolerance`,
`_beyond_own_stem`, `_kept_beams`, `_stem_joined`, `_beam_levels` -- so the
population classified here is exactly the population the decision counted,
not a re-invented one.

CONTROL (can fail): the re-derived `certain` must equal the verdict's own
`detail.levels_certain` for every row, or the probe exits 1.

    python3 benchmarks/omr-missing-notes-2026-09/probe/beam_stroke_sources_2_25.py \\
        <record.json> --out <out.json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import adjudicate as A                      # noqa: E402
from tools.omr.staged import adjudicators                         # noqa: E402,F401
from tools.omr.staged.adjudicators import rhythm as RH            # noqa: E402
from tools.omr.staged.record import (Kind, Outcome, Q, Scope,     # noqa: E402
                                     Subject)
from tools.omr.staged.record_io import load_record                # noqa: E402
from tools.omr.staged.review.rerun import rebuild_gather           # noqa: E402


def _box_overlap(a, b) -> bool:
    return RH._boxes_overlap(a, b)


def _cell_up_factor(ev: A.Evidence, cell) -> Optional[float]:
    """`up` such that `page_x = cell_bbox_page_px[0] + canonical_x / up`,
    derived EMPIRICALLY from any one detector `Q.GLYPH_BOX` row in this cell
    that carries both frames -- there is no persisted `upscale_factor`
    quantity on a SAVED record, so this is solved from the same pair
    `gather._page_box` computes forward, rather than re-derived a second
    way that could disagree with it.
    """
    rows = ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                   subject=cell)
    for r in rows:
        d = r.detail or {}
        page = d.get("bbox_page_px")
        v = r.value
        if not page or len(page) != 4 or not isinstance(v, (list, tuple)):
            continue
        page_w = page[2] - page[0]
        if page_w <= 0:
            continue
        try:
            can_w = float(v[3])
        except (TypeError, ValueError, IndexError):
            continue
        if can_w > 0:
            return can_w / page_w
    return None


def _cell_box_page(ev: A.Evidence, cell) -> Optional[Tuple[float, float,
                                                            float, float]]:
    rows = ev.log.rows(Q.CELL_BOX, cell, scope=Scope.SELF_AND_ANCESTORS)
    if not rows:
        return None
    v = rows[-1].value
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return None
    return tuple(float(x) for x in v)


def _page_to_canonical(box_page, cell_box_page, up) -> Optional[Tuple[
        float, float, float, float]]:
    if box_page is None or cell_box_page is None or not up:
        return None
    px0, py0, px1, py1 = box_page
    cx0, cy0 = cell_box_page[0], cell_box_page[1]
    return ((px0 - cx0) * up, (py0 - cy0) * up,
            (px1 - px0) * up, (py1 - py0) * up)


def _ledger_line_boxes(ev: A.Evidence, cell) -> List[Tuple[float, float,
                                                            float, float]]:
    out = []
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        v = r.value
        if isinstance(v, (list, tuple)) and len(v) >= 5 and v[0] == "ledgerLine":
            out.append((float(v[1]), float(v[2]), float(v[3]), float(v[4])))
    return out


def _arc_boxes(ev: A.Evidence, cell) -> List[Tuple[float, float, float, float]]:
    out = []
    for r in ev.log.rows(Q.ARC_BOX, cell,
                        scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        if "x0" in d and "x1" in d and "y0" in d and "y1" in d:
            out.append((float(d["x0"]), float(d["y0"]),
                        float(d["x1"]) - float(d["x0"]),
                        float(d["y1"]) - float(d["y0"])))
    return out


def _wedge_boxes(ev: A.Evidence, cell, up: Optional[float],
                 cell_box_page) -> List[Tuple[float, float, float, float]]:
    out = []
    boxes_by_key = {r.subject.to_key(): r for r in ev.rows(
        Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell)}
    for r in ev.log.rows(Q.WEDGE_BOX, cell,
                        scope=Scope.SELF_AND_DESCENDANTS):
        gbox = boxes_by_key.get(r.subject.to_key())
        if gbox is not None and isinstance(gbox.value, (list, tuple)) \
                and len(gbox.value) >= 5:
            v = gbox.value
            out.append((float(v[1]), float(v[2]), float(v[3]), float(v[4])))
            continue
        d = r.detail or {}
        page = d.get("bbox_page_px")
        if page and len(page) == 4:
            can = _page_to_canonical(tuple(page), cell_box_page, up)
            if can is not None:
                out.append(can)
    return out


def _ledger_rung_boxes(ev: A.Evidence, glyph_subject, up: Optional[float],
                       cell_box_page) -> List[Tuple[float, float, float,
                                                     float]]:
    """This HEAD's own decided-found `Q.LEDGER_RUNG_INK` windows, in
    canonical pixels. Filed on the head's own glyph subject (EXACT scope --
    it is a per-glyph reading, not one a cell or staff query would widen).
    """
    out = []
    for r in ev.log.rows(Q.LEDGER_RUNG_INK, glyph_subject,
                        scope=Scope.EXACT):
        if not r.value:
            continue
        d = r.detail or {}
        page = d.get("window_page_px")
        if not page or len(page) != 4:
            continue
        can = _page_to_canonical(tuple(page), cell_box_page, up)
        if can is not None:
            out.append(can)
    return out


def _staff_band_canonical(ev: A.Evidence, cell, up: Optional[float],
                          cell_box_page) -> Optional[Tuple[float, float]]:
    """This cell's OWN staff line span, in canonical y. `Q.STAFF_LINES` is
    PAGE pixels (`gather.py:312`), so it is converted through the SAME
    `up`/`cell_box_page` pair every other page-frame quantity here uses.
    `None` where the cell carries no `Q.STAFF_LINES`, or no frame to
    convert it with."""
    rows = ev.log.rows(Q.STAFF_LINES, cell,
                      scope=Scope.SELF_AND_ANCESTORS)
    if not rows or not up or cell_box_page is None:
        return None
    v = rows[-1].value
    if not isinstance(v, (list, tuple)) or len(v) < 2:
        return None
    ys = [(float(y) - cell_box_page[1]) * up for y in v]
    return min(ys), max(ys)


#: A stroke whose centre lies this many staff spaces outside THIS cell's own
#: five-line band is labelled `other_staff_via_pad` -- the cell is padded 4
#: spaces (CLAUDE.md SS10; 6 where the neighbour is far), so a stroke well
#: past that is standing in territory this staff's own lines cannot reach and
#: is very likely detected ink that belongs to the neighbour, carried into
#: this cell's crop by the pad. A LABEL ONLY -- no decision reads it.
OTHER_STAFF_PAD_SPACES = 2.5


def classify_stroke(box, ledger_lines, ledger_rungs, wedges, arcs,
                    band, space) -> List[str]:
    labels = []
    if any(_box_overlap(box, b) for b in ledger_lines):
        labels.append("ledger_line_box")
    if any(_box_overlap(box, b) for b in ledger_rungs):
        labels.append("ledger_rung_ink")
    if any(_box_overlap(box, b) for b in wedges):
        labels.append("wedge_box")
    if any(_box_overlap(box, b) for b in arcs):
        labels.append("arc_box")
    if band is not None and space:
        top, bottom = band
        byc = box[1] + box[3] / 2.0
        gap = (top - byc) if byc < top else (byc - bottom if byc > bottom
                                             else 0.0)
        if gap / space > OTHER_STAFF_PAD_SPACES:
            labels.append("other_staff_via_pad")
    if not labels:
        labels.append("unexplained")
    return labels


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    log, _ = rebuild_gather(rec)
    spec = A.REGISTRY[Q.DURATION]

    # ⚠️ `rebuild_gather`'s own docstring: "Verdicts are NOT replayed: the
    # point is to re-decide them." `_own_stem_side` reads `Q.STEM_DIRECTION`'s
    # VERDICT (decided earlier in `adjudicate.ORDER`), so a `log` with no
    # verdicts at all makes it abstain on EVERY head -- which is why the
    # control first failed on 89 of 555 Brahms heads, always with `side`
    # printed `None`. The verdict is read from the record's own saved list
    # instead, by subject key -- the fact `_own_stem_side` itself reads,
    # replayed rather than rebuilt.
    stem_dir_by_subject = {
        v["subject"]: v for v in rec["verdicts"]
        if v["quantity"] == Q.STEM_DIRECTION}

    def own_stem_side(subject_key: str):
        v = stem_dir_by_subject.get(subject_key)
        if (v is None or v.get("outcome") != "decided"
                or v.get("reason") != "stem_projection"
                or v.get("value") not in ("up", "down")):
            return None
        return str(v["value"])

    rows = [v for v in rec["verdicts"] if v["quantity"] == Q.DURATION
            and (v.get("detail") or {}).get("beam_evidence") == "read"]

    out = []
    mismatches = 0
    for v in rows:
        sub = Subject.from_key(v["subject"])
        ev = A.Evidence(log, sub, spec)
        vb = ev.rows(Q.GLYPH_BOX)
        if not vb:
            continue
        vbv = vb[-1].value
        x_center = float(vbv[1]) + float(vbv[3]) / 2.0
        head_width = float(vbv[3])
        head_box = RH._xywh_head(vbv)
        cell = sub.at(Kind.CELL)

        kept, cv, yolo = RH._kept_beams(ev, cell)
        stems = ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
        side = own_stem_side(v["subject"])
        kept, far_side = RH._on_stem_side(kept, head_box, side)
        tol = RH._join_tolerance(ev, cell)
        own_stems = RH._stems_on(head_box, stems) if head_box is not None \
            else []
        kept_all = kept
        kept, beyond = RH._beyond_own_stem(kept, stems, own_stems, side, tol)
        joined, attached = RH._stem_joined(kept, stems, head_box)
        certain, possible = RH._beam_levels(kept, x_center, head_width,
                                            joined)
        # ⚠️ ROADMAP 2.18b RULE 8, replicated exactly (`adjudicate_duration`
        # lines ~1079-1084): dropping a beyond-tip stroke may not turn a
        # marked note unmarked. Skipping this step is why the CONTROL first
        # failed on 89 of 555 Brahms heads.
        if beyond and not possible and not RH._attached_flags(
                ev, cell, attached, tol)[1]:
            kept, beyond = kept_all, []
            joined, attached = RH._stem_joined(kept, stems, head_box)
            certain, possible = RH._beam_levels(kept, x_center, head_width,
                                                joined)
        d = v.get("detail") or {}
        if certain != d.get("levels_certain"):
            mismatches += 1

        joined_ids = {b.id for b in joined}
        counted = []
        for b in kept:
            x0 = b.detail.get("x0", 0)
            x1 = b.detail.get("x1", 0)
            if b.id in joined_ids or x0 <= x_center <= x1:
                counted.append(b)
        if not counted:
            continue

        up = _cell_up_factor(ev, cell)
        cell_box_page = _cell_box_page(ev, cell)
        ledger_lines = _ledger_line_boxes(ev, cell)
        arcs = _arc_boxes(ev, cell)
        wedges = _wedge_boxes(ev, cell, up, cell_box_page)
        ledger_rungs = _ledger_rung_boxes(ev, sub, up, cell_box_page)
        band = _staff_band_canonical(ev, cell, up, cell_box_page)
        sp = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                    subject=cell)
        space = float(sp[-1].value) if sp else None

        stroke_facts = []
        head_labels = set()
        for b in counted:
            box = RH._xywh(b)
            if box is None:
                continue
            labels = classify_stroke(box, ledger_lines, ledger_rungs,
                                     wedges, arcs, band, space)
            head_labels.update(labels)
            stroke_facts.append({
                "reader": "cv" if b.reader == RH.READERS.CV_LINES else "yolo",
                "box": list(box), "labels": labels,
            })

        out.append({
            "subject": v["subject"], "tag": a.tag,
            "levels_certain": certain, "n_counted": len(counted),
            "labels": sorted(head_labels),
            "strokes": stroke_facts,
        })

    print(f"CONTROL: {len(rows) - mismatches} of {len(rows)} re-derived "
          f"'certain' equal the verdict's own detail.levels_certain")
    print(f"{len(out)} heads with >=1 COUNTED stroke, of {len(rows)} "
          f"beam_evidence=='read' verdicts")
    every_label = collections.Counter(
        lab for h in out for lab in h["labels"])
    print("heads carrying each label (a head may carry several):")
    for lab, n in every_label.most_common():
        print(f"  {n:4d}  {lab}")
    only_unexplained = sum(1 for h in out if h["labels"] == ["unexplained"])
    print(f"heads with NO explanatory label at all: {only_unexplained}")

    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(f"wrote {a.out} ({len(out)} heads)")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
