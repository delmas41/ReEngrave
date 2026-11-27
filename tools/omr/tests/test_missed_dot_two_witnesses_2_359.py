"""ROADMAP 2.359 -- a dot the detector missed is written blue where the page and the bar agree (flag `OMR_MISSED_DOT_TWO_WITNESSES`, OFF).

STAGED ADJUDICATE (`rhythm._with_missed_dot`: a note read plain beside an unread round mark of its own ink in its dot place is held
NARROWED {plain, dotted}) + INFER (`inferences.missed_dot_decline`: the bar, every other note read, short by exactly the marks' dots,
writes them dotted, GUESSED `missed_dot_fills_bar`).

CONTROLS FROM REAL ROWS (CLAUDE.md rule 7): `fixtures/missed_dot_2_359_brahms.json.gz` holds the Brahms 20261123-night GATHER rows
(page strokes, detector boxes, staff positions, claims) around 22 heads Sean judged, and the record's verdicts for their bars:
  * his 10 undotted notes (out/print/step0-redbars/answers_brahms.json tiles 1, 2, 4, 10, 11, 16, 17, 23) -- on main written plain in a
    bar that does not add up; with the flag 9 are dotted, and tile 11 stays as it was (its bar's voices abstained: no witness);
  * his "not a dot" sheet tiles (out/print/2.357-step0/answers.json): nine ledger-line pieces and the bass-clef piece -- every one is
    ink joined to other ink (his 2026-11-26 observation), never a mark;
  * his dot tile 6, in a bar holding an unread head (the bar is no witness), and tile 19, a mark two heads' dot places share.
The meter's root in the print is mocked here (the 6/8 is a carried reading; `_printed_meter_roots` has its own tests).
"""
from __future__ import annotations

import gzip
import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import inferences
from tools.omr.staged.adjudicate import Candidate, Ruling
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Kind, Log, Outcome, Q, Subject, Verdict

FIX = pathlib.Path(__file__).parent / "fixtures" / "missed_dot_2_359_brahms.json.gz"
ENV = rhythm.MISSED_DOT_ENV
DATA = json.loads(gzip.open(FIX, "rt").read())
CASES = DATA["cases"]
SEAN_DOTTED = ("sean_t1", "sean_t2a", "sean_t2b", "sean_t4", "sean_t10", "sean_t16a", "sean_t16b", "sean_t17", "sean_t23")
NOT_DOTS = [k for k in CASES if k.startswith("sheet") and ("ledger" in k or "clef" in k)]


def _log(narrow=(), meter_on_the_bars=False):
    """The real rows; the heads in `narrow` carry the ADJUDICATE narrowing the flag files (plain first, dotted second).
    `meter_on_the_bars`: the meter verdicts are filed LAST, resting on every duration -- as the real carried 6/8 does (its carry is
    weighed by the bars), which is what made the first replay raise `UphillConsequence`."""
    log = Log()
    for o in DATA["observations"]:
        log.observe(Subject.from_key(o["subject"]), o["quantity"], o["value"], reader=o["reader"], frame=o["frame"],
                    score=o.get("score"), **(o.get("detail") or {}))
    log.freeze()
    rows = [v for v in DATA["verdicts"] if not v.get("supersedes")]
    if meter_on_the_bars:
        rows = [v for v in rows if v["quantity"] != "meter"] + [v for v in rows if v["quantity"] == "meter"]
    durations = []
    for v in rows:
        sub = Subject.from_key(v["subject"])
        outcome, value, reason, cands = Outcome(v["outcome"]), v.get("value"), v.get("reason") or "t", ()
        if v["quantity"] == "duration" and v["subject"] in narrow and outcome is Outcome.DECIDED:
            plain = dict(value)
            dotted = {**plain, "beats": plain["beats"] * 1.5, "written": plain["written"] * 1.5, "dots": 1}
            outcome, value, reason = Outcome.NARROWED, None, rhythm.MISSED_DOT_REASON
            cands = (Candidate(plain, support=1.0), Candidate(dotted, support=0.5))
        elif v.get("candidates"):
            cands = tuple(Candidate(c.get("value"), support=c.get("support") or 0.0) for c in v["candidates"])
        basis = tuple(durations) if (meter_on_the_bars and v["quantity"] == "meter") else ()
        rec = log.record(Verdict(id=log._next_id("vrd"), subject=sub, quantity=v["quantity"], outcome=outcome, value=value,
                                 decider=v.get("decider") or "t", reason=reason, candidates=cands, detail=v.get("detail") or {},
                                 considered=basis, basis=basis))
        if v["quantity"] == "duration":
            durations.append(rec.id)
    return log


def _mark(log, case):
    return rhythm.missed_dot_mark(log, Subject.from_key(CASES[case]))


def _on():
    return mock.patch.dict(os.environ, {ENV: "1"})


