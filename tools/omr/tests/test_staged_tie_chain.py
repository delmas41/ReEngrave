"""The tie CHAIN: what the report can now say, and what it still cannot.

⚠️⚠️ THIS FILE GUARDS AN ACCOUNTING CHANGE, NOT A READING ONE. `tied_to_next`
and `tied_from_prev` are the last two entries in
`gather_coverage.NO_VOCABULARY` and they STAY there: no `Q` names a tie chain,
because a chain is a fact about a PART -- it crosses barlines and system
breaks -- and the part is built inside `staged/export.build`, after
`Q.PART_PARTITION` is read and after the record JSON has already been written.
See `benchmarks/omr-staged-tie-chain-2026-09/FINDINGS.md`.

What DID change is that the exporter now says what it did, in three ways the
report could not express before:

1. a CHAIN is counted apart from a LINK (they differ by one per chain);
2. `tie` and `slur` stop reporting each other's verdicts as their own;
3. a tie written onto a chord member that carries no tie is COUNTED.

⚠️ Every test here was run RED against `origin/main` before it was kept.
"""

import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q

from .test_staged_export import CELL_W, _arc_page


# ─────────────────────────────────────────────────────────────────────────────
# 1. A chain is not a link
# ─────────────────────────────────────────────────────────────────────────────


class TestAChainIsNotALink(unittest.TestCase):
    """⚠️ A chain of N notes is N-1 links. Quoting links as "ties" over-counts
    every chain of three or more, which is 4 of 46 chains on Litolff
    `984073` p1-3 and **82 of 275** on Breitkopf Brahms 1 p0-3 -- not a
    rounding error on the second document.
    """

    def test_two_links_sharing_a_note_are_ONE_chain(self):
        # three consecutive notes, two abutting tie arcs: n0~n1~n2
        page = _arc_page(arcs=[(0, 50, 190), (0, 160, 300)],
                         kinds={0: "tie", 1: "tie"})
        _xml, rep = SX.to_musicxml(page)
        w = rep["written"]
        self.assertEqual(w["tie_links_marked"], 2)
        self.assertEqual(w["tie_chains_marked"], 1)
        self.assertEqual(w["tie_chains_over_two_notes"], 1)

    def test_two_SEPARATE_links_are_two_chains(self):
        """The positive control for the test above: without it, a rule that
        always answered "one chain" would pass it."""
        page = _arc_page(arcs=[(0, 50, 190), (0, 270, 410)],
                         kinds={0: "tie", 1: "tie"})
        _xml, rep = SX.to_musicxml(page)
        w = rep["written"]
        self.assertEqual(w["tie_links_marked"], 2)
        self.assertEqual(w["tie_chains_marked"], 2)
        self.assertEqual(w.get("tie_chains_over_two_notes", 0), 0)


class TestChainSizesCountsNOTESAndSurvivesASharedStart(unittest.TestCase):
    """⚠️⚠️ WRITTEN BECAUSE THE FIRST CUT OF THE REACH PROBE GOT IT WRONG ON A
    REAL PAGE. Keying the closure on a `start -> stop` dict loses a head that
    begins TWO links -- a chord member tied onward while the head beside it
    starts another -- and reports every chain as a pair. On the Litolff record
    that read `{2: 50}` where the union-find reads chains of three and four.
    """

    def test_a_run_of_three_links_is_one_chain_of_four_notes(self):
        self.assertEqual(sorted(SX._chain_sizes([(1, 2), (2, 3), (3, 4)])
                                .values()), [4])

    def test_one_head_starting_two_links_does_not_lose_one(self):
        # 1->2 and 1->3: one chain of three notes, not two chains of two
        sizes = sorted(SX._chain_sizes([(1, 2), (1, 3)]).values())
        self.assertEqual(sizes, [3])

    def test_disjoint_links_stay_disjoint(self):
        self.assertEqual(sorted(SX._chain_sizes([(1, 2), (3, 4)]).values()),
                         [2, 2])

    def test_no_links_is_no_chains(self):
        self.assertEqual(SX._chain_sizes([]), {})


