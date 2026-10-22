"""Which glyphs of a bar sound TOGETHER — and the bar sum that needs them.

⚠️ COHERENCE, NOT ACCURACY.

⚠️ THE POINT OF THIS FILE. Until 2026-09-09 chord grouping existed in exactly
one place — `export._events`, at serialisation time — so every stage before
EXPORT counted each chord member as a separate time-advancing event. The
pipeline's own bar-sum check (`consequences.reconcile_duration`) therefore
could not match the meter on any bar holding a chord, and said nothing about
it: an inflated total simply never equals the meter and the rule does nothing.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, evaluate
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, State

CELL = R.cell(0, 0, 0, 0)


def _head(log, gi, x, w=20, head="noteheadBlack", y=0):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, head, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (head, x - w // 2, y, w, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return g


def _rest(log, gi, x, kind="restQuarter"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.REST, kind, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (kind, x - 10, 0, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return g


def _events(log):
    log.freeze()
    adjudicate._ensure_decisions()
    v = adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.EVENT], CELL)
    return v


class TestAnEventIsWhatSoundsTogether(unittest.TestCase):

    def test_two_noteheads_in_one_column_are_ONE_event(self):
        log = Log()
        _head(log, 0, 100)
        _head(log, 1, 102)          # a chord: same column, 2px apart
        v = _events(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "x_clustered")
        self.assertEqual(v.detail["n_glyphs"], 2)
        self.assertEqual(v.detail["n_events"], 1)
        self.assertEqual(v.value["events"][0]["glyphs"], [0, 1])

    def test_two_noteheads_a_passage_apart_are_TWO_events(self):
        log = Log()
        _head(log, 0, 100)
        _head(log, 1, 400)
        v = _events(log)
        self.assertEqual(v.detail["n_events"], 2)
        self.assertEqual(v.detail["n_chords"], 0)

    def test_a_rest_is_its_own_event(self):
        """Nothing sounds together with silence."""
        log = Log()
        _head(log, 0, 100)
        _rest(log, 1, 100)          # same column, still not a chord
        v = _events(log)
        self.assertEqual(v.detail["n_events"], 2)
        kinds = sorted(e["kind"] for e in v.value["events"])
        self.assertEqual(kinds, ["chord", "rest"])

    def test_an_empty_bar_abstains_rather_than_reporting_no_events(self):
        log = Log()
        log.observe(R.glyph(0, 0, 0, 0, 0), Q.GLYPH_BOX, ("clefG", 0, 0, 10, 10),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        v = _events(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "nothing_to_group")

    def test_events_come_out_in_x_order(self):
        log = Log()
        _head(log, 0, 400)
        _head(log, 1, 100)
        _head(log, 2, 250)
        v = _events(log)
        xs = [e["x"] for e in v.value["events"]]
        self.assertEqual(xs, sorted(xs))


class TestTheClusteringRuleIsTheEXPORTERS(unittest.TestCase):
    """⚠️ RULE PARITY, MEASURED ON ONE POPULATION — which is the only claim
    that can be made honestly.

    The record's grouping and `export._events` run over DIFFERENT populations:
    this decision groups every notehead we READ, the exporter groups only the
    ones it can WRITE. Measured on two real pages, that accounts for most of
    the difference (24 chord members against the export's 16; 172 against 102)
    and a residual of 1 and 7 remains, which is the exporter's own filter
    chain and NOT the clustering. Two candidate explanations for the residual
    were tested and refuted: the tolerance being computed over a different set
    of widths (identical numbers), and the exporter admitting narrowed
    durations (overshoots — 24 and 115).

    So what is pinned here is the RULE, on one population, against the legacy
    function itself. Making the two agree outright means the exporter
    consuming this verdict, which is a separate change.
    """

    def test_same_detections_same_grouping(self):
        from tools.omr.voicing import group_chords_in_measure
        xs = [100, 103, 240, 244, 246, 500]
        log = Log()
        for i, x in enumerate(xs):
            _head(log, i, x)
        mine = _events(log).value["events"]
        mine_groups = [tuple(e["glyphs"]) for e in mine if e["kind"] == "chord"]

        dets = [{"category": "notehead", "class": "noteheadBlack",
                 "bbox": [x - 10, 0, 20, 16], "pitch": "C4",
                 "duration_beats": 1.0, "duration_type": "quarter", "dots": 0,
                 "index": i}
                for i, x in enumerate(xs)]
        legacy = group_chords_in_measure(dets)
        legacy_groups = [tuple(sorted(n["index"] for n in e["noteheads"]))
                         for e in legacy if e["kind"] == "chord"]
        self.assertEqual(mine_groups, legacy_groups)


class TestTheBarSumCountsAnEventOnce(unittest.TestCase):
    """The consumer that was silently broken."""

    def _cell_with_chord(self):
        """A 2/4 bar: a two-note chord of one quarter, plus a quarter.

        Summed over NOTEHEADS that is 3.0 and fits nothing; summed over
        EVENTS it is 2.0 and fits the bar exactly.
        """
        log = Log()
        g0 = _head(log, 0, 100)
        g1 = _head(log, 1, 102)
        g2 = _head(log, 2, 400)
        log.freeze()
        for g in (g0, g1, g2):
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
                outcome=Outcome.DECIDED,
                value={"beats": 1.0, "written": 1.0, "duration_type": "quarter",
                       "dots": 0},
                decider="t", reason="head_and_marks"))
        return log

    def test_ungrouped_the_bar_would_be_three_beats(self):
        """The control: without the grouping the total is the double-count."""
        log = self._cell_with_chord()
        notes = consequences._standing(log, CELL, Q.DURATION)
        naive = sum(float((v.value or {}).get("beats") or 0.0) for v in notes)
        self.assertEqual(naive, 3.0)

    def test_grouped_the_chord_contributes_once(self):
        log = self._cell_with_chord()
        adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.EVENT], CELL)
        notes = consequences._standing(log, CELL, Q.DURATION)
        current = {v.id: v.value for v in notes}
        total = consequences._event_totals(log, CELL, notes, current)
        self.assertEqual(total, 2.0)

    def test_NO_event_verdict_means_NO_repair(self):
        """⚠️ It refuses rather than falling back to the per-notehead sum. A
        bar whose grouping is unknown is a bar whose sum is unknown, and
        repairing against a possibly-inflated total is the laundered guess the
        rule's `bound` exists to prevent."""
        log = self._cell_with_chord()          # no EVENT verdict recorded
        notes = consequences._standing(log, CELL, Q.DURATION)
        current = {v.id: v.value for v in notes}
        self.assertIsNone(
            consequences._event_totals(log, CELL, notes, current))

    def test_a_duration_the_grouping_never_mentions_is_still_time(self):
        """Dropping it would understate the bar as silently as the
        double-count overstated it."""
        log = self._cell_with_chord()
        adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.EVENT], CELL)
        orphan = R.glyph(0, 0, 0, 0, 99)
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=orphan, quantity=Q.DURATION,
            outcome=Outcome.DECIDED,
            value={"beats": 0.5, "written": 0.5, "duration_type": "eighth",
                   "dots": 0},
            decider="t", reason="head_and_marks"))
        notes = consequences._standing(log, CELL, Q.DURATION)
        current = {v.id: v.value for v in notes}
        self.assertEqual(
            consequences._event_totals(log, CELL, notes, current), 2.5)


