"""ROADMAP 2.201: one accidental family -- the TYPE from the mark's own strokes, the extent grown along them. Synthetic marks of KNOWN geometry
(a natural: two stems, the right one LOWER; a sharp: two level stems and two bars; a flat: one stem and a bowl) drawn on a cell, run through the real
stroke map; every control below can FAIL (a mirrored natural, a level natural, a box that cuts a stem, a stem fused to a note stem, a stem a head owns)."""
import os
import unittest
from unittest import mock

import cv2
import numpy as np

from tools.omr.staged import accidental_family as AF
from tools.omr.staged import gather as G
from tools.omr.staged import stroke_map as SM
from tools.omr.tests.test_stroke_map_2_195 import LINES, SP, _cell


def _stem(img, x, y0, y1, w=20):
    img[y0:y1, x - w // 2:x + w // 2] = 0


def _bar(img, p, q, t=24):
    cv2.line(img, p, q, 0, t)


def _natural(img, x=400, top=400, right_drop=80, stems=240):
    """left stem top..top+stems; right stem right_drop lower; two slanted bars between them."""
    _stem(img, x, top, top + stems)
    _stem(img, x + 60, top + right_drop, top + right_drop + stems)
    _bar(img, (x, top + 170), (x + 60, top + 140), 22)
    _bar(img, (x, top + 245), (x + 60, top + 215), 22)


def _sharp(img, x=400, top=400, right_drop=-10, stems=300):
    _stem(img, x, top, top + stems)
    _stem(img, x + 60, top + right_drop, top + right_drop + stems)
    _bar(img, (x - 15, top + 130), (x + 75, top + 100), 24)
    _bar(img, (x - 15, top + 210), (x + 75, top + 180), 24)


def _flat(img, x=400, top=400, stem=280):
    _stem(img, x, top, top + stem)
    cv2.ellipse(img, (x + 38, top + stem - 55), (38, 52), 0, -90, 90, 0, 22)


def _row(draw, box_fn=None, blocked=(), cls="accidentalFlat", rivals=(), **kw):
    img, raw = _cell()
    draw(img, **kw)
    res = SM.map_strokes(img, SP, LINES, raw)
    ys, xs = np.nonzero(img == 0)
    # the detector's box: the ink's own box, or a cut one
    ink_box = (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))
    box = box_fn(ink_box) if box_fn else ink_box
    shares = SM.strokes_in_box(res, box)
    return AF.family_row(cls, box, res.strokes, shares, float(SP), blocked=blocked, rivals=rivals), res, box, shares


class FamilyType(unittest.TestCase):
    def test_a_natural_reads_natural_whatever_the_detector_called_it(self):
        for cls in ("accidentalFlat", "accidentalSharp", "keyFlat"):
            fam = _row(_natural, cls=cls)[0]
            self.assertEqual(fam["type"], "natural", (cls, fam["features"]))
            self.assertEqual(fam["detector_class"], cls)          # the label is kept as a fact
        self.assertEqual(fam["features"]["n_stems"], 2)
        self.assertGreaterEqual(max(fam["features"]["stagger_top_sp"], fam["features"]["stagger_bottom_sp"]), AF.NATURAL_STAGGER_MIN_SP)

    def test_TWIN_a_sharp_reads_sharp_and_a_flat_reads_flat(self):
        sharp = _row(_sharp, cls="accidentalNatural")[0]
        self.assertEqual(sharp["type"], "sharp", sharp["features"])
        flat = _row(_flat, cls="accidentalNatural")[0]
        self.assertEqual(flat["type"], "flat", flat["features"])
        self.assertEqual(flat["features"]["n_stems"], 1)

    def test_CONTROL_the_stagger_is_the_measure_a_level_natural_is_a_sharp_and_a_mirrored_one_is_not_a_natural(self):
        level = _row(lambda img: _natural(img, right_drop=0))[0]
        self.assertEqual(level["type"], "sharp", level["features"])       # same drawing, the stagger removed: the type moves
        mirrored = _row(lambda img: _natural(img, right_drop=-80))[0]      # the right stem HIGHER: no printed accidental
        self.assertNotEqual(mirrored["type"], "natural", mirrored["features"])

    def test_the_band_between_the_cutoffs_is_unclear_not_a_guess(self):
        mid = _row(lambda img: _natural(img, right_drop=int(0.3 * SP)))[0]
        self.assertEqual(mid["type"], "unclear", mid["features"])
        self.assertEqual(mid["why"], "stagger_between_cutoffs")
        self.assertLess(mid["margin"], 0)

    def test_the_detectors_candidates_are_kept_in_the_family_only(self):
        fam = _row(_natural, cls="accidentalFlat", rivals=("accidentalSharp", "accidentalDoubleSharp", "rest8th"))[0]
        self.assertEqual(fam["candidates"], ["flat", "sharp"])           # a double is the same type; a non-accidental is never a candidate
        self.assertFalse(fam["agrees_with_detector"])

    def test_no_stem_is_unclear(self):
        def blob(img):
            cv2.circle(img, (400, 500), 40, 0, -1)
        self.assertIn(_row(blob)[0]["type"], ("unclear", "unread"))


