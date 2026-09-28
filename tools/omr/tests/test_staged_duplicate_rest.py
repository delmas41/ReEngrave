"""ROADMAP 2.15: one physical rest, boxed more than once, is counted twice
in the bar sum.

⚠️ RUN RED FIRST, against the unrepaired tree (`origin/main`, before
`adjudicators/family_precision.py` grew `_duplicate_box_refusal`): every test
in `TestDuplicateRestAdjudication` fails because
`adjudicate_rest_is_not_a_rest` never refuses two overlapping rest glyphs,
so BOTH verdicts come back `value=False, reason="rest"` — the fixtures in
this class exist to fail on that behaviour, not on an import error, since
`Q.REST_IS_NOT_A_REST` and its decision both already existed for the human
witness (ROADMAP 3.4g).

⚠️ THE WORK ORDER'S OWN CLAIM DID NOT SURVIVE CONTACT WITH THE RECORD. It
said the ROADMAP 2.15 example's two boxes "overlap substantially"; measured
on the record (`glyph/2/1/0/7/0`/`.../1`, Brahms provenance c19cbca7) they
are IoU 0.16, and a crop of it
(`benchmarks/omr-bar-sum-holdout-2026-09/out/print/r215-*`) shows ONE
filled rectangle with two boxes covering roughly half each — the SHATTERING
plate (CLAUDE.md SS10) fragmenting one mark's ink, not two boxes drawn on
top of each other. The record's own IoU distribution (see
`adjudicators/family_precision.py`'s `REST_DUPLICATE_IOU_MIN` docstring) has
NO gap between "IoU 0.03" and "IoU 0.71" for a same-class pair — the gap is
between that whole range and EXACTLY ZERO, which is why the fixtures below
use both a MODEST overlap (mirroring the crop-confirmed population) and a
disjoint pair, rather than two boxes drawn on top of each other.

⚠️ EVERY REFUSAL TEST HAS A POSITIVE CONTROL IN THE SAME CLASS (CLAUDE.md
§6b) — `test_two_separate_rests_no_overlap_are_both_kept` is the one that
can fail: without it, a rule that refused every rest in a cell regardless of
geometry would pass every test above it.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import export as SX
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_bar_sum_holdout import _bar
from tools.omr.tests.test_staged_export import _add_rest, _vrd

REFUSAL = "rest_is_a_duplicate_box"


# ─────────────────────────────────────────────────────────────────────────────
# fixtures — a live Log, exactly the `adjudicate_rest_is_not_a_rest` domain
# ─────────────────────────────────────────────────────────────────────────────

def _rest_box(log, gi, cls, *, x_c, y_c, w_c=100.0, h_c=50.0, score):
    """One rest glyph's `Q.GLYPH_BOX` and `Q.REST` rows, in the shape GATHER
    emits (`gather.py`'s `log.observe(g, Q.REST, name, ...)`,
    `log.observe(g, Q.GLYPH_BOX, (d.smufl_name, ...), score=..., ...)`)."""
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, (cls, x_c, y_c, w_c, h_c),
                reader=READERS.DETECTOR, frame="cell:0", score=score,
                category="rest")
    log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0",
                score=score, category="rest")
    return g


def _run(log, *quantities):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=tuple(quantities))
    return log


class TestDuplicateRestAdjudication(unittest.TestCase):
    """`adjudicate_rest_is_not_a_rest`'s geometric rule, in isolation."""

    def test_two_overlapping_same_class_boxes_the_lower_confidence_one_loses(
            self):
        """Two `restWhole` boxes at MODEST overlap (IoU ~0.43, inside the
        crop-confirmed range, nowhere near "boxes drawn on top of each
        other") — the SAME shape as the ROADMAP 2.15 named example. The
        higher-confidence box survives; the other is refused and named."""
        log = Log()
        lo = _rest_box(log, 0, "restWhole", x_c=100.0, y_c=100.0, score=0.5)
        hi = _rest_box(log, 1, "restWhole", x_c=140.0, y_c=100.0, score=0.6)
        _run(log, Q.REST_IS_NOT_A_REST)

        v_lo = log.verdict(Q.REST_IS_NOT_A_REST, lo)
        v_hi = log.verdict(Q.REST_IS_NOT_A_REST, hi)
        self.assertEqual(v_lo.outcome, Outcome.DECIDED)
        self.assertIs(v_lo.value, True)
        self.assertEqual(v_lo.reason, REFUSAL)

        self.assertEqual(v_hi.outcome, Outcome.DECIDED)
        self.assertIs(v_hi.value, False)
        self.assertEqual(v_hi.reason, "rest")

    def test_two_separate_rests_no_overlap_are_both_kept(self):
        """⚠️ THE CONTROL THAT CAN FAIL. Two `restWhole` boxes far enough
        apart that they do not touch (IoU exactly 0.0) — the shape a genuine
        two-voice bar produces (each voice's own whole-bar rest at a
        different rung) and the shape 1,284 of 1,713 same-class Brahms pairs
        actually are. Neither is refused for being a duplicate."""
        log = Log()
        a = _rest_box(log, 0, "restWhole", x_c=100.0, y_c=100.0, score=0.5)
        b = _rest_box(log, 1, "restWhole", x_c=900.0, y_c=100.0, score=0.6)
        _run(log, Q.REST_IS_NOT_A_REST)

        v_a = log.verdict(Q.REST_IS_NOT_A_REST, a)
        v_b = log.verdict(Q.REST_IS_NOT_A_REST, b)
        self.assertIs(v_a.value, False)
        self.assertEqual(v_a.reason, "rest")
        self.assertIs(v_b.value, False)
        self.assertEqual(v_b.reason, "rest")

    def test_overlapping_boxes_of_different_classes_neither_survives(self):
        """A role-twin pair (`rest8th`/`rest16th`) at high overlap (IoU
        ~0.98) — the shape the ROADMAP 2.15 diagnosis's OWN highest-overlap
        crop shows (one hook-shaped mark, two nearly-coincident boxes).
        `Q.DURATION` has not run yet (`adjudicate.ORDER` schedules
        `Q.REST_IS_NOT_A_REST` before it), so this decision cannot read a
        beats figure — it reads the CLASS, and a class disagreement is
        CANNOT TELL (CLAUDE.md rule 8): both are refused rather than one
        being picked."""
        log = Log()
        a = _rest_box(log, 0, "rest8th", x_c=100.0, y_c=100.0,
                     w_c=40.0, h_c=60.0, score=0.43)
        b = _rest_box(log, 1, "rest16th", x_c=101.0, y_c=100.0,
                     w_c=39.0, h_c=60.0, score=0.37)
        _run(log, Q.REST_IS_NOT_A_REST)

        v_a = log.verdict(Q.REST_IS_NOT_A_REST, a)
        v_b = log.verdict(Q.REST_IS_NOT_A_REST, b)
        self.assertIs(v_a.value, True)
        self.assertEqual(v_a.reason, REFUSAL)
        self.assertIs(v_b.value, True)
        self.assertEqual(v_b.reason, REFUSAL)

    def test_a_three_way_same_class_cluster_keeps_exactly_one(self):
        """Three mutually-overlapping `restWhole` boxes (a heavier
        fragmentation than the two-box named example) — exactly the
        HIGHEST-confidence one survives, not zero and not more than one."""
        log = Log()
        a = _rest_box(log, 0, "restWhole", x_c=100.0, y_c=100.0, score=0.4)
        b = _rest_box(log, 1, "restWhole", x_c=130.0, y_c=100.0, score=0.7)
        c = _rest_box(log, 2, "restWhole", x_c=160.0, y_c=100.0, score=0.5)
        _run(log, Q.REST_IS_NOT_A_REST)

        survivors = [g for g in (a, b, c)
                    if log.verdict(Q.REST_IS_NOT_A_REST, g).value is False]
        self.assertEqual(survivors, [b])
        for g in (a, c):
            v = log.verdict(Q.REST_IS_NOT_A_REST, g)
            self.assertIs(v.value, True)
            self.assertEqual(v.reason, REFUSAL)

    def test_the_verdict_names_which_box_it_lost_to(self):
        """The record should say WHY, not just THAT — `detail["duplicate_
        of"]` is the surviving box's own observation id, an openable fact
        rather than a bare boolean."""
        log = Log()
        lo = _rest_box(log, 0, "restWhole", x_c=100.0, y_c=100.0, score=0.5)
        hi = _rest_box(log, 1, "restWhole", x_c=140.0, y_c=100.0, score=0.6)
        _run(log, Q.REST_IS_NOT_A_REST)
        v_lo = log.verdict(Q.REST_IS_NOT_A_REST, lo)
        hi_box = log.rows(Q.GLYPH_BOX, hi)[-1]
        self.assertEqual(v_lo.detail.get("duplicate_of"), hi_box.id)
        self.assertIn(hi_box.id, v_lo.used)


