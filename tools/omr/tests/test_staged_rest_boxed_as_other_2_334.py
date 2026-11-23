"""ROADMAP 2.334 -- an eighth rest the detector boxes as something else is still a rest (STAGED ADJUDICATE, `OMR_REST_BOXED_AS_OTHER`).

"A box says where to look; the ink says the kind." A mark with an eighth rest's shape (a bulb at the top left and a stroke down to the
right), standing alone in the staff, is an eighth rest whatever the detector called it. NEVER a real accidental (a sharp, natural or flat
has a full-height stroke on its left; a double sharp is an x about one space tall) and never a clef (taller or wider than the window).

Every control is REAL: the fixture holds the GATHER rows filed on the 20261122-night records -- `gather_unboxed_rest_ink`'s measure of
the printed ink and the detector boxes standing on it -- for
  * missed motif rests (Litolff red bars; the rest's ink boxed `accidentalDoubleSharp` or `clefF`): OFF they are not read (the controls
    fail before the change), ON they are read as eighth rests and the double-sharp box is refused `eighth_rest_shaped_ink`;
  * read motif rests (a standing rest8th box, a clefF box beside it, or no box): read once, never a second rest;
  * real accidentals: Sean's claim tiles 2.285 r1/r2 (sharp, flat, natural ink) and flat/sharp/natural ink under its own box -- never
    refused, never a rest.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged.record import Log, Outcome, Q, READERS, Subject

FIX = json.loads((pathlib.Path(__file__).parent / "fixtures" / "rest_boxed_as_other_2_334.json").read_text())["cases"]
ORDER = (Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL, Q.UNBOXED_INK_IS_A_REST)


def _run(case, on: bool, own_box: str = None):
    """Replay one place. `own_box` (real-accidental tiles whose accidental box the detector filed in another cell): an accidental box of
    that class over the ink's own extent -- the question is whether such a box would give way, the ink is the real one."""
    with mock.patch.dict(os.environ, {"OMR_REST_BOXED_AS_OTHER": "1" if on else "0"}):
        log = Log()
        boxes = list(case["boxes"])
        if own_box:
            cell = "/".join(case["subject"].split("/")[:5])
            bb = case["shape"]["detail"]["bbox_page_px"]
            boxes.append(dict(subject=cell + "/990", value=[own_box, 0, 0, 1, 1], score=0.5,
                              detail=dict(bbox_page_px=bb, category="accidental")))
        for b in boxes:
            d = b["detail"]
            log.observe(Subject.from_key(b["subject"]), Q.GLYPH_BOX, tuple(b["value"]), reader=READERS.DETECTOR, frame="cell:0",
                        score=b.get("score"), category=d.get("category"), bbox_page_px=d.get("bbox_page_px"))
        sh = case["shape"]
        log.observe(Subject.from_key(case["subject"]), Q.UNBOXED_REST_SHAPE, sh["value"], reader=READERS.CV_UNBOXED_REST_SHAPE,
                    frame="cell:0", **sh["detail"])
        log.freeze()
        adjudicate._ensure_decisions()
        adjudicate.run(log, order=ORDER)
        rest = log.verdict(Q.UNBOXED_INK_IS_A_REST, Subject.from_key(case["subject"]))
        accs = {b["subject"]: log.verdict(Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL, Subject.from_key(b["subject"]))
                for b in boxes if (b["detail"].get("category") == "accidental")}
        return rest, accs


def _group(name):
    return [c for c in FIX.values() if c["group"] == name]


def _read_eighth(v):
    return v is not None and v.outcome is Outcome.DECIDED and v.value == "eighth"


class TestMissedRestsAreRead(unittest.TestCase):

    def test_controls_are_enough(self):
        self.assertGreaterEqual(len(_group("missed_dsharp")) + len(_group("missed_clef")), 6)
        self.assertGreaterEqual(len(_group("read")), 3)

    def test_off_the_missed_rests_stay_unread_RED(self):
        """The control that can fail: OFF (main) every missed motif rest is `already_read_as_a_glyph` -- not read."""
        for c in _group("missed_dsharp") + _group("missed_clef"):
            rest, _ = _run(c, on=False)
            self.assertFalse(_read_eighth(rest), c["subject"])

    def test_on_a_double_sharp_box_gives_way_and_the_rest_is_read(self):
        for c in _group("missed_dsharp"):
            rest, accs = _run(c, on=True)
            self.assertTrue(_read_eighth(rest), (c["subject"], rest and rest.reason))
            self.assertTrue(accs)
            for s, v in accs.items():
                self.assertIs(v.outcome, Outcome.DECIDED, s)
                self.assertIs(v.value, True, s)
                self.assertEqual(v.reason, "eighth_rest_shaped_ink", s)

    def test_on_an_f_clef_box_gives_way_and_the_rest_is_read(self):
        for c in _group("missed_clef"):
            rest, _ = _run(c, on=True)
            self.assertTrue(_read_eighth(rest), (c["subject"], rest and rest.reason))
            self.assertIn("boxed_as_other", rest.detail)


class TestReadRestsStayOnce(unittest.TestCase):

    def test_a_rest_box_on_the_ink_is_never_doubled(self):
        """A rest8th box standing on the ink (alone, or beside a clefF box) reads the rest: the ink reader never adds a second one."""
        for c in _group("read"):
            has_rest_box = any(str(b["value"][0]).startswith("rest") for b in c["boxes"])
            for on in (False, True):
                rest, _ = _run(c, on=on)
                if has_rest_box:
                    self.assertFalse(_read_eighth(rest), (c["subject"], on))
                    self.assertEqual(rest.reason, "already_read_as_a_glyph", (c["subject"], on))
                else:
                    self.assertTrue(_read_eighth(rest), (c["subject"], on))


class TestRealAccidentalsStay(unittest.TestCase):

    def test_seans_judged_accidentals_never_give_way(self):
        kinds = {"brahms:glyph/14/0/3/5/350000": "accidentalSharp", "brahms:glyph/19/1/5/3/350000": "accidentalSharp",
                 "brahms:glyph/19/0/3/9/350000": "accidentalFlat", "litolff:glyph/8/0/7/6/350000": "accidentalFlat",
                 "litolff:glyph/2/1/9/5/350000": "accidentalFlat", "brahms:glyph/14/0/2/1/350000": "accidentalNatural",
                 "brahms:glyph/14/1/1/8/350001": "accidentalNatural"}
        for key, c in FIX.items():
            if c["group"] != "real_accidental":
                continue
            for cls in (kinds[key], "accidentalDoubleSharp"):
                rest, accs = _run(c, on=True, own_box=cls)
                self.assertFalse(_read_eighth(rest), (key, cls))
                for s, v in accs.items():
                    self.assertIs(v.value, False, (key, cls, v.reason))

    def test_boxed_accidental_ink_never_gives_way(self):
        for c in _group("boxed_accidental"):
            rest, accs = _run(c, on=True)
            self.assertFalse(_read_eighth(rest), c["subject"])
            for s, v in accs.items():
                self.assertIs(v.value, False, (s, v.reason))


if __name__ == "__main__":
    unittest.main()
