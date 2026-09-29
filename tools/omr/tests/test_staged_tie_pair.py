"""ROADMAP 3.2b -- `Q.TIE_PAIR`: WHICH two noteheads a tie joins, decided in
ADJUDICATE, and the ONE pairing EXPORT writes `<tie>`/`<tied>` from.

CONVENTION (CLAUDE.md §10, measured): a tie's two heads are at ONE staff
position, and a tie FLANKS them. The pairing is `transcribe.
_pair_ties_in_staff`'s (the legacy reference reader) with its two guesses
turned into refusals: no same-position pair ABSTAINS (the legacy rule falls
through to the nearest heads in x), and more than one NARROWS (the legacy rule
takes the nearest).

⚠️ The refusal tests each carry a POSITIVE CONTROL in the same class -- the
same geometry with the one fact changed that should let it pair -- or they
would pass by refusing everything.

⚠️ Run RED against `origin/main` (`efe7eb66`) before it was kept: every test
here fails there (no `Q.TIE_PAIR`; the exporter paired ties by slur COVERAGE).
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import export as SX
from tools.omr.staged import gather_coverage as GC
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

from .test_staged_export import _arc_page, _vrd

#: page pixels: one staff space is 10 px, a head is 12 x 10
H_W, H_H = 12.0, 10.0
CELL_W = 200.0
ORDER = (Q.ARC_KIND, Q.TIE_PAIR)


def _cells(log, n, staff_i=0):
    for m in range(n):
        log.observe(R.cell(0, 0, staff_i, m), Q.CELL_BOX,
                    [m * CELL_W, 50.0, (m + 1) * CELL_W, 170.0],
                    reader=READERS.GEOMETRY, frame=f"cell:{m}")


def _head(log, cell, gi, x, y, staff_i=0):
    """A head whose page box starts at `x`, `y` (centre x + 6, y + 5)."""
    g = R.glyph(0, 0, staff_i, cell, gi)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", 0, 0, H_W, H_H),
                reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.9,
                category="notehead", bbox_page_px=[x, y, x + H_W, y + H_H])
    return g


def _arc(log, cell, gi, x0, x1, y0=112.0, y1=118.0, cls="tie", staff_i=0):
    g = R.glyph(0, 0, staff_i, cell, gi)
    log.observe(g, Q.ARC_BOX, cls, reader=READERS.DETECTOR,
                frame=f"cell:{cell}", score=0.8, x0=x0, x1=x1, y0=y0, y1=y1,
                bbox_page_px=[x0, y0, x1, y1])
    return g


def _decide(log, *arcs):
    log.freeze()
    adjudicate.run(log, order=ORDER)
    return [log.verdict(Q.TIE_PAIR, a) for a in arcs]


class TestItIsRegistered(unittest.TestCase):
    def test_it_decides_and_runs_after_everything_it_reads(self):
        spec = adjudicate.REGISTRY[Q.TIE_PAIR]
        self.assertFalse(spec.stub)
        order = list(adjudicate.ORDER)
        for upstream in (Q.ARC_KIND, Q.ARC_OWNER, Q.GLYPH_OWNER):
            self.assertLess(order.index(upstream), order.index(Q.TIE_PAIR),
                            upstream)


class TestATiePairsItsTwoFlankingHeads(unittest.TestCase):

    def test_a_tie_inside_one_bar(self):
        log = Log()
        _cells(log, 2)
        a = _head(log, 0, 0, 40.0, 100.0)
        b = _head(log, 0, 1, 120.0, 100.0)
        arc = _arc(log, 0, 5, 55.0, 115.0)
        (v,) = _decide(log, arc)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, {"start": a.to_key(), "stop": b.to_key()})
        self.assertFalse(v.detail["crosses_barline"])

    def test_BOTH_halves_of_a_tie_a_barline_cut_name_the_same_pair(self):
        """The canonical tie crosses a barline and is detected as two arcs;
        the half that begins AT the barline has its start head a whole
        first-half away, past the 3-width reach. Without the cut-edge window
        it abstained `no_start_head` (found on the engraved page, 6 of 13)."""
        log = Log()
        _cells(log, 3)
        a = _head(log, 0, 0, 150.0, 100.0)
        b = _head(log, 1, 0, 230.0, 100.0)
        h1 = _arc(log, 0, 5, 165.0, 200.0)       # cut at the barline (right)
        h2 = _arc(log, 1, 5, 200.0, 222.0)       # cut at the barline (left)
        v1, v2 = _decide(log, h1, h2)
        want = {"start": a.to_key(), "stop": b.to_key()}
        self.assertEqual((v1.value, v2.value), (want, want))
        self.assertTrue(v1.detail["crosses_barline"])

    def test_a_scan_tie_whose_box_begins_OVER_its_start_head(self):
        """Litolff p3: start-head centres sit 0.37-0.54 widths INSIDE the
        detected box; the legacy `0 <= dx` window misses every one."""
        log = Log()
        _cells(log, 2)
        a = _head(log, 0, 0, 40.0, 100.0)        # centre 46
        b = _head(log, 0, 1, 120.0, 100.0)
        arc = _arc(log, 0, 5, 41.0, 115.0)       # starts 5 px left of centre
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, {"start": a.to_key(), "stop": b.to_key()})


class TestItNeverGuesses(unittest.TestCase):

    def test_a_SLUR_is_never_paired(self):
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 100.0)
        _head(log, 0, 1, 120.0, 100.0)
        arc = _arc(log, 0, 5, 55.0, 115.0, cls="slur")
        (v,) = _decide(log, arc)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "not_a_tie")

    def test_heads_at_TWO_positions_are_not_a_tie(self):
        """⚠️ The legacy rule falls through to the nearest heads in x here and
        writes a tie between two different notes. Half a space apart is one
        diatonic step."""
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 100.0)
        _head(log, 0, 1, 120.0, 105.0)
        arc = _arc(log, 0, 5, 55.0, 115.0)
        (v,) = _decide(log, arc)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_pair_at_one_position")

    def test_POSITIVE_CONTROL_the_same_arc_pairs_at_one_position(self):
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 100.0)
        _head(log, 0, 1, 120.0, 101.0)           # 0.1 space: one position
        arc = _arc(log, 0, 5, 55.0, 115.0)
        (v,) = _decide(log, arc)
        self.assertEqual(v.reason, "paired")

    def test_two_candidate_pairs_NARROW(self):
        """A tied chord with one arc detected: two pairs, each at one
        position. Which one this arc is, is not something it can say."""
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 100.0)
        _head(log, 0, 1, 40.0, 110.0)
        _head(log, 0, 2, 120.0, 100.0)
        _head(log, 0, 3, 120.0, 110.0)
        arc = _arc(log, 0, 5, 55.0, 115.0, y0=103.0, y1=109.0)
        (v,) = _decide(log, arc)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "more_than_one_pair")
        self.assertEqual(len(v.candidates), 2)

    def test_two_start_heads_at_ONE_x_narrow(self):
        """A duplicate detection: two heads at one position and one x."""
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 100.0)
        _head(log, 0, 1, 40.0, 100.0)
        _head(log, 0, 2, 120.0, 100.0)
        arc = _arc(log, 0, 5, 55.0, 115.0)
        (v,) = _decide(log, arc)
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_the_NEARER_head_at_one_position_is_forced_not_preferred(self):
        """Positive control for the narrowing above: a tie joins CONSECUTIVE
        notes, so of two heads at the partner's position the farther has the
        nearer between it and the arc. That is decided, not narrowed."""
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 20.0, 100.0)            # farther, same position
        near = _head(log, 0, 1, 40.0, 100.0)
        b = _head(log, 0, 2, 120.0, 100.0)
        arc = _arc(log, 0, 5, 55.0, 115.0)
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, {"start": near.to_key(),
                                   "stop": b.to_key()})

    def test_an_arc_across_a_WHOLE_bar_is_not_a_tie(self):
        """A tie joins two consecutive notes, so it never crosses a whole bar.
        Litolff p3 has 20 such `tie` boxes; the first crop was a staff line."""
        log = Log()
        _cells(log, 3)
        _head(log, 0, 0, 150.0, 100.0)
        _head(log, 2, 0, 430.0, 100.0)
        arc = _arc(log, 1, 5, 200.0, 400.0)
        (v,) = _decide(log, arc)
        self.assertEqual(v.reason, "spans_a_whole_bar")

    def test_a_relocated_copy_is_not_a_candidate(self):
        """The head set is the one EXPORT writes: a copy `glyph_owner` gives
        to another staff has a twin there and is dropped at EXPORT."""
        log = Log()
        _cells(log, 2)
        a = _head(log, 0, 0, 40.0, 100.0)
        _head(log, 0, 1, 120.0, 100.0)
        arc = _arc(log, 0, 5, 55.0, 115.0)
        log.freeze()
        log.record(Verdict(id=log._next_id("vrd"), subject=a,
                           quantity=Q.GLYPH_OWNER, outcome=Outcome.DECIDED,
                           value="staff/0/0/1", decider="t", reason="x"))
        adjudicate.run(log, order=ORDER)
        v = log.verdict(Q.TIE_PAIR, arc)
        self.assertEqual(v.reason, "no_start_head")


class TestATiedChord(unittest.TestCase):
    """ROADMAP 3.2c. A tied chord is engraved ONE ARC PER TIED NOTE, stacked,
    and arcs do not cross: where the stack and the pairs match one-to-one by
    vertical order the matching FOLLOWS. Anything else keeps narrowing."""

    def _chord(self, log, n=2):
        heads = []
        for i in range(n):
            heads.append((_head(log, 0, 2 * i, 40.0, 100.0 + 10 * i),
                          _head(log, 0, 2 * i + 1, 120.0, 100.0 + 10 * i)))
        return heads

    def test_two_arcs_two_pairs_pair_by_vertical_order(self):
        log = Log()
        _cells(log, 2)
        (a0, b0), (a1, b1) = self._chord(log)
        upper = _arc(log, 0, 5, 55.0, 115.0, y0=92.0, y1=97.0)
        lower = _arc(log, 0, 6, 55.0, 115.0, y0=118.0, y1=124.0)
        vu, vl = _decide(log, upper, lower)
        self.assertEqual(vu.reason, "paired_in_a_chord")
        self.assertEqual(vu.value, {"start": a0.to_key(), "stop": b0.to_key()})
        self.assertEqual(vl.value, {"start": a1.to_key(), "stop": b1.to_key()})

    def test_CONTROL_two_arcs_at_ONE_position_still_narrow(self):
        """Two boxes of one arc (a duplicate detection) are not two tied
        notes; which box is real is not something the stack can say."""
        log = Log()
        _cells(log, 2)
        self._chord(log)
        d1 = _arc(log, 0, 5, 55.0, 115.0, y0=103.0, y1=109.0)
        d2 = _arc(log, 0, 6, 56.0, 114.0, y0=104.0, y1=110.0)
        v1, v2 = _decide(log, d1, d2)
        self.assertEqual((v1.outcome, v2.outcome),
                         (Outcome.NARROWED, Outcome.NARROWED))

    def test_CONTROL_two_arcs_three_pairs_is_not_one_to_one(self):
        log = Log()
        _cells(log, 2)
        self._chord(log, n=3)
        a = _arc(log, 0, 7, 55.0, 115.0, y0=92.0, y1=97.0)
        b = _arc(log, 0, 8, 55.0, 115.0, y0=128.0, y1=134.0)
        va, vb = _decide(log, a, b)
        self.assertEqual((va.reason, vb.reason),
                         ("more_than_one_pair", "more_than_one_pair"))

    def test_CONTROL_starts_that_are_not_ONE_chord_still_narrow(self):
        """Found on the Breitkopf p1 crops: two stacked arcs over heads a note
        apart are not a tied chord."""
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 100.0)
        _head(log, 0, 1, 20.0, 110.0)            # another column
        _head(log, 0, 2, 120.0, 100.0)
        _head(log, 0, 3, 120.0, 110.0)
        upper = _arc(log, 0, 5, 55.0, 115.0, y0=92.0, y1=97.0)
        lower = _arc(log, 0, 6, 55.0, 115.0, y0=118.0, y1=124.0)
        vu, vl = _decide(log, upper, lower)
        self.assertEqual((vu.outcome, vl.outcome),
                         (Outcome.NARROWED, Outcome.NARROWED))

    def test_CONTROL_a_slur_in_the_stack_does_not_count(self):
        log = Log()
        _cells(log, 2)
        self._chord(log)
        tie = _arc(log, 0, 5, 55.0, 115.0, y0=92.0, y1=97.0)
        _arc(log, 0, 6, 55.0, 115.0, y0=118.0, y1=124.0, cls="slur")
        (v,) = _decide(log, tie)
        self.assertEqual(v.outcome, Outcome.NARROWED)


class TestTheSystemEdge(unittest.TestCase):

    def test_a_tie_running_off_the_system_abstains_and_says_so(self):
        log = Log()
        _cells(log, 2)
        _head(log, 1, 0, 330.0, 100.0)
        arc = _arc(log, 1, 5, 345.0, 400.0)      # cut by the system's end
        (v,) = _decide(log, arc)
        self.assertEqual(v.reason, "runs_off_the_system")

    def test_POSITIVE_CONTROL_a_missing_stop_inside_a_bar_is_a_reading_gap(
            self):
        log = Log()
        _cells(log, 2)
        _head(log, 1, 0, 330.0, 100.0)
        _head(log, 1, 1, 390.0, 60.0)            # a head after it, elsewhere
        arc = _arc(log, 1, 5, 345.0, 370.0)
        (v,) = _decide(log, arc)
        self.assertEqual(v.reason, "no_stop_head")

    def test_a_tie_entering_from_the_previous_system(self):
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 60.0, 100.0)
        arc = _arc(log, 0, 5, 20.0, 50.0)        # nothing precedes it
        (v,) = _decide(log, arc)
        self.assertEqual(v.reason, "enters_from_previous_system")


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT writes the record's pairs, and only those
# ─────────────────────────────────────────────────────────────────────────────

START, STOP = "glyph/0/0/0/0/3", "glyph/0/0/0/1/4"   # F4 (bar 1) -> bar 2's C4


def _tie_page(*, stop_pitch="F4", pairs=((START, STOP),), abstain=None):
    """`_arc_page`'s two bars, a tie arc at the barline, `Q.TIE_PAIR` rows."""
    page = _arc_page(arcs=[(0, 380, 500), (1, 0, 40)],
                     kinds={0: "tie", 1: "tie"}, n_measures=2)
    vr = page["record"]["verdicts"]
    vr.append(_vrd(5000, STOP, Q.PITCH, stop_pitch))
    arcs = ["glyph/0/0/0/0/500", "glyph/0/0/0/1/501"]
    for i, (s, e) in enumerate(pairs):
        vr.append(_vrd(5001 + i, arcs[i], Q.TIE_PAIR,
                       {"start": s, "stop": e}, reason="paired"))
    if abstain:
        vr.append(_vrd(5100, arcs[len(pairs)], Q.TIE_PAIR, None,
                       outcome="abstained", reason=abstain))
    return page