class FamilyExtent(unittest.TestCase):
    def _cut(self, ink):                       # the box stops short: keeps the top 2.0 spaces of the 3.2 the natural is tall
        return (ink[0], ink[1], ink[2], ink[1] + 2.0 * SP)

    def test_a_box_that_cuts_the_lower_stem_is_grown_and_still_reads_natural(self):
        fam, res, box, shares = _row(_natural, box_fn=self._cut)
        self.assertTrue(fam["grown"], fam["grown_sp"])
        self.assertGreater(fam["grown_sp"]["down"], 0.5)
        self.assertEqual(fam["type"], "natural", fam["features"])

    def test_CONTROL_without_the_growth_the_same_box_does_not_read_natural(self):
        fam, res, box, shares = _row(_natural, box_fn=self._cut)
        inside = [i for i, s in shares if s >= AF.COVER_SHARE_MIN]
        t = AF.read_type(res.strokes, inside, float(SP))
        self.assertNotEqual(t["type"], "natural", t)         # the cut box alone: one whole stem and a stub, i.e. the "flat" Sean saw

    def test_a_stem_fused_to_a_note_stem_is_not_the_marks_to_grow_along(self):
        def fused(img):
            _natural(img)
            _stem(img, 460, 640, 1000)                       # the right stem runs on into a note stem: one 6.0-space stroke
        fam, res, box, shares = _row(fused, box_fn=self._cut)
        self.assertLess(fam["grown_sp"]["down"], 1.0)          # only the left stem's own 0.6 space past the cut: the fused stroke is not followed
        self.assertEqual(fam["type"], "unclear", fam["features"])   # and a lone stem is NOT read as a flat while a second vertical is refused
        self.assertEqual(fam["why"], "second_stem_fused_or_owned")

    def test_a_stem_a_head_owns_is_never_grown_along(self):
        fam0, res, box, shares = _row(_natural, box_fn=self._cut)
        right = max((i for i in fam0["members"] if res.strokes[i].kind == "vertical"), key=lambda i: res.strokes[i].box[0])
        self.assertGreater(fam0["grown_sp"]["down"], 0.5)
        fam1 = AF.family_row("accidentalFlat", box, res.strokes, shares, float(SP), blocked=[right])     # a head owns the right stem
        self.assertLess(fam1["grown_sp"]["down"], 1.0)
        self.assertEqual(fam1["type"], "unclear", fam1["features"])

    def test_an_uncut_box_does_not_grow(self):
        fam = _row(_natural)[0]
        self.assertFalse(fam["grown"])


