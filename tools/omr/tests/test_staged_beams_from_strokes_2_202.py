"""ROADMAP 2.202 (STAGED ADJUDICATE `rhythm._beams_from_strokes` + pure `beam_strokes`), flag `OMR_BEAMS_FROM_STROKES`, default OFF, step 3 of the shared ink map.

A head's beam levels from the stroke map: a detector beam box on no beam-shaped stroke NARROWS; a box on a short hook of a stem that carries
no spanning beam is a FLAG (Sean 2026-10-22); the strokes at the stem tip are counted and a stroke no box named is a candidate only. Every
test that says RED has a twin beside it that must NOT fire, and `TestTheControlCanFail` breaks the hook/beam cut and shows the RED test turn.
Constructed cells only (no record, no gather)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import beam_strokes as BS
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS, STROKE_GLYPH_BASE
from tools.omr.tests.test_staged_duration import _staff_space
from tools.omr.tests.test_staged_rhythm_leftovers import CELL, _head, _real_stem, _stroke

FLAG = rhythm.BEAMS_FROM_STROKES_ENV
SP = 100.0

# three stems of down-stemmed heads, as in the 2.140 tile (stems at x 244, 400, 563 reaching y 820; beam hangs at the bottom tip)
STEM_X = (244, 400, 563)
STEM_TOP, TIP = 383, 820
BEAM = (251, 757, 364, 63)            # a beam stroke between stems 0 and 1
HOOK = (251, 770, 110, 25)            # a 1.1-space-long hook off stem 0 (nothing reaches stem 1)


def S(kind, box, length, thick, touches=(), sag=0.03, angle=0.0):
    return dict(kind=kind, box=box, L=length, T=thick, touches=list(touches), sag=sag, angle=angle)


def stem_stroke(i):
    return S("vertical", (STEM_X[i], STEM_TOP, 31, TIP - STEM_TOP), 4.37, 0.3, sag=0.0, angle=90.0)


def beam_stroke(touches, box=BEAM, thick=0.63):
    return S("horizontal", box, box[2] / SP, thick, touches)


def hook_stroke(touches, box=HOOK, length=1.1, thick=0.25):
    return S("horizontal", box, length, thick, touches)


def build(strokes, *, boxes=(), cv=(), heads=(0, 1), extra=None):
    """One cell: the heads on down stems, the CV rows for `cv` boxes, the stroke map `strokes` (list of S(...) in ordinal order) and the
    detector beam boxes `boxes` as [(box, [ordinals under it] or None)] (None: a box with no Q.GLYPH_STROKES row)."""
    log = Log()
    _staff_space(log, SP)
    gs = []
    for hi in heads:
        gs.append(_head(log, hi, [(235, 355, 135, 142), (393, 348, 127, 118), (554, 354, 143, 125)][hi]))
        _real_stem(log, (STEM_X[hi], STEM_TOP, 31, TIP - STEM_TOP))
    for box in cv:
        _stroke(log, box, cv=True)
    for i, st in enumerate(strokes):
        log.observe(R.glyph(0, 0, 0, 0, STROKE_GLYPH_BASE + i), Q.STROKE, st["kind"], reader=READERS.CV_STROKE, frame="cell:0",
                    stroke_box=list(st["box"]), length_spaces=st["L"], angle_deg=st["angle"], thickness_spaces=st["T"],
                    thickness_spread_spaces=0.02, fill=0.9, sagitta_spaces=st["sag"], touches=[[j, 1.0] for j in st["touches"]],
                    staff_space_local_px=SP, ends=[0, 0, 0, 0], end_steps_from_top=[0.0, 0.0], component=0)
    for k, (box, under) in enumerate(boxes):
        _stroke(log, box, cv=False)
        gb = R.glyph(0, 0, 0, 0, 20 + k)
        log.observe(gb, Q.GLYPH_BOX, ("beam",) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.7)
        if under is not None:
            log.observe(gb, Q.GLYPH_STROKES, list(under), reader=READERS.CV_GLYPH_STROKES, frame="cell:0",
                        shares=[1.0] * len(under), cover_min=0.5)
    if extra:
        extra(log)
    return log, gs[0]


def dur(on, strokes, **kw):
    log, g = build(strokes, **kw)
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)
    return log.verdict(Q.DURATION, g)


def levels(v):
    return sorted(c.value["beam_levels"] for c in v.candidates)


PAIR = [stem_stroke(0), stem_stroke(1), beam_stroke([0, 1])]
PAIR[0]["touches"] = [2]
PAIR[1]["touches"] = [2]


class TestPureShapes(unittest.TestCase):
    """`beam_strokes.role_of`: the role is a function of the stroke's own fields; each case has a twin that must not fire."""

    def views(self, strokes):
        return [BS.StrokeView(i, s["kind"], s["box"], s["L"], s["T"], s["sag"], s["angle"], tuple((j, 1.0) for j in s["touches"]), SP)
                for i, s in enumerate(strokes)]

    def role(self, strokes, i):
        return BS.roles(self.views(strokes))[i]["role"]

    def test_two_stems_thick_is_a_beam_RED_and_one_stem_is_a_stub_TWIN(self):
        self.assertEqual(self.role(PAIR, 2), "beam")
        one = [stem_stroke(0), beam_stroke([0])]
        one[0]["touches"] = [1]
        self.assertEqual(self.role(one, 1), "beam_stub")

    def test_two_stems_but_thinner_than_a_beam_or_curved_is_a_span_not_a_beam(self):
        thin = [stem_stroke(0), stem_stroke(1), beam_stroke([0, 1], thick=0.25)]
        self.assertEqual(self.role(thin, 2), "span_thin")
        curved = [stem_stroke(0), stem_stroke(1), S("curve", BEAM, 3.6, 0.63, [0, 1], sag=0.4)]
        self.assertEqual(self.role(curved, 2), "span_thin")           # "a beam never has an arc" (Sean 2026-10-09)

    def test_the_hook_cut_has_a_decided_band_a_near_miss_band_and_a_refusal(self):
        for length, want in ((0.63, "hook"), (1.4, "hook"), (1.6, "hook"), (1.93, "hook_or_stub"), (2.4, "hook_or_stub"), (2.69, "other")):
            s = [stem_stroke(0), hook_stroke([0], length=length)]
            s[0]["touches"] = [1]
            self.assertEqual(self.role(s, 1), want, length)

    def test_a_vertical_longer_than_any_stem_is_a_barline_and_a_stroke_leaning_on_it_is_no_hook(self):
        bar = [dict(stem_stroke(0), L=12.0, touches=[1]), hook_stroke([0])]
        self.assertEqual(self.role(bar, 1), "other")           # milestone 2.202: 118 of 122 'hooks' stood on barlines
        ok = [dict(stem_stroke(0), touches=[1]), hook_stroke([0])]
        self.assertEqual(self.role(ok, 1), "hook")             # twin: the same geometry on a stem-length vertical

    def test_a_stroke_touching_no_stem_is_nothing_a_vertical_is_not_a_hook(self):
        self.assertEqual(self.role([hook_stroke([])], 0), "other")
        self.assertEqual(self.role([stem_stroke(0)], 0), "other")

    def test_box_support_names_why_it_refuses(self):
        role = BS.roles(self.views(PAIR))
        self.assertEqual(BS.box_support([2], role)["support"], "beam")
        self.assertEqual(BS.box_support([], role)["reason"], "box_on_paper")
        self.assertEqual(BS.box_support([0], role)["reason"], "box_on_a_stem")