class TestALinkCrossingABarlineIsCountedAsOne(unittest.TestCase):
    """The cross-barline tie is the configuration the merge exists for -- 10
    of 59 links on Litolff p1-3, 140 of 632 on Brahms p0-3 -- and it must be
    counted ONCE, not once per detected half."""

    def test_a_tie_across_a_barline_is_one_link_in_two_bars(self):
        # ⚠️ The SAME two halves `TestTheBarlineDoesNotMakeTwoSlurs` uses --
        # an arc running to its cell's right edge and one resuming at the next
        # cell's left edge, at one height -- so the two tests exercise one
        # geometry and cannot drift apart about what a barline looks like.
        page = _arc_page(arcs=[(0, 300, CELL_W), (1, 0, 200)],
                         kinds={0: "tie", 1: "tie"}, n_measures=2)
        _xml, rep = SX.to_musicxml(page)
        w = rep["written"]
        self.assertEqual(w["tie_links_marked"], 1)
        self.assertEqual(w["tie_links_crossing_a_barline"], 1)
        self.assertEqual(w["tie_chains_marked"], 1)

    def test_a_tie_INSIDE_one_bar_is_not_counted_as_crossing(self):
        """The positive control in the same class: a counter that incremented
        unconditionally would pass the test above."""
        _xml, rep = SX.to_musicxml(
            _arc_page(arcs=[(0, 50, 190)], kinds={0: "tie"}))
        w = rep["written"]
        self.assertEqual(w["tie_links_marked"], 1)
        self.assertEqual(w.get("tie_links_crossing_a_barline", 0), 0)
        self.assertEqual(w.get("tie_links_crossing_a_system_break", 0), 0)


class TestASlurContributesNoTieChainCounts(unittest.TestCase):
    """The other half of the positive control: these counters must see the
    TIE pool only. A slur is paired by the same function on the same page."""

    def test_a_slur_marks_no_tie_link(self):
        _xml, rep = SX.to_musicxml(_arc_page(arcs=[(0, 50, 190)]))
        w = rep["written"]
        self.assertEqual(w["slurs"], 1)
        self.assertEqual(w.get("tie_links_marked", 0), 0)
        self.assertEqual(w.get("tie_chains_marked", 0), 0)


# ─────────────────────────────────────────────────────────────────────────────
# 2. `tie` and `slur` share a quantity and stopped reporting it twice
# ─────────────────────────────────────────────────────────────────────────────


def _row(report, family):
    return next(r for r in report["families"] if r["family"] == family)


class TestTwoFamiliesSharingAQuantityAreCountedApart(unittest.TestCase):
    """⚠️⚠️ FOUND ON A REAL RECORD, NOT BY REVIEW. `FAMILIES` maps BOTH `tie`
    and `slur` to `Q.ARC_KIND`, and `coverage()` counted every decided verdict
    of that quantity for each -- so on Litolff `984073` p1-3 both rows read
    `decided: 514` against a real split of **270 ties and 244 slurs**, which
    the `detector_glyphs` column one place to the left had right all along. A
    reader comparing `decided 514` with `written 49` would conclude the
    exporter drops 465 ties.
    """

    def test_the_two_rows_do_not_report_the_same_number(self):
        page = _arc_page(arcs=[(0, 50, 190), (0, 270, 410)],
                         kinds={0: "tie"})     # arc 1 stays a slur
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(_row(rep, "tie")["decided"], 1)
        self.assertEqual(_row(rep, "slur")["decided"], 1)

    def test_the_split_is_an_exact_partition_of_the_quantity(self):
        """⚠️ A PARTITION, ASSERTED. Attributing by value could silently drop
        a verdict whose value names neither family; the sum is what stops
        that being invisible."""
        page = _arc_page(arcs=[(0, 50, 190), (0, 270, 410), (0, 160, 300)],
                         kinds={0: "tie", 2: "tie"})
        _xml, rep = SX.to_musicxml(page)
        total = len([v for v in rep and
                     SX.Record(page).verdicts_of(Q.ARC_KIND)
                     if v["outcome"] == "decided"])
        self.assertEqual(
            _row(rep, "tie")["decided"] + _row(rep, "slur")["decided"], total)

    def test_a_family_with_its_OWN_quantity_is_untouched(self):
        """The control: the split must apply only where a quantity really is
        shared, or every other row silently reads zero."""
        page = _arc_page(arcs=[(0, 50, 190)], kinds={0: "tie"})
        _xml, rep = SX.to_musicxml(page)
        note = _row(rep, "note")
        self.assertGreater(note["decided"], 0)
        self.assertNotIn("abstentions_name_no_family", note)


