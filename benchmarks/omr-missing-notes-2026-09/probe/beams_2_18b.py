"""ROADMAP 2.18b -- measure classes B and E and the missed-flag path, AFTER 2.18.

PATH: STAGED. Reads ONE saved record once (`record_io.load_record`), replays
its GATHER rows (`review.rerun.rebuild_gather`) and RE-DECIDES them on this
tree (`review.rerun.run_stages` = `pipeline.decide`), so every number is what
the CURRENT tree does with the frozen gather. For every standing
`duration: narrowed/beams_ambiguous` it re-derives the inputs through
`adjudicate_duration`'s own helpers (post-2.18: `_own_stem_side`,
`_on_stem_side`, `_stem_joined`, `_beam_levels`) and describes each stroke
that is POSSIBLE but not CERTAIN:

  B  `beyond_stem_tip` -- on the stem side, centre more than one space past
     the tip of the head's own attached stem. For each: where it sits in the
     head's OWN staff (staff steps from the top line, from the head's own
     `Q.NOTEHEAD_STAFF_POSITION`), which stems touch it, and whom
     `Q.GLYPH_OWNER` gives the heads on those stems.
  E  `stem_side_stem_misses_stroke` -- on the stem side, within reach, the
     stem does not overlap it. For each: the x and y gap between the stem's
     box and the stroke's, in staff spaces.

And the missed-flag population: every notehead DECIDED at its head value
with a stem attached and no beam and no flag (`levels == 0`,
`beam_evidence == "none_over_this_note"`), with the detector boxes that sit
at that stem's tip.

CONTROL (can fail): the re-derived `(certain, possible)` must equal the
re-decided verdict's own detail for every narrowed head, or it exits 1.

`--off` sets `STEM_JOIN_TOLERANCE_SPACES = 0`, which is the 2.18 tree exactly
(`price_2_18b.py`'s control proves it): the B/E table in FINDINGS §11 is the
`--off` run, the "after" population the default run.

    python3 benchmarks/omr-missing-notes-2026-09/probe/beams_2_18b.py \\
        <record.json> --out <out.json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import adjudicate as A                      # noqa: E402
from tools.omr.staged import adjudicators                         # noqa: E402,F401
from tools.omr.staged.adjudicators import rhythm as RH            # noqa: E402
from tools.omr.staged.record import (Kind, Outcome, Q, Scope,     # noqa: E402
                                     Subject)
from tools.omr.staged.record_io import load_record                # noqa: E402
from tools.omr.staged.review import rerun as RR                   # noqa: E402

TIP_SLACK_SPACES = 1.0


def _tip(stem, side):
    x, y, w, h = RH._xywh(stem)
    return y if side == "up" else y + h


def _gap_1d(a0, a1, b0, b1):
    """0 when the intervals overlap, else the distance between them."""
    return max(0.0, max(a0, b0) - min(a1, b1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    ap.add_argument("--off", action="store_true",
                    help="tolerance 0 -- the 2.18 tree")
    a = ap.parse_args()
    if a.off:
        RH.STEM_JOIN_TOLERANCE_SPACES = 0.0

    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = RR._to_result(log, doc, None)
    _xml, report, refusals, _placed = RR.export_with_subjects(result)
    refusal_of = {s: r for s, r in refusals}
    spec = A.REGISTRY[Q.DURATION]

    heads_out, flags_out, mismatches = [], [], 0
    verdicts = [v for v in result["record"]["verdicts"]
                if v["quantity"] == Q.DURATION]
    standing = RR._verdict_index(result["record"]["verdicts"])
    for v in verdicts:
        if standing.get((Q.DURATION, v["subject"])) is not v:
            continue
        d = v.get("detail") or {}
        if "levels_certain" not in d:
            continue
        sub = Subject.from_key(v["subject"])
        ev = A.Evidence(log, sub, spec)
        vb = ev.rows(Q.GLYPH_BOX)[-1].value
        head_box = RH._xywh_head(vb)
        x_center = head_box[0] + head_box[2] / 2.0
        width = head_box[2]
        hyc = head_box[1] + head_box[3] / 2.0
        cell = sub.at(Kind.CELL)
        kept, _cv, _yolo = RH._kept_beams(ev, cell)
        stems = ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
        side, _sv = RH._own_stem_side(ev)
        kept, far = RH._on_stem_side(kept, head_box, side)
        tol = RH._join_tolerance(ev, cell)
        own = RH._stems_on(head_box, stems)
        kept_all = kept
        kept, _beyond = RH._beyond_own_stem(kept, stems, own, side, tol)
        joined, attached = RH._stem_joined(kept, stems, head_box)
        certain, possible = RH._beam_levels(kept, x_center, width, joined)
        if _beyond and not possible and not RH._attached_flags(
                ev, cell, attached, tol)[1]:
            # the adjudicator's rule-8 guard, mirrored so the control holds
            kept = kept_all
            joined, attached = RH._stem_joined(kept, stems, head_box)
            certain, possible = RH._beam_levels(kept, x_center, width,
                                                joined)
        sp_rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                          subject=cell)
        space = float(sp_rows[-1].value) if sp_rows else None
        pos_rows = log.rows(Q.NOTEHEAD_STAFF_POSITION, sub)
        top_y = (hyc - float(pos_rows[-1].value) * space / 2.0
                 if pos_rows and space else None)

        if v["outcome"] == "narrowed" and v["reason"] == "beams_ambiguous":
            if (certain, possible) != (d.get("levels_certain"),
                                       d.get("levels_possible")):
                mismatches += 1
            sign = -1.0 if side == "up" else 1.0
            reach = (max((_tip(s, side) - hyc) * sign for s in attached)
                     if attached and side else None)
            joined_ids = {b.id for b in joined}
            pad = width * RH.BEAM_EDGE_TOLERANCE_WIDTHS
            strokes = []
            for b in kept:
                x0, x1 = b.detail.get("x0", 0), b.detail.get("x1", 0)
                cert = b.id in joined_ids or x0 <= x_center <= x1
                poss = cert or (x0 - pad <= x_center <= x1 + pad)
                if not poss:
                    continue
                bx, by, bw, bh = RH._xywh(b)
                byc = by + bh / 2.0
                f = {"certain": cert, "reader": b.reader,
                     "dy_spaces": round((byc - hyc) * (sign if side else 1)
                                        / space, 2) if space else None,
                     "step_in_own_staff": (round((byc - top_y)
                                                 / (space / 2.0), 2)
                                           if top_y is not None else None),
                     "box": [bx, by, bw, bh]}
                if side is None:
                    f["label"] = ("no_side_stem_attached" if attached
                                  else "no_side_no_stem")
                elif not attached:
                    f["label"] = "stem_side_no_stem_attached"
                elif (byc - hyc) * sign > reach + TIP_SLACK_SPACES * space:
                    f["label"] = "beyond_stem_tip"
                elif cert:
                    f["label"] = "certain"
                else:
                    f["label"] = "stem_side_stem_misses_stroke"
                if attached and space:
                    gx = min(_gap_1d(*_xr(s), bx, bx + bw) for s in attached)
                    gy = min(_gap_1d(*_yr(s), by, by + bh) for s in attached)
                    f["stem_gap_x_spaces"] = round(gx / space, 3)
                    f["stem_gap_y_spaces"] = round(gy / space, 3)
                    f["past_stroke_end_widths"] = round(
                        max(0.0, x0 - x_center, x_center - x1) / width, 3)
                # the stroke's own stems, and whom ownership gives their heads
                touching = [s for s in stems
                            if RH._boxes_overlap(RH._xywh(s), (bx, by, bw, bh))]
                owners = []
                for s in touching:
                    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                                     subject=cell):
                        if (r.detail or {}).get("category") != "notehead":
                            continue
                        hb = RH._xywh_head(r.value)
                        if hb and RH._boxes_overlap(RH._xywh(s), hb):
                            ov = log.verdict(Q.GLYPH_OWNER, r.subject)
                            own = sub.at(Kind.STAFF).to_key()
                            owners.append(
                                "self" if r.subject == sub else
                                ("none" if ov is None or ov.outcome
                                 is not Outcome.DECIDED else
                                 ("own_staff" if ov.value == own
                                  else "other_staff")))
                f["stroke_stems"] = len(touching)
                f["stroke_stem_heads"] = dict(collections.Counter(owners))
                strokes.append(f)
            labels = [f["label"] for f in strokes if not f["certain"]]
            s = set(labels)
            if s and s <= {"beyond_stem_tip"}:
                cls = "B_only_beyond_stem_tip"
            elif "beyond_stem_tip" in s and s <= {"beyond_stem_tip",
                                                  "stem_side_stem_misses_stroke"}:
                cls = "BE_beyond_tip_and_missed"
            elif s and s <= {"stem_side_stem_misses_stroke"}:
                cls = "E_stem_side_missed"
            elif s & {"stem_side_no_stem_attached", "no_side_no_stem"}:
                cls = "C_no_stem_attached"
            elif "no_side_stem_attached" in s:
                cls = "D_direction_not_own"
            else:
                cls = "other"
            heads_out.append({
                "subject": v["subject"], "side": side, "certain": certain,
                "possible": possible, "stems_attached": len(attached),
                "reach_spaces": (round(reach / space, 2)
                                 if reach is not None and space else None),
                "class": cls, "labels": labels,
                "export_refusal": refusal_of.get(v["subject"]),
                "head_box": list(head_box), "space": space,
                "strokes": strokes})
        elif (v["outcome"] == "decided" and attached
              and d.get("beam_evidence") == "none_over_this_note"
              and not d.get("flags_attached")
              and str(d.get("head", "")).startswith("noteheadBlack")):
            # the missed-flag population: a stemmed black head read as a
            # QUARTER because no beam and no flag reached it
            tips = []
            for s in attached:
                sx, sy, sw, shh = RH._xywh(s)
                up = side == "up" if side else (sy + shh / 2.0 < hyc)
                ty = sy if up else sy + shh
                tips.append((sx, ty, sw, up))
            near = []
            for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                             subject=cell):
                if r.subject == sub:
                    continue
                gb = RH._xywh_head(r.value)
                for sx, ty, sw, up in tips:
                    # a flag hangs to the RIGHT of the stem from its tip
                    win = (sx, ty - (0 if up else 3 * space), 2.0 * space,
                           3 * space)
                    if gb and RH._boxes_overlap(gb, win):
                        near.append(str(r.value[0]))
            flags_out.append({
                "subject": v["subject"], "side": side,
                "value": (v.get("value") or {}).get("beats"),
                "tips": [[t[0], t[1], t[2], t[3]] for t in tips],
                "head_box": list(head_box), "space": space,
                "boxes_at_tip": near,
                "export_refusal": refusal_of.get(v["subject"])})

    print(f"CONTROL: {len(heads_out) - mismatches} of {len(heads_out)} "
          f"narrowed heads re-derived equal to the verdict's detail")
    pop = [h for h in heads_out if h["export_refusal"] == "duration_narrowed"]
    print(f"narrowed now: {len(heads_out)}; EXPORT duration_narrowed: "
          f"{len(pop)}  (report says "
          f"{(report.get('notes_not_written') or {}).get('duration_narrowed')})")
    for k, n in collections.Counter(h["class"] for h in pop).most_common():
        print(f"  {n:4d}  {k}")
    print(f"missed-flag population (stemmed black head decided at its head "
          f"value): {len(flags_out)}; with a detector box at the stem tip: "
          f"{sum(1 for f in flags_out if f['boxes_at_tip'])}")
    print("  classes at the tip:", dict(collections.Counter(
        n for f in flags_out for n in set(f["boxes_at_tip"]))))
    Path(a.out).write_text(json.dumps({"heads": heads_out,
                                       "missed_flag": flags_out,
                                       "notes_not_written":
                                           report.get("notes_not_written")},
                                      indent=1, default=str))
    print(f"wrote {a.out}")
    return 1 if mismatches else 0


def _xr(s):
    x, _y, w, _h = RH._xywh(s)
    return x, x + w


def _yr(s):
    _x, y, _w, h = RH._xywh(s)
    return y, y + h


if __name__ == "__main__":
    raise SystemExit(main())