class TestOffIsByteIdentical(unittest.TestCase):

    def test_flag_OFF_the_verdict_is_the_same_with_or_without_the_stroke_map(self):
        bare = dur(False, [], cv=[BEAM], boxes=[(BEAM, None)])
        mapped = dur(False, PAIR, cv=[BEAM], boxes=[(BEAM, [2])])
        for f in ("outcome", "value", "reason", "detail", "candidates"):
            self.assertEqual(getattr(bare, f), getattr(mapped, f), f)
        self.assertNotIn("beams_from_strokes", mapped.detail)

    def test_flag_OFF_a_box_on_paper_still_decides_a_beam_as_on_main(self):
        v = dur(False, PAIR, boxes=[((300, 100, 300, 40), [])])
        self.assertEqual(v.outcome, Outcome.DECIDED)

    def test_flag_ON_without_a_stroke_map_changes_nothing(self):
        off = dur(False, [], cv=[BEAM], boxes=[(BEAM, None)])
        on = dur(True, [], cv=[BEAM], boxes=[(BEAM, None)])
        for f in ("outcome", "value", "reason", "candidates"):
            self.assertEqual(getattr(off, f), getattr(on, f), f)
        self.assertNotIn("beams_from_strokes", on.detail)


class TestABeamedPair(unittest.TestCase):

    def test_ON_the_stroke_map_agrees_with_the_old_readers_and_the_value_is_as_today(self):
        off = dur(False, PAIR, cv=[BEAM], boxes=[(BEAM, [2])])
        on = dur(True, PAIR, cv=[BEAM], boxes=[(BEAM, [2])])
        self.assertEqual((on.outcome, on.value), (off.outcome, off.value))
        self.assertEqual(on.value["beam_levels"], 1)
        self.assertEqual(on.detail["beams_from_strokes"]["settled"], "agrees")
        self.assertEqual(on.detail["beams_from_strokes"]["tip"]["beams"], [2])

    def test_ON_a_second_pair_of_heads_does_not_disturb_the_first(self):
        # CONTROL: a third stem with its own beam stroke elsewhere in the cell; head 0's tip still counts one level
        s = PAIR + [stem_stroke(2), beam_stroke([3], box=(570, 757, 300, 63))]
        s[3]["touches"] = [4]
        v = dur(True, s, cv=[BEAM], boxes=[(BEAM, [2])], heads=(0, 1, 2))
        self.assertEqual(v.value["beam_levels"], 1)


