"""ROADMAP 2.18 -- classify EVERY `duration:beams_ambiguous` head by mechanism.

PATH: STAGED. Reads ONE saved record once (`record_io.load_record`), rebuilds
its GATHER rows into a `Log` (`review.rerun.rebuild_gather`, the replay the
rerun control proves), and for every duration verdict the record holds as
`narrowed/beams_ambiguous` re-derives the SAME inputs `adjudicate_duration`
used -- through its own helpers (`_kept_beams`, `_stem_joined`,
`_beam_levels` called WITHOUT a stem side, which is the pre-2.18 column
test) -- then labels each stroke that is POSSIBLE but not CERTAIN for this
head with *why* it is only possible, and each head with the class of its
possible-only strokes. It also records what EXPORT did with the head
(`review.rerun.export_with_subjects`, whose own control is that the
per-subject refusals sum to `notes_not_written`).

    python3 benchmarks/omr-missing-notes-2026-09/probe/beams_mechanism.py \\
        <record.json> --out <out.json>

CONTROL (can fail): the re-derived `(certain, possible)` must equal the
verdict's own `levels_certain`/`levels_possible` for every row, or the probe
exits 1 -- a classification over inputs the decision did not see is not a
classification of the decision. Run it on a record gathered BEFORE 2.18: on
a post-2.18 record the verdicts were made with the stem side and the column
test here no longer reproduces them (which is the control failing, as it
should).
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
from tools.omr.staged.record import Kind, Q, Scope, Subject       # noqa: E402
from tools.omr.staged.record_io import load_record                # noqa: E402
from tools.omr.staged.review.rerun import (                       # noqa: E402
    export_with_subjects, rebuild_gather)

#: A stroke whose centre lies more than this far PAST the attached stem's tip
#: (staff spaces) is labelled `beyond_stem_tip`. A LABEL ONLY -- no decision
#: reads it. One space = a beam's thickness plus a stacked stroke's gap.
TIP_SLACK_SPACES = 1.0


def _cv(row) -> bool:
    return row.reader == RH.READERS.CV_LINES


def label_stroke(b, head_box, direction, attached, space):
    """Why is stroke `b` only POSSIBLY over this head? One word."""
    box = RH._xywh(b)
    hyc = head_box[1] + head_box[3] / 2.0
    byc = box[1] + box[3] / 2.0
    if direction in ("up", "down"):
        sign = -1.0 if direction == "up" else 1.0
        if (byc - hyc) * sign <= 0:
            return "wrong_side"
        if attached and space:
            tips = [(RH._xywh(s)[1] if direction == "up"
                     else RH._xywh(s)[1] + RH._xywh(s)[3]) for s in attached]
            reach = max((t - hyc) * sign for t in tips)
            if (byc - hyc) * sign > reach + TIP_SLACK_SPACES * space:
                return "beyond_stem_tip"
            return "stem_side_stem_misses_stroke"
        return "stem_side_no_stem_attached"
    if attached:
        return "direction_unread_stem_attached"
    return "direction_unread_no_stem"


def classify(head_box, x_center, width, kept, joined, attached, direction,
             space):
    """One head -> (labels of its possible-only strokes, per-stroke facts)."""
    pad = (width or 0.0) * RH.BEAM_EDGE_TOLERANCE_WIDTHS
    joined_ids = {b.id for b in joined}
    labels, facts = [], []
    hyc = head_box[1] + head_box[3] / 2.0
    for b in kept:
        x0 = b.detail.get("x0", 0)
        x1 = b.detail.get("x1", 0)
        certain = b.id in joined_ids or x0 <= x_center <= x1
        possible = certain or (x0 - pad <= x_center <= x1 + pad)
        if not possible:
            continue
        lab = label_stroke(b, head_box, direction, attached, space)
        box = RH._xywh(b)
        facts.append({
            "certain": certain, "label": lab,
            "reader": "cv" if _cv(b) else "yolo",
            "dy_spaces": (round((box[1] + box[3] / 2.0 - hyc) / space, 2)
                          if space else None),
            "box": list(box)})
        if not certain:
            labels.append(lab)
    return labels, facts


def head_class(labels) -> str:
    """The class of one head; the first test that holds wins."""
    s = set(labels)
    if s <= {"wrong_side"}:
        return "A_far_side_of_own_stem"
    if s <= {"wrong_side", "beyond_stem_tip"}:
        return "B_far_side_or_past_stem_tip"
    if "direction_unread_stem_attached" in s:
        return "D_stem_attached_direction_abstained"
    if s & {"direction_unread_no_stem", "stem_side_no_stem_attached"} and \
            "stem_side_stem_misses_stroke" not in s:
        return "C_no_stem_attached"
    return "E_stem_side_within_reach_stem_misses_stroke"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    log, _ = rebuild_gather(rec)
    spec = A.REGISTRY[Q.DURATION]
    stem_dir = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == Q.STEM_DIRECTION}

    rows = [v for v in rec["verdicts"] if v["quantity"] == Q.DURATION
            and v.get("outcome") == "narrowed"
            and v.get("reason") == "beams_ambiguous"]
    out = []
    mismatches = 0
    for v in rows:
        sub = Subject.from_key(v["subject"])
        ev = A.Evidence(log, sub, spec)
        vb = ev.rows(Q.GLYPH_BOX)[-1].value
        x_center = float(vb[1]) + float(vb[3]) / 2.0
        width = float(vb[3])
        head_box = RH._xywh_head(vb)
        cell = sub.at(Kind.CELL)
        kept, cv, yolo = RH._kept_beams(ev, cell)
        stems = ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
        joined, attached = RH._stem_joined(kept, stems, head_box)
        certain, possible = RH._beam_levels(kept, x_center, width, joined)
        d = v.get("detail") or {}
        if (certain, possible) != (d.get("levels_certain"),
                                   d.get("levels_possible")):
            mismatches += 1
        sp = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                     subject=cell)
        space = float(sp[-1].value) if sp else None
        sd = stem_dir.get(v["subject"]) or {}
        direction = (sd.get("value") if sd.get("outcome") == "decided"
                     else None)
        labels, facts = classify(head_box, x_center, width, kept, joined,
                                 attached, direction, space)
        out.append({
            "subject": v["subject"], "head": d.get("head"),
            "certain": certain, "possible": possible,
            "stems_attached": len(attached), "beams_by_stem": len(joined),
            "n_cell_stems": len(stems), "cv_beams": len(cv),
            "yolo_beams": len(yolo), "kept": len(kept),
            "stem_direction": direction,
            "stem_direction_reason": sd.get("reason"),
            "head_box": list(head_box), "space": space,
            "labels": labels, "class": head_class(labels),
            "certain_on_far_side": sum(
                1 for f in facts if f["certain"]
                and f["label"] == "wrong_side"),
            "strokes": facts,
        })

    _xml, report, refusals, _placed = export_with_subjects(doc)
    refusal_of = {s: r for s, r in refusals}
    for h in out:
        h["export_refusal"] = refusal_of.get(h["subject"])

    print(f"CONTROL: {len(rows) - mismatches} of {len(rows)} re-derived "
          f"(certain, possible) equal the verdict's own detail")
    print("export refusal of the narrowed heads:",
          dict(collections.Counter(h["export_refusal"] for h in out)))
    for name, pop in (("all narrowed", out),
                      ("counted duration_narrowed at EXPORT",
                       [h for h in out
                        if h["export_refusal"] == "duration_narrowed"])):
        print(f"\n{name}: n={len(pop)}")
        for k, n in collections.Counter(h["class"] for h in pop).most_common():
            print(f"  {n:4d}  {k}")
        print("  stroke labels:", dict(collections.Counter(
            lab for h in pop for lab in h["labels"])))
        print("  stem_direction reason:", dict(collections.Counter(
            h["stem_direction_reason"] for h in pop)))
        print("  heads with >=1 CERTAIN stroke on the far side:",
              sum(1 for h in pop if h["certain_on_far_side"]))
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {a.out} ({len(out)} heads)")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
