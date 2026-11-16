"""ROADMAP 2.311 -- reduce one STAGED record to the facts the funnel needs (reads only, decides nothing).

    PYTHONPATH=. python3 benchmarks/note-loss-funnel-2026-11/extract.py REC.record.json OUT.facts.json

Exports the record exactly as `tools.omr.staged.export` does on main's defaults, with two read-only taps:
  * `lane_report.traced_export` stamps each written <note> with the glyph key it was written from (so a written note has
    a place on the page);
  * `_place_notes`' own `fates` out-param (per glyph subject: `written`, `written_relocated`, or the exporter's refusal
    name) is kept -- the exporter's own per-subject ledger, never re-derived here.
Writes: every glyph box (page px, detector class), its fate, its live ADJUDICATE verdicts that decide note-ness, value and
owner, the written notes (type, dots, pitch, blue, part, measure, onset) and every red-marked bar list from the report.
"""
from __future__ import annotations

import json
import sys

from tools.omr.staged import export as E
from tools.omr.staged import lane_report as LR
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

VQ = (Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.DURATION, Q.GLYPH_OWNER, Q.REST_IS_NOT_A_REST if hasattr(Q, "REST_IS_NOT_A_REST") else "rest_is_not_a_rest",
      Q.NOTEHEAD_IS_AN_EIGHTH_REST if hasattr(Q, "NOTEHEAD_IS_AN_EIGHTH_REST") else "notehead_is_an_eighth_rest",
      "unboxed_ink_is_a_rest", "pitch", "accidental")


def _small(v, n=300):
    s = json.dumps(v, default=str)
    return v if len(s) <= n else s[:n] + "...(cut)"


def main(rec_path: str, out_path: str) -> None:
    result = load_record(rec_path)
    if "record" not in result:
        result = {"record": result, "summary": {}}
    obs = result["record"]["observations"]
    boxes = LR.glyph_boxes(obs)
    head_class = {o["subject"] for o in obs if o.get("quantity") == Q.NOTEHEAD_CLASS}
    head_class_val = {o["subject"]: o.get("value") for o in obs if o.get("quantity") == Q.NOTEHEAD_CLASS}
    rest_obs = {o["subject"] for o in obs if o.get("quantity") == Q.REST}
    categories = {}
    for o in obs:
        if o.get("quantity") == Q.GLYPH_BOX:
            d = o.get("detail") or {}
            categories[o["subject"]] = d.get("category")
    claimed = [dict(subject=o["subject"], value=_small(o.get("value"), 120), box=(o.get("detail") or {}).get("bbox_page_px"))
               for o in obs if o.get("quantity") == Q.CLAIMED_AREA]
    live = LR._live(result["record"]["verdicts"], VQ)
    fates_box = {}
    orig = E._place_notes

    def tapped(*a, **k):
        out = orig(*a, **k)
        fates_box["fates"] = k.get("fates")
        return out
    E._place_notes = tapped
    try:
        with LR.traced_export():
            xml, report = E.to_musicxml(result)
    finally:
        E._place_notes = orig
    fates = dict(fates_box.get("fates") or {})
    sym = LR.parse_symbols(xml, boxes)
    glyphs = {}
    for sub, b in boxes.items():
        g = dict(page=b["page"], box=b["box"], cls=b["cls"], category=categories.get(sub),
                 head=sub in head_class, head_class=_small(head_class_val.get(sub), 80), rest=sub in rest_obs,
                 fate=fates.get(sub))
        glyphs[sub] = g
    for (s, q), v in live.items():
        if s in glyphs:
            glyphs[s].setdefault("v", {})[q] = dict(outcome=v.get("outcome"), value=_small(v.get("value")),
                                                   reason=v.get("reason"), decider=v.get("decider"))
    red = report.get("bars_written_red") or {}
    bars = dict(
        red_not_add_up=[{k: b.get(k) for k in ("page", "system", "staff", "cell", "measure", "part", "events", "want_quarters",
                                               "counted_quarters", "words", "two_voice", "doubled_staff_copy", "read", "guessed")}
                        | {"glyphs": [r.get("glyph") for r in b.get("rows") or ()]} for b in red.get("bars_list") or ()],
        held=[{k: v for k, v in b.items() if k != "rows"} for b in (report.get("bars_held_out_sum") or {}).get("held") or ()],
        unread_empty=list((report.get("unread_empty_bars") or {}).get("list") or ()),
        partial=[{k: v for k, v in b.items() if k not in ("rows",)} for b in (report.get("partial_bars") or {}).get("bars") or ()],
    )
    marked = report.get("possibly_unread_mark") or {}
    bars["possibly_unread_mark"] = _small(marked, 20000)
    out = dict(record=rec_path, provenance=_small(result["record"].get("provenance") or result.get("provenance"), 3000),
               glyphs=glyphs, written=sym["hosts"], loose=[d for d in sym["loose"] if d.get("kind") in ("note", "rest")],
               bars=bars, notes_not_written=report.get("notes_not_written"), conservation={
                   k: v for k, v in (report.get("conservation") or {}).items() if k not in ("in_red_bars", "in_partial_gaps", "in_held_bars")},
               claimed_area=claimed, red_xml_marks=xml.count(E.UNREAD_BAR_MARK_COLOR),
               cells={o["subject"]: o["value"] for o in obs if o.get("quantity") == Q.CELL_BOX})
    with open(out_path, "w") as f:
        json.dump(out, f, default=str)
    print("glyphs", len(glyphs), "written", len(sym["hosts"]), "fates", len(fates),
          "red", len(bars["red_not_add_up"]), "held", len(bars["held"]), "unread", len(bars["unread_empty"]),
          "partial", len(bars["partial"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