class TestAFlagBoxedAsABeam(unittest.TestCase):
    """The detector draws a BEAM box on a FLAG (3 of Sean's 6 crops): one stem, a short thin stroke at its tip."""

    ONE = [dict(stem_stroke(0), touches=[1]), hook_stroke([0])]
    TWO = [dict(stem_stroke(0), touches=[1, 2]), hook_stroke([0]), hook_stroke([0], box=(251, 700, 110, 25))]

    def test_flag_OFF_the_box_is_a_beam_level(self):
        v = dur(False, self.TWO, boxes=[((251, 690, 110, 110), [1, 2])], heads=(0,))
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))
        self.assertEqual(v.detail["beam_evidence"], "read")

    def test_flag_ON_two_hooks_under_the_box_are_a_SIXTEENTH_FLAG_RED(self):
        v = dur(True, self.TWO, boxes=[((251, 690, 110, 110), [1, 2])], heads=(0,))
        self.assertEqual((v.outcome, v.value["beam_levels"], v.value["beats"]), (Outcome.DECIDED, 2, 0.25))
        self.assertEqual(v.detail["beam_evidence"], "flag")
        self.assertEqual(v.detail["flag_levels"], 2)
        self.assertEqual(v.detail["beams_from_strokes"]["settled"], "box_flag")
        self.assertEqual(v.detail["beams_by_stem"], 0)

    def test_flag_ON_one_hook_is_an_eighth_flag_not_a_beam(self):
        v = dur(True, self.ONE, boxes=[((251, 760, 110, 40), [1])], heads=(0,))
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))
        self.assertEqual(v.detail["beam_evidence"], "flag")

    def test_flag_ON_a_hook_box_the_older_one_stem_ink_filter_ALREADY_removed_is_still_a_flag_RED(self):
        # milestone 2.202: 0 of 418 map-hook boxes were still in `kept` when the block ran (the 2.74 ink test drops a stroke on one stem first)
        def drop_all(ev, cell, kept, stems, tol, **kw):
            return [], {b.id: "one_stem" for b in kept}, []
        with mock.patch.object(rhythm, "_not_a_beam_by_ink", drop_all):
            off = dur(False, self.TWO, boxes=[((251, 690, 110, 110), [1, 2])], heads=(0,))
            on = dur(True, self.TWO, boxes=[((251, 690, 110, 110), [1, 2])], heads=(0,))
        self.assertNotEqual(off.detail.get("beam_evidence"), "flag")
        self.assertEqual((on.outcome, on.value["beam_levels"], on.detail["beam_evidence"]), (Outcome.DECIDED, 2, "flag"))

    def test_TWIN_the_same_hook_on_a_stem_that_carries_a_spanning_beam_is_a_stub_not_a_flag(self):
        # stem 0 also touches the thick stroke across to stem 1: a beamed stem, the short stroke beside it is a stub (candidate level only)
        s = [dict(stem_stroke(0), touches=[2, 3]), dict(stem_stroke(1), touches=[2]), beam_stroke([0, 1]), hook_stroke([0], box=(251, 700, 110, 25))]
        v = dur(True, s, boxes=[((251, 690, 110, 50), [3])])
        self.assertNotEqual(v.detail.get("beam_evidence"), "flag")
        self.assertEqual(v.detail["beams_from_strokes"]["boxes"][0]["reason"], "hook_on_a_beamed_stem")

    def test_TWIN_a_hook_longer_than_the_cut_plus_its_near_miss_is_not_a_flag(self):
        s = [dict(stem_stroke(0), touches=[1]), hook_stroke([0], length=2.69, box=(251, 770, 270, 25))]
        v = dur(True, s, boxes=[((251, 760, 270, 40), [1])], heads=(0,))
        self.assertNotEqual(v.detail["beam_evidence"], "flag")
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_TWIN_a_hook_inside_the_near_miss_band_is_never_decided_a_flag(self):
        s = [dict(stem_stroke(0), touches=[1]), hook_stroke([0], length=1.93, box=(251, 770, 193, 25))]
        v = dur(True, s, boxes=[((251, 760, 193, 40), [1])], heads=(0,))
        self.assertNotEqual(v.detail["beam_evidence"], "flag")
        self.assertEqual(v.detail["beams_from_strokes"]["boxes"][0]["reason"], "hook_or_stub")


