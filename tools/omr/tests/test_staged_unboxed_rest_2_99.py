"""ROADMAP 2.99 -- an eighth or a quarter rest the detector never boxed, read
on ITS OWN ink and never off the bar.

2.96 found 448 held bars holding rest-shaped ink no box accounts for; Sean's
tiles 7-9: three of three hold an eighth rest, BUT on tile 7 the first marked
piece was a FLAT. So the decision weighs shape AND place: a flat has a vertical
stroke and stands just left of its head; a rest has neither.

`adjudicate_unboxed_ink_is_a_rest` reads `Q.UNBOXED_REST_SHAPE` (GATHER's
measurement of a rest-sized cluster of ink); EVALUATE's `size_unboxed_rest`
gives a decided rest its length; the bar the rest stands in is never consulted.

Every refusal carries its positive control in the same class (the twin that
differs in exactly the refused property IS decided), so a decision that
refuses everything cannot pass. Tests named `*_RED` fail on the tree without
the decision (the quantity does not exist there).
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, consequences
from tools.omr.staged import export as SX
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

G = R.glyph(0, 0, 0, 2, 350_000)

#: Shapes MEASURED off the clusters the detector's own standing boxes cover
#: (FINDINGS 2.99): an eighth rest, a quarter rest and a flat on Litolff p1-3.
EIGHTH = dict(w=1.34, h=2.29, step=3.9, mass_y=0.43, col=0.75,
              profile=[0.39, 0.58, 0.58, 0.58, 0.75, 0.59])
QUARTER = dict(w=1.19, h=2.81, step=4.4, mass_y=0.55, col=1.0,
               profile=[0.4, 0.89, 1.0, 0.77, 0.6, 0.31])
FLAT = dict(w=1.04, h=2.7, step=4.0, mass_y=0.57, col=1.0,
            profile=[1.0, 1.0, 0.35, 0.35, 0.33, 0.23])
SHARP = dict(w=1.18, h=3.06, step=4.0, mass_y=0.49, col=1.0,
             profile=[0.68, 1.0, 0.98, 0.7, 0.92, 0.75])
ARPEGGIO = dict(w=1.08, h=3.3, step=4.96, mass_y=0.553, col=0.91,
                profile=[0.6, 0.69, 0.91, 0.87, 0.65, 0.46])


def _shape(log, *, w, h, step, mass_y, col, profile, pieces=1, cover=0.0,
           by=(), head=None, first=False, header_known=True, left=False,
           edge=False):
    log.observe(G, Q.UNBOXED_REST_SHAPE, h,
                reader=READERS.CV_UNBOXED_REST_SHAPE, frame="cell:2",
                n_pieces=pieces, width_spaces=w, height_spaces=h,
                staff_step=step, fill=0.4, max_column_share=col,
                mass_y=mass_y, column_profile=profile, coverage=cover,
                covered_by=list(by), right_head=head, first_cell=first,
                header_known=header_known, left_of_header=left,
                touches_cell_edge=edge,
                bbox_canonical=[10, 10, 30, 40],
                bbox_page_px=[0.0, 0.0, 10.0, 10.0])


def _case(base=EIGHTH, **kw):
    log = Log()
    _shape(log, **{**base, **kw})
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.UNBOXED_INK_IS_A_REST,))
    return log, log.verdict(Q.UNBOXED_INK_IS_A_REST, G)


class TestTheDecision(unittest.TestCase):

    def test_an_eighth_rest_shaped_cluster_is_an_eighth_rest_RED(self):
        _log, v = _case(EIGHTH)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "eighth")
        self.assertEqual(v.reason, "rest8th_shape")

    def test_a_quarter_rest_shaped_cluster_is_a_quarter_rest_RED(self):
        _log, v = _case(QUARTER)
        self.assertEqual(v.value, "quarter")
        self.assertEqual(v.reason, "restQuarter_shape")

    def test_it_records_the_row_it_stood_on_and_the_measurements(self):
        log, v = _case(EIGHTH)
        row = log.rows(Q.UNBOXED_REST_SHAPE, G)[-1]
        self.assertEqual(set(v.used), {row.id})
        self.assertEqual(v.missing, ())
        self.assertEqual(v.detail["height_spaces"], 2.29)
        self.assertEqual(v.detail["staff_step"], 3.9)
        self.assertEqual(v.detail["column_profile"], EIGHTH["profile"])

    def test_the_decision_reads_no_bar(self):
        """⚠️ THE RULE, ASSERTED OFF THE REGISTRY: no meter, event, duration
        or voice quantity is declared, so none can be read."""
        wants = set(adjudicate.REGISTRY[Q.UNBOXED_INK_IS_A_REST].wants)
        for q in (Q.METER, Q.EVENT, Q.DURATION, Q.VOICES, Q.ONSET_COLUMN):
            self.assertNotIn(q, wants)

    # ── the flat (Sean's tile 7 of 2.96) ─────────────────────────────────
    def test_a_flat_is_not_a_rest_it_has_a_stem_stroke(self):
        """A full-height stroke on the LEFT and little else: a stem with a
        bowl. Even at a rest's height and place."""
        _l, v = _case(FLAT)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "stem_stroke_not_a_rest")
        _l, v = _case(FLAT, h=2.29, w=1.3, step=3.9)   # eighth-sized flat
        self.assertIs(v.value, False)

    def test_the_same_size_without_the_stroke_is_a_rest_POSITIVE_CONTROL(self):
        _l, v = _case(FLAT, profile=EIGHTH["profile"], col=0.75, h=2.29,
                      w=1.34, step=3.9, mass_y=0.43)
        self.assertEqual(v.value, "eighth")

    def test_a_flat_beside_its_head_is_still_not_a_rest(self):
        """The flat's head stands right of it (dx 0.2). Whatever the head, the
        flat's own stroke is what refuses it."""
        head = {"class": "noteheadBlack", "dx_spaces": 0.2, "dy_spaces": 0.5}
        _l, v = _case(FLAT, head=head)
        self.assertIs(v.value, False)

    def test_a_sharp_is_not_a_rest(self):
        """Two strokes: a sharp's right slices fill again, a quarter rest's
        right side is thin."""
        _l, v = _case(SHARP)
        self.assertIsNot(v.value, "quarter")
        self.assertIsNot(v.value, "eighth")

    def test_an_arpeggio_line_beside_its_chord_is_not_a_quarter_rest(self):
        """The same zigzag as a quarter rest, but it stands against its chord:
        a head just to its right makes it abstain; the SAME ink with no head
        there is the positive control."""
        head = {"class": "noteheadBlack", "dx_spaces": 0.3, "dy_spaces": 0.5}
        _l, v = _case(ARPEGGIO, head=head)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "head_beside_it")
        _l, v = _case(ARPEGGIO, head=None)
        self.assertEqual(v.value, "quarter")

    def test_an_eighth_rest_next_to_a_head_is_still_an_eighth_rest(self):
        """Heads stand right beside real eighth rests (0.1-0.6 spaces on 18 of
        19 standing ones): the head is no claim against an eighth."""
        head = {"class": "noteheadBlack", "dx_spaces": 0.2, "dy_spaces": 1.0}
        _l, v = _case(EIGHTH, head=head)
        self.assertEqual(v.value, "eighth")

    # ── the staccato / dot / crumb ───────────────────────────────────────
    def test_a_dot_or_crumb_sized_cluster_is_not_decided(self):
        for w, h in ((0.5, 0.5), (0.6, 1.3)):
            _l, v = _case(EIGHTH, w=w, h=h)
            self.assertIs(v.outcome, Outcome.ABSTAINED, (w, h))
            self.assertEqual(v.reason, "shape_cannot_tell")

    def test_a_head_with_a_stem_or_a_beam_group_is_not_decided(self):
        for w, h in ((1.4, 3.9), (2.3, 2.2)):
            _l, v = _case(EIGHTH, w=w, h=h)
            self.assertIs(v.outcome, Outcome.ABSTAINED, (w, h))

    def test_ink_heavy_in_its_lower_half_is_not_an_eighth_rest(self):
        """An eighth rest's blob is on top; mass in the lower half is a
        flat's bowl or a head."""
        _l, v = _case(EIGHTH, mass_y=0.58)
        self.assertEqual(v.reason, "shape_cannot_tell")
        _l, v = _case(EIGHTH, mass_y=0.45)               # the twin
        self.assertEqual(v.value, "eighth")

    # ── Sean's tile 10: the END OF A SLUR is not a rest ──────────────────
    SLUR_END = dict(w=1.35, h=1.72, step=4.34, mass_y=0.476, col=0.395,
                    profile=[0.33, 0.37, 0.4, 0.33, 0.35, 0.4])

    def test_the_end_of_a_slur_is_not_an_eighth_rest_RED(self):
        """Brahms p1 s1 staff 3 bar 6 (tile 10, Sean: *"end of slur"*): a thin
        diagonal stroke with the size and place of an eighth rest. No ink
        column is more than 40% of its height; the thinnest standing eighth
        rest in 140 measured is 49%."""
        _l, v = _case(self.SLUR_END)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "thin_stroke_not_a_rest")

    def test_a_real_eighth_rest_beside_a_slur_stays_a_rest_POSITIVE_CONTROL(self):
        """The same size and place with the blob a rest has (tallest column
        62%): decided, and a slur box that does not cover it changes nothing."""
        _l, v = _case(self.SLUR_END, col=0.62,
                      profile=[0.3, 0.5, 0.62, 0.55, 0.45, 0.4],
                      cover=0.0, by=[])
        self.assertEqual(v.value, "eighth")

    # ── place ────────────────────────────────────────────────────────────
    def test_off_the_middle_of_the_staff_abstains(self):
        _l, v = _case(EIGHTH, step=1.9)
        self.assertEqual(v.reason, "shape_cannot_tell")
        _l, v = _case(EIGHTH, step=4.3)                  # inside the window
        self.assertEqual(v.value, "eighth")

    def test_too_many_pieces_abstains(self):
        _l, v = _case(EIGHTH, pieces=5)
        self.assertEqual(v.reason, "shape_cannot_tell")

    def test_a_cluster_at_the_cell_edge_does_not_decide(self):
        _l, v = _case(EIGHTH, edge=True)
        self.assertEqual(v.reason, "shape_cannot_tell")
        _l, v = _case(EIGHTH, edge=False)
        self.assertEqual(v.value, "eighth")

    # ── a claim by a standing box ────────────────────────────────────────
    def test_ink_a_standing_rest_box_covers_is_already_read(self):
        _l, v = _case(EIGHTH, cover=0.9, by=["rest8th"])
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "already_read_as_a_glyph")

    def test_ink_a_standing_accidental_box_covers_is_not_a_rest(self):
        _l, v = _case(FLAT, cover=0.9, by=["accidentalFlat"])
        self.assertIs(v.value, False)

    def test_partial_cover_abstains_and_none_decides_POSITIVE_CONTROL(self):
        _l, v = _case(EIGHTH, cover=0.3, by=["slur"])
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "claimed_by_another_class")
        _l, v = _case(EIGHTH, cover=0.0)
        self.assertEqual(v.value, "eighth")

    # ── the header ───────────────────────────────────────────────────────
    def test_ink_inside_the_clef_key_meter_header_abstains(self):
        _l, v = _case(EIGHTH, first=True, header_known=True, left=True)
        self.assertEqual(v.reason, "in_the_header")
        _l, v = _case(EIGHTH, first=True, header_known=False)
        self.assertEqual(v.reason, "in_the_header")
        _l, v = _case(EIGHTH, first=True, header_known=True, left=False)
        self.assertEqual(v.value, "eighth")        # the twin: past the header

    def test_no_ink_reading_abstains(self):
        _l, v = _case(EIGHTH, col=None, pieces=0)
        self.assertEqual(v.reason, "no_ink_reading")


