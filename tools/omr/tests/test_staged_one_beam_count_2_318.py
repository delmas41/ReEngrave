"""ROADMAP 2.318 r3 (STAGED ADJUDICATE: `beam_strokes.beam_count` + `rhythm._one_beam_count`), flag `OMR_ONE_BEAM_COUNT`, default OFF.

THE ONE BEAM COUNT: with the flag ON the beam count of a stemmed note comes from the stroke map alone (the staff-erased raster), the stem found
by INK and followed to its far end, every head on one stem sharing the one count; where the map cannot tell the note NARROWS, never "no beam".

Controls are REAL: `fixtures/one_beam_count_2_318/controls.json` holds the stroke rows of the cell of each of Sean's 24 beam tiles (2.317 answers:
0 quarter, 1 eighth, 2 sixteenth), Litolff p2 bar 13 (four eighths) and a few judged notes the read-only test had turned right->wrong. No record, no
gather, no PDF (the fast tier). `TestTheControlCanFail` runs the OLD stem pick (the stem's midpoint against the head's centre) and the old tip
count on the same strokes and shows them wrong where the new count is right or marked.

OPEN, REPORTED, NOT HIDDEN: two of Sean's notes are still written wrong (`xfail(strict)` below) -- a beam fused with an `ff` (Litolff p13 8/2, L11) and a
second beam fused to the first on a staff line (Brahms B09). Whoever fixes one will see its xfail turn red and must delete the mark."""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

import pytest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import beam_strokes as BS
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS, STROKE_GLYPH_BASE
from tools.omr.tests.test_staged_duration import _staff_space
from tools.omr.tests.test_staged_rhythm_leftovers import _head, _real_stem

FLAG = rhythm.ONE_BEAM_COUNT_ENV
FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "one_beam_count_2_318" / "controls.json"
NOTES = json.loads(FIXTURE.read_text())["notes"]

#: Sean's judged notes still written wrong with the flag ON (module doc). The key is the glyph the tile boxed.
OPEN_WRONG = {}


def views(note):
    ow = note["owner"] or {}
    mask = {int(o): "owned" for o in ow.get("owned", ())}
    mask.update({int(o): "contested" for o in ow.get("contested", ())})
    out = []
    for s in note["strokes"]:
        b = s["box"]
        if not b or len(b) < 4:
            continue
        out.append(BS.StrokeView(
            ordinal=s["ord"], kind=mask.get(s["ord"], str(s["kind"])), box=tuple(float(v) for v in b[:4]), length=float(s["len"] or 0),
            thickness=float(s["th"] or 0), sagitta=s["sag"], angle=float(s["ang"] or 0),
            touches=tuple((int(a), float(c)) for a, c in (s["touches"] or ())), space_px=float(s["sp"] or 0), row_id=s["id"],
            profile=tuple(int(v) for v in (s["prof"] or ())), ends=tuple(float(v) for v in (s["ends"] or ())[:4]),
            end_steps=tuple(float(v) for v in (s.get("steps") or ())[:2]), cut=str(s.get("cut") or ""), family=str(s.get("fam") or "")))
    return out


def new_count(note):
    vs = views(note)
    roles = BS.roles(vs, face_join=True, trough=True, one_count=True)
    return BS.beam_count(vs, roles, tuple(float(x) for x in note["head"]), note["side"] if note["side"] in ("up", "down") else None)


def old_count(note):
    """What `_beams_from_strokes` read before this lane: the stem picked by its MIDPOINT against the head's centre, the tip's beams counted."""
    vs = views(note)
    roles = BS.roles(vs, face_join=True, trough=True)
    head = tuple(float(x) for x in note["head"])
    side = note["side"]
    if side not in ("up", "down"):
        return None
    hcy = head[1] + head[3] / 2.0
    for box in note["own_stems"].values():
        b = tuple(float(x) for x in box[:4])
        if ("up" if (b[1] + b[3] / 2.0) < hcy else "down") != side:
            continue
        sv = BS.find_stem_stroke(vs, b)
        if sv is not None:
            return len(BS.tip_reading(vs, roles, sv, side, head_box=head, face_join=True)["beams"])
    return None