class TestABeamBoxOnNothingNarrows(unittest.TestCase):

    def test_flag_ON_a_box_on_empty_paper_NARROWS_keeping_the_beam_as_a_candidate_RED(self):
        v = dur(True, [dict(stem_stroke(0), touches=[]), ], boxes=[((251, 757, 364, 63), [])], heads=(0,))
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(levels(v), [0, 1])
        self.assertEqual(v.detail["beams_from_strokes"]["boxes"][0]["reason"], "box_on_paper")
        self.assertEqual(v.reason, "beams_ambiguous")

    def test_flag_OFF_the_same_box_DECIDES(self):
        v = dur(False, [dict(stem_stroke(0), touches=[])], boxes=[((251, 757, 364, 63), [])], heads=(0,))
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))

    def test_flag_ON_a_box_on_a_stem_alone_NARROWS(self):
        v = dur(True, [dict(stem_stroke(0), touches=[])], boxes=[((240, 500, 40, 320), [0])], heads=(0,))
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.detail["beams_from_strokes"]["boxes"][0]["reason"], "box_on_a_stem")

    def test_TWIN_flag_ON_a_box_on_a_real_beam_stroke_still_DECIDES(self):
        v = dur(True, PAIR, boxes=[(BEAM, [2])])
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))

    def test_flag_ON_a_box_on_a_thin_slur_across_two_stems_NARROWS_a_thick_one_does_not(self):
        thin = [dict(stem_stroke(0), touches=[2]), dict(stem_stroke(1), touches=[2]), beam_stroke([0, 1], thick=0.25)]
        v = dur(True, thin, boxes=[(BEAM, [2])])
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.detail["beams_from_strokes"]["boxes"][0]["reason"], "thin_or_curved_span")
        self.assertEqual(dur(True, PAIR, boxes=[(BEAM, [2])]).outcome, Outcome.DECIDED)

    def test_flag_ON_a_box_with_no_glyph_strokes_row_is_left_as_it_was(self):
        # the cell was not mapped for that box: cannot tell is not 'on paper' (rule 8)
        v = dur(True, PAIR, boxes=[(BEAM, None)])
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))
        self.assertEqual(v.detail["beams_from_strokes"]["boxes"][0]["support"], "unlinked")

    def test_flag_ON_a_CV_stroke_the_map_agrees_with_is_never_removed_whatever_a_stray_box_says(self):
        v = dur(True, PAIR, cv=[BEAM], boxes=[((300, 100, 300, 40), [])])
        # the stray box overlaps the CV stroke's x-range, so `_kept_beams` never kept it: the CV stroke alone decides
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))


