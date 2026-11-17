"""ROADMAP 2.311 small test -- what stopped the notes in red bars whose value was refused for a beam reason (reads only).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/beam_tally.py \
        --plate litolff --facts LIT.facts.json --record LIT.record.json --out LIT.beamnotes.json

Population: every head (a note) on a frozen-sample page whose bar is red (`redbars.red_bars`) and whose value the record refused with
`duration_narrowed` (any beam / flag reason), or `chord_value_undecided`. For each, the record's own mechanism is read from the duration verdict's
detail (stems attached to the head, beam strokes found by stem, the certain / possible levels, strokes refused at the tip) and the page position of its
stem is resolved (head_stem verdict -> `stem` row, mapped to page px through the head's own glyph_box row). Nothing is decided.
"""
from __future__ import annotations

import argparse
import json

from redbars import red_bars
from tools.omr.staged.record_io import load_record

SAMPLE = json.load(open("benchmarks/lane-report/sample.json"))
BEAM_REASONS = {"beams_ambiguous", "beam_discounted_uncertain", "beam_certain_not_joined", "tip_readers_disagree", "flag_ink_unread", "flags_disagree",
                "hooks_counted", "open_head_flag_contradiction"}


def mechanism(fate: str, reason: str, d: dict) -> str:
    """the record's own words for what stopped this note, first match (ours to argue)."""
    if fate == "chord_value_undecided":
        if d.get("stems_attached", 0) == 0:
            return "chord_no_stem_attached"
        return "chord_stem_attached_members_disagree"
    st = d.get("stems_attached", 0)
    if st == 0:
        return "no_stem_attached_to_the_head"
    if reason == "beam_certain_not_joined":
        return "beam_stroke_seen_but_ink_says_not_joined"
    if reason == "beams_ambiguous":
        if d.get("beams_by_stem", 0) == 0:
            return "beam_ink_over_the_note_but_joined_to_no_stem"
        return "beam_joined_to_a_stem_but_count_between_levels"
    if reason == "beam_discounted_uncertain":
        rs = d.get("refused_strokes") or []
        if any(r.get("at_tip") for r in rs):
            return "stroke_at_stem_tip_refused_as_another_marks_ink"
        if rs:
            return "stroke_refused_away_from_the_tip"
        if d.get("beams_ledger_line") or d.get("beams_slash") or d.get("beams_neighbour_staff") or d.get("beams_decided_arc"):
            return "detector_beam_box_discounted_as_ledger_slash_neighbour_or_arc"
        return "detector_beam_box_with_no_stroke_found"
    return "other_" + reason


def main() -> None:
    ap = argparse.ArgumentParser()
    for n in ("plate", "facts", "record", "out"):
        ap.add_argument("--" + n, required=True)
    a = ap.parse_args()
    f = json.load(open(a.facts))
    pages = set(SAMPLE["plates"][a.plate]["pages"])
    bars = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in red_bars(f, pages)}
    r = load_record(a.record)
    rec = r.get("record", r)
    byid = {o["id"]: o for o in rec["observations"]}
    dur = {}
    hs = {}
    sdir = {}
    gbox = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "duration":
            dur[v["subject"]] = v
        elif v["quantity"] == "head_stem":
            hs[v["subject"]] = v
        elif v["quantity"] == "stem_direction":
            sdir[v["subject"]] = v
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box":
            gbox[o["subject"]] = o
    out = []
    for k, g in f["glyphs"].items():
        p = k.split("/")
        if len(p) != 6 or not g["head"]:
            continue
        key = tuple(int(x) for x in p[1:5])
        if key not in bars:
            continue
        fate = g.get("fate")
        d = dur.get(k)
        if fate not in ("duration_narrowed", "chord_value_undecided") or d is None:
            continue
        reason = d.get("reason")
        if fate == "duration_narrowed" and reason not in BEAM_REASONS:
            continue
        det = d.get("detail") or {}
        item = dict(key=k, plate=a.plate, page=key[0], system=key[1], staff=key[2], cell=key[3], head_box=g["box"], head_class=g["head_class"],
                    fate=fate, reason=reason, bar_kind=bars[key]["kind"], mechanism=mechanism(fate, reason, det),
                    candidates=[c.get("value") for c in d.get("candidates") or []], levels=[det.get("levels_certain"), det.get("levels_possible")],
                    stems_attached=det.get("stems_attached"), beams_by_stem=det.get("beams_by_stem"), beam_evidence=det.get("beam_evidence"),
                    cv_beams=det.get("cv_beams"), yolo_beams=det.get("yolo_beams"), not_by_ink=det.get("beams_not_by_ink_why"),
                    refused=det.get("refused_strokes"), certain_conflicts=det.get("certain_conflicts"),
                    tip=(det.get("beams_from_strokes") or {}).get("tip"))
        h = hs.get(k) or {}
        item["head_stem"] = [h.get("outcome"), h.get("value"), h.get("reason")]
        sd = sdir.get(k) or {}
        item["stem_dir"] = [sd.get("outcome"), sd.get("value")]
        so = byid.get(h.get("value")) if isinstance(h.get("value"), str) else None
        gb = gbox.get(k)
        if so is not None and gb is not None and so["quantity"] == "stem" and gb["frame"] == so["frame"] and gb["subject"] != so["subject"]:
            _, gx, gy, gw, gh = gb["value"]
            b = g["box"]
            sc = (b[2] - b[0]) / float(gw)
            sx, sy, sw, sh = so["value"]
            item["stem_box"] = [b[0] + (sx - gx) * sc, b[1] + (sy - gy) * sc, b[0] + (sx + sw - gx) * sc, b[1] + (sy + sh - gy) * sc]
        out.append(item)
    json.dump(out, open(a.out, "w"), indent=0, default=str)
    import collections
    print(a.plate, "red bars", len(bars), "refused notes in them", len(out))
    print(collections.Counter((i["fate"], i["reason"]) for i in out).most_common())
    print(collections.Counter(i["mechanism"] for i in out).most_common())
    print("stem box resolved", sum(1 for i in out if "stem_box" in i))


if __name__ == "__main__":
    main()
