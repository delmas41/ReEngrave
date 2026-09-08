"""Tests for the per-symbol ledger.

⚠️ EVERY ASSERTION HERE WAS RUN RED BEFORE IT WAS BELIEVED GREEN. This project
has caught several vacuous tests — one asserted on label LENGTH where a single
huge glyph is one character, so a case that should have been rejected still
produced a short string and the test passed either way. `probe/mutate_ledger.py`
in the benchmark directory re-runs this file against a deliberately broken
instrument and asserts the suite goes RED; the mutations it applies are listed
in its docstring beside the test each one is expected to fell.

The fixtures are built here, in full, rather than loaded — so
*"the second quarter note of bar 3 is a B"* is a thing this file states and
then asserts on, which is what Sean asked for.
"""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
import tempfile

from tools.omr.symbol_ledger import (
    PartJoin, adjudicate, assessable, build_ledger, compare_attrs,
    cross_check_note_extraction, extract_symbols, lcs_pairs, load_side,
    propose_pairings, rows_to_csv, self_check_identity, summarise,
)


# ---------------------------------------------------------------------------
# Fixtures — written out so the music is visible in the test
# ---------------------------------------------------------------------------

def _score(parts_xml: str) -> str:
    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <score-partwise version="3.1">
          <part-list>{"".join(f'<score-part id="P{i+1}"><part-name>{n}</part-name></score-part>' for i, n in enumerate(_NAMES))}</part-list>
          {parts_xml}
        </score-partwise>
        """)


_NAMES: list[str] = []


def _note(step: str, octave: int, dur: int, ntype: str, *, alter: int | None = None,
          dots: int = 0, chord: bool = False, rest: bool = False,
          voice: str = "1", extra: str = "") -> str:
    if rest:
        body = "<rest/>"
    else:
        a = f"<alter>{alter}</alter>" if alter is not None else ""
        body = f"<pitch><step>{step}</step>{a}<octave>{octave}</octave></pitch>"
    c = "<chord/>" if chord else ""
    d = "<dot/>" * dots
    return (f"<note>{c}{body}<duration>{dur}</duration><voice>{voice}</voice>"
            f"<type>{ntype}</type>{d}{extra}</note>")


def _measure(n: int, notes: str, *, attrs: str = "") -> str:
    return f'<measure number="{n}">{attrs}{notes}</measure>'


ATTRS = ("<attributes><divisions>1</divisions><key><fifths>0</fifths></key>"
         "<time><beats>4</beats><beat-type>4</beat-type></time>"
         "<clef><sign>G</sign><line>2</line></clef></attributes>")


def one_part_three_bars(second_of_bar3: tuple[str, int] = ("B", 4)) -> str:
    """Bar 3 is four quarters; its SECOND is `second_of_bar3`."""
    global _NAMES
    _NAMES = ["Violin 1"]
    step, octv = second_of_bar3
    bar1 = "".join(_note("C", 4, 1, "quarter") for _ in range(4))
    bar2 = "".join(_note("D", 4, 1, "quarter") for _ in range(4))
    bar3 = (_note("A", 4, 1, "quarter") + _note(step, octv, 1, "quarter")
            + _note("E", 4, 1, "quarter") + _note("F", 4, 1, "quarter"))
    return _score(
        "<part id=\"P1\">"
        + _measure(1, bar1, attrs=ATTRS) + _measure(2, bar2) + _measure(3, bar3)
        + "</part>")


def write(tmp: Path, name: str, xml: str) -> Path:
    p = tmp / name
    p.write_text(xml)
    return p


# ---------------------------------------------------------------------------


class TestExtraction(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def test_a_note_is_addressed_by_part_bar_and_beat(self):
        """Sean's sentence, as an address."""
        f = write(self.tmp, "a.musicxml", one_part_three_bars())
        syms, _ = load_side(f, "truth")
        bar3 = [s for s in syms if s.family == "note" and s.measure == 3]
        self.assertEqual(len(bar3), 4)
        second = bar3[1]
        self.assertEqual(second.onset_ql, 1.0)          # the SECOND quarter
        self.assertEqual(second.attrs["pitch"], "B4")   # …is a B
        self.assertEqual(second.describe(), "Violin 1 bar 3 beat 2 note B4")

    def test_onset_accumulates_and_a_chord_shares_it(self):
        global _NAMES
        _NAMES = ["Viola"]
        notes = (_note("C", 4, 2, "half")
                 + _note("E", 4, 2, "half") + _note("G", 4, 2, "half", chord=True))
        f = write(self.tmp, "c.musicxml",
                  _score(f'<part id="P1">{_measure(1, notes, attrs=ATTRS)}</part>'))
        syms, _ = load_side(f, "truth")
        onsets = [s.onset_ql for s in syms if s.family == "note"]
        self.assertEqual(onsets, [0.0, 2.0, 2.0])

    def test_backup_rewinds_the_clock(self):
        global _NAMES
        _NAMES = ["Piano"]
        notes = (_note("C", 4, 4, "whole", voice="1")
                 + "<backup><duration>4</duration></backup>"
                 + _note("G", 3, 4, "whole", voice="2"))
        f = write(self.tmp, "b.musicxml",
                  _score(f'<part id="P1">{_measure(1, notes, attrs=ATTRS)}</part>'))
        syms, _ = load_side(f, "truth")
        self.assertEqual([s.onset_ql for s in syms if s.family == "note"], [0.0, 0.0])

    def test_every_family_that_fires_is_declared(self):
        from tools.omr.symbol_ledger import FAMILIES
        global _NAMES
        _NAMES = ["Oboe"]
        notes = ('<direction><direction-type><dynamics><ff/></dynamics>'
                 '</direction-type></direction>'
                 '<direction><direction-type><wedge type="crescendo"/>'
                 '</direction-type></direction>'
                 '<direction><direction-type><words>legato</words>'
                 '</direction-type></direction>'
                 + _note("C", 4, 4, "whole", extra=(
                     '<notations><slur type="start" number="1"/><tied type="start"/>'
                     '<fermata/><articulations><staccato/></articulations>'
                     '<ornaments><trill-mark/></ornaments></notations>')))
        f = write(self.tmp, "f.musicxml",
                  _score(f'<part id="P1">{_measure(1, notes, attrs=ATTRS)}'
                         f'</part>'))
        syms, _ = load_side(f, "truth")
        fams = {s.family for s in syms}
        self.assertEqual(fams, {"dynamic", "hairpin", "word", "note", "slur",
                                "tie", "fermata", "articulation", "ornament",
                                "clef", "key", "time"})
        for fam in fams:
            self.assertIn(fam, FAMILIES, f"{fam} fires but is not declared")