class TestExportWritesTheRecordsPair(unittest.TestCase):

    def test_the_named_pair_is_tied(self):
        xml, rep = SX.to_musicxml(_tie_page())
        self.assertEqual(rep["tie_pairing"], "record")
        self.assertEqual(xml.count('<tie type="start"/>'), 1)
        self.assertEqual(xml.count('<tie type="stop"/>'), 1)
        self.assertEqual(rep["written"]["tie_links_crossing_a_barline"], 1)
        self.assertEqual([(t["start"], t["stop"]) for t in rep["tie_links"]],
                         [(START, STOP)])

    def test_two_halves_naming_one_pair_write_ONE_tie(self):
        xml, rep = SX.to_musicxml(_tie_page(pairs=((START, STOP),
                                                   (START, STOP))))
        self.assertEqual(xml.count('<tie type="start"/>'), 1)
        self.assertEqual(
            rep["written"]["tie_arcs_naming_an_already_named_pair"], 1)

    def test_a_record_with_NO_tie_pair_keeps_the_exporters_pairing(self):
        """A record gathered before 3.2b: "no reader ran" must not export as
        "every tie abstained", and the report names which pairing ran."""
        page = _arc_page(arcs=[(0, 50, 190)], kinds={0: "tie"})
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["tie_pairing"], "exporter")
        self.assertEqual(rep["written"]["ties"], 1)

    def test_an_ABSTAINED_tie_is_never_paired_by_the_exporter_instead(self):
        """⚠️ Rule 8: a fallback never converts "cannot tell" into an answer.
        The same arc exported with no `Q.TIE_PAIR` row writes a tie by slur
        coverage (the control above); with an abstention it writes none."""
        page = _arc_page(arcs=[(0, 50, 190)], kinds={0: "tie"})
        page["record"]["verdicts"].append(
            _vrd(5100, "glyph/0/0/0/0/500", Q.TIE_PAIR, None,
                 outcome="abstained", reason="no_pair_at_one_position"))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["tie_pairing"], "record")
        self.assertNotIn("<tie ", xml)
        self.assertEqual(
            rep["arcs_not_written"]["tie_pair_no_pair_at_one_position"], 1)