class TestAnAbstentionOnASharedQuantityIsReportedONCE(unittest.TestCase):
    """⚠️ An abstention says the decision could not name a KIND, so it belongs
    to neither family. Filing it under both is the same double count one row
    up; filing it under neither, silently, would be worse."""

    def _page_with_an_abstained_arc(self):
        page = _arc_page(arcs=[(0, 50, 190)], kinds={0: "tie"})
        for v in page["record"]["verdicts"]:
            if v["quantity"] == Q.ARC_KIND:
                v["outcome"] = "abstained"
                v["value"] = None
                v["reason"] = "no_arc_box"
        return page

    def test_it_lands_in_abstained_without_a_family(self):
        _xml, rep = SX.to_musicxml(self._page_with_an_abstained_arc())
        self.assertEqual(rep["abstained_without_a_family"],
                         {Q.ARC_KIND: {"no_arc_box": 1}})

    def test_it_is_not_also_counted_under_either_family(self):
        _xml, rep = SX.to_musicxml(self._page_with_an_abstained_arc())
        self.assertEqual(_row(rep, "tie")["abstained"], {})
        self.assertEqual(_row(rep, "slur")["abstained"], {})

    def test_the_row_SAYS_where_its_abstentions_went(self):
        """⚠️ `abstained: {}` is ambiguous between "none" and "reported
        elsewhere". The flag is what makes the row readable on its own."""
        _xml, rep = SX.to_musicxml(self._page_with_an_abstained_arc())
        self.assertTrue(_row(rep, "tie")["abstentions_name_no_family"])

    def test_a_record_with_no_abstention_reports_an_EMPTY_map(self):
        """The positive control: a key that is always populated says nothing.
        """
        _xml, rep = SX.to_musicxml(
            _arc_page(arcs=[(0, 50, 190)], kinds={0: "tie"}))
        self.assertEqual(rep["abstained_without_a_family"], {})


# ─────────────────────────────────────────────────────────────────────────────
# 3. A tie on a chord can reach the WRONG note, and that is now a number
# ─────────────────────────────────────────────────────────────────────────────


def _chord_tie_page(*, tied_head_is_the_upper):
    """One bar: four heads, a chord on the SECOND, and a tie arc covering the
    chord column and the head after it.

    `voicing.group_chords_in_measure` sorts a chord LOWEST FIRST (larger
    canonical y is lower in pitch), so which head `_paired_spans` binds is
    decided by DETECTION order while which head the renderer writes on is
    decided by PITCH order. The two need not agree, and that is the defect.
    """
    page = _arc_page(arcs=[(0, 160, 310)], kinds={0: "tie"}, chord_on=(0, 1))
    obs = page["record"]["observations"]
    # the chord's two heads, in detection order
    chord = [o for o in obs if o["quantity"] == Q.GLYPH_BOX
             and o["detail"].get("category") == "notehead"
             and o["value"][1] == 60 + 1 * 110]
    assert len(chord) == 2, chord
    ys = [o["value"][2] for o in chord]
    # ⚠️ Larger canonical y is LOWER in pitch. To make the tied head the
    # upper one, the arc must bind the SMALLER-y head, which `_paired_spans`
    # reaches by detection order -- so put it first.
    want_first = min(ys) if tied_head_is_the_upper else max(ys)
    if chord[0]["value"][2] != want_first:
        i, j = obs.index(chord[0]), obs.index(chord[1])
        obs[i], obs[j] = obs[j], obs[i]
    return page


