"""`wedge_anchor`: the two notes one hairpin opens and closes on.

⚠️ THE RULE IS NOT RE-DERIVED HERE AND MUST NOT BE.
`export._wedge_anchors_from_candidates` is `_wedge_anchors`' own body, split
out so the staged decision can call it with page-pixel candidates instead of
the exporter's `measures` shims. Its three constants
(`_WEDGE_ANCHOR_PAD_NOTEHEADS`, `_WEDGE_START_RULE`,
`_WEDGE_STOP_REACH_NOTEHEADS`) are MEASURED and live in exactly one place; the
tests below assert that this decision REACHES that rule with the right inputs
and abstains where it cannot, never that the rule's own answers are what they
are — `tools/omr/tests/test_export.py::TestHairpins` already owns that, and
duplicating it here would be two tests pinning one behaviour.

⚠️ THE REFUSALS ARE THE TESTS THAT MATTER, and they carry their POSITIVE
CONTROL in the same class: a battery of refusal tests can pass by refusing
everything, so every refusal here sits beside an input that is ACCEPTED.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

STAFF = R.staff(0, 0, 0)
OTHER = R.staff(0, 0, 1)


def _head(log, staff_i, cell, gi, x, *, w=20.0, y=100.0, h=20.0,
          page=True):
    """One notehead. ⚠️ `bbox_page_px` is CORNERS `[x0, y0, x1, y1]`."""
    g = R.glyph(0, 0, staff_i, cell, gi)
    detail = dict(category="notehead")
    if page:
        detail.update(bbox_page_px=[x, y, x + w, y + h],
                      x_center_page=x + w / 2.0, y_center_page=y + h / 2.0)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x, y, w, h),
                reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.9,
                **detail)
    return g


def _hairpin(log, staff_i, cell, gi, x0, x1, *, kind="crescendo",
             page=True, reader=READERS.CV_HAIRPINS, y=160.0):
    g = R.glyph(0, 0, staff_i, cell, gi)
    detail = {}
    if page:
        detail.update(bbox_page_px=[x0, y, x1, y + 8.0],
                      x_center_page=(x0 + x1) / 2.0)
    log.observe(g, Q.WEDGE_BOX, kind, reader=reader,
                frame=G.FRAME_PAGE if page else f"cell:{cell}",
                score=0.8, **detail)
    return g


def _decide(log, subject):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.WEDGE_ANCHOR, subject)


class TestItIsNoLongerAStub(unittest.TestCase):
    def test_the_registry_says_it_decides(self):
        self.assertFalse(adjudicate.REGISTRY[Q.WEDGE_ANCHOR].stub)

    def test_it_is_not_the_last_stub_any_more(self):
        """⚠️ This asserted `stubs() == (Q.DIRECTION,)` -- true for one day.
        `direction` was closed on 2026-09-11 and the roster is empty, which is
        asserted where the roster LIVES (`test_staged_stage_contract.py`).
        What belongs in THIS file is the claim about THIS decision, so that is
        all that is left here."""
        self.assertNotIn(Q.WEDGE_ANCHOR, adjudicate.stubs())

    def test_it_runs_AFTER_voices(self):
        """⚠️⚠️ IT DID NOT, AND NO TEST COULD HAVE FOUND THAT. Placed beside
        the fermata and the ornament — its natural home, since all three take
        their subjects from a glyph row — it ran BEFORE `Q.VOICES` was
        decided and read None every time: a declared input that could never
        answer, the same shape as `Q.STEM`'s 916 unread rows.

        No behavioural test reaches it, because "one voice" and "voices
        unknown" give the SAME ANSWER on every page with one voice, which is
        every fixture in this file. `inventory --check` found it in one line
        by comparing `wants` against `ORDER`; this pins the repair so a future
        re-ordering fails here rather than silently going quiet again.
        """
        order = list(adjudicate.ORDER)
        self.assertLess(order.index(Q.VOICES), order.index(Q.WEDGE_ANCHOR))


class TestAHairpinIsAnchoredToNotes(unittest.TestCase):
    """⚠️ THE POSITIVE CONTROL FOR EVERY REFUSAL BELOW."""

    def test_a_hairpin_between_two_notes_names_them_both(self):
        """A slur is drawn OVER its notes and a hairpin BETWEEN them, which is
        why `_noteheads_under` scores 0 of 4 on real hairpins — the ink here
        overlaps NEITHER head."""
        log = Log()
        a = _head(log, 0, 0, 0, 10.0)
        b = _head(log, 0, 0, 1, 200.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        v = _decide(log, w)
        self.assertEqual(v.outcome.value, "decided")
        self.assertEqual(v.reason, "nearest_either_side")
        self.assertEqual(v.value, [a.to_key(), b.to_key()])
        self.assertEqual(v.detail["kind"], "crescendo")

    def test_the_kind_travels_with_the_anchor(self):
        """⚠️ An exporter holding only the two note keys would have to re-read
        the hairpin's class to know which way it points — the re-derivation
        this stage exists to remove."""
        log = Log()
        _head(log, 0, 0, 0, 10.0)
        _head(log, 0, 0, 1, 200.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0, kind="diminuendo")
        self.assertEqual(_decide(log, w).detail["kind"], "diminuendo")

    def test_ONE_anchor_note_is_enough(self):
        """Sean's rule, 2026-09-05, and the commonest shape on a scan: the ink
        read correctly, the bar found, only one note under it recovered. Worth
        Mahler 5 p2 going 4 -> 6 exported `<wedge>` against a truth of 6."""
        log = Log()
        a = _head(log, 0, 0, 0, 10.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        v = _decide(log, w)
        self.assertEqual(v.value, [a.to_key(), a.to_key()])
        self.assertTrue(v.detail["degenerate"])

    def test_a_neighbouring_bar_may_supply_the_stop(self):
        """⚠️ The `+1` measure window is `_wedge_anchors`' own and is NOT
        slack: the Mahler truth's crescendo runs `m5 -> m6`, ending on the
        next bar's downbeat, which is where hairpins ordinarily end."""
        log = Log()
        _head(log, 0, 0, 0, 10.0)
        b = _head(log, 0, 1, 0, 200.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        v = _decide(log, w)      # ⚠️ ONCE: adjudicating a frozen log twice
        self.assertEqual(v.value[1], b.to_key())   # raises AlreadyAdjudicated
        self.assertEqual(v.detail["stop_cell"], 1)


class TestTheRefusals(unittest.TestCase):
    """Each refusal, beside an input that is ACCEPTED — a battery of refusal
    tests can otherwise pass by refusing everything."""

    def test_a_row_with_no_page_box_ABSTAINS_rather_than_using_the_cell_frame(self):
        """⚠️ A REAL BRANCH, NOT A DEFENSIVE ONE. `gather_wedge_boxes` emits
        two readers and the DETECTOR's row carries a cell-frame box and no
        page box — 1 row of 47 on the Breitkopf Brahms 1 record. Two staves'
        canonical frames coincide BY CONSTRUCTION, so comparing a cell-frame
        hairpin with a page-frame notehead is the frame error that made
        `Q.ONSET_COLUMN` report 1,062 columns of nothing."""
        log = Log()
        _head(log, 0, 0, 0, 10.0)
        _head(log, 0, 0, 1, 200.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0, page=False,
                     reader=READERS.DETECTOR)
        v = _decide(log, w)
        self.assertEqual(v.outcome.value, "abstained")
        self.assertEqual(v.reason, "no_page_frame")
        self.assertEqual(v.detail["reader"], READERS.DETECTOR)

    def test_the_positive_control_for_the_frame_refusal(self):
        """The SAME hairpin, the SAME notes, differing only in carrying a page
        box — it decides. Without this the test above passes if the decision
        refuses everything."""
        log = Log()
        _head(log, 0, 0, 0, 10.0)
        _head(log, 0, 0, 1, 200.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0, page=True,
                     reader=READERS.DETECTOR)
        self.assertEqual(_decide(log, w).outcome.value, "decided")

    def test_a_head_with_no_page_box_is_not_a_candidate(self):
        """The mirror of the row above: a notehead the gather could not place
        in page pixels cannot anchor anything either, and the decision says
        `no_anchor` rather than silently comparing frames."""
        log = Log()
        _head(log, 0, 0, 0, 10.0, page=False)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        v = _decide(log, w)
        self.assertEqual(v.reason, "no_anchor")

    def test_a_staff_the_detector_found_no_notes_in_abstains(self):
        """Three of the four hairpins detected on the Mahler page sit on a
        staff with zero noteheads. A ceiling of the anchoring, not a bug."""
        log = Log()
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        v = _decide(log, w)
        self.assertEqual(v.outcome.value, "abstained")
        self.assertEqual(v.reason, "no_anchor")

    def test_a_REST_cannot_anchor_a_hairpin(self):
        """⚠️ AND A FERMATA'S CARRIER LIST IS THE OPPOSITE, WHICH IS WHY THIS
        IS ASSERTED RATHER THAN ASSUMED. `adjudicate_fermata_owner` pairs
        against notes AND rests, because on a conductor's page the commonest
        carrier of a pause is a whole-bar rest. A hairpin is not a pause: it
        is a DYNAMIC over sounding notes, `_wedge_anchors` reads candidates
        out of `_measure_noteheads` alone, and MusicXML/LilyPond both need a
        note to hang `\\<` and `\\!` on. A rest anchoring one would write a
        crescendo over silence.

        Found by a mutation arm — widening the filter to `("notehead",
        "rest")` survived every other test in this file.
        """
        log = Log()
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.GLYPH_BOX, ("restQuarter", 10.0, 100.0, 20.0, 30.0),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                    category="rest",
                    bbox_page_px=[10.0, 100.0, 30.0, 130.0])
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        v = _decide(log, w)
        self.assertEqual(v.outcome.value, "abstained")
        self.assertEqual(v.reason, "no_anchor")

    def test_the_positive_control_a_NOTE_in_the_same_place_anchors_it(self):
        """The same box, the same bar, `category` the only difference."""
        log = Log()
        a = _head(log, 0, 0, 0, 10.0, w=20.0, h=30.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        self.assertEqual(_decide(log, w).value[0], a.to_key())

    def test_the_window_does_not_reach_two_bars_away(self):
        """⚠️ Anything wider would let a staff that rests for four bars donate
        an anchor from the far side of them — `_wedge_anchors`' own words."""
        log = Log()
        _head(log, 0, 2, 0, 400.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        self.assertEqual(_decide(log, w).reason, "no_anchor")

    def test_the_positive_control_for_the_window(self):
        """One bar nearer and the same note anchors it."""
        log = Log()
        a = _head(log, 0, 1, 0, 400.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        self.assertEqual(_decide(log, w).value[0], a.to_key())


class TestTheHeadsAreTheOWNERS(unittest.TestCase):
    """⚠️ `arc_owner`'s rule, for its reason: a cross-staff duplicate is filed
    on the staff that DETECTED it, so anchoring against the cell's own heads
    would compare the hairpin to a page nobody sees."""

    def test_a_head_this_staff_does_not_own_cannot_anchor_its_hairpin(self):
        log = Log()
        head = _head(log, 0, 0, 0, 10.0)
        # `glyph_owner` moves it to the staff below; nothing is left here.
        log.observe(head, Q.GLYPH_BAND_DISTANCE, 0.2,
                    reader=READERS.GEOMETRY, frame=G.FRAME_PAGE,
                    candidate=OTHER.to_key())
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        v = _decide(log, w)
        self.assertEqual(v.reason, "no_anchor")

    def test_the_positive_control_no_contest_keeps_the_head(self):
        """With no contest the head stays, and the very same hairpin
        decides — so the test above is about OWNERSHIP and not about the
        head having vanished."""
        log = Log()
        head = _head(log, 0, 0, 0, 10.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        self.assertEqual(_decide(log, w).value[0], head.to_key())


class TestWhatItRecords(unittest.TestCase):
    def test_voices_read_is_recorded_so_UNKNOWN_is_not_read_as_ONE(self):
        """⚠️ A note no `Q.VOICES` verdict mentions is voice 0, the identical
        default `_paired_spans` applies — but "one voice" and "voices unknown"
        are the same NUMBER and different FACTS, so the verdict says which."""
        log = Log()
        _head(log, 0, 0, 0, 10.0)
        _head(log, 0, 0, 1, 200.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        self.assertEqual(_decide(log, w).detail["voices_read"], 0)

    def test_the_candidate_count_travels_so_a_thin_read_is_visible(self):
        log = Log()
        _head(log, 0, 0, 0, 10.0)
        _head(log, 0, 0, 1, 200.0)
        w = _hairpin(log, 0, 0, 90, 40.0, 195.0)
        self.assertEqual(_decide(log, w).detail["n_candidates"], 2)


class TestTheFrameConventionIsCORNERS(unittest.TestCase):
    """⚠️⚠️ THE MUTATION THAT SURVIVED EVERY ASSERTION IN THE ARC EXPORT'S
    FIRST BATTERY was reading a CORNER box `[x0,y0,x1,y1]` as a WIDTH box
    `[x,y,w,h]`: it turned a 140px arc into a 1190px one and every count still
    held, because counting spans cannot see a frame error — ONLY NAMING THE
    NOTES CAN. So this fixture is placed far from the origin, where the two
    spellings genuinely disagree, and asserts WHICH note is named.
    """

    def test_the_hairpin_right_edge_is_a_CORNER_not_a_width(self):
        log = Log()
        near = _head(log, 0, 0, 0, 1000.0)
        far = _head(log, 0, 0, 1, 1400.0)
        # corners: the ink runs 1030 -> 1060, so the NEAR head is its stop.
        # read as [x, y, w, h] the right edge would be 1030 + 1060 = 2090 and
        # the FAR head would win.
        w = _hairpin(log, 0, 0, 90, 1030.0, 1060.0)
        v = _decide(log, w)
        self.assertEqual(v.value, [near.to_key(), near.to_key()])
        self.assertNotIn(far.to_key(), v.value)


if __name__ == "__main__":
    unittest.main()
