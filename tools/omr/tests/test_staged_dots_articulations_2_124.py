"""ROADMAP 2.124 / 2.125 -- the dot ledger, the staccato family and the
LilyPond measure rest on a carried meter.

STAGED only. Each class was run RED against the tree before the fix:

* 2.124: Litolff 20261013-night read `dot_role_balance` 601 != 15 + 364 + 241.
  The 19 extra were the staccato marks `_condensed_double` copied onto the
  Contrabass copy of a condensed `Violoncello e Basso` staff:
  `_CONDENSED_STRIP_KEYS` was written before 2.12c added
  `dot_role_articulations`, so the copy carries the staccato, the render
  counts it, and the log counted that dot ONCE.
* 2.125: 465 Litolff / 2,838 Brahms `artic*` boxes had "no verdict" in the
  2.118 funnel because `FAMILIES["articulation"]` claims the `artic` prefix --
  which includes `articStaccato*`, whose ONLY meaning is `Q.DOT_ROLE`.
  Brahms 4,101 - 1,263 `Q.ARTICULATION_MARK` rows = 2,838 = its staccato
  boxes exactly; Litolff 465 - 18 = 447 = 152 + 295.
* 2.125 (LilyPond): Brahms warnings 93 -> 445 were 199 `barcheck failed` and
  120 `mid-measure time signature` from `r1 |` written for a decided
  whole-bar rest on a bar whose OWN system declared no meter
  (`_Bar("empty", meter, ...)` -- `meter` is None there; `judged` is the
  meter in force). The red brackets caused none of them.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as LY
from tools.omr.staged.record import Q
from tools.omr.tests.test_staged_export import (
    _add_rest,
    _condensed_cello_bass_page,
    _obs,
    _one_staff_page,
    _vrd,
)

_HAS_LILYPOND = shutil.which("lilypond") is not None
_4_4 = {"numerator": 4, "denominator": 4, "raw": "4/4"}
_WHOLE = {"beats": 4.0, "written": 4.0, "dots": 0}


def _with_staccato(page, *, owner_gi=0, n=1, cls="articStaccatoAbove"):
    """`n` staccato-role dots owned by the notehead `owner_gi`."""
    owner = f"glyph/0/0/0/0/{owner_gi}"
    for k in range(n):
        sub = f"glyph/0/0/0/0/{900 + k}"
        page["record"]["observations"].append(
            _obs(900 + k, sub, Q.GLYPH_BOX, [cls, 100 * owner_gi + 10, 5, 8, 8],
                 category="articulation"))
        page["record"]["observations"].append(
            _obs(950 + k, sub, Q.AUG_DOT, [104.0, 46.0],
                 detector_role="staccato", detector_class=cls))
        v = _vrd(950 + k, sub, Q.DOT_ROLE, "staccato",
                 reason="centred_and_offset_from_a_head")
        v["detail"] = {"owner": owner, "articulation": "staccato"}
        page["record"]["verdicts"].append(v)
    return page


class TestDotRoleBalanceOnACondensedStaff(unittest.TestCase):
    """2.124. The doubled Contrabass copy writes the staccato a second time;
    the log counted the dot once, so the equality needs the copy in its own
    named bucket -- exactly as `notes_doubled_to_condensed_slot` and
    `accidentals_printed_on_a_doubled_copy` already do."""

    def test_the_balance_holds_when_the_copy_carries_the_staccato(self):
        page = _with_staccato(_condensed_cello_bass_page(
            extra_notes_on_cello=1))
        _xml, rep = SX.to_musicxml(page)
        b = rep["dot_role_balance"]
        self.assertEqual(b["population"], 1)
        self.assertEqual(b["written_staccato"], 1, b)
        self.assertTrue(b["balanced"], b)

    def test_the_copy_is_named_not_hidden(self):
        page = _with_staccato(_condensed_cello_bass_page(
            extra_notes_on_cello=1), n=2)
        xml, rep = SX.to_musicxml(page)
        b = rep["dot_role_balance"]
        self.assertEqual(b["population"], 2)
        self.assertEqual(b["written_staccato_on_a_doubled_copy"], 2, b)
        self.assertTrue(b["balanced"], b)
        # the FILE is unchanged by the fix: the copy still wears its staccato
        self.assertEqual(xml.count("<staccato/>"), 4)

    def test_a_plain_staff_reports_no_doubled_copy(self):
        page = _with_staccato(_one_staff_page(
            notes=[("C4", _WHOLE)], meter=_4_4))
        _xml, rep = SX.to_musicxml(page)
        b = rep["dot_role_balance"]
        self.assertEqual(b["written_staccato_on_a_doubled_copy"], 0)
        self.assertEqual(b["written_staccato"], 1)
        self.assertTrue(b["balanced"], b)


class TestAStaccatoBoxHasAFamily(unittest.TestCase):
    """2.125. Every `articStaccato*` / `augmentationDot` box is a `Q.DOT_ROLE`
    subject; the `articulation` family must not count them as ink it never
    asked about."""

    def _coverage(self):
        page = _with_staccato(_one_staff_page(
            notes=[("C4", _WHOLE)], meter=_4_4), n=3)
        sub = "glyph/0/0/0/0/800"
        page["record"]["observations"].append(
            _obs(800, sub, Q.GLYPH_BOX, ["articAccentAbove", 100, 5, 8, 8],
                 category="articulation"))
        page["record"]["observations"].append(
            _obs(801, sub, Q.ARTICULATION_MARK, "articAccentAbove"))
        dsub = "glyph/0/0/0/0/810"
        page["record"]["observations"].append(
            _obs(810, dsub, Q.GLYPH_BOX, ["augmentationDot", 150, 50, 8, 8],
                 category="dot"))
        page["record"]["observations"].append(
            _obs(811, dsub, Q.AUG_DOT, [154.0, 54.0],
                 detector_role="dot", detector_class="augmentationDot"))
        page["record"]["verdicts"].append(
            _vrd(811, dsub, Q.DOT_ROLE, None, outcome="abstained",
                 reason="dot_role_ambiguous"))
        _xml, rep = SX.to_musicxml(page)
        rows = {r["family"]: r for r in SX.coverage(
            page, rep["written"])["families"]}
        return rows, rep

    def test_the_articulation_family_counts_only_what_it_decides(self):
        rows, _rep = self._coverage()
        self.assertEqual(rows["articulation"]["detector_glyphs"], 1, rows)

    def test_the_dot_family_counts_every_dot_role_box(self):
        rows, rep = self._coverage()
        dot = rows["dot"]
        self.assertEqual(dot["detector_glyphs"], 4, dot)
        self.assertEqual(dot["quantity"], Q.DOT_ROLE)
        self.assertEqual(dot["decided"], 3, dot)
        self.assertEqual(dot["written"], 3, dot)
        self.assertEqual(dot["detector_glyphs"],
                         rep["dot_role_balance"]["population"])

    def test_no_detected_class_is_left_unclaimed(self):
        page = _with_staccato(_one_staff_page(
            notes=[("C4", _WHOLE)], meter=_4_4))
        _xml, rep = SX.to_musicxml(page)
        cov = SX.coverage(page, rep["written"])
        self.assertNotIn("articStaccatoAbove", cov["unclaimed_classes"])
        self.assertNotIn("augmentationDot", cov["unclaimed_classes"])


def _two_system_page_with_a_carried_meter():
    """System 0 declares 6/8 and holds a dotted-half note; system 1 declares
    NO meter (it is carried) and holds a decided whole-bar rest."""
    page = _one_staff_page(
        notes=[("C4", {"beats": 3.0, "written": 3.0, "dots": 1})],
        meter={"numerator": 6, "denominator": 8, "raw": "6/8"})
    v = page["record"]["verdicts"]
    v.append(_vrd(910, "staff/0/1/0", Q.MEASURE_PARTITION, 1))
    v.append(_vrd(911, "staff/0/1/0", Q.CLEF, "treble"))
    v.append(_vrd(912, "system/0/1", Q.SYSTEM_STAFF_COUNT, 1))
    sub = "glyph/0/1/0/0/5"
    page["record"]["observations"].append(
        _obs(620, sub, Q.GLYPH_BOX, ["restWhole", 300, 50, 20, 30],
             category="rest"))
    page["record"]["observations"].append(
        _obs(720, sub, Q.REST, "restWhole", category="rest"))
    v.append(_vrd(820, sub, Q.DURATION,
                  {"measure_rest": True, "beats": 3.0, "written": 3.0}))
    return page


def _compile(text):
    with tempfile.TemporaryDirectory() as d:
        ly = Path(d) / "score.ly"
        ly.write_text(text)
        return subprocess.run(["lilypond", "-s", "--output", d, str(ly)],
                              capture_output=True, text=True, timeout=120)


class TestAWholeBarRestOnACarriedMeterIsSizedByTheMeterInForce(unittest.TestCase):
    """2.125 (LilyPond warnings). `r1` in a 6/8 bar overflows it: LilyPond
    reports `barcheck failed` there and `mid-measure time signature` at the
    next `\\time`. The MusicXML twin already sized this bar by `judged`.
    `OMR_LILY_CARRIED_METER_REST` is default ON (Sean 2026-10-14)."""

    def test_the_rest_is_a_bar_of_the_meter_in_force(self):
        with mock.patch.dict(os.environ, {LY.CARRIED_METER_REST_ENV: "1"}):
            text, _rep = LY.to_lilypond(
                _two_system_page_with_a_carried_meter())
        flat = [l.strip() for l in text.split("\n")]
        self.assertNotIn("r1 |", flat, text)
        self.assertIn("r2. |", flat, text)

    def test_default_is_on(self):
        env = {k: v for k, v in os.environ.items()
               if k != LY.CARRIED_METER_REST_ENV}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertTrue(LY.carried_meter_rest_enabled())
            text, _rep = LY.to_lilypond(
                _two_system_page_with_a_carried_meter())
        self.assertIn("r2. |", [l.strip() for l in text.split("\n")])

    def test_explicit_off_leaves_the_file_as_it_was(self):
        with mock.patch.dict(os.environ, {LY.CARRIED_METER_REST_ENV: "0"}):
            self.assertFalse(LY.carried_meter_rest_enabled())
            text, _rep = LY.to_lilypond(
                _two_system_page_with_a_carried_meter())
        self.assertIn("r1 |", [l.strip() for l in text.split("\n")])

    @unittest.skipUnless(_HAS_LILYPOND, "lilypond not on PATH")
    def test_the_file_compiles_without_a_barcheck_warning(self):
        with mock.patch.dict(os.environ, {LY.CARRIED_METER_REST_ENV: "1"}):
            text, _rep = LY.to_lilypond(
                _two_system_page_with_a_carried_meter())
        proc = _compile(text)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("barcheck", proc.stderr)

    def test_a_bar_with_no_meter_anywhere_is_untouched(self):
        page = _one_staff_page(notes=[], n_measures=1, meter=None)
        _add_rest(page, gi=5, cls="restWhole",
                  dur={"measure_rest": True, "beats": 2.0, "written": 2.0})
        with mock.patch.dict(os.environ, {LY.CARRIED_METER_REST_ENV: "1"}):
            text, _rep = LY.to_lilypond(page)
        self.assertRegex(text, r"r\d\.* \|")


if __name__ == "__main__":
    unittest.main()
