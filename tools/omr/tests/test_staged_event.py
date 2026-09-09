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


def _head(log, gi, x, w=20, head="noteheadBlack"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, head, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (head, x - w // 2, 0, w, 16),
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


class TestTheDivisiGuardIsReportedAsMissing(unittest.TestCase):
    """⚠️ AN EARLIER DRAFT WROTE `divisi_guard: "ran"` WHEREVER STEM ROWS
    MERELY EXISTED — a field claiming a check that never happened, which is
    exactly what this record exists to make impossible. The legacy rule
    refuses to merge two same-x noteheads whose STEMS POINT OPPOSITE WAYS (two
    divisi voices, not one chord); that tier is not built here, so what is
    reported is the state of the INPUT it would need.
    """

    def test_it_never_claims_to_have_run(self):
        log = Log()
        _head(log, 0, 100)
        _head(log, 1, 102)
        v = _events(log)
        self.assertEqual(v.detail["divisi_guard"], "not_implemented")

    def test_the_stem_evidence_state_is_reported(self):
        log = Log()
        _head(log, 0, 100)
        _head(log, 1, 102)
        v = _events(log)
        self.assertEqual(v.detail["stem_evidence"], State.ABSENT.value)


if __name__ == "__main__":
    unittest.main()
