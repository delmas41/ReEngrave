"""ROADMAP 2.19 -- why is each held bar held? Dump every bar 2.8 holds out,
with its events per voice and every refusal filed in the same cell.

PATH: STAGED. Re-decides ONE saved record with the tree this file sits in
(`review.rerun`: rebuild the GATHER rows, `pipeline.decide`, `to_musicxml`),
so base and arm are the same gather and differ only in the code.

The events and streams are captured by wrapping `export._bar_holds_out` at
run time -- the exporter's own rule, not a restatement -- and the per-glyph
refusals come from `rerun.export_with_subjects`, whose control (per-subject
tallies == the exporter's own `notes_not_written`) raises if it fails. A
second control here: the bars this wrapper sees held must equal
`report["bars_held_out_sum"]["bars"]` (minus doubled-staff copies, which are
stripped of glyphs and cannot be located).

    python3 .../held_funnel_2_19.py <record.json> --out <dump.json>
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


def _cell_of(sub):
    p = (sub or "").split("/")
    if len(p) >= 6 and p[0] == "glyph":
        return tuple(int(x) for x in p[1:5])
    return None


def _ev_summary(ev, divisions):
    from tools.omr.staged import export as EX
    heads = ev.get("noteheads") or []
    base = ev.get("rest") if ev.get("kind") == "rest" else (heads[0] if heads else {})
    return {
        "kind": ev.get("kind"),
        "x": round(float(ev.get("x_position") or 0), 1),
        "beats": ev.get("duration_beats"),
        "type": base.get("duration_type") if base else None,
        "dots": base.get("dots") if base else None,
        "tuplet": next((h.get("tuplet") for h in heads
                        if isinstance(h.get("tuplet"), dict)), None),
        "measure_rest": bool((ev.get("rest") or {}).get("measure_rest")),
        "units": EX._event_units(ev, divisions),
        "glyphs": ([h.get("glyph") for h in heads] if heads
                   else [(ev.get("rest") or {}).get("glyph")]),
        "classes": ([h.get("class") for h in heads] if heads
                    else [(ev.get("rest") or {}).get("class")]),
        "pitches": [h.get("pitch") for h in heads],
        "bboxes": ([h.get("bbox") for h in heads] if heads
                   else [(ev.get("rest") or {}).get("bbox")]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    ap.add_argument("--musicxml", default=None,
                    help="also write the re-decided file (for bar_sum_check)")
    a = ap.parse_args()

    from tools.omr.staged import export as EX
    from tools.omr.staged.record import Q
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = RR._to_result(log, doc, None)

    captured = []
    orig = EX._bar_holds_out

    def wrapped(events, streams, divisions, meter):
        out = orig(events, streams, divisions, meter)
        subs = [g for ev in events for g in
                ([h.get("glyph") for h in ev.get("noteheads") or []]
                 or [(ev.get("rest") or {}).get("glyph")])]
        cells = {_cell_of(g) for g in subs if _cell_of(g)}
        captured.append({
            "cell": sorted(cells)[0] if len(cells) == 1 else None,
            "cells": sorted(cells),
            "held": out is not None,
            "detail": out,
            "meter": meter,
            "n_streams": len(streams) if streams is not None else 1,
            "streams": [[_ev_summary(ev, divisions) for ev in s]
                        for s in (streams if streams is not None else [events])],
        })
        return out

    EX._bar_holds_out = wrapped
    try:
        xml, rep, refusals, placed = RR.export_with_subjects(result)
    finally:
        EX._bar_holds_out = orig
    if a.musicxml:
        Path(a.musicxml).write_text(xml)

    standing = RR._verdict_index(result["record"]["verdicts"])

    def vinfo(q, s):
        v = standing.get((q, s))
        if not v:
            return None
        return {"outcome": v["outcome"], "reason": v.get("reason"),
                "value": v.get("value"),
                "candidates": v.get("candidates")}

    boxes = {o["subject"]: o["value"] for o in result["record"]["observations"]
             if o["quantity"] == Q.GLYPH_BOX}
    refused_by_cell = collections.defaultdict(list)
    for s, reason in refusals:
        c = _cell_of(s)
        if c is None:
            continue
        refused_by_cell[c].append({
            "glyph": s, "refusal": reason, "box": boxes.get(s),
            "duration": vinfo(Q.DURATION, s),
            "not_a_notehead": vinfo(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, s),
            "owner": vinfo(Q.GLYPH_OWNER, s),
        })

    held_rep = (rep.get("bars_held_out_sum") or {})
    by_loc = {(h["page"], h["system"], h["staff"], h["cell"]): h
              for h in held_rep.get("held") or []}
    bars = []
    for c in captured:
        if not c["held"] or c["cell"] is None:
            continue
        h = by_loc.get(tuple(c["cell"]))
        c["report"] = ({k: h[k] for k in ("measure", "part",
                                          "meter_carried_in_file")}
                       if h else None)
        c["refused_in_cell"] = [r for r in refused_by_cell.get(tuple(c["cell"]), [])
                                if r["refusal"] != EX._BAR_SUM_REFUSAL]
        bars.append(c)

    n_held_rep = held_rep.get("bars", 0)
    n_doubled = held_rep.get("bars_on_a_doubled_staff", 0)
    control_ok = (len(bars) == n_held_rep - n_doubled
                  and len(by_loc) == len(bars))
    out = {"record": a.record, "root": str(ROOT),
           "bars_held_out_sum": n_held_rep,
           "bars_on_a_doubled_staff": n_doubled,
           "of_bars_with_events": held_rep.get("of_bars_with_events"),
           "bars_judged_by_a_carried_meter":
               held_rep.get("bars_judged_by_a_carried_meter"),
           "captured_held": len(bars),
           "control_held_count_matches": control_ok,
           "notes_not_written": rep.get("notes_not_written"),
           "written": rep.get("written"),
           "notes_in_file": xml.count("<note"),
           "bars": bars}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(f"held {n_held_rep} (doubled {n_doubled}) of "
          f"{held_rep.get('of_bars_with_events')}; captured {len(bars)}; "
          f"control {'PASS' if control_ok else 'FAIL'}; "
          f"written {rep.get('written')}")
    return 0 if control_ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