class TestTwoBeamLevels(unittest.TestCase):
    TWO_LEVELS = [dict(stem_stroke(0), touches=[2, 3]), dict(stem_stroke(1), touches=[2, 3]),
                  beam_stroke([0, 1]), beam_stroke([0, 1], box=(251, 690, 364, 50), thick=0.5)]

    def test_both_levels_counted_by_the_old_readers_agree_with_the_strokes_and_decide_a_sixteenth(self):
        v = dur(True, self.TWO_LEVELS, cv=[BEAM, (251, 690, 364, 50)])
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 2))
        self.assertEqual(v.detail["beams_from_strokes"]["settled"], "agrees")
        self.assertEqual(sorted(v.detail["beams_from_strokes"]["tip"]["beams"]), [2, 3])

    def test_a_second_beam_shaped_stroke_no_old_reader_counted_is_a_CANDIDATE_only_RED(self):
        v = dur(True, self.TWO_LEVELS, cv=[BEAM])
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(levels(v), [1, 2])
        self.assertEqual(v.detail["beams_from_strokes"]["settled"], "stroke_candidate")
        # twin: flag off, the same cell decides one level (the readers saw one)
        off = dur(False, self.TWO_LEVELS, cv=[BEAM])
        self.assertEqual((off.outcome, off.value["beam_levels"]), (Outcome.DECIDED, 1))

    def test_two_strokes_closer_than_a_beam_gap_are_one_level(self):
        s = [dict(stem_stroke(0), touches=[2, 3]), dict(stem_stroke(1), touches=[2, 3]),
             beam_stroke([0, 1]), beam_stroke([0, 1], box=(251, 770, 364, 50))]
        v = dur(True, s, cv=[BEAM])
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))

    def test_the_old_readers_counting_more_than_the_strokes_is_a_disagreement_narrowed_not_an_argmax(self):
        # CV says two levels, the map has one stroke at the tip: [1, 2] with the readers' two kept as the candidate
        v = dur(True, PAIR, cv=[BEAM, (251, 690, 364, 50)])
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(levels(v), [1, 2])
        self.assertEqual(v.detail["beams_from_strokes"]["settled"], "disagree_narrowed")
        off = dur(False, PAIR, cv=[BEAM, (251, 690, 364, 50)])
        self.assertEqual((off.outcome, off.value["beam_levels"]), (Outcome.DECIDED, 2))      # twin: today the readers' two decide

    def test_the_stroke_map_without_this_heads_stem_says_nothing(self):
        s = [beam_stroke([]), ]
        v = dur(True, s, cv=[BEAM], boxes=[(BEAM, [0])])
        self.assertNotIn("beams_from_strokes", v.detail)
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))


class TestTheControlCanFail(unittest.TestCase):
    """CLAUDE rule 7: the hook/beam test must be able to fail. Break the cut and the RED flag test turns; restore it and it passes."""

    TWO = TestAFlagBoxedAsABeam.TWO

    def run_flag_case(self):
        return dur(True, self.TWO, boxes=[((251, 690, 110, 110), [1, 2])], heads=(0,))

    def test_with_the_cut_in_place_the_hooks_are_a_flag(self):
        self.assertEqual(self.run_flag_case().detail["beam_evidence"], "flag")

    def test_with_the_hook_cut_broken_the_same_cell_is_NOT_a_flag(self):
        with mock.patch.object(BS, "HOOK_MAX_SPACES", 0.1), mock.patch.object(BS, "HOOK_NEAR_MISS_SPACES", 0.1):
            v = self.run_flag_case()
        self.assertNotEqual(v.detail["beam_evidence"], "flag")
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_with_the_beam_thickness_cut_broken_a_thin_slur_is_taken_for_a_beam(self):
        thin = [dict(stem_stroke(0), touches=[2]), dict(stem_stroke(1), touches=[2]), beam_stroke([0, 1], thick=0.25)]
        with mock.patch.object(BS, "BEAM_MIN_THICKNESS_SP", 0.1):
            v = dur(True, thin, boxes=[(BEAM, [2])])
        self.assertEqual(v.outcome, Outcome.DECIDED)        # the broken cut lets the slur support the box; at 0.5 it narrows (above)


class TestOtherGuards(unittest.TestCase):

    def test_a_hollow_head_is_never_beamed_so_the_block_does_not_run(self):
        log, g = build(PAIR, boxes=[((300, 100, 300, 40), [])], heads=(0,))
        # re-class the head as a half
        log2 = Log()
        _staff_space(log2, SP)
        h = _head(log2, 0, (235, 355, 135, 142), cls="noteheadHalf")
        _real_stem(log2, (STEM_X[0], STEM_TOP, 31, TIP - STEM_TOP))
        with mock.patch.dict(os.environ, {FLAG: "1"}):
            adjudicate.run(log2)
        v = log2.verdict(Q.DURATION, h)
        self.assertNotIn("beams_from_strokes", v.detail)

    def test_the_flag_is_an_allow_list(self):
        for val, want in (("1", True), ("true", True), ("on", True), ("", False), ("0", False), ("yes please", False), ("off", False)):
            with mock.patch.dict(os.environ, {FLAG: val}):
                self.assertEqual(rhythm.beams_from_strokes_enabled(), want, val)


if __name__ == "__main__":
    unittest.main()