class FamilyGuess(unittest.TestCase):
    def _fam(self, t, det, cands, cls=None):
        return {"type": t, "detector_type": det, "detector_class": cls or {"flat": "accidentalFlat", "sharp": "accidentalSharp", "natural": "accidentalNatural"}.get(det, "accidentalFlat"),
                "candidates": cands, "margin": 0.3, "why": "x"}

    def test_agreement_with_one_detector_class_is_not_a_guess(self):
        self.assertIsNone(AF.guess_of(self._fam("flat", "flat", ["flat"])))

    def test_CONTROL_every_other_case_is_written_guessed(self):
        g = AF.guess_of(self._fam("natural", "flat", ["flat"]))
        self.assertEqual(g["chosen"]["value"], "natural")
        self.assertEqual([c["value"] for c in g["candidates"]], ["natural", "flat"])
        self.assertIsNotNone(AF.guess_of(self._fam("flat", "flat", ["flat", "natural"])))          # the detector offered two
        self.assertIsNotNone(AF.guess_of(self._fam("flat", "flat", ["flat"], cls="keyFlat")))       # a key* label: the role came from position
        u = AF.guess_of(self._fam("unclear", "flat", ["flat", "sharp"]))
        self.assertEqual(u["chosen"]["value"], "flat")                                              # the detector's candidate stands, flagged
        self.assertIsNone(AF.guess_of(None))

    def test_nothing_reads(self):
        self.assertFalse(AF.reads(5.0))                       # READ_MARGIN is Sean's to set


class FamilyFlag(unittest.TestCase):
    def test_default_off_and_allow_list(self):
        for v, want in ((None, False), ("", False), ("0", False), ("typo", False), ("1", True), ("true", True), ("on", True)):
            with mock.patch.dict(os.environ, {AF.ENV: v} if v is not None else {}, clear=False):
                if v is None:
                    os.environ.pop(AF.ENV, None)
                self.assertEqual(AF.enabled(), want, v)

    def test_family_classes_are_both_series_and_only_accidentals(self):
        for c in ("accidentalFlat", "accidentalDoubleSharp", "keyFlat", "keyNatural", "keySharp"):
            self.assertTrue(AF.is_family_class(c), c)
        for c in ("keyboardPedalUp", "noteheadBlack", "rest8th", "clefG"):
            self.assertFalse(AF.is_family_class(c), c)


class _Det:
    category = "accidental"
    confidence = 0.8

    def __init__(self, name, x, y, w, h):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = name, x, y, w, h