class TestSelfChecks(unittest.TestCase):
    """The controls that make a printed zero a result instead of a suspect."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def test_a_file_against_itself_is_wholly_matched(self):
        f = write(self.tmp, "a.musicxml", one_part_three_bars())
        out = self_check_identity(f)
        self.assertTrue(out["ok"], out)
        self.assertEqual(set(out["counts"]), {"matched_exact"})
        self.assertTrue(out["coverage"]["balanced"])

    def test_the_identity_check_can_actually_fail(self):
        """⚠️ RED FIRST. A control that has never failed is not known to be able
        to. Two files that differ by one pitch must NOT self-check clean."""
        a = write(self.tmp, "a.musicxml", one_part_three_bars())
        b = write(self.tmp, "b.musicxml", one_part_three_bars(("C", 5)))
        res = build_ledger(row_id="t", pred_path=b, truth_path=a)
        self.assertNotEqual(set(r.outcome for r in res.rows), {"matched_exact"})

    def test_coverage_balances_and_would_notice_if_it_did_not(self):
        a = write(self.tmp, "a.musicxml", one_part_three_bars())
        b = write(self.tmp, "b.musicxml", one_part_three_bars(("C", 5)))
        res = build_ledger(row_id="t", pred_path=b, truth_path=a)
        cov = res.coverage_check()
        self.assertTrue(cov["balanced"], cov)
        self.assertEqual(cov["truth_rows"], cov["truth_symbols_in"])
        # and the invariant is not trivially true: drop a row and it must break
        res.rows.pop()
        self.assertFalse(res.coverage_check()["balanced"])

    def test_independent_parser_agrees_about_the_notes(self):
        f = write(self.tmp, "a.musicxml", one_part_three_bars())
        out = cross_check_note_extraction(f)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["n_mine"], out["n_theirs"])


class TestAntiCircularity(unittest.TestCase):
    """The rule this instrument exists for."""

    def test_an_attribute_is_only_reported_from_a_key_blind_to_it(self):
        self.assertTrue(assessable("pitch", ["ord"]))
        self.assertTrue(assessable("pitch", ["onset"]))
        self.assertFalse(assessable("pitch", ["pitch"]))
        self.assertFalse(assessable("pitch", ["joint"]))
        self.assertTrue(assessable("duration_ql", ["pitch"]))
        self.assertFalse(assessable("duration_ql", ["onset"]),
                         "onset accrues durations — it is NOT duration-blind")
        self.assertFalse(assessable("duration_ql", ["joint"]))

    def test_a_pitch_only_pairing_declines_to_score_pitch(self):
        from tools.omr.symbol_ledger import Symbol
        t = Symbol("truth", 0, "V", 1, 0.0, "note", "1", 0, {"pitch": "C4"})
        p = Symbol("pred", 0, "V", 1, 0.0, "note", "1", 0, {"pitch": "D4"})
        wrong, unknown = compare_attrs(t, p, ["pitch"], "note")
        self.assertNotIn("pitch", wrong)
        self.assertIn("pitch", unknown)

    def test_ord_abstains_rather_than_guessing_across_unequal_counts(self):
        from tools.omr.symbol_ledger import Symbol
        mk = lambda i, s: Symbol(s, 0, "V", 1, float(i), "note", "1", i, {"pitch": "C4"})
        props = propose_pairings([mk(i, "truth") for i in range(4)],
                                 [mk(i, "pred") for i in range(3)], "note")
        ordp = next(p for p in props if p.name == "ord")
        self.assertTrue(ordp.abstained)
        self.assertEqual(ordp.pairs, {})

    def test_disagreeing_keys_produce_an_ambiguity_not_a_tidy_answer(self):
        adj = adjudicate([
            type("P", (), {"name": "onset", "pairs": {0: 1}, "abstained": False})(),
            type("P", (), {"name": "pitch", "pairs": {0: 0}, "abstained": False})(),
        ], 1, 2)
        self.assertIn(0, adj.ambiguous)
        self.assertNotIn(0, adj.partner)


class TestOutcomes(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def _ledger(self, pred_xml: str, truth_xml: str, **kw):
        a = write(self.tmp, "truth.musicxml", truth_xml)
        b = write(self.tmp, "pred.musicxml", pred_xml)
        return build_ledger(row_id="t", pred_path=b, truth_path=a, **kw)

    def test_the_second_quarter_of_bar_3_read_as_a_C_is_named_a_pitch_error(self):
        """The commission, literally. One row, one address, one named attribute."""
        res = self._ledger(one_part_three_bars(("C", 5)), one_part_three_bars())
        hits = [r for r in res.rows
                if r.measure == 3 and r.onset_ql == 1.0 and r.family == "note"]
        self.assertEqual(len(hits), 1)
        r = hits[0]
        self.assertEqual(r.outcome, "matched_attribute_error")
        self.assertEqual(r.attrs_wrong, ("pitch",))
        self.assertEqual(r.attrs["pitch"], "B4")
        self.assertEqual(r.partner_attrs["pitch"], "C5")
        self.assertEqual(r.description, "Violin 1 bar 3 beat 2 note B4")
        self.assertIn("ord", r.basis)
        self.assertEqual(r.basis_strength, "corroborated")
        # and nothing ELSE is charged
        others = [x for x in res.rows if x.outcome != "matched_exact"]
        self.assertEqual(len(others), 1)

    def test_a_pairing_only_one_key_names_is_flagged_uncorroborated(self):
        """⚠️ ONE KEY IS ONE SIGNAL, and the suite must say so.

        Delete the 2nd of four quarters. `ord` abstains (counts differ);
        after that the 2nd truth note is named ONLY by `onset` — `pitch` and
        `joint` both decline, because its pitch is simply gone. The pitch
        verdict taken from that lone pairing is real but uncorroborated, and
        it is exactly where this instrument's own residual misattribution
        lives, so it may never be pooled with the corroborated ones.

        This test exists because `probe/mutate_ledger.py` caught its absence:
        hard-coding `strength = "corroborated"` passed the whole suite.
        """
        global _NAMES
        _NAMES = ["Violin 1"]
        four = (_note("C", 4, 1, "quarter") + _note("D", 4, 1, "quarter")
                + _note("E", 4, 1, "quarter") + _note("F", 4, 1, "quarter"))
        three = (_note("C", 4, 1, "quarter") + _note("E", 4, 1, "quarter")
                 + _note("F", 4, 1, "quarter"))
        truth = _score(f'<part id="P1">{_measure(1, four, attrs=ATTRS)}</part>')
        pred = _score(f'<part id="P1">{_measure(1, three, attrs=ATTRS)}</part>')
        res = self._ledger(pred, truth)
        weak = [r for r in res.rows if r.basis_strength == "single_key"]
        self.assertTrue(weak, "no pairing was flagged uncorroborated")
        d4 = [r for r in weak if r.attrs.get("pitch") == "D4"]
        self.assertEqual(len(d4), 1)
        self.assertEqual(d4[0].basis, ("onset",))
        self.assertEqual(d4[0].attrs_wrong, ("pitch",))
        # and the corroborated ones are NOT flagged
        self.assertTrue(any(r.basis_strength == "corroborated" for r in res.rows))

    def test_a_wholly_unread_staff_is_uncorresponded_not_charged(self):
        """⚠️ THE HEADLINE BEHAVIOUR. With no part join the ledger says
        'I cannot tell', and says so on every symbol — it does not bill the
        page as misread."""
        res = self._ledger(one_part_three_bars(), one_part_three_bars(),
                           part_join=[PartJoin(0, (), "unresolved",
                                               reason="no staff map")])
        self.assertEqual(set(r.outcome for r in res.rows), {"uncorresponded"})
        self.assertEqual(set(r.reason for r in res.rows), {"part_unresolved"})
        self.assertTrue(res.coverage_check()["balanced"])

    def test_a_measure_count_mismatch_marks_the_map_hypothesised(self):
        res = self._ledger(one_part_three_bars(), one_part_three_bars(),
                           expected_measures=99)
        self.assertEqual(res.measure_map["status"], "hypothesised")
        self.assertTrue(all(r.measure_map == "hypothesised" for r in res.rows))

    def test_a_family_absent_from_the_prediction_is_missing_not_uncorresponded(self):
        """⚠️ The defect the mutation matrix caught: the cell set must be the
        UNION of both sides'. Driven off the prediction alone, a truth symbol
        whose whole family vanished was never visited."""
        global _NAMES
        _NAMES = ["Oboe"]
        with_slur = _score('<part id="P1">' + _measure(
            1, _note("C", 4, 4, "whole",
                     extra='<notations><slur type="start" number="1"/></notations>'),
            attrs=ATTRS) + "</part>")
        without = _score('<part id="P1">' + _measure(
            1, _note("C", 4, 4, "whole"), attrs=ATTRS) + "</part>")
        res = self._ledger(without, with_slur)
        slurs = [r for r in res.rows if r.family == "slur"]
        self.assertEqual([r.outcome for r in slurs], ["missing"])

    def test_a_condensed_staff_merges_its_reference_parts_and_says_so(self):
        global _NAMES
        _NAMES = ["Flute 1", "Flute 2"]
        a2 = _note("C", 5, 4, "whole")
        truth = _score(
            f'<part id="P1">{_measure(1, a2, attrs=ATTRS)}</part>'
            f'<part id="P2">{_measure(1, a2, attrs=ATTRS)}</part>')
        _NAMES = ["Flauti"]
        pred = _score(f'<part id="P1">{_measure(1, a2, attrs=ATTRS)}</part>')
        res = build_ledger(
            row_id="t",
            pred_path=write(self.tmp, "p2.musicxml", pred),
            truth_path=write(self.tmp, "t2.musicxml", truth),
            part_join=[PartJoin(0, (0, 1), "resolved")])
        notes = [r for r in res.rows if r.family == "note"]
        self.assertEqual([r.outcome for r in notes], ["matched_exact"],
                         "two flutes printing a2 are ONE notehead")
        self.assertTrue(all(r.condensed for r in notes))

    def test_every_row_carries_a_traceable_address_in_the_csv(self):
        res = self._ledger(one_part_three_bars(("C", 5)), one_part_three_bars())
        csv = rows_to_csv(res.rows)
        self.assertIn("Violin 1 bar 3 beat 2 note B4", csv)
        header = csv.splitlines()[0]
        for col in ("part_name", "measure", "onset_ql", "outcome", "basis",
                    "basis_strength", "attrs_wrong"):
            self.assertIn(col, header)


class TestSummary(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def test_the_counts_always_add_up_to_the_symbols_that_went_in(self):
        a = write(self.tmp, "a.musicxml", one_part_three_bars())
        b = write(self.tmp, "b.musicxml", one_part_three_bars(("C", 5)))
        res = build_ledger(row_id="t", pred_path=b, truth_path=a)
        s = summarise(res)
        self.assertEqual(sum(s["outcomes"].values()),
                         s["coverage"]["truth_rows"] + s["coverage"]["pred_rows_own"])
        self.assertTrue(s["coverage"]["balanced"])


class TestLcs(unittest.TestCase):

    def test_it_preserves_order(self):
        self.assertEqual(lcs_pairs("abc", "abc"), [(0, 0), (1, 1), (2, 2)])
        self.assertEqual(lcs_pairs("abc", "ac"), [(0, 0), (2, 1)])
        self.assertEqual(lcs_pairs("ab", "ba"), [(0, 1)])  # either is length 1; the DP takes truth-first
        self.assertEqual(lcs_pairs("", "abc"), [])


if __name__ == "__main__":
    unittest.main()