def _printed():
    return mock.patch.object(inferences, "_printed_meter_roots", lambda *a, **k: ("printed",))


def _cell(case):
    return Subject.from_key("cell/" + "/".join(CASES[case].split("/")[1:5]))


def _bar_sum(log, cell):
    from tools.omr.staged.bar_length import bar_length
    from tools.omr.staged.consequences import _left_the_bar, _standing
    notes = [v for v in _standing(log, cell, Q.DURATION) if _left_the_bar(log, v.subject) is None]
    return bar_length(log, cell, notes, first_candidate=True).value


class TestTheInkWitness(unittest.TestCase):
    """ADJUDICATE: which real marks stand in a note's dot place as ink of their own."""

    @classmethod
    def setUpClass(cls):
        cls.log = _log()

    def test_seans_ten_undotted_notes_each_have_their_mark(self):
        for case in [c for c in CASES if c.startswith("sean_")]:
            rid, facts = _mark(self.log, case)
            self.assertIsNotNone(rid, (case, facts))

    def test_ledger_pieces_and_the_clef_piece_are_never_a_mark(self):
        # Sean 2026-11-26: "the ledger lines are all connected to the ink of the note that they are a part of"
        for case in NOT_DOTS:
            rid, facts = _mark(self.log, case)
            self.assertIsNone(rid, (case, facts))

    def test_joined_ink_alone_separates_seans_dots_from_his_not_dots(self):
        # Sean 2026-11-26: a dot's ink is not connected to its note; a ledger line's is. On the page stroke map's own ink components
        # (the page raster, staff lines erased) every one of his 10 marks is alone in its component, every not-a-dot piece is not.
        BLOBS = {"sheet01": (0, 3910, 1552), "sheet02": (0, 2434, 2318), "sheet05": (4, 1327, 1239), "sheet07": (5, 5086, 3992),
                 "sheet16": (8, 3705, 6164), "sheet20": (14, 2049, 4213), "sheet21": (14, 1007, 6378), "sheet22": (19, 3716, 522),
                 "sheet23": (19, 5180, 1248), "sheet24": (19, 2544, 3362), "sean_t1": (8, 1303, 2916), "sean_t2a": (8, 3922, 3176),
                 "sean_t2b": (8, 4064, 3176), "sean_t4": (8, 4621, 2709), "sean_t10": (8, 1354, 6736), "sean_t11": (19, 3029, 3117),
                 "sean_t16a": (8, 5198, 2403), "sean_t16b": (8, 5343, 2401), "sean_t17": (8, 5197, 2960), "sean_t23": (8, 1720, 6124)}
        for name, (pg, x, y) in BLOBS.items():
            page = rhythm._missed_dot_page(self.log, pg)
            hit = [d for _, d in page["strokes"] if abs(d["bbox_page_px"][0] - x) <= 3 and abs(d["bbox_page_px"][1] - y) <= 3]
            self.assertEqual(len(hit), 1, name)
            alone = page["comp"][hit[0]["component"]] == 1
            self.assertEqual(alone, name.startswith("sean_"), name)

    def test_a_mark_two_boxes_of_one_head_share_is_held_and_the_bar_abstains(self):
        # Sean's dot tile 19: two detector boxes on ONE printed head (glyph/12/0/9/6/6 and /8, one chord event); the mark is in
        # both boxes' dot place, so both are held -- and the bar refuses a marked note in a chord (never a guess)
        twins = ("glyph/12/0/9/6/6", "glyph/12/0/9/6/8")
        for g in twins:
            rid, facts = rhythm.missed_dot_mark(self.log, Subject.from_key(g))
            self.assertIsNotNone(rid, facts)
        log = _log(set(twins))
        with _on(), _printed():
            why, _ = inferences.missed_dot_decline(log, _cell("sheet19_two_heads"))
        self.assertEqual(why, "marked_note_in_a_chord")

    def test_a_staccato_above_the_head_is_not_in_the_dot_place(self):
        # the two staccato wedges over Brahms p19 system 0 staff 0 bar 6 (boxed glyph/19/0/0/6/7 and /15) are page blobs of their own
        # ink; neither stands in the dot place of any head on the page, whatever the box says
        st = [o for o in DATA["observations"] if o["quantity"] == "page_stroke" and o["value"] == "blob" and o["subject"] == "page/19"
              and (3695 <= o["detail"]["bbox_page_px"][0] <= 3700 or 3798 <= o["detail"]["bbox_page_px"][0] <= 3802)
              and o["detail"]["bbox_page_px"][1] < 460]
        self.assertEqual(len(st), 2)
        page = rhythm._missed_dot_page(self.log, 19)
        self.assertTrue(page["heads"])
        for _, hb, hstep, staff in page["heads"]:
            for s in st:
                self.assertFalse(rhythm._in_dot_place(hb, hstep, staff, s["detail"]))

    def test_flag_off_the_ruling_is_unchanged(self):
        g = Subject.from_key(CASES["sean_t4"])
        spec = adjudicate.REGISTRY[Q.DURATION] if Q.DURATION in adjudicate.REGISTRY else None
        adjudicate._ensure_decisions()
        spec = adjudicate.REGISTRY[Q.DURATION]
        ev = adjudicate.Evidence(self.log, g, spec)
        plain = Ruling(value={"beats": 1.0, "written": 1.0, "dots": 0, "beam_levels": 0}, reason="head_and_marks")
        with mock.patch.dict(os.environ, {ENV: "0"}):
            self.assertIs(rhythm._with_missed_dot(ev, plain), plain)
        with _on():
            got = rhythm._with_missed_dot(ev, plain)
        self.assertIsNone(got.value)
        self.assertEqual(got.reason, rhythm.MISSED_DOT_REASON)
        self.assertEqual([c.value["beats"] for c in got.candidates], [1.0, 1.5])     # plain first, the dotted value beside it