class TestATieOnAChordCanLandOnANoteThatCarriesNone(unittest.TestCase):
    """⚠️⚠️ A TIE IS NOT A SPAN AND THE CHORD RULE TREATS IT AS ONE. `<slur>`
    carries a `number=` and hangs off the chord's representative `<note>`;
    `<tied>` carries none and joins THE TWO NOTES IT NAMES -- `_pair_arcs`
    says so in its own docstring. But `voicing.group_chords_in_measure` hoists
    the flag onto the EVENT with `any()` and the renderer writes it at
    `n == 0`, so a chord whose UPPER member is tied gets the tie on its LOWEST
    note: a tie between two different pitches.

    MEASURED, Litolff `984073` p1-3: of 48 events carrying `tied_to_next`,
    **17 write the tie on a note that carries none**; `tied_from_prev` 15.

    ⚠️ NOT FIXED, DELIBERATELY -- the hoist is in `voicing.py`, shared with
    the LEGACY exporter and so with the 11-work engraved benchmark, and the
    repair moves hundreds of elements on a scan. This test pins the COUNTER,
    which is what stops the size of it being lost again.
    """

    def test_the_wrong_note_case_is_counted(self):
        _xml, rep = SX.to_musicxml(
            _chord_tie_page(tied_head_is_the_upper=True))
        self.assertEqual(
            rep["written"]["tie_starts_written_on_an_untied_note"], 1)

    def test_the_RIGHT_note_case_is_NOT_counted(self):
        """⚠️ THE POSITIVE CONTROL, and the whole battery needs it: a counter
        that incremented on every chord tie would pass the test above and mean
        nothing. Same fixture, same chord, only which head the arc binds."""
        _xml, rep = SX.to_musicxml(
            _chord_tie_page(tied_head_is_the_upper=False))
        self.assertEqual(
            rep["written"].get("tie_starts_written_on_an_untied_note", 0), 0)

    def test_a_single_note_tie_is_never_counted(self):
        _xml, rep = SX.to_musicxml(
            _arc_page(arcs=[(0, 160, 310)], kinds={0: "tie"}))
        self.assertEqual(
            rep["written"].get("tie_starts_written_on_an_untied_note", 0), 0)
        self.assertEqual(rep["written"]["ties"], 1)

    def test_the_file_still_carries_exactly_one_tie_either_way(self):
        """⚠️ THE BEHAVIOUR IS UNCHANGED AND THIS SAYS SO. The counter reports
        the defect; it does not repair it, and a future session must be able
        to see from the tests that nothing moved."""
        for upper in (True, False):
            xml, _rep = SX.to_musicxml(
                _chord_tie_page(tied_head_is_the_upper=upper))
            root = ET.fromstring(xml)
            self.assertEqual(len(root.findall('.//tied[@type="start"]')), 1)
            self.assertEqual(len(root.findall('.//tied[@type="stop"]')), 1)
            self.assertEqual(len(root.findall(".//note/chord")), 1)


class TestTheTieChainNumbersAreCONSISTENTWithEachOther(unittest.TestCase):
    """⚠️ The partition discipline this repo runs on every other family: the
    links and the chains must describe the same population, or the report has
    two answers and no way to tell which."""

    def test_links_never_exceed_the_spans_the_exporter_marked(self):
        page = _arc_page(arcs=[(0, 50, 190), (0, 160, 300), (0, 270, 410)],
                         kinds={0: "tie", 1: "tie", 2: "tie"})
        _xml, rep = SX.to_musicxml(page)
        w = rep["written"]
        self.assertEqual(w["tie_links_marked"], w["tie_spans_marked"])
        self.assertLessEqual(w["tie_chains_marked"], w["tie_links_marked"])
        self.assertLessEqual(w["tie_chains_over_two_notes"],
                             w["tie_chains_marked"])