# ─────────────────────────────────────────────────────────────────────────────
# export consequence — the bar sums once, not twice
# ─────────────────────────────────────────────────────────────────────────────

def _duplicate_bar(*, refuse_gi=None, second_cls="restWhole"):
    """A bar with TWO measure-length rests sharing the one voice — the
    ROADMAP 2.15 shape: `_bar_holds_out`'s lone-measure-rest branch only
    fires at `len(stream) == 1`, so two of them are summed literally.
    `refuse_gi`, if given, adds the `Q.REST_IS_NOT_A_REST` verdict
    `adjudicate_rest_is_not_a_rest` would file — proven in
    `TestDuplicateRestAdjudication` above — so this fixture exercises
    EXPORT's own, already-shipped consumer (`export._place_notes`) rather
    than re-deriving the adjudicator's answer by hand.
    """
    page = _bar([])
    _add_rest(page, 5, "restWhole",
             {"beats": 4.0, "written": 4.0, "dots": 0, "is_rest": True,
              "measure_rest": True})
    _add_rest(page, 6, second_cls,
             {"beats": 4.0, "written": 4.0, "dots": 0, "is_rest": True,
              "measure_rest": True})
    if refuse_gi is not None:
        sub = f"glyph/0/0/0/0/{refuse_gi}"
        page["record"]["verdicts"].append(
            _vrd(950, sub, Q.REST_IS_NOT_A_REST, True, reason=REFUSAL))
    return page