def what_the_file_would_say(note, c):
    """The beam count the duration adjudicator would act on: a count; `None` = the note is marked (narrowed or silent). A stem the map counts no
    beam on goes to the flag reader, which is another mark: a note whose value today comes from a flag keeps it."""
    if c["state"] in ("read", "narrowed") and c["certain"] == 0 and note["src"] in ("flag", "shared/other") and note["today"] is not None:
        return note["today"]          # no beam read: the value is what the flag reader (the stem-tip hooks) says, as today -- `hooks_counted` in the real run
    return c["certain"] if c["state"] == "read" else None


JUDGED = sorted(k for k, n in NOTES.items() if n["truth"] is not None)


class TestNeverWrongOnSeansNotes(unittest.TestCase):

    def test_the_controls_are_real(self):
        self.assertEqual(len([n for n in NOTES.values() if n["tile"]]), 24)                  # Sean's 24 tiles
        self.assertEqual(len([k for k in NOTES if k.startswith("glyph/2/1/7/13/")]), 4)       # Litolff p2 bar 13
        for n in NOTES.values():
            self.assertGreater(len(n["strokes"]), 3)

    def test_no_note_is_written_wrong(self):
        wrong = {}
        for k in JUDGED:
            note = NOTES[k]
            v = what_the_file_would_say(note, new_count(note))
            if v is not None and v != note["truth"]:
                wrong[k] = (note["tile"], note["truth"], v)
        self.assertEqual(set(wrong), set(OPEN_WRONG), wrong)

    def test_b09_two_beams_that_run_on_stem_to_stem_are_read_two(self):
        # Sean's B09 (Brahms p18 12/2): the second beam is a SECOND STROKE (5.8 sp, from the second stem to the last) beside the long first one; their
        # boxes' centres are 0.39 sp apart (a sloped stroke's box is taller than its ink), their centre lines at the stem 0.96 sp apart.
        k = next(k for k, n in NOTES.items() if n["tile"] == "B09")
        c = new_count(NOTES[k])
        self.assertEqual((c["state"], c["certain"]), ("read", 2))

    def test_a_head_cut_in_pieces_does_not_lend_the_count_its_outline_as_a_stem(self):
        # Litolff p2 0/0/9/0/0 (not judged; today an eighth): a 1.9 sp vertical piece of the head's own outline stands beside the head's real 4.9 sp stem
        # and was taken for it, reading "no beam" (an eighth turned quarter). With the outline slack it is the head's, and the real stem is read.
        c = new_count(NOTES["glyph/2/0/9/0/0"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "HEAD_OUTLINE_SLACK_SPACES", BS.STEM_MATCH_X_SLACK_SPACES):
            self.assertEqual(new_count(NOTES["glyph/2/0/9/0/0"])["certain"], 0)             # the control fails without it

    def test_a_stem_that_runs_past_a_head_both_ways_with_no_verdict_is_read_at_its_free_end(self):
        # Litolff p2 0/0/5/1/2 (not judged; today an eighth): one 7.6 sp vertical beside the head runs past it both ways; the farther end is where the
        # chord's LOWER head sits. r5 read both ends and marked the note; r6: the end another head sits on is not a tip, the free end is -- one beam.
        c = new_count(NOTES["glyph/2/0/5/1/2"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "FREE_END_IS_THE_TIP", False):
            self.assertEqual(new_count(NOTES["glyph/2/0/5/1/2"])["state"], "narrowed")       # r5: both ends, marked
            with mock.patch.object(BS, "BOTH_WAYS_BOTH", False):
                self.assertEqual(new_count(NOTES["glyph/2/0/5/1/2"])["state"], "read")       # r4: the farther end's one value

    # ── round 6: each control is the real stroke rows of the note named; each fails with its rule switched off ──────────────────────────────────

    def test_r6_seans_eighth_beside_a_neighbours_stem_is_read_not_several_stems(self):
        # Sean's rhythm-leftovers-2 tile 10 (Litolff p2 0/3/1/2, an eighth): the neighbour's stem passes 0.22 sp below this head. An end that barely
        # passes the head is a stem's foot, not a tip.
        c = new_count(NOTES["glyph/2/0/3/1/2"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "FREE_END_IS_THE_TIP", False):
            self.assertEqual(new_count(NOTES["glyph/2/0/3/1/2"])["why"], "several_stems")

    def test_r6_a_beam_ends_on_its_outer_stem(self):
        c = new_count(NOTES["glyph/2/0/8/0/3"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "END_JOIN", False):
            self.assertEqual(new_count(NOTES["glyph/2/0/8/0/3"])["certain"], 0)             # r5 wrote a quarter
        # never Sean's L10: a 1.9 sp sliver of a head beside a stub does not make the stub a beam (the note stays marked one or two)
        k = next(k for k, n in NOTES.items() if n["tile"] == "L10")
        self.assertEqual((new_count(NOTES[k])["certain"], new_count(NOTES[k])["possible"]), (1, 2))

    def test_r6_a_stem_ends_at_its_beam_where_its_ink_runs_on_into_a_letter(self):
        c = new_count(NOTES["glyph/13/1/1/8/0"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "STEM_ENDS_AT_ITS_BEAM", False):
            self.assertEqual(new_count(NOTES["glyph/13/1/1/8/0"])["certain"], 0)
        # never: a stem that runs on through a ledger line / a row of heads and touches no letter is not cut there (a quarter stays a quarter)
        self.assertEqual(new_count(NOTES["glyph/15/0/0/19/2"])["certain"], 0)

    def test_r6_a_mark_at_a_bare_tip_that_may_be_a_flag_or_a_broken_beam_marks_the_note(self):
        for k in ("glyph/13/0/1/8/3", "glyph/17/0/12/3/0"):
            c = new_count(NOTES[k])
            self.assertEqual((c["state"], c["certain"], c["possible"]), ("narrowed", 0, 1), k)
            with mock.patch.object(BS, "MARK_AT_BARE_TIP", False):
                self.assertEqual(new_count(NOTES[k])["state"], "read", k)                    # r5: "no beam", a plain quarter

    def test_r6_the_last_note_before_a_barline_reads_its_stem_in_the_barlines_ink(self):
        c = new_count(NOTES["glyph/2/1/9/7/4"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "STEM_IN_A_BARLINE", False):
            self.assertEqual(new_count(NOTES["glyph/2/1/9/7/4"])["state"], "silent")

    def test_r6_the_first_note_after_a_clef_reads_its_stem_in_the_clefs_ink(self):
        c = new_count(NOTES["glyph/15/1/3/18/0"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "STEM_CLAIMING_FAMILIES", ("barline",)):
            self.assertEqual(new_count(NOTES["glyph/15/1/3/18/0"])["state"], "silent")

    def test_r6_the_flag_OFF_readers_of_the_same_strokes_are_untouched(self):
        # `tip_reading` / `roles` are shared with the 2.202 path that runs with the flag OFF: the outer-stem join and the box-at-the-tip rule act
        # only where the one beam count asks (`one_count=True`). OFF must reproduce the record.
        note = NOTES["glyph/2/0/8/0/3"]
        vs = views(note)
        plain = BS.roles(vs, face_join=True, trough=True)
        stem, sd = BS.stems_by_ink(vs, tuple(float(x) for x in note["head"]), None)["stems"][0]
        self.assertEqual(BS.tip_reading(vs, plain, stem, sd, head_box=tuple(note["head"]), face_join=True)["beams"], [])
        self.assertEqual(len(BS.tip_reading(vs, plain, stem, sd, head_box=tuple(note["head"]), face_join=True, one_count=True)["beams"]), 1)

    def test_r6_a_stem_a_hair_short_of_its_head_end_on_is_its_stem(self):
        c = new_count(NOTES["glyph/17/0/3/2/3"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "END_ON_BRIDGE", False):
            self.assertEqual(new_count(NOTES["glyph/17/0/3/2/3"])["state"], "silent")

    def test_r6_a_second_beam_is_counted_only_at_the_stems_it_reaches(self):
        c = new_count(NOTES["glyph/17/0/9/4/2"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "THICK_REACH_SPACES", 99.0):
            self.assertEqual(new_count(NOTES["glyph/17/0/9/4/2"])["state"], "narrowed")     # r5 marked it one or two

    def test_r6_two_voices_stems_in_one_line_through_the_head_are_its_stem(self):
        c = new_count(NOTES["glyph/13/1/5/8/10"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "ONE_STEM_MAX_SPACES", BS.STEM_MAX_SPACES):
            self.assertEqual(new_count(NOTES["glyph/13/1/5/8/10"])["state"], "silent")

    def test_r6_a_box_on_the_beam_at_the_stems_far_end_carries_the_stems_count(self):
        c = new_count(NOTES["glyph/6/1/7/4/7"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "BOX_AT_TIP_SHARES_THE_COUNT", False):
            self.assertEqual(new_count(NOTES["glyph/6/1/7/4/7"])["certain"], 0)             # r5: a quarter among its stem's eighths

    def test_r6_a_ledger_line_far_from_the_beam_is_not_a_second_beam(self):
        c = new_count(NOTES["glyph/4/0/10/6/1"])
        self.assertEqual((c["state"], c["certain"]), ("read", 1))
        with mock.patch.object(BS, "STUB_STACKS_ON_THE_BEAM", False):
            self.assertEqual(new_count(NOTES["glyph/4/0/10/6/1"])["state"], "narrowed")

    def test_the_four_brahms_second_beam_sixteenths_are_marked_never_an_eighth(self):
        for tile in ("B01", "B04", "B06", "B10"):
            k = next(k for k, n in NOTES.items() if n["tile"] == tile)
            c = new_count(NOTES[k])
            self.assertEqual(c["state"], "narrowed", tile)
            self.assertEqual((c["certain"], c["possible"]), (1, 2), tile)                      # one beam or two: marked, candidates 1 and 2
            self.assertIn("thick_at_stem", [x for s in c["stems"] for x in s["causes"]], tile)

    def test_litolff_p2_bar_13_four_beamed_eighths_are_read_one_beam(self):
        for k in (k for k in NOTES if k.startswith("glyph/2/1/7/13/")):
            c = new_count(NOTES[k])
            self.assertEqual((c["state"], c["certain"]), ("read", 1), k)

    def test_the_litolff_quarters_sean_named_are_never_given_a_beam(self):
        for tile in ("L02", "L05", "L07", "L09"):                                              # the quarters the bar-crop reader gave a beam
            k = next(k for k, n in NOTES.items() if n["tile"] == tile)
            c = new_count(NOTES[k])
            self.assertEqual(c["certain"], 0, tile)                                            # zero certain; possibly marked, never a beam written

    def test_only_the_notes_with_no_value_today_carry_one_now_where_the_map_reads_them(self):
        # every tile note the file writes NO value for today (the 347's kind) ends read right or marked
        for k, n in NOTES.items():
            if n["tile"] and n["today"] is None and k not in OPEN_WRONG:
                v = what_the_file_would_say(n, new_count(n))
                self.assertTrue(v is None or v == n["truth"], (k, n["tile"], v, n["truth"]))


@pytest.mark.parametrize("glyph", [pytest.param(k, marks=pytest.mark.xfail(strict=True, reason=OPEN_WRONG[k])) if k in OPEN_WRONG else k for k in JUDGED])
def test_each_judged_note_is_right_or_marked(glyph):
    note = NOTES[glyph]
    v = what_the_file_would_say(note, new_count(note))
    assert v is None or v == note["truth"], (note["tile"], note["truth"], v)


class TestTheControlCanFail(unittest.TestCase):
    """The OLD stem pick and tip count, on the same real strokes: wrong where the new count is right or marked."""

    def test_the_old_count_writes_the_brahms_second_beam_sixteenths_as_eighths(self):
        for tile in ("B01", "B04", "B06", "B09", "B10"):
            k = next(k for k, n in NOTES.items() if n["tile"] == tile)
            self.assertEqual(NOTES[k]["truth"], 2)
            with mock.patch.object(BS, "LEVEL_BY_LINE", False):                                # B09: levels by box centres merge its two beams
                self.assertEqual(old_count(NOTES[k]), 1, tile)                                    # one beam where Sean says two: a hidden wrong

    def test_the_old_stem_pick_is_silent_on_the_upper_head_of_a_chord_and_the_new_one_reads_it(self):
        k = "glyph/5/0/1/5/12"                                                                # judged a sixteenth (Brahms p5)
        self.assertEqual(NOTES[k]["truth"], 2)
        self.assertIsNone(old_count(NOTES[k]))                                                # the stem's midpoint is below this head's centre: no stem
        c = new_count(NOTES[k])
        self.assertEqual((c["state"], c["certain"]), ("read", 2))

    def test_a_beam_the_stem_crosses_but_does_not_end_at_is_another_notes_and_the_quarter_stays_a_quarter(self):
        # Litolff L07 (Sean: a quarter): its stem touches a beam two spaces INWARD of its tip, another group's beam crossing it. Round 3 marked it
        # (`beamed_stem_uncounted`); the beam is not at the stem's end, so the stem has no beam and the quarter is read.
        k = next(k for k, n in NOTES.items() if n["tile"] == "L07")
        c = new_count(NOTES[k])
        self.assertEqual((c["state"], c["certain"], c["possible"]), ("read", 0, 0))

    def test_the_beam_of_a_stem_claimed_as_a_head_is_not_read_as_none(self):
        # Sean's rhythm-leftovers-3 tile 3 (an eighth, Litolff p2 13/1): the beam at the stem's end is a stroke a head box has claimed (the detector boxed the
        # beam). A claim says who owns ink, not what shape it has: beam-shaped claimed ink the stem touches at its end is marked, never "no beam".
        c = new_count(NOTES["glyph/2/1/5/13/1"])
        self.assertEqual((c["state"], c["certain"], c["possible"]), ("narrowed", 0, 1))
        self.assertIn("claimed_ink_at_tip", [x for s in c["stems"] for x in s["causes"]])

    def test_a_beam_fused_with_an_ff_is_marked_never_none(self):
        # Sean's L11 (Litolff p13 8/2): the stem's end meets ink a word has claimed. Only a dynamic's or a word's ink, and only a beam's thickness of it.
        k = next(k for k, n in NOTES.items() if n["tile"] == "L11")
        c = new_count(NOTES[k])
        self.assertEqual((c["state"], c["certain"], c["possible"]), ("narrowed", 0, 1))

    def test_claimed_ink_thinner_than_a_beam_does_not_hide_one(self):
        k = next(k for k, n in NOTES.items() if n["tile"] == "L11")
        note = NOTES[k]
        thin = json.loads(json.dumps(note))
        for s in thin["strokes"]:
            if s.get("fam") in ("word", "dynamic", "text"):
                s["th"] = 0.3                                                                  # a hairpin is thinner than a beam (Sean 2026-10-09)
        c = new_count(thin)
        self.assertEqual((c["state"], c["certain"]), ("read", 0))

    def test_a_stem_the_verdict_sends_the_wrong_way_is_not_read_from_the_other_end(self):
        # A direction verdict the ink contradicts is two readers disagreeing: the count is silent (cannot tell), never the ink's side by guess (`INK_SIDE`
        # is measured and refused). The same stem, with the verdict right, is found.
        k = "glyph/2/1/5/13/1"
        note = NOTES[k]
        wrong = "down" if note["side"] == "up" else "up"
        self.assertEqual(BS.stems_by_ink(views(note), tuple(float(x) for x in note["head"]), wrong)["stems"], [])
        self.assertEqual([sd for _s, sd in BS.stems_by_ink(views(note), tuple(float(x) for x in note["head"]), note["side"])["stems"]], [note["side"]])

    def test_a_stroke_the_stem_does_not_touch_is_never_its_stem(self):
        note = NOTES[next(k for k, n in NOTES.items() if n["tile"] == "B02")]
        vs = [v for v in views(note) if v.kind != "vertical"]                                # take every vertical stroke out: no stem
        roles = BS.roles(vs, face_join=True, trough=True)
        c = BS.beam_count(vs, roles, tuple(float(x) for x in note["head"]), note["side"])
        self.assertEqual((c["state"], c["why"]), ("silent", "no_vertical_touches_the_head"))


class TestTheStemIsFoundByInk(unittest.TestCase):

    SP = 100.0
    HEAD = (200.0, 400.0, 130.0, 100.0)

    def v(self, ordinal, kind, box, touches=(), length=None, thick=0.3):
        return BS.StrokeView(ordinal, kind, tuple(float(x) for x in box), (box[3] / self.SP) if length is None else length, thick, 0.0, 90.0,
                             tuple((j, 1.0) for j in touches), self.SP, row_id="r%d" % ordinal)

    def test_a_vertical_that_touches_the_heads_ink_is_the_stem_followed_to_its_far_end(self):
        blob = self.v(0, "blob", (200, 400, 130, 100), touches=(1,))
        stem = self.v(1, "vertical", (300, 100, 30, 340), touches=(0,))                      # rises from the head's right edge
        r = BS.stems_by_ink([blob, stem], self.HEAD, "up")
        self.assertEqual([(s.ordinal, sd) for s, sd in r["stems"]], [(1, "up")])

    def test_a_vertical_beside_the_head_that_touches_none_of_its_ink_is_nobodys_stem_here(self):
        blob = self.v(0, "blob", (200, 400, 130, 100))
        near = self.v(1, "vertical", (400, 100, 30, 340))                                     # a full space of paper from the head's ink: not its stem
        r = BS.stems_by_ink([blob, near], self.HEAD, "up")
        self.assertEqual((r["stems"], r["why"]), ([], "no_vertical_touches_the_head"))

    def test_a_stem_a_scan_parted_from_its_head_by_a_hair_is_still_its_stem_RED_and_a_full_space_away_is_not_TWIN(self):
        blob = self.v(0, "blob", (200, 400, 130, 100))
        hair = self.v(1, "vertical", (350, 100, 30, 340))                                     # 0.2 sp of paper (within the measured 2.161 bridge)
        self.assertEqual([sd for _s, sd in BS.stems_by_ink([blob, hair], self.HEAD, "up")["stems"]], ["up"])
        far = self.v(1, "vertical", (400, 100, 30, 340))
        self.assertEqual(BS.stems_by_ink([blob, far], self.HEAD, "up")["stems"], [])

    def test_a_head_no_reader_found_a_stem_for_carries_no_beam_unless_a_beam_runs_over_its_column(self):
        blob = self.v(0, "blob", (200, 400, 130, 100))
        c = BS.beam_count([blob], BS.roles([blob]), self.HEAD, "up", finder_stem=False)
        self.assertEqual((c["state"], c["certain"], c["possible"]), ("read", 0, 0))
        beam = self.v(1, "horizontal", (100, 200, 400, 60), touches=(2, 3), thick=0.6)        # a beam across its column on two OTHER stems, none under it
        others = [self.v(2, "vertical", (100, 200, 30, 300), touches=(1,)), self.v(3, "vertical", (470, 200, 30, 300), touches=(1,))]
        c2 = BS.beam_count([blob, beam] + others, BS.roles([blob, beam] + others), self.HEAD, "up", finder_stem=False)
        self.assertEqual(c2["state"], "silent")
        c3 = BS.beam_count([blob], BS.roles([blob]), self.HEAD, "up", finder_stem=True)     # the finder HAD a stem the ink cannot find: cannot tell
        self.assertEqual(c3["state"], "silent")

    def test_a_stem_cut_by_a_crossing_is_followed_across_it_to_the_tip(self):
        blob = self.v(0, "blob", (200, 400, 130, 100), touches=(1,))
        low = self.v(1, "vertical", (300, 250, 30, 190), touches=(0,))
        high = self.v(2, "vertical", (300, 100, 30, 110))                                     # 40 px (0.4 sp) of paper between them: the same stem
        (stem, sd), = BS.stems_by_ink([blob, low, high], self.HEAD, "up")["stems"]
        self.assertEqual((sd, stem.box[1]), ("up", 100.0))

    def test_every_head_on_one_stem_gets_that_stems_one_count(self):
        # a chord: two heads on one up stem; the upper head's centre is ABOVE the stem's midpoint (the old pick found no stem there)
        low, high = (200.0, 520.0, 130.0, 100.0), (200.0, 300.0, 130.0, 100.0)
        strokes = [self.v(0, "blob", low, touches=(2,)), self.v(1, "blob", high, touches=(2,)), self.v(2, "vertical", (300, 80, 30, 540), touches=(0, 1, 3)),
                   self.v(3, "horizontal", (300, 76, 200, 60), touches=(2, 4), thick=0.6), self.v(4, "vertical", (470, 80, 30, 300), touches=(3,))]
        roles = BS.roles(strokes, face_join=True, trough=True)
        counts = [BS.beam_count(strokes, roles, h, "up") for h in (low, high)]
        self.assertEqual([(c["state"], c["certain"]) for c in counts], [("read", 1), ("read", 1)])
        self.assertEqual(counts[0]["stems"][0]["stem"], counts[1]["stems"][0]["stem"])

    def test_two_stems_one_way_at_one_head_pick_the_one_on_the_engraving_side(self):
        blob = self.v(0, "blob", (200, 400, 130, 100), touches=(1, 2))
        mine = self.v(1, "vertical", (300, 100, 30, 340), touches=(0,))                      # up -> right
        other = self.v(2, "vertical", (200, 100, 30, 340), touches=(0,))                     # a neighbour's, at the left edge
        (stem, _sd), = BS.stems_by_ink([blob, mine, other], self.HEAD, "up")["stems"]
        self.assertEqual(stem.ordinal, 1)


def _pair_cell(strokes, heads=(0, 1)):
    """Two heads on down stems (as the 2.202 tests build them), each head's ink a blob that touches its stem, and the stroke map `strokes`."""
    sp = 100.0
    stem_x, top, tip = (244, 400), 383, 820
    head_boxes = [(235, 355, 135, 142), (393, 348, 127, 118)]
    log = Log()
    _staff_space(log, sp)
    gs = []
    for hi in heads:
        gs.append(_head(log, hi, head_boxes[hi]))
        _real_stem(log, (stem_x[hi], top, 31, tip - top))
    for i, st in enumerate(strokes):
        kind, box, length, thick, touches = st
        log.observe(R.glyph(0, 0, 0, 0, STROKE_GLYPH_BASE + i), Q.STROKE, kind, reader=READERS.CV_STROKE, frame="cell:0", stroke_box=list(box),
                    length_spaces=length, angle_deg=0.0 if kind == "horizontal" else 90.0, thickness_spaces=thick, thickness_spread_spaces=0.02, fill=0.9,
                    sagitta_spaces=0.0, touches=[[j, 1.0] for j in touches], staff_space_local_px=sp, ends=[0, 0, 0, 0], end_steps_from_top=[0.0, 0.0],
                    component=0)
    return log, gs[0]


def _dur(strokes, on, heads=(0, 1)):
    log, g = _pair_cell(strokes, heads)
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)
    return log.verdict(Q.DURATION, g)


BLOB0 = ("blob", (235, 355, 135, 142), 1.4, 0.9, [1])
STEM0 = ("vertical", (244, 383, 31, 437), 4.37, 0.3, [0, 4])
BLOB1 = ("blob", (393, 348, 127, 118), 1.2, 0.9, [3])
STEM1 = ("vertical", (400, 383, 31, 437), 4.37, 0.3, [2, 4])
BEAM = ("horizontal", (251, 757, 364, 63), 3.64, 0.63, [1, 3])
PAIR = [BLOB0, STEM0, BLOB1, STEM1, BEAM]
QUARTER = [BLOB0, ("vertical", (244, 383, 31, 437), 4.37, 0.3, [0])]
FLAGGED = [BLOB0, ("vertical", (244, 383, 31, 437), 4.37, 0.3, [0, 2]), ("horizontal", (251, 770, 110, 25), 1.1, 0.25, [1])]


class TestThroughTheDurationAdjudicator(unittest.TestCase):

    def test_flag_OFF_nothing_the_flag_adds_is_in_the_verdict(self):
        v = _dur(PAIR, False)
        self.assertNotIn("one_beam_count", v.detail)

    def test_flag_ON_a_beamed_pair_is_an_eighth_from_the_stroke_map_alone(self):
        v = _dur(PAIR, True)
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))
        self.assertEqual(v.detail["one_beam_count"]["state"], "read")
        self.assertEqual(v.detail["beam_evidence"], "read")

    def test_flag_ON_a_bare_stem_with_a_clean_tip_is_a_quarter_read_not_assumed(self):
        v = _dur(QUARTER, True, heads=(0,))
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 0))
        self.assertEqual(v.detail["one_beam_count"]["state"], "read")

    def test_flag_ON_a_head_the_map_holds_no_stem_for_is_NARROWED_never_a_quarter(self):
        v = _dur([BLOB0], True, heads=(0,))
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(sorted(c.value["beam_levels"] for c in v.candidates), [0, 1])
        self.assertEqual(v.detail["one_beam_count"]["state"], "silent")

    def test_flag_ON_a_flag_stays_with_the_flag_reader(self):
        # one hook at a stem's tip with no detector box: the count is zero beams, and the verdict is what it is for any unbeamed stem
        on = _dur(FLAGGED, True, heads=(0,))
        off = _dur(FLAGGED, False, heads=(0,))
        self.assertEqual((on.outcome, on.value, on.reason), (off.outcome, off.value, off.reason))


if __name__ == "__main__":
    unittest.main()