class TestTheBarWitness(unittest.TestCase):
    """INFER: the bar, every other note read, short by exactly the marks' dots."""

    def test_main_writes_seans_notes_plain_in_a_bar_that_does_not_add_up(self):
        log = _log()
        for case in SEAN_DOTTED + ("sean_t11",):
            cell = _cell(case)
            self.assertNotEqual(_bar_sum(log, cell), 3.0, case)                      # red on main
            with _on(), _printed():
                self.assertEqual(inferences._missed_dot_guesses(log, cell), [], case)   # nothing narrowed: nothing to guess

    def test_branch_dots_seans_nine_and_the_bar_adds_up(self):
        narrow = {CASES[c] for c in SEAN_DOTTED}
        log = _log(narrow)
        for case in SEAN_DOTTED:
            cell = _cell(case)
            with _on(), _printed():
                why, marked = inferences.missed_dot_decline(log, cell)
                props = inferences._missed_dot_guesses(log, cell)
            self.assertIsNone(why, case)
            got = {p.subject.to_key(): p for p in props}
            self.assertIn(CASES[case], got, case)
            p = got[CASES[case]]
            self.assertEqual(p.reason, inferences.MISSED_DOT_FILLS_REASON)
            self.assertEqual(p.value["dots"], 1)
            plain = _bar_sum(log, cell)
            self.assertEqual(plain + sum(q.value["beats"] / 3.0 for q in props), 3.0, case)   # each dot adds a third of the dotted value

    def test_tile_11_two_stem_directions_voices_abstained_abstains(self):
        log = _log({CASES["sean_t11"]})
        with _on(), _printed():
            why, _ = inferences.missed_dot_decline(log, _cell("sean_t11"))
        self.assertEqual(why, "not_one_voice")

    def test_one_of_two_marks_alone_does_not_fill_the_bar(self):
        # tile 2: two quarters, each with its dot; with only one held, the bar is short by 1.0 and one dot adds 0.5 -- abstain
        log = _log({CASES["sean_t2a"]})
        with _on(), _printed():
            why, _ = inferences.missed_dot_decline(log, _cell("sean_t2a"))
        self.assertEqual(why, "bar_not_short_by_exactly_the_dots")

    def test_a_bar_holding_an_unread_head_is_no_witness(self):
        log = _log({CASES["sheet06_unread_bar"]})
        with _on(), _printed():
            why, _ = inferences.missed_dot_decline(log, _cell("sheet06_unread_bar"))
        self.assertEqual(why, "something_else_in_the_bar_unread")

    def test_the_guess_never_rests_on_the_meter_that_rests_on_the_bars(self):
        # the first replay of this lane raised UphillConsequence on Brahms: the guess named the meter verdict in its basis, and the
        # carried 6/8 is weighed by the bars (its closure holds this very narrowing). The basis is the printed readings instead.
        from tools.omr.staged.record import UphillConsequence
        narrow = {CASES[c] for c in SEAN_DOTTED}
        log = _log(narrow, meter_on_the_bars=True)
        cell = _cell("sean_t4")
        meter = log.verdict(Q.METER, cell.at(Kind.SYSTEM))
        with _on(), _printed():
            props = inferences._missed_dot_guesses(log, cell)
        self.assertEqual(len(props), 1)
        p = props[0]
        self.assertNotIn(meter.id, p.basis)
        prior = log.verdict(Q.DURATION, p.subject)
        self.assertIn(prior.id, log.closure(meter.id))           # the control: the meter does rest on the narrowing

        def write(basis):
            return log.record(Verdict(id=log._next_id("vrd"), subject=p.subject, quantity=Q.DURATION, outcome=Outcome.DECIDED,
                                      value=p.value, decider="infer:t", reason=p.reason, basis=(prior.id,) + tuple(basis),
                                      considered=(prior.id,) + tuple(basis), supersedes=prior.id))
        with self.assertRaises(UphillConsequence):
            write((meter.id,))                                  # the old basis: meter -> dot -> meter
        write(tuple(b for b in p.basis if log.row(b) is not None))   # the new basis records

    def test_flag_off_proposes_nothing(self):
        log = _log({CASES[c] for c in SEAN_DOTTED})
        with mock.patch.dict(os.environ, {ENV: "0"}), _printed():
            for case in SEAN_DOTTED:
                self.assertEqual(inferences._missed_dot_guesses(log, _cell(case)), [])


