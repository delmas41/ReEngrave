"""The staged CLI's `--pdf` render and its plain-words accounting summary —
ROADMAP 3.3 Part A (CLAUDE.md §1's product definition: "one command, a whole
movement, MusicXML and a LilyPond PDF").

⚠️ THESE TEST `_render_pdf` AND `_print_accounting_summary` DIRECTLY, not the
whole `python3 -m tools.omr.staged` CLI end to end: that entry point always
runs a real GATHER from a PDF (`pipeline.run_staged`), which is what
`tools/omr/tests/test_staged_pipeline*.py` already exercises, and re-running
a gather here would duplicate that rather than test what THIS lane added.
The two functions this lane added to `tools/omr/staged/__main__.py` take a
`.ly` path and a coverage-report dict — exactly what
`tools.omr.staged.lilypond.to_lilypond` / `tools.omr.staged.export.
to_musicxml` already produce over a tiny fixture record with NO weights, no
detector and no real PDF. Reusing `test_staged_export.py`'s fixture helpers
rather than duplicating them, the same way `test_staged_lilypond.py` does.

Run RED first: with `_render_pdf` / `_print_accounting_summary` removed (or
checked out from `origin/main`, which has neither), this whole file fails on
import with `ImportError: cannot import name '_render_pdf'`.

ROADMAP 3.5 (merged 2026-09-28, `135b7a60`) changed two premises this file
was written against, and the tests here follow the tree (CLAUDE.md rule 10):
the summary now prints TWO bar lines -- `unread bars ("<word>", read
NOTHING): N` and `held-out bars ("<word>"): N` -- off
`report["unread_bar_marks"]`, where one figure labelled "unread bars" used
to stand in for only the held-out-by-sum count; and a bar roadmap 2.8 holds
out is rendered in the `.ly` as a red full-measure rest marked with the
same word, so LilyPond compiles it CLEAN rather than logging a bar-check
failure. The bar-check parser's own "can it count one" control therefore
lives on a hand-broken `.ly` below, not on the exporter's output.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as LY
from tools.omr.staged.__main__ import _print_accounting_summary, _render_pdf
from tools.omr.tests.test_staged_export import QUARTER, _one_staff_page

_HAS_LILYPOND = shutil.which("lilypond") is not None

#: A bar whose one quarter note EXACTLY fills it — the positive control a
#: compile-failure test needs a sibling of (CLAUDE.md §6b: "a refusal test
#: needs a positive control in the same class").
_FULL_BAR_METER = {"numerator": 1, "denominator": 4, "raw": "1/4"}
#: A bar the one quarter note only HALF fills — ROADMAP 2.8 holds this bar
#: out of the MusicXML, and (independently) LilyPond's own bar check flags
#: the underfull bar in its stderr.
_HALF_EMPTY_BAR_METER = {"numerator": 2, "denominator": 4, "raw": "2/4"}


def _capture_stdout(fn, *args, **kwargs):
    buf = StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue()


def _capture_stderr(fn, *args, **kwargs):
    buf = StringIO()
    old = sys.stderr
    sys.stderr = buf
    try:
        fn(*args, **kwargs)
    finally:
        sys.stderr = old
    return buf.getvalue()


class TestRenderPdfWithLilypondAbsent(unittest.TestCase):
    """CLAUDE.md rule 8: a missing renderer is "cannot tell", never turned
    into a crash or a silently-empty "success". Runs with NO weights, no
    detector, no gather — `shutil.which` is simply patched to report
    lilypond as absent regardless of what is actually on this machine's
    PATH, so the test is not conditional on the runner's environment."""

    def test_ly_still_exists_no_crash_no_pdf_clear_message(self):
        ly_text, _report = LY.to_lilypond(
            _one_staff_page(notes=[("C4", QUARTER)], meter=_FULL_BAR_METER))
        with tempfile.TemporaryDirectory() as d:
            ly_path = Path(d) / "out.ly"
            ly_path.write_text(ly_text)
            pdf_path = Path(d) / "out.pdf"

            with mock.patch("shutil.which", return_value=None):
                out = _capture_stdout(_render_pdf, ly_path, pdf_path)

            self.assertFalse(pdf_path.exists())
            self.assertTrue(ly_path.is_file())          # untouched
            self.assertEqual(ly_path.read_text(), ly_text)
            self.assertIn("NO PDF", out)
            self.assertIn("lilypond", out.lower())
            self.assertIn(str(ly_path), out)             # says where the .ly is