class FamilyGather(unittest.TestCase):
    """`gather_accidental_family` end to end on a synthetic cell, and the OFF parity of its two consumers."""

    def _cell(self, draw):
        img, raw = _cell()
        draw(img)

        class C:
            page_index, system_index, staff_index, measure_index = 0, 0, 0, 0
            staff_line_ys_canonical = LINES
            upscale_factor = 1.0
            bbox_page_px = (0, 0, 1400, 1000)
        C.image_no_staff, C.binary = img, raw
        return C()

    def test_flag_off_files_nothing_and_on_sets_the_family_on_the_detection(self):
        c = self._cell(_natural)
        res = SM.map_strokes(c.image_no_staff, SP, LINES, c.binary)
        det = _Det("accidentalFlat", 390, 390, 100, 330)
        key = {"cell": (0, 0, 0, 0)}
        from tools.omr.staged import record as R
        dets = {R.cell(0, 0, 0, 0).to_key(): [det]}
        with mock.patch.dict(os.environ, {AF.ENV: "0", G.STROKE_MAP_ENV: "1"}):
            self.assertEqual(G.gather_accidental_family([c], {0: (0, 0)}, dets, {(0, 0, 0, 0): res}), 0)
        self.assertFalse(hasattr(det, "accidental_family"))
        with mock.patch.dict(os.environ, {AF.ENV: "1", G.STROKE_MAP_ENV: "0"}):
            self.assertEqual(G.gather_accidental_family([c], {0: (0, 0)}, dets, {(0, 0, 0, 0): res}), 0)     # needs the stroke map
        with mock.patch.dict(os.environ, {AF.ENV: "1", G.STROKE_MAP_ENV: "1"}):
            self.assertEqual(G.gather_accidental_family([c], {0: (0, 0)}, dets, {(0, 0, 0, 0): res}), 1)
        self.assertEqual(det.accidental_family["type"], "natural")
        self.assertEqual(det.accidental_family["detector_class"], "accidentalFlat")
        self.assertIsNone(det.accidental_family["head_right"])

    def test_a_head_directly_right_at_the_marks_height_makes_it_in_bar(self):
        c = self._cell(_natural)
        res = SM.map_strokes(c.image_no_staff, SP, LINES, c.binary)
        det = _Det("accidentalFlat", 390, 390, 100, 330)
        head = _Det("noteheadBlack", 520, 510, 130, 100)
        head.category = "notehead"
        from tools.omr.staged import record as R
        dets = {R.cell(0, 0, 0, 0).to_key(): [det, head]}
        with mock.patch.dict(os.environ, {AF.ENV: "1", G.STROKE_MAP_ENV: "1"}):
            G.gather_accidental_family([c], {0: (0, 0)}, dets, {(0, 0, 0, 0): res})
        self.assertIsNotNone(det.accidental_family["head_right"])
        far = _Det("noteheadBlack", 900, 510, 130, 100)
        far.category = "notehead"
        dets = {R.cell(0, 0, 0, 0).to_key(): [det, far]}
        with mock.patch.dict(os.environ, {AF.ENV: "1", G.STROKE_MAP_ENV: "1"}):
            G.gather_accidental_family([c], {0: (0, 0)}, dets, {(0, 0, 0, 0): res})
        self.assertIsNone(det.accidental_family["head_right"])            # CONTROL: the same mark with its head three spaces off is not in-bar


# ───────────────────────── ADJUDICATE + EXPORT, on the record rows GATHER files ─────────────────────────

from tools.omr.staged import export as E                      # noqa: E402
from tools.omr.staged import record as R                      # noqa: E402
from tools.omr.staged.record import Log, Q, READERS           # noqa: E402
from tools.omr.tests import test_staged_accidental as TA      # noqa: E402


def _fam(t, det_class, cands, *, why="x", margin=0.3, head_right=None):
    return {"type": t, "why": why, "margin": margin, "features": {}, "grown": False, "grown_sp": {"up": 0.0, "down": 0.0},
            "detector_class": det_class, "detector_type": AF.type_of_class(det_class), "candidates": cands,
            "agrees_with_detector": (t == AF.type_of_class(det_class)) if t in AF.TYPES else None, "head_right": head_right}


def _acc_row(log, gi, x, position, cls, alteration, family=None, w=12.0):
    """The position row GATHER files; `family` is the 2.201 detail (None = the flag OFF, exactly the row main files)."""
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, (cls, x - w, position * TA.HALF - TA.SPACE, w, TA.SPACE * 2), reader=READERS.DETECTOR, frame="cell:0",
                score=0.8, category="accidental")
    log.observe(g, Q.ACCIDENTAL_STAFF_POSITION, float(position), reader=READERS.GEOMETRY, frame="cell:0", alteration=alteration,
                detector_class=cls, anchor_fraction=0.5, box_centre_position=float(position), residual=0.0, rounded=int(round(position)),
                x0=x - w, x1=x, y0=position * TA.HALF - TA.SPACE, y1=position * TA.HALF + TA.SPACE, confidence=0.8,
                **({"family": family} if family else {}))
    return g


def _file(family, cls="accidentalFlat", alteration="natural"):
    log = Log()
    TA._cell_unit(log)
    _acc_row(log, 0, 100.0, 7.0, cls, alteration, family)
    TA._head(log, 1, 106.0, 7.0)
    TA._durations(log, 1)
    xml, report = E.to_musicxml(TA._full(TA._decide(log)))
    return log, xml, report