LIT = json.loads(gzip.open(pathlib.Path(__file__).parent / "fixtures" / "missed_dot_2_359_litolff.json.gz", "rt").read())


def _litolff_log():
    log = Log()
    for o in LIT["observations"]:
        log.observe(Subject.from_key(o["subject"]), o["quantity"], o["value"], reader=o["reader"], frame=o["frame"],
                    score=o.get("score"), **(o.get("detail") or {}))
    log.freeze()
    for v in LIT["verdicts"]:
        if v.get("supersedes"):
            continue
        cands = tuple(Candidate(c.get("value"), support=c.get("support") or 0.0) for c in (v.get("candidates") or ()))
        log.record(Verdict(id=log._next_id("vrd"), subject=Subject.from_key(v["subject"]), quantity=v["quantity"],
                           outcome=Outcome(v["outcome"]), value=v.get("value"), decider=v.get("decider") or "t",
                           reason=v.get("reason") or "t", candidates=cands, detail=v.get("detail") or {}))
    return log


class TestAStaccatoOverAnotherNoteIsNotADot(unittest.TestCase):
    """ROUND 2. A staccato dot stands directly above or below the notehead it belongs to, and belongs to that note; a lengthening dot
    stands just right of its notehead, in that note's own space, as ink of its own. NEVER: a mark that stands over or under ANOTHER
    notehead taken as the dot of the note on its left. REAL CASE (Sean, 2026-11-26, Litolff p4, `out/print/2.359/answers.json`): the
    mark by glyph/4/0/6/14/1 -- "IT is actually a Stacatto mark" -- stands over the next notehead (glyph/4/0/6/14/4) in the same
    beam group; round 1 took it for the dot of 14/1 and an eighth note read correctly became unwritten."""

    @classmethod
    def setUpClass(cls):
        cls.log = _litolff_log()

    def test_the_named_staccato_is_refused_as_a_dot(self):
        rid, facts = rhythm.missed_dot_mark(self.log, Subject.from_key(LIT["cases"]["staccato_p4"]))
        self.assertIsNone(rid, facts)
        self.assertEqual(facts["why"], "over_another_head")

    def test_the_control_fails_on_round_ones_rule(self):
        # CLAUDE.md rule 7: the same real rows, the over/under test switched off (round 1's rule), take the staccato for a dot
        with mock.patch.object(rhythm, "MISSED_DOT_OVER_HEAD_SPACES", 0.0):
            rid, facts = rhythm.missed_dot_mark(self.log, Subject.from_key(LIT["cases"]["staccato_p4"]))
        self.assertIsNotNone(rid, facts)

    def test_the_second_staccato_on_the_page_is_refused_too(self):
        rid, facts = rhythm.missed_dot_mark(self.log, Subject.from_key(LIT["cases"]["staccato_p4_b"]))
        self.assertIsNone(rid, facts)

    def test_the_note_stays_as_read_with_the_flag_on(self):
        adjudicate._ensure_decisions()
        ev = adjudicate.Evidence(self.log, Subject.from_key(LIT["cases"]["staccato_p4"]), adjudicate.REGISTRY[Q.DURATION])
        plain = Ruling(value={"beats": 0.5, "written": 0.5, "dots": 0, "beam_levels": 1}, reason="head_and_marks")
        with _on():
            self.assertIs(rhythm._with_missed_dot(ev, plain), plain)

    def test_a_head_the_page_refuses_is_not_a_notehead_to_stand_over(self):
        # Sean's dot tile 19 stands in the column of glyph/12/0/9/6/4 -- a box the page claims as not a notehead (and 1.9 spaces off):
        # a real lengthening dot, never refused by it
        log = _log()
        rid, facts = _mark(log, "sheet19_two_heads")
        self.assertIsNotNone(rid, facts)

    def test_no_dot_sean_judged_stands_over_or_under_a_read_notehead(self):
        # his 10 undotted notes: each real dot is still found on the real rows
        log = _log()
        for case in [c for c in CASES if c.startswith("sean_")]:
            rid, facts = _mark(log, case)
            self.assertIsNotNone(rid, (case, facts))


if __name__ == "__main__":
    unittest.main()