@unittest.skipUnless(_HAS_LILYPOND, "lilypond not on PATH")
class TestRenderPdfWithLilypondPresent(unittest.TestCase):
    """A real compile, over a fixture record with no weights and no
    detector — `to_lilypond` is a pure function of the record dict."""

    def test_a_full_bar_compiles_clean(self):
        ly_text, _report = LY.to_lilypond(
            _one_staff_page(notes=[("C4", QUARTER)], meter=_FULL_BAR_METER))
        with tempfile.TemporaryDirectory() as d:
            ly_path = Path(d) / "out.ly"
            ly_path.write_text(ly_text)
            pdf_path = Path(d) / "out.pdf"
            out = _capture_stdout(_render_pdf, ly_path, pdf_path)

            self.assertTrue(pdf_path.is_file(), out)
            self.assertGreater(pdf_path.stat().st_size, 0)
        self.assertIn("lilypond exit 0", out)
        self.assertIn("0 bar-check failures", out)
        self.assertIn("0 unterminated ties", out)

    def test_an_underfull_bar_is_a_marked_rest_that_compiles_clean(self):
        """The POSITIVE CONTROL's sibling: same shape, one changed fact (the
        meter). Since ROADMAP 3.5 the exporter itself applies roadmap 2.8's
        hold-out: the underfull bar is NOT written as its own too-short
        notes (which LilyPond would flag as a bar-check failure) but as a
        red full-measure rest carrying the mark word -- CLAUDE.md §1,
        "MARKED as unread and never invented", rule 8, never silence. So the
        `.ly` must carry the mark, the exporter's own report must count it,
        and the compile must be clean."""
        ly_text, report = LY.to_lilypond(
            _one_staff_page(notes=[("C4", QUARTER)],
                           meter=_HALF_EMPTY_BAR_METER))
        marks = report["unread_bar_marks"]
        self.assertEqual(marks["held_out_sum"], 1)       # sanity
        self.assertEqual(marks["written"], 1)
        word = marks["words"]["bar_does_not_add_up"]     # read, not retyped
        self.assertIn("\\once \\override Rest.color = #red", ly_text)
        self.assertIn(f'^\\markup {{ "{word}" }}', ly_text)
        self.assertNotIn("c'4", ly_text)                 # the note is held out

        with tempfile.TemporaryDirectory() as d:
            ly_path = Path(d) / "out.ly"
            ly_path.write_text(ly_text)
            pdf_path = Path(d) / "out.pdf"
            out = _capture_stdout(_render_pdf, ly_path, pdf_path)
            self.assertTrue(pdf_path.is_file(), out)

        self.assertIn("lilypond exit 0", out)
        self.assertIn("0 bar-check failures", out)

    def test_the_bar_check_count_can_still_read_one_failure(self):
        """CLAUDE.md rule 7: a control must be able to fail, run in the
        state where it fails. The exporter no longer produces an underfull
        bar (3.5 marks it instead), so the state is built BY HAND: the
        full-bar `.ly` with its `\\time 1/4` rewritten to `\\time 2/4`,
        leaving the `c'4 |` bar check half empty. The count `_render_pdf`
        parses from lilypond's own stderr must move from 0 to 1."""
        ly_text, _report = LY.to_lilypond(
            _one_staff_page(notes=[("C4", QUARTER)], meter=_FULL_BAR_METER))
        self.assertIn("\\time 1/4", ly_text)             # the fact we break
        broken = ly_text.replace("\\time 1/4", "\\time 2/4")
        self.assertNotEqual(broken, ly_text)
        with tempfile.TemporaryDirectory() as d:
            ly_path = Path(d) / "out.ly"
            ly_path.write_text(broken)
            pdf_path = Path(d) / "out.pdf"
            out = _capture_stdout(_render_pdf, ly_path, pdf_path)

        self.assertIn("1 bar-check failures", out)

    def test_a_slow_compile_is_reported_not_hung(self):
        """`_render_pdf` wraps the compile in a timeout (CLAUDE.md rule 8
        again: a renderer that never returns must not hang the whole
        one-command run). Faked with a monkeypatched `subprocess.run` rather
        than an actually slow document, which would make this test itself
        slow for no benefit."""
        ly_text, _report = LY.to_lilypond(
            _one_staff_page(notes=[("C4", QUARTER)], meter=_FULL_BAR_METER))
        with tempfile.TemporaryDirectory() as d:
            ly_path = Path(d) / "out.ly"
            ly_path.write_text(ly_text)
            pdf_path = Path(d) / "out.pdf"

            def _timeout(*a, **kw):
                raise subprocess.TimeoutExpired(cmd="lilypond", timeout=1800)

            with mock.patch("subprocess.run", side_effect=_timeout):
                out = _capture_stdout(_render_pdf, ly_path, pdf_path)

        self.assertFalse(pdf_path.exists())
        self.assertIn("NO PDF", out)
        self.assertIn("1800", out)