class TestAContradictionIsRefusedAndNamed(unittest.TestCase):
    """A tie's two heads sound ONE pitch -- the one place a pitch reading is
    checkable with no truth file."""

    def test_two_different_pitches_are_not_tied(self):
        xml, rep = SX.to_musicxml(_tie_page(stop_pitch="C4"))
        self.assertNotIn("<tie ", xml)
        self.assertEqual(rep["arcs_not_written"]["tie_pitch_contradiction"],
                         1)
        (c,) = rep["tie_contradictions"]
        self.assertEqual((c["start"], c["stop"], c["pitches"]),
                         (START, STOP, ["F4", "C4"]))

    def test_same_step_different_spelling_is_counted_APART(self):
        """`F#4 -> F4` is the far head of a cross-barline tie not restating
        its accidental: a pitch fix, not a pairing fault."""
        page = _tie_page(stop_pitch="F4")
        page["record"]["verdicts"].append(_vrd(5200, START, Q.PITCH, "F#4"))
        xml, rep = SX.to_musicxml(page)
        self.assertNotIn("<tie ", xml)
        self.assertEqual(rep["arcs_not_written"]["tie_spelling_differs"], 1)

    def test_POSITIVE_CONTROL_one_pitch_is_tied(self):
        xml, rep = SX.to_musicxml(_tie_page(stop_pitch="F4"))
        self.assertEqual(rep["tie_contradictions"], [])
        self.assertIn('<tie type="start"/>', xml)


class TestTheVocabularyGapIsClosed(unittest.TestCase):
    def test_tied_flags_map_to_TIE_PAIR(self):
        for key in ("tied_to_next", "tied_from_prev"):
            self.assertEqual(GC.LEGACY_TO_Q.get(key), "TIE_PAIR", key)
            self.assertNotIn(key, GC.NO_VOCABULARY, key)


if __name__ == "__main__":
    unittest.main()
