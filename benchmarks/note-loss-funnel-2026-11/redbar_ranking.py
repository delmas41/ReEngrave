"""ROADMAP 2.311 -- the ranked list of ALL red bars on both plates by first cause (rows add up to 309 / 276).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/redbar_ranking.py \
        --lit LIT.facts.json --lit-extra LIT.extra.json --bra BRA.facts.json --bra-extra BRA.extra.json \
        --json benchmarks/note-loss-funnel-2026-11/redbar-ranking.json --md benchmarks/note-loss-funnel-2026-11/redbar-ranking.md
"""
from __future__ import annotations

import argparse
import collections
import json

from redbar_classify import Ctx, classify, base_rates

SAMPLE = json.load(open("benchmarks/lane-report/sample.json"))

# row -> (cause in a musician's words, owner: reader/stage and function)
ROWS = {
    "staff_lost": ("the staff was not named or has no bars: its bars are dropped whole",
                   "EXPORT export.py `staff_not_identified` / `owner_staff_has_no_measures`"),
    "lost_beam_ambiguous": ("a note's beam could not be told (joined to its neighbours or not): value held",
                            "ADJUDICATE rhythm.py::adjudicate_duration (beams branch)"),
    "lost_bare_stem": ("a note on a stem with beam ink beside it that was judged uncertain (no flag, no sure beam): value held",
                       "ADJUDICATE rhythm.py::adjudicate_duration (`beam_discounted_uncertain`; INFER inferences.py BARE_STEM)"),
    "lost_beam_not_joined": ("a beam is certain but does not reach this note: value held",
                             "ADJUDICATE rhythm.py::adjudicate_duration"),
    "lost_dot_or_staccato": ("a dot beside a plain note, augmentation or staccato not decided: value held",
                             "ADJUDICATE rhythm.py::adjudicate_dot_role + adjudicate_duration"),
    "lost_flag_unread": ("flag ink beside a stem seen but the flag not read: value held",
                         "ADJUDICATE rhythm.py::adjudicate_duration (`flag_ink_unread`)"),
    "lost_head_flag_contradiction": ("the head shape and the flag/stem disagree: value held",
                                     "ADJUDICATE rhythm.py::adjudicate_duration"),
    "lost_rest_value": ("a rest whose shape and the place it hangs disagree: value held",
                        "ADJUDICATE rhythm.py::adjudicate_duration (`rest_slot_contradicts_class`)"),
    "lost_value_other": ("a note or rest value held for another reason", "ADJUDICATE rhythm.py::adjudicate_duration"),
    "lost_chord_value": ("a chord on one stem whose members' values the marks do not settle: chord held",
                         "EXPORT export.py `chord_value_undecided` (from ADJUDICATE adjudicate_duration chord reasons)"),
    "lost_no_pitch": ("a head read but its pitch could not be placed (no clef in force / ledger unread)",
                      "EVALUATE consequences.py::restate_pitch"),
    "red_only_for_a_refused_tip": ("red only because a RIGHTLY refused mark (a neighbour staff's head or rest cut by the cell edge, or a sliver of a head we read) was filed as an unread gap; every real mark of the bar was written",
                                   "EXPORT export.py `_attach_unplaced` (marks the gap for a refusal not in `_NOT_A_GAP_REASONS`)"),
    "lost_hollow_head_held": ("a hollow (half-note) head whose value was held because beam- or flag-like ink stands beside its stem (a hollow head carries no beam or flag)",
                              "ADJUDICATE rhythm.py::adjudicate_duration (head fill is not weighed against the beam/flag reading)"),
    "sum_voice_is_a_copy": ("two voices disagree because the second voice is a copy of marks already counted in the first (the same boxes written twice)",
                            "EXPORT voice assignment (export.py `_place_notes` / voice split)"),
    "lost_refused_head_edge_own": ("a mark refused as 'not a note', cut by the cell's top/bottom edge and nearer THIS staff than any other: this staff's own far head, cut by the cell pad",
                                   "GATHER cell pad (measure_extractor.PAD_*) + ADJUDICATE notehead_precision.py (clipped_fragment)"),
    "lost_refused_head_edge_other": ("a mark refused as 'not a note', cut by the cell's top/bottom edge and nearer another staff: a neighbour's head tip, rightly refused, yet this bar is marked unread",
                                     "ADJUDICATE notehead_precision.py; EXPORT `_attach_unplaced` marks the gap"),
    "lost_refused_rest_edge_own": ("a rest-like mark refused, cut by the cell edge, nearer this staff", "ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest (`rest_clipped_by_crop`)"),
    "lost_refused_rest_edge_other": ("a rest-like mark refused, cut by the cell edge, nearer another staff (a neighbour's rest cut by the cell), this bar marked unread for it",
                                     "ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest (`rest_clipped_by_crop`)"),
    "lost_refused_head_sliver": ("a mark refused as 'not a note' that lies on a head we did read: a sliver of that head, bar marked unread for it",
                                 "ADJUDICATE notehead_precision.py::adjudicate_notehead_is_not_a_notehead"),
    "lost_refused_head_far": ("a mark refused as 'not a note' standing more than 3.5 spaces off the staff: could be a far head or a neighbour's",
                              "ADJUDICATE notehead_precision.py (clipped_fragment / too_narrow) + cell pad measure_extractor.PAD_*"),
    "lost_refused_head_alone": ("a narrow mark refused as 'not a note', alone inside this staff's own cell: may be a real head not read",
                                "ADJUDICATE notehead_precision.py::adjudicate_notehead_is_not_a_notehead"),
    "lost_refused_head_unknown": ("a mark refused as 'not a note' (cell geometry missing)", "ADJUDICATE notehead_precision.py"),
    "lost_refused_rest_edge": ("a rest-like mark refused, touching the cell's top/bottom edge (a neighbour staff's rest cut by the cell)",
                               "ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest (`rest_clipped_by_crop`)"),
    "lost_refused_rest_inside": ("a rest-like mark refused inside this staff (stroke into a head, outside its staff, has a stem...)",
                                 "ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest"),
    "lost_wide_box": ("a box too wide to be one mark left unread", "EXPORT export.py `unread:wide_box_unread`"),
    "lost_other": ("another read mark not written", "EXPORT export.py::_place_notes"),
    "nothing_unboxed_rest_ink": ("no note or rest boxed; rest-sized ink there that the rest reader could not tell",
                                 "ADJUDICATE unboxed_rest.py::adjudicate_unboxed_ink_is_a_rest (abstained)"),
    "nothing_other_ink": ("no note or rest boxed, yet mark-sized ink on the staff: never boxed by the detector",
                          "GATHER detector (a box it never drew has no subject)"),
    "nothing_blank": ("no note or rest boxed and no mark-sized ink on the staff (bar printed empty or only lines)",
                      "GATHER cell / EXPORT empty-bar rule"),
    "twin_owned_elsewhere": ("every mark in the cell was given to another staff (owned elsewhere), the bar written empty",
                             "ADJUDICATE adjudicate_glyph_owner"),
    "twin_claimed_or_twin": ("every mark in the cell was refused as ink of a barline/word/dynamic or as a twin box",
                             "ADJUDICATE claim order (barline / word claim) + notehead_precision"),
    "sum_short_dot_ink_never_boxed": ("short by half the note: a dot is printed beside a plain written note and the detector drew no box on it",
                                      "GATHER detector (dot never boxed); ADJUDICATE aug_dot_join.py cannot join a dot with no box"),
    "sum_short_dot_boxed_augmentation": ("short by a dot: a dot box decided 'augmentation' beside a plain written note, not written on it",
                                         "ADJUDICATE aug_dot_join.py / EXPORT dot attach"),
    "sum_short_dot_boxed_undecided": ("short by a dot: a dot box beside a plain written note whose role (dot or staccato) was undecided",
                                      "ADJUDICATE rhythm.py::adjudicate_dot_role (`dot_role_ambiguous`)"),
    "sum_foreign_note": ("a note standing nearer another staff counted in this bar (a second voice from the neighbour)",
                         "ADJUDICATE adjudicate_glyph_owner + EXPORT note placing"),
    "sum_duplicate_head": ("one head counted twice (two written heads on the same place)", "EXPORT export.py::_place_notes (duplicate guard)"),
    "sum_tuplet_mark": ("a tuplet mark is printed in the bar; the bar was counted without it", "no reader: tuplets are written only where marked"),
    "sum_small_head": ("a small (grace-sized) head counted at full value", "ADJUDICATE notehead class (no grace reader)"),
    "sum_long_dot_written_too_many": ("long by exactly one dot: a dot written that taking away would fill the bar",
                                      "ADJUDICATE rhythm.py::adjudicate_dot_role"),
    "sum_unboxed_rest_ink": ("short: rest-sized ink in the bar the rest reader could not tell (shape / claimed / head beside)",
                             "ADJUDICATE unboxed_rest.py::adjudicate_unboxed_ink_is_a_rest"),
    "sum_head_given_away": ("short: a head standing on this staff was given to another staff (owned elsewhere)", "ADJUDICATE adjudicate_glyph_owner"),
    "sum_all_guessed": ("does not add up and every written note is GUESSED (blue): the sum inherits the guesses", "INFER inferences.py"),
    "sum_beam_flag_values": ("short, no cause found, and the bar holds notes written shorter than a quarter whose value comes from beams/flags (a beam/flag read may be wrong)",
                             "ADJUDICATE rhythm.py::adjudicate_duration (beams / flags)"),
    "sum_unboxed_mark_ink": ("short: mark-sized ink on the staff inside no detector box (a note or rest never boxed)", "GATHER detector (a box it never drew has no subject)"),
    "sum_short_single_event": ("short: the bar holds ONE written event under a known meter, plain, and nothing else read (rest of the bar unread or the event is longer)",
                               "INFER inferences.py one-event rule did not fill it (the event was READ, not narrowed)"),
    "sum_long_whole_rest_beside_notes": ("long: a whole rest is written beside notes of the same voice and counted as a whole bar of silence",
                                         "ADJUDICATE rest value (restWhole shape) + EXPORT voice assignment"),
    "sum_long_note_at_barline": ("long: a note standing at the bar's edge, counted here, is the exact surplus (it may belong to the next bar)",
                                "EXPORT export.py note-to-bar placing (`_place_notes`) / measure_extractor cells"),
    "sum_long_a_rest_too_long": ("long: a rest counted here is the exact surplus, or one step too long (a stroke read as a rest, or a rest value too long)",
                                 "ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest + rhythm.py rest value"),
    "sum_long_one_note_a_step_long": ("long: one written note a step shorter would fill the bar exactly (a value read too long: head fill / unread flag or beam)",
                                      "ADJUDICATE rhythm.py::adjudicate_duration (head fill / flags)"),
    "sum_long_fills_another_meter": ("long: the bar adds up exactly to another common meter (3, 4 or 6 quarters): the meter carried may be stale",
                                     "EVALUATE meter carry (`OMR_METER_CARRY`) / ADJUDICATE meter reader"),
    "sum_unexplained_short": ("short and no test fired (unexplained)", "unknown"),
    "sum_unexplained_long": ("long and no test fired (unexplained)", "unknown"),
    "sum_unexplained_two": ("two voices disagree and no test fired (unexplained)", "unknown"),
    "sum_unexplained": ("does not add up, no counts in the record (unexplained)", "unknown"),
    "sum_other_kind": ("every read mark written yet the bar is marked (unread/partial with nothing lost)", "EXPORT export.py bar marking"),
}