def _events_after_stems(log):
    """⚠️ `Q.STEM_DIRECTION` FIRST, because the guard reads its VERDICT and
    not the stem rows. Running only `Q.EVENT` — which every other test here
    does, correctly, since they have no stems — would report
    `no_direction_decided` and pass a divisi test for the wrong reason."""
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.STEM_DIRECTION,))
    return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.EVENT], CELL)


def _stem(log, x, y, w=3, h=60):
    """One CV stem stroke on the cell, in the shape `gather_cv_lines` emits."""
    log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                frame="cell:0", x0=x, x1=x + w, y_center=y + h / 2,
                image="no_staff", staff_lines_erased=True)


class TestTheDivisiGuardIsLIVE(unittest.TestCase):
    """⚠️ IT REPORTED `not_implemented` UNTIL ITS INPUT EXISTED, 2026-09-10.
    An earlier draft wrote `divisi_guard: "ran"` wherever stem ROWS merely
    existed — a field claiming a check that never happened — so the field was
    deliberately made to say so. `Q.STEM_DIRECTION` now decides, and the field
    reports what the guard DID.

    ⚠️ THE STATE OF THE INPUT IS STILL REPORTED BESIDE IT, because a guard
    that ran over a bar whose stems were never read has separated nothing and
    must not read as a clean bill.
    """

    def test_with_no_stems_it_says_no_direction_was_decided(self):
        log = Log()
        _head(log, 0, 100)
        _head(log, 1, 102)
        v = _events(log)
        self.assertEqual(v.detail["divisi_guard"], "no_direction_decided")
        self.assertEqual(v.detail["divisi_separated"], 0)

    def test_the_stem_evidence_state_is_reported(self):
        log = Log()
        _head(log, 0, 100)
        _head(log, 1, 102)
        v = _events(log)
        self.assertEqual(v.detail["stem_evidence"], State.ABSENT.value)

    # ⚠️ THE GEOMETRY IS REAL DIVISI AND THE FIXTURE HAD TO BE FIXED TO BE SO.
    # A first cut put both heads at one y with both stems between their boxes,
    # so EACH stem overlapped BOTH heads and every head abstained
    # `stems_disagree` -- the guard then saw no directions at all and merged,
    # which reads as the guard failing when it is the fixture that is not
    # divisi. An upper voice takes its stem on the RIGHT going up and a lower
    # voice on the LEFT going down, and the two heads are at different
    # PITCHES, which is what separates them.
    UPPER_X, LOWER_X = 100, 102        # boxes 90..110 and 92..112
    UPPER_Y, LOWER_Y = 0, 40           # ...at different heights

    def test_two_heads_at_one_x_on_OPPOSITE_stems_are_TWO_events(self):
        """⚠️ THE FAULT THE GUARD EXISTS FOR: x-only grouping merged two
        divisi voices into one "chord" and then mode-voted a single duration
        over the pair, corrupting both."""
        log = Log()
        _head(log, 0, self.UPPER_X, y=self.UPPER_Y)
        _head(log, 1, self.LOWER_X, y=self.LOWER_Y)
        _stem(log, 88, -60, h=64)           # touches the UPPER head, rising
        _stem(log, 111, 52, h=60)           # touches the LOWER head, falling
        v = _events_after_stems(log)
        self.assertEqual(v.detail["n_events"], 2, v.detail)
        self.assertEqual(v.detail["divisi_guard"], "ran")
        self.assertEqual(v.detail["divisi_separated"], 1)

    def test_the_SAME_direction_still_merges(self):
        """The positive control, and a battery of separation tests needs one:
        a guard that separated EVERYTHING would pass the test above."""
        log = Log()
        _head(log, 0, self.UPPER_X, y=self.UPPER_Y)
        _head(log, 1, self.LOWER_X, y=self.LOWER_Y)
        _stem(log, 88, -60, h=64)           # upper, rising
        _stem(log, 111, -60, h=104)         # lower, ALSO rising
        v = _events_after_stems(log)
        self.assertEqual(v.detail["divisi_separated"], 0, v.detail)
        self.assertEqual(v.detail["n_events"], 1, v.detail)

    def test_an_UNKNOWN_direction_never_blocks_a_merge(self):
        """⚠️ Exactly as `voicing._directions_conflict` does not. A head whose
        stem the CV rung missed must behave as it did before this quantity
        existed."""
        log = Log()
        _head(log, 0, self.UPPER_X, y=self.UPPER_Y)
        _head(log, 1, self.LOWER_X, y=self.LOWER_Y)
        _stem(log, 88, -60, h=64)           # only the UPPER head gets a stem
        v = _events_after_stems(log)
        self.assertEqual(v.detail["n_events"], 1, v.detail)

    def test_a_head_met_by_two_OPPOSING_stems_abstains_rather_than_voting(self):
        """⚠️ `stems_disagree` is not `no_stem`, and the exporter must be able
        to tell them apart: the first is ink we cannot read, the second is a
        whole note or a stem the CV rung missed. Picking one would hand the
        guard a confident wrong answer."""
        log = Log()
        _head(log, 0, 100)
        _stem(log, 92, -60)                 # both cross this head's box
        _stem(log, 108, 10)
        log.freeze()
        adjudicate._ensure_decisions()
        v = adjudicate.run(log, order=(Q.STEM_DIRECTION,))[0]
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "stems_disagree")


if __name__ == "__main__":
    unittest.main()