class TestSizeUnboxedRest(unittest.TestCase):
    """EVALUATE: a decided rest takes its value's length -- from the class, not
    from the bar."""

    def _decided(self, value):
        log, v = _case(EIGHTH if value == "eighth" else QUARTER)
        return log, v

    def test_an_eighth_takes_half_a_quarter_RED(self):
        log, v = self._decided("eighth")
        out = consequences.size_unboxed_rest(log, G, v)
        self.assertEqual(len(out), 1)
        d = log.verdict(Q.DURATION, G)
        self.assertEqual(d.value["beats"], 0.5)
        self.assertTrue(d.value["is_rest"])
        self.assertTrue(d.value["unboxed_rest"])
        self.assertEqual(d.decider, "size_unboxed_rest")

    def test_a_quarter_takes_a_quarter(self):
        log, v = self._decided("quarter")
        consequences.size_unboxed_rest(log, G, v)
        self.assertEqual(log.verdict(Q.DURATION, G).value["beats"], 1.0)

    def test_it_is_idempotent(self):
        log, v = self._decided("eighth")
        consequences.size_unboxed_rest(log, G, v)
        self.assertEqual(consequences.size_unboxed_rest(log, G, v), [])

    def test_a_False_or_abstained_verdict_writes_nothing(self):
        for base, kw in ((FLAT, {}), (ARPEGGIO, dict(head={
                "class": "n", "dx_spaces": 0.2, "dy_spaces": 0.0}))):
            log, v = _case(base, **kw)
            self.assertEqual(consequences.size_unboxed_rest(log, G, v), [])
            self.assertIsNone(log.verdict(Q.DURATION, G))

    def test_it_reads_no_bar(self):
        rule = [r for r in __import__(
            "tools.omr.staged.evaluate", fromlist=["RULES"]).RULES
            if r.consequence.value == "size_unboxed_rest"]
        self.assertEqual(len(rule), 1)
        self.assertEqual(rule[0].cause, Q.UNBOXED_INK_IS_A_REST)