class FamilyAdjudicateExport(unittest.TestCase):
    def test_a_clear_family_type_is_written_with_its_alteration_and_blue(self):
        fam = _fam("natural", "accidentalFlat", ["flat"])
        log, xml, report = _file(fam)
        v = log.verdict(Q.ACCIDENTAL_OWNER, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.detail["alteration"], "natural")
        self.assertEqual(v.detail["family"]["type"], "natural")
        self.assertIn("<accidental>natural</accidental>", xml)
        self.assertIn('color="%s"' % E.GUESS_COLOR, xml)                   # the strokes changed the detector's type: GUESSED
        self.assertIn("accidental_family", xml)                            # the rule is named in the machine-readable carrier

    def test_TWIN_agreement_with_a_lone_detector_class_is_not_blue(self):
        fam = _fam("flat", "accidentalFlat", ["flat"])
        _log, xml, _r = _file(fam, alteration="b")
        self.assertIn("<accidental>flat</accidental>", xml)
        self.assertNotIn('color="%s"' % E.GUESS_COLOR, xml)

    def test_TWIN_the_flag_off_row_has_no_family_and_is_written_as_main_writes_it(self):
        _log, xml, _r = _file(None, alteration="b")
        self.assertIn("<accidental>flat</accidental>", xml)
        self.assertNotIn('color="%s"' % E.GUESS_COLOR, xml)

    def test_an_unclear_type_keeps_the_detectors_candidate_and_is_blue(self):
        fam = _fam("unclear", "accidentalFlat", ["flat", "sharp"], why="stagger_between_cutoffs", margin=-0.1)
        log, xml, _r = _file(fam, alteration="b")
        self.assertEqual(log.verdict(Q.ACCIDENTAL_OWNER, R.glyph(0, 0, 0, 0, 0)).detail["alteration"], "b")
        self.assertIn("<accidental>flat</accidental>", xml)
        self.assertIn('color="%s"' % E.GUESS_COLOR, xml)

    def test_a_key_class_box_after_the_signature_is_an_in_bar_accidental_by_position_and_is_blue(self):
        fam = _fam("flat", "keyFlat", ["flat"])
        log, xml, _r = _file(fam, cls="keyFlat", alteration="b")
        self.assertEqual(log.verdict(Q.ACCIDENTAL_OWNER, R.glyph(0, 0, 0, 0, 0)).outcome, "decided")
        self.assertIn("<accidental>flat</accidental>", xml)
        self.assertIn('color="%s"' % E.GUESS_COLOR, xml)

    def test_the_clear_type_replaces_the_corner_check(self):
        """With a clear family type 2.190's corner reader is not consulted (it read the same ink through a box that can cut it)."""
        row_shape = {"bl": 0.9, "tr": 0.9, "shape": "sharp"}          # a corner reading that would say sharp
        log = Log()
        TA._cell_unit(log)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.GLYPH_BOX, ("accidentalFlat", 88.0, 7 * TA.HALF - TA.SPACE, 12.0, TA.SPACE * 2), reader=READERS.DETECTOR, frame="cell:0",
                    score=0.8, category="accidental")
        log.observe(g, Q.ACCIDENTAL_STAFF_POSITION, 7.0, reader=READERS.GEOMETRY, frame="cell:0", alteration="natural", detector_class="accidentalFlat",
                    anchor_fraction=0.504, box_centre_position=7.0, residual=0.0, rounded=7, x0=88.0, x1=100.0, y0=7 * TA.HALF - TA.SPACE,
                    y1=7 * TA.HALF + TA.SPACE, confidence=0.8, shape=row_shape, family=_fam("natural", "accidentalFlat", ["flat"]),
                    one_ink={"rivals": [{"class": "accidentalSharp", "conf": 0.5}], "margin": 0.3, "winner": {"class": "accidentalFlat", "conf": 0.8}, "iou_min": 0.5})
        TA._head(log, 1, 106.0, 7.0)
        with mock.patch.dict(os.environ, {"OMR_ONE_INK_ONE_MARK": "1", "OMR_ACCIDENTAL_SHAPE": "1"}):
            TA._decide(log)
        v = log.verdict(Q.ACCIDENTAL_OWNER, g)
        self.assertEqual(v.detail["alteration"], "natural")
        self.assertNotIn("shape_check", v.detail)