def rowtable(items: list) -> list:
    c = collections.defaultdict(list)
    for r in items:
        c[r["row"]].append(r)
    n = len(items)
    out = []
    for row, rs in sorted(c.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        words = collections.Counter(r["reason"].split(" (")[0] for r in rs)
        kinds = collections.Counter(r["kind"] for r in rs)
        wrong_likely = sum(1 for r in rs if row.startswith("sum_short_dot") and r["n_written_plain"])
        contra = sum(1 for r in rs if r["kind"] == "does_not_add_up" and (r["n_written_plain"] or r["n_written_blue"]))
        out.append(dict(row=row, cause=ROWS.get(row, (row, "?"))[0], owner=ROWS.get(row, (row, "?"))[1], bars=len(rs), share=round(len(rs) / n, 4),
                        record_reasons=dict(words.most_common(5)), red_kind=dict(kinds),
                        value_risk=dict(wrong_value_likely=wrong_likely, sum_contradicts_written_values=contra,
                                        only_unread=len(rs) - contra)))
    return out


def md(res: dict) -> str:
    o = ["# 2.311 -- why every red bar is red (first cause, ALL red bars)", "",
         "STAGED, one saved gather per plate (`lit-a`, `bra-a`), no re-gather; classifier `redbar_classify.py`, driver `redbar_ranking.py`. The first cause keeps",
         "`redbars.cause_of`'s order (Sean read 12 random bars aloud and it matched every time); each vague bucket is then split by a test on the record's own rows.",
         "Value risk: `wrong` = the sum matches EXACTLY a dot printed and not read, so a plain value written READ is probably wrong; `sum` = the bar does not add up, so a",
         "written value (or a mark) is wrong or missing -- the record cannot say which; `unread` = the bar is red only because something was marked unread.", ""]
    for name in ("combined", "litolff", "brahms"):
        t = res[name]
        n = sum(r["bars"] for r in t["rows"])
        o += ["## %s: %d red bars" % (name, n), "", "| # | cause | record's reason words | bars | share | owner | wrong / sum / unread |", "|--|--|--|--|--|--|--|"]
        for i, r in enumerate(t["rows"], 1):
            v = r["value_risk"]
            o.append("| %d | %s | %s | %d | %.1f%% | %s | %d / %d / %d |" % (
                i, r["cause"], "; ".join("%s (%d)" % kv for kv in list(r["record_reasons"].items())[:3]), r["bars"], 100 * r["share"], r["owner"],
                v["wrong_value_likely"], v["sum_contradicts_written_values"] - v["wrong_value_likely"], v["only_unread"]))
        o.append("")
    o += ["## Controls: how often each test's evidence also sits in a bar that is NOT red", "",
          "A test that fires as often on bars that add up as on red bars explains nothing by itself. Share of bars carrying the evidence (cells of the count pages):", "",
          "| evidence | Litolff red | Litolff not red | Brahms red | Brahms not red |", "|--|--|--|--|--|"]
    br = {p: res[p]["base_rates"] for p in ("litolff", "brahms")}
    names = sorted({k for p in br for g in br[p].values() for k in g if k != "bars"})
    for nm in names:
        cells = []
        for p in ("litolff", "brahms"):
            for g in ("red", "not red"):
                d = br[p].get(g, {})
                cells.append("%.1f%% of %d" % (100.0 * d.get(nm, 0) / max(1, d.get("bars", 1)), d.get("bars", 0)))
        o.append("| %s | %s |" % (nm, " | ".join(cells)))
    o += ["", "Rows resting on an arithmetic fit only (`one note a step long`, `a rest too long`, `fills another meter`, `beam/flag values`) are the weakest witness:",
          "the bar sum can confirm, never supply (CLAUDE.md section 4). Rows resting on ink we sized (`unboxed ink`, `dot ink`) fire on 7-24% of bars that add up",
          "(table above): only the exact-sum match (dot) or the record's own verdict (unboxed rest) makes them a mechanism. Cause rows that come straight from",
          "the record's reason words (`lost_*`, `twin_*`, `nothing_*`) carry no such caveat."]
    return "\n".join(o)


def main() -> None:
    ap = argparse.ArgumentParser()
    for n in ("lit", "lit-extra", "bra", "bra-extra", "json", "md"):
        ap.add_argument("--" + n, required=True)
    a = ap.parse_args()
    allbars, res = [], {}
    for plate, fp, ep in (("litolff", a.lit, a.lit_extra), ("brahms", a.bra, a.bra_extra)):
        f = json.load(open(fp))
        extra = json.load(open(ep))
        ctx = Ctx(plate, f, extra, set(SAMPLE["plates"][plate]["pages"]))
        items = classify(ctx)
        print(plate, len(items))
        res[plate] = dict(rows=rowtable(items), n=len(items),
                          base_rates=base_rates(ctx, {(i["page"], i["system"], i["staff"], i["cell"]) for i in items}))
        allbars += items
    res["combined"] = dict(rows=rowtable(allbars), n=len(allbars))
    res["bars"] = allbars
    json.dump(res, open(a.json, "w"), indent=1, default=str)
    open(a.md, "w").write(md(res))
    for name in ("combined", "litolff", "brahms"):
        print("==", name, res[name]["n"])
        for r in res[name]["rows"]:
            print("  %4d %5.1f%%  %-34s" % (r["bars"], 100 * r["share"], r["row"]))


if __name__ == "__main__":
    main()