class TestAccountingSummaryReadsTheReportNeverRecomputes(unittest.TestCase):
    """CLAUDE.md §1, in plain words: every unread bar is MARKED, never
    invented, and the user must see how many. The figures come straight off
    `staged.export.coverage`'s own report (ROADMAP 2.8 / 3.5's
    `unread_bar_marks` / part-join provenance) -- this checks the console
    lines read the SAME numbers and the SAME mark words the file carries,
    not a second computation of them. The expected words are read off the
    report, never retyped here, so a renaming in `UNREAD_BAR_MARK_WORDS`
    cannot make these tests disagree with the file."""

    @staticmethod
    def _expected_lines(report):
        marks = report["unread_bar_marks"]
        return (f'unread bars ("{marks["words"]["unread"]}", read NOTHING): '
                f'{marks["unread"]}',
                f'held-out bars ("{marks["words"]["bar_does_not_add_up"]}"): '
                f'{marks["held_out_sum"]}',
                f'total bars marked red in the file: {marks["written"]}')

    def test_a_bar_that_adds_up_reports_zero_unread(self):
        _xml, report = SX.to_musicxml(
            _one_staff_page(notes=[("C4", QUARTER)], meter=_FULL_BAR_METER))
        self.assertEqual(report["bars_held_out_sum"]["bars"], 0)  # sanity
        self.assertEqual(report["unread_bar_marks"]["held_out_sum"], 0)
        self.assertEqual(report["unread_bar_marks"]["unread"], 0)

        err = _capture_stderr(
            _print_accounting_summary, musicxml_report=report,
            lilypond_report=None)

        unread, held, written = self._expected_lines(report)
        self.assertIn(unread, err)
        self.assertTrue(unread.endswith(": 0"))
        self.assertIn(held, err)
        self.assertTrue(held.endswith(": 0"))
        self.assertIn(written + " ", err)
        self.assertTrue(written.endswith(": 0"))
        self.assertIn("staves held out: 0", err)

    def test_an_underfull_bar_is_counted_as_unread_not_silence(self):
        """The sibling of the test above: one changed fact (the meter), and
        the printed count must move from 0 to 1 -- the same "a control must
        be able to fail" discipline applied to the printed line, not just
        the exporter's own report."""
        _xml, report = SX.to_musicxml(
            _one_staff_page(notes=[("C4", QUARTER)],
                           meter=_HALF_EMPTY_BAR_METER))
        self.assertEqual(report["bars_held_out_sum"]["bars"], 1)  # sanity
        self.assertEqual(report["unread_bar_marks"]["held_out_sum"], 1)
        self.assertEqual(report["unread_bar_marks"]["unread"], 0)

        err = _capture_stderr(
            _print_accounting_summary, musicxml_report=report,
            lilypond_report=None)

        unread, held, written = self._expected_lines(report)
        # ROADMAP 3.5: the two reasons are printed APART. A bar whose
        # events do not add up is "held-out", not "read NOTHING".
        self.assertIn(held, err)
        self.assertTrue(held.endswith(": 1"))
        self.assertIn(unread, err)
        self.assertTrue(unread.endswith(": 0"))
        self.assertIn(written + " ", err)
        self.assertTrue(written.endswith(": 1"))

    def test_without_musicxml_it_says_so_rather_than_a_fake_zero(self):
        """⚠️ CLAUDE.md rule 8: "cannot tell" must never read like "clean".
        A `--lilypond`-only run has no ROADMAP 2.8 hold-out figure (that
        accounting lives in `_part_xml`, the MusicXML renderer only) -- the
        summary must say the figure was not computed, not print a bare 0
        that reads exactly like a document with no unread bars."""
        _text, ly_report = LY.to_lilypond(
            _one_staff_page(notes=[("C4", QUARTER)], meter=_FULL_BAR_METER))

        err = _capture_stderr(
            _print_accounting_summary, musicxml_report=None,
            lilypond_report=ly_report)

        self.assertIn("unread / held-out bars: not computed", err)
        self.assertNotIn("read NOTHING): 0", err)
        self.assertNotIn('held-out bars ("', err)
        self.assertNotIn("total bars marked red", err)

    def test_staves_held_out_is_read_not_recomputed(self):
        """A minimal, hand-built report for just this one field: no fixture
        in `test_staged_export.py` currently drives `held_out_staves` above
        zero (it requires an unidentified-part join shape that belongs to
        that file's own fixture family), so this checks the FORMATTING
        contract directly -- `_print_accounting_summary` must read
        `report["part_join"]["held_out_staves"]` verbatim, never re-derive
        it from `unidentified_parts` or anything else."""
        fake_report = {"part_join": {"held_out_staves": 3},
                       "bars_held_out_sum": {"bars": 0, "of_bars_with_events": 0}}

        err = _capture_stderr(
            _print_accounting_summary, musicxml_report=fake_report,
            lilypond_report=None)

        self.assertIn("staves held out: 3", err)


if __name__ == "__main__":
    unittest.main()
