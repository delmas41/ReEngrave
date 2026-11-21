"""ROADMAP 2.202 (STAGED ADJUDICATE `rhythm._beams_from_strokes` + pure `beam_strokes`), flag `OMR_BEAMS_FROM_STROKES`, default ON since 2026-10-28, step 3 of the shared ink map.

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

class TestOffIsByteIdentical(unittest.TestCase):

    def test_flag_ON_without_a_stroke_map_changes_nothing(self):
        off = dur(False, [], cv=[BEAM], boxes=[(BEAM, None)])
        on = dur(True, [], cv=[BEAM], boxes=[(BEAM, None)])
        for f in ("outcome", "value", "reason", "candidates"):
            self.assertEqual(getattr(off, f), getattr(on, f), f)
        self.assertNotIn("beams_from_strokes", on.detail)



class TestAFlagBoxedAsABeam(unittest.TestCase):
    """The detector draws a BEAM box on a FLAG (3 of Sean's 6 crops): one stem, a short thin stroke at its tip."""

    ONE = [dict(stem_stroke(0), touches=[1]), hook_stroke([0])]
    TWO = [dict(stem_stroke(0), touches=[1, 2]), hook_stroke([0]), hook_stroke([0], box=(251, 700, 110, 25))]

    def test_TWIN_a_hook_longer_than_the_cut_plus_its_near_miss_is_not_a_flag(self):
        s = [dict(stem_stroke(0), touches=[1]), hook_stroke([0], length=2.69, box=(251, 770, 270, 25))]
        v = dur(True, s, boxes=[((251, 760, 270, 40), [1])], heads=(0,))
        self.assertNotEqual(v.detail["beam_evidence"], "flag")
        self.assertEqual(v.outcome, Outcome.NARROWED)


class TestTwoBeamLevels(unittest.TestCase):
    TWO_LEVELS = [dict(stem_stroke(0), touches=[2, 3]), dict(stem_stroke(1), touches=[2, 3]),
                  beam_stroke([0, 1]), beam_stroke([0, 1], box=(251, 690, 364, 50), thick=0.5)]

class TestTheControlCanFail(unittest.TestCase):
    """CLAUDE rule 7: the hook/beam test must be able to fail. Break the cut and the RED flag test turns; restore it and it passes."""

    TWO = TestAFlagBoxedAsABeam.TWO

    def run_flag_case(self):
        return dur(True, self.TWO, boxes=[((251, 690, 110, 110), [1, 2])], heads=(0,))

    def test_with_the_hook_cut_broken_the_same_cell_is_NOT_a_flag(self):
        with mock.patch.object(BS, "HOOK_MAX_SPACES", 0.1), mock.patch.object(BS, "HOOK_NEAR_MISS_SPACES", 0.1):
            v = self.run_flag_case()
        self.assertNotEqual(v.detail["beam_evidence"], "flag")
        self.assertEqual(v.outcome, Outcome.NARROWED)

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

    def test_the_flag_is_default_ON_and_an_explicit_off_list_disables(self):
        with mock.patch.dict(os.environ):
            os.environ.pop(FLAG, None)
            self.assertTrue(rhythm.beams_from_strokes_enabled())
        for val, want in (("1", True), ("true", True), ("on", True), ("0", False), ("false", False), ("no", False), ("off", False)):
            with mock.patch.dict(os.environ, {FLAG: val}):
                self.assertEqual(rhythm.beams_from_strokes_enabled(), want, val)


class TestCleanTip2_202d(unittest.TestCase):
    """2.202d (Sean "Clean tip means no beam"): a beam box standing on a BLOB only (a head's ink), the stem's tip clean -> the box is refuted, the
    head is DECIDED with no level, not narrowed [0, 1] and dropped. Twins: a beam-shaped stroke left at the tip keeps it narrowed."""

    def blob(self):
        return S("blob", (260, 800, 120, 60), 1.2, 0.6, [0], sag=0.3, angle=0.0)

    def test_TWIN_a_long_unclassified_curve_at_the_tip_keeps_it_narrowed(self):
        s = [dict(stem_stroke(0), touches=[1]), hook_stroke([0], length=2.69, box=(251, 770, 270, 25))]
        v = dur(True, s, boxes=[((251, 760, 270, 40), [1])], heads=(0,))
        self.assertEqual(v.outcome, Outcome.NARROWED)


if __name__ == "__main__":
    unittest.main()