class FamilyPositionRow(unittest.TestCase):
    """`gather_accidental_positions` with and without `d.accidental_family` (what `gather_accidental_family` sets)."""

    def _rows(self, dets):
        log = Log()
        G.gather_accidental_positions(log, [TA._Cell()], {0: (0, 0)}, {R.cell(0, 0, 0, 0).to_key(): dets})
        return log.rows(Q.ACCIDENTAL_STAFF_POSITION, R.cell(0, 0, 0, 0), scope=R.Scope.SELF_AND_DESCENDANTS)

    def test_the_family_type_names_the_alteration_and_its_anchor_and_the_label_stays_a_fact(self):
        d = TA._Det("accidentalFlat", 100.0, 0.0, 12.0, 40.0)
        d.accidental_family = {**_fam("natural", "accidentalFlat", ["flat"]), "box": [96.0, -10.0, 112.0, 50.0], "anchor_fraction": 0.504}
        (row,) = self._rows([d])
        self.assertEqual(row.detail["alteration"], "natural")
        self.assertEqual(row.detail["detector_class"], "accidentalFlat")
        self.assertEqual(row.detail["anchor_fraction"], 0.504)
        self.assertEqual((row.detail["x0"], row.detail["x1"], row.detail["y0"], row.detail["y1"]), (96.0, 112.0, -10.0, 50.0))   # the GROWN box
        self.assertEqual(row.detail["family"]["type"], "natural")
        self.assertAlmostEqual(row.value, (-10.0 + 60.0 * 0.504) / (TA.SPACE / 2.0), places=3)

    def test_CONTROL_without_the_family_the_row_is_exactly_the_detectors(self):
        d = TA._Det("accidentalFlat", 100.0, 0.0, 12.0, 40.0)
        (row,) = self._rows([d])
        self.assertEqual(row.detail["alteration"], "b")
        self.assertEqual(row.detail["anchor_fraction"], 0.715)
        self.assertNotIn("family", row.detail)
        self.assertEqual((row.detail["x0"], row.detail["x1"], row.detail["y0"], row.detail["y1"]), (100.0, 112.0, 0.0, 40.0))

    def test_a_key_class_box_gets_a_row_only_through_the_family(self):
        d = TA._Det("keyFlat", 100.0, 0.0, 12.0, 40.0)
        self.assertEqual(list(self._rows([d])), [])                              # main: key* boxes never get an accidental row
        d.accidental_family = {**_fam("flat", "keyFlat", ["flat"]), "box": [100.0, 0.0, 112.0, 40.0], "anchor_fraction": 0.715}
        (row,) = self._rows([d])
        self.assertEqual(row.detail["alteration"], "b")
        self.assertEqual(row.detail["detector_class"], "keyFlat")

    def test_an_unclear_family_keeps_the_detectors_class_geometry(self):
        d = TA._Det("accidentalSharp", 100.0, 0.0, 12.0, 40.0)
        d.accidental_family = {**_fam("unclear", "accidentalSharp", ["sharp"], why="no_stem"), "box": [100.0, 0.0, 112.0, 40.0], "anchor_fraction": 0.501}
        (row,) = self._rows([d])
        self.assertEqual(row.detail["alteration"], "#")
        self.assertEqual(row.detail["anchor_fraction"], 0.501)             # the class's own anchor: no type was read


if __name__ == "__main__":
    unittest.main()