class TestDuplicateRestExport(unittest.TestCase):

    def test_UNREPAIRED_two_measure_rests_in_one_voice_are_held_out(self):
        """⚠️ THE BUG ITSELF, DOCUMENTED. With no `Q.REST_IS_NOT_A_REST`
        refusal (today's tree before ADJUDICATE ever decides one — the
        starting point ROADMAP 2.15 named), two DECIDED measure rests are
        neither one LONE the way `_bar_holds_out` requires, so both are
        summed at 4.0 quarters each and the bar is held out as a bar that
        does not add up — the exact double-count this item exists to fix."""
        _xml, rep = SX.to_musicxml(_duplicate_bar())
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(rep["written"].get("measure_rests_read", 0), 0)
        self.assertEqual(rep["bars_held_out_sum"]["noteheads_and_rests"], 2)

    def test_REPAIRED_one_rest_is_written_and_the_bar_sums_once(self):
        """With the refusal `adjudicate_rest_is_not_a_rest` files (glyph 5,
        the lower-priority box in `TestDuplicateRestAdjudication`'s own
        shape), EXPORT drops it before duration or placement ever sees it —
        `export._place_notes` already honours a decided `Q.REST_IS_NOT_A_
        REST`, so no export-side change was needed. Exactly one `<rest
        measure="yes">` is written and the bar is the SAME lone-measure-rest
        case CLAUDE.md §10 names, whatever the meter."""
        xml, rep = SX.to_musicxml(_duplicate_bar(refuse_gi=5))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        self.assertEqual(rep["written"].get("measure_rests_read", 0), 1)
        self.assertEqual(
            rep["notes_not_written"].get(f"not_a_rest:{REFUSAL}"), 1)
        rests = ET.fromstring(xml).findall(".//note/rest")
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].get("measure"), "yes")

    def test_a_disagreeing_pair_writes_neither_and_is_counted(self):
        """The `neither decides` shape: two overlapping boxes of DIFFERENT
        classes are both refused (`TestDuplicateRestAdjudication`'s
        role-twin test) — EXPORT writes zero rests for them and counts both
        under the SAME named refusal, rather than guessing which class was
        right."""
        page = _bar([])
        _add_rest(page, 5, "rest8th",
                 {"beats": 0.5, "written": 0.5, "dots": 0, "is_rest": True})
        _add_rest(page, 6, "rest16th",
                 {"beats": 0.25, "written": 0.25, "dots": 0, "is_rest": True})
        for gi in (5, 6):
            page["record"]["verdicts"].append(
                _vrd(960 + gi, f"glyph/0/0/0/0/{gi}", Q.REST_IS_NOT_A_REST,
                     True, reason=REFUSAL))
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"].get("rests", 0), 0)
        self.assertEqual(
            rep["notes_not_written"].get(f"not_a_rest:{REFUSAL}"), 2)


if __name__ == "__main__":
    unittest.main()