class TestExportWritesTheRest(unittest.TestCase):
    """EXPORT: a decided unboxed rest is written as a rest in ITS OWN bar, the
    accounting EQUALITY still balances (the rest joins its left-hand side by
    name), and the bar is judged like any other -- the rest is evidence the ink
    is there, never a licence to make a bar add up."""

    TWO_FOUR = {"numerator": 2, "denominator": 4, "raw": "2/4"}
    SUB = "glyph/0/0/0/0/350000"

    def _page(self, notes, *, rest=None, outcome="decided"):
        import xml.etree.ElementTree as ET  # noqa: F401
        from tools.omr.tests.test_staged_export import (
            _obs, _one_staff_page, _vrd)
        page = _one_staff_page(notes=notes, meter=self.TWO_FOUR)
        if rest is not None:
            page["record"]["observations"].append(_obs(
                5000, self.SUB, Q.UNBOXED_REST_SHAPE, 2.2,
                bbox_canonical=[500, 40, 530, 100],
                bbox_page_px=[500.0, 40.0, 530.0, 100.0]))
            page["record"]["verdicts"].append(_vrd(
                5001, self.SUB, Q.UNBOXED_INK_IS_A_REST,
                rest if outcome == "decided" else None, outcome=outcome))
            beats = 0.5 if rest == "eighth" else 1.0
            page["record"]["verdicts"].append(_vrd(
                5002, self.SUB, Q.DURATION,
                {"beats": beats, "written": beats, "dots": 0,
                 "beam_levels": 0, "is_rest": True, "unboxed_rest": True}))
        return page

    QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0}
    EIGHTH = {"beats": 0.5, "written": 0.5, "dots": 0}

    def test_the_missing_eighth_rest_completes_the_bar_RED(self):
        """A quarter and an eighth are 1.5 quarters in a 2/4 bar: HELD OUT
        without the rest. With the rest read off the ink, the bar adds up."""
        import xml.etree.ElementTree as ET
        notes = [("C4", self.QUARTER), ("D4", self.EIGHTH)]
        xml0, rep0 = SX.to_musicxml(self._page(notes))
        self.assertEqual(rep0["bars_held_out_sum"]["bars"], 1)      # control
        xml1, rep1 = SX.to_musicxml(self._page(notes, rest="eighth"))
        self.assertEqual(rep1["bars_held_out_sum"]["bars"], 0)
        root = ET.fromstring(xml1)
        self.assertEqual(len(root.findall(".//note/pitch")), 2)
        rests = root.findall(".//note/rest")
        self.assertEqual(len(rests), 1)
        self.assertIsNone(rests[0].get("measure"))          # not a measure rest
        self.assertTrue(rep1["balance"]["balanced"])
        self.assertEqual(rep1["balance"]["unboxed_rests_placed"], 1)

    def test_an_abstained_reading_writes_nothing_POSITIVE_CONTROL(self):
        notes = [("C4", self.QUARTER), ("D4", self.EIGHTH)]
        _xml, rep = SX.to_musicxml(self._page(notes, rest="eighth",
                                              outcome="abstained"))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(rep["balance"]["unboxed_rests_placed"], 0)
        self.assertTrue(rep["balance"]["balanced"])

    def test_a_rest_in_a_bar_that_already_adds_up_overfills_it_and_says_so(self):
        """The false-positive measure, on the page: the rest is NOT forgiven
        by a bar that was already right. The bar is held out and counted, and
        the equality still balances."""
        notes = [("C4", self.QUARTER), ("D4", self.QUARTER)]
        _xml, rep0 = SX.to_musicxml(self._page(notes))
        self.assertEqual(rep0["bars_held_out_sum"]["bars"], 0)
        _xml, rep1 = SX.to_musicxml(self._page(notes, rest="eighth"))
        self.assertEqual(rep1["bars_held_out_sum"]["bars"], 1)
        self.assertTrue(rep1["balance"]["balanced"])

    def test_a_quarter_rest_takes_a_quarter(self):
        import xml.etree.ElementTree as ET
        xml, rep = SX.to_musicxml(self._page([("C4", self.QUARTER)],
                                             rest="quarter"))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        types = [t.text for t in ET.fromstring(xml).findall(".//note/type")]
        self.assertIn("quarter", types)


if __name__ == "__main__":
    unittest.main()
