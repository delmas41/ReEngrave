"""ROADMAP 2.22 -- 2.19's held-bar dump, at MOVEMENT scale.

PATH: STAGED. `held_funnel_2_19.py` extended, not replaced: the same wrap of
`export._bar_holds_out` (the exporter's own rule, not a restatement) and the
same control (bars captured == `report["bars_held_out_sum"]` minus doubled
copies). What is added is only what the movement-scale classes need:

  * the page-frame x of every captured glyph (`Q.GLYPH_BOX.detail.
    bbox_page_px`) and the staff's `Q.STAFF_SPACING`, so the 2.21 voice gate
    can be SIMULATED in the unit it is built in;
  * the cell's `Q.CELL_STAFF_SPACE`, so a stacked meter-digit pair can be
    looked for in staff spaces;
  * the system's own `Q.METER` verdict (outcome, reason, value).

The record is loaded ONCE (`record_io.load_record`). Phase A exports the
record's OWN verdicts (made on the tree that gathered it) with today's
exporter; phase B (`--redecide`) rebuilds the GATHER rows and re-decides on
the tree this file sits in (`review.rerun`, as 2.19 did) and exports again.
Phase A is written before phase B starts, so a phase B that is too slow can be
killed without losing anything.

    python3 .../held_funnel_mvt_2_22.py <record.json> --label L --out-dir D [--redecide]
"""
from __future__ import annotations

import argparse
import collections
import gc
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

T0 = time.time()


def say(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


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


def dump(result, label, phase, out_dir, write_xml):
    from tools.omr.staged import export as EX
    from tools.omr.staged.record import Q
    from tools.omr.staged.review import rerun as RR

    captured = []
    orig = EX._bar_holds_out

    def wrapped(events, streams, divisions, meter):
        out = orig(events, streams, divisions, meter)
        if out is None:
            return out
        subs = [g for ev in events for g in
                ([h.get("glyph") for h in ev.get("noteheads") or []]
                 or [(ev.get("rest") or {}).get("glyph")])]
        cells = {_cell_of(g) for g in subs if _cell_of(g)}
        captured.append({
            "cell": sorted(cells)[0] if len(cells) == 1 else None,
            "cells": sorted(cells),
            "detail": out,
            "meter": meter,
            "n_streams": len(streams) if streams is not None else 1,
            "streams": [[_ev_summary(ev, divisions) for ev in s]
                        for s in (streams if streams is not None else [events])],
        })
        return out

    say(f"{phase}: export")
    EX._bar_holds_out = wrapped
    try:
        xml, rep, refusals, _placed = RR.export_with_subjects(result)
    finally:
        EX._bar_holds_out = orig
    if write_xml:
        (out_dir / f"{label}-{phase}.musicxml").write_text(xml)
    say(f"{phase}: exported, {len(captured)} held captured; indexing")

    held_cells = {tuple(c["cell"]) for c in captured if c["cell"]}
    rec = result["record"]
    standing = RR._verdict_index(rec["verdicts"])

    def vinfo(q, s):
        v = standing.get((q, s))
        if not v:
            return None
        return {"outcome": v["outcome"], "reason": v.get("reason"),
                "value": v.get("value"),
                "candidates": v.get("candidates")}

    boxes, page_px, staff_sp, cell_sp = {}, {}, {}, {}
    for o in rec["observations"]:
        q = o["quantity"]
        if q == Q.GLYPH_BOX:
            c = _cell_of(o["subject"])
            if c in held_cells:
                boxes[o["subject"]] = o["value"]
                bp = (o.get("detail") or {}).get("bbox_page_px")
                if bp:
                    page_px[o["subject"]] = bp
        elif q == Q.STAFF_SPACING:
            staff_sp[o["subject"]] = o["value"]
        elif q == Q.CELL_STAFF_SPACE:
            cell_sp[o["subject"]] = o["value"]

    refused_by_cell = collections.defaultdict(list)
    for s, reason in refusals:
        c = _cell_of(s)
        if c is None or c not in held_cells:
            continue
        refused_by_cell[c].append({
            "glyph": s, "refusal": reason, "box": boxes.get(s),
            "page_px": page_px.get(s),
            "duration": vinfo(Q.DURATION, s),
            "not_a_notehead": vinfo(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, s),
            "owner": vinfo(Q.GLYPH_OWNER, s),
        })

    held_rep = (rep.get("bars_held_out_sum") or {})
    by_loc = {(h["page"], h["system"], h["staff"], h["cell"]): h
              for h in held_rep.get("held") or []}
    bars = []
    for c in captured:
        if c["cell"] is None:
            continue
        p, sy, st, ce = c["cell"]
        h = by_loc.get(tuple(c["cell"]))
        c["report"] = ({k: h.get(k) for k in ("measure", "part",
                                              "meter_carried_in_file")}
                       if h else None)
        c["refused_in_cell"] = [r for r in refused_by_cell.get(tuple(c["cell"]), [])
                                if r["refusal"] != EX._BAR_SUM_REFUSAL]
        for s in c["streams"]:
            for e in s:
                e["page_px"] = [page_px.get(g) for g in e["glyphs"]]
        c["staff_spacing_px"] = staff_sp.get(f"staff/{p}/{sy}/{st}")
        c["cell_staff_space"] = cell_sp.get(f"cell/{p}/{sy}/{st}/{ce}")
        c["system_meter"] = vinfo(Q.METER, f"system/{p}/{sy}")
        bars.append(c)

    n_held_rep = held_rep.get("bars", 0)
    n_doubled = held_rep.get("bars_on_a_doubled_staff", 0)
    control_ok = (len(bars) == n_held_rep - n_doubled
                  and len(by_loc) == len(bars))
    out = {"label": label, "phase": phase, "root": str(ROOT),
           "provenance": result.get("provenance"),
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
    path = out_dir / f"{label}-{phase}.held.json"
    path.write_text(json.dumps(out, default=str))
    summ = {k: v for k, v in out.items() if k != "bars"}
    (out_dir / f"{label}-{phase}.summary.json").write_text(
        json.dumps(summ, indent=1, default=str))
    say(f"{phase}: held {n_held_rep} (doubled {n_doubled}) of "
        f"{held_rep.get('of_bars_with_events')}; captured {len(bars)}; "
        f"control {'PASS' if control_ok else 'FAIL'}; -> {path}")
    return control_ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--redecide", action="store_true")
    ap.add_argument("--skip-own", action="store_true")
    ap.add_argument("--musicxml", action="store_true")
    a = ap.parse_args()
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    say(f"loading {a.record}")
    doc = load_record(a.record)
    say("loaded")
    ok = True
    if not a.skip_own:
        ok &= dump(doc, a.label, "own", out_dir, a.musicxml)
        gc.collect()
    if a.redecide:
        rec = doc["record"] if "record" in doc else doc
        say("redecide: rebuild_gather")
        log, _ = RR.rebuild_gather(rec)
        prov = doc.get("provenance")
        del doc, rec
        gc.collect()
        say("redecide: run_stages")
        RR.run_stages(log, progress=True)
        say("redecide: stages done")
        result = RR._to_result(log, {"provenance": prov}, None)
        ok &= dump(result, a.label, "redecided", out_dir, a.musicxml)
    say("done")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
