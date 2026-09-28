"""ROADMAP 4.2b -- detect a movement boundary off the page.

`tools.omr.staged.adjudicators.movement.adjudicate_movement_start` reads
GATHER only (a tempo word at a system's own header, a time signature
STATEMENT on nearly every staff, a margin-label reset, a wider first-system
indent) and, where at least two of those cues agree, produces the SAME
`Q.MOVEMENT_SPANS` fact `--movements` files by hand -- as a VERDICT rather
than a GATHER observation, because it runs in ADJUDICATE.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c); every
assertion is about a verdict the machine wrote or a pure function's return
value.

Each `Log`-based test builds the SMALLEST GATHER shape the cue it exercises
actually reads -- see `tools.omr.staged.adjudicators.movement`'s own
docstring for what each cue is and why a tempo word alone must not be
enough (the module's own worked counter-example, Litolff Beethoven 5 p.62's
mid-movement "Tempo I." plus a fresh meter, is exactly this test's shape).
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers ADJUDICATE
from tools.omr.staged import movements as MV
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import header as header_mod
from tools.omr.staged.adjudicators import movement as MOV
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import Kind, Log, Observation, Outcome, Q, READERS

DOC = R.DOCUMENT
SPEC = adjudicate.REGISTRY[Q.MOVEMENT_SPANS]


def _obs(subject, quantity, value, *, reader, frame, **detail):
    """A bare `Observation`, filed straight into a `Log` -- the same shape
    `Log.observe` produces, built by hand so a test can control exactly
    which cue's rows exist and which do not."""
    return Observation(id="", subject=subject, quantity=quantity, value=value,
                       reader=reader, frame=frame, detail=dict(detail))


def _staff_lines(log, page, sysnum, n_staves):
    for st in range(n_staves):
        log.observe(R.staff(page, sysnum, st), Q.STAFF_LINES,
                    [10, 20, 30, 40, 50], reader=READERS.GEOMETRY,
                    frame="page")


def _tempo_word(log, page, sysnum, *, staff=0, text="Andante con moto"):
    log.observe(R.glyph(page, sysnum, staff, 0, 0), Q.DIRECTION_WORD, text,
                reader=READERS.SURYA, frame="page", category="tempo")


def _meter_statement(log, page, sysnum, n_staves, *, glyph="timeSig3"):
    for st in range(n_staves):
        log.observe(R.staff(page, sysnum, st), Q.METER_GLYPH, glyph,
                    reader=READERS.DETECTOR, frame="cell:0")


def _margin_labels(log, page, sysnum, texts):
    for st, text in enumerate(texts):
        log.observe(R.staff(page, sysnum, st), Q.MARGIN_LABEL, text,
                    reader=READERS.TEXT_LAYER, frame="system_margin")


def _human_spans(log, spans):
    log.observe(DOC, Q.MOVEMENT_SPANS, list(spans), reader=READERS.CLI,
               frame="page", tier="movements")


def _decide(log):
    log.freeze()
    return adjudicate.adjudicate_one(log, SPEC, DOC)


# ─────────────────────────────────────────────────────────────────────────────
# Pure cue functions -- no Log at all
# ─────────────────────────────────────────────────────────────────────────────


class TestPureCues(unittest.TestCase):
    def test_tempo_word_needs_cell_zero(self):
        here = _obs(R.glyph(0, 1, 0, 0, 0), Q.DIRECTION_WORD, "Allegro",
                   reader=READERS.SURYA, frame="page", category="tempo")
        mid_system = _obs(R.glyph(0, 1, 0, 7, 0), Q.DIRECTION_WORD, "Tempo I.",
                         reader=READERS.SURYA, frame="page", category="tempo")
        self.assertTrue(MOV._tempo_word_fires([here]))
        self.assertFalse(MOV._tempo_word_fires([mid_system]))
        self.assertFalse(MOV._tempo_word_fires([]))

    def test_tempo_word_needs_the_tempo_category(self):
        dynamic = _obs(R.glyph(0, 1, 0, 0, 0), Q.DIRECTION_WORD, "dolce",
                      reader=READERS.SURYA, frame="page",
                      category="expression")
        self.assertFalse(MOV._tempo_word_fires([dynamic]))

    def test_meter_statement_needs_a_majority_at_cell_zero(self):
        rows = [_obs(R.staff(0, 1, st), Q.METER_GLYPH, "timeSig3",
                    reader=READERS.DETECTOR, frame="cell:0")
               for st in range(2)]
        self.assertTrue(MOV._meter_statement_fires(rows, n_staves=3))
        self.assertFalse(MOV._meter_statement_fires(rows, n_staves=10))
        self.assertFalse(MOV._meter_statement_fires(rows, n_staves=0))

    def test_meter_statement_ignores_a_mid_system_change(self):
        """The Litolff p.62 shape the module docstring names: a meter glyph
        exists on the staff but at a LATER cell, never cell 0."""
        rows = [_obs(R.staff(0, 1, 0), Q.METER_GLYPH, "timeSig3",
                    reader=READERS.DETECTOR, frame="cell:8")]
        self.assertFalse(MOV._meter_statement_fires(rows, n_staves=1))

    def test_label_reset_needs_coverage_and_either_absence_or_length(self):
        full = [_obs(R.staff(0, 1, st), Q.MARGIN_LABEL, name,
                    reader=READERS.TEXT_LAYER, frame="system_margin")
               for st, name in enumerate(["Violino I", "Violino II", "Viola"])]
        self.assertTrue(MOV._label_reset_fires(full, [], n_staves=3))

        abbrev_before = [_obs(R.staff(0, 0, st), Q.MARGIN_LABEL, name,
                             reader=READERS.TEXT_LAYER, frame="system_margin")
                        for st, name in enumerate(["Vl.1", "Vl.2", "Va."])]
        self.assertTrue(MOV._label_reset_fires(full, abbrev_before,
                                               n_staves=3))

        same_every_system = abbrev_before
        self.assertFalse(MOV._label_reset_fires(abbrev_before,
                                                same_every_system,
                                                n_staves=3))

        sparse = full[:1]   # 1 of 3 staves -- below LABEL_COVERAGE_MIN
        self.assertFalse(MOV._label_reset_fires(sparse, [], n_staves=3))

    def test_indent_needs_a_baseline_and_a_real_widening(self):
        self.assertTrue(MOV._indent_fires(cur_x=230.0, baseline_x=200.0))
        self.assertFalse(MOV._indent_fires(cur_x=205.0, baseline_x=200.0))
        self.assertFalse(MOV._indent_fires(cur_x=None, baseline_x=200.0))
        self.assertFalse(MOV._indent_fires(cur_x=230.0, baseline_x=None))

    def test_is_movement_start_needs_the_declared_minimum(self):
        self.assertFalse(MOV.is_movement_start(
            {"tempo_word": True, "meter_statement": False,
             "label_reset": False, "wider_indent": False}))
        self.assertTrue(MOV.is_movement_start(
            {"tempo_word": True, "meter_statement": True,
             "label_reset": False, "wider_indent": False}))

    def test_spans_from_boundaries_matches_the_movements_spec_shape(self):
        systems = [R.system(0, 0), R.system(0, 1), R.system(1, 0)]
        spans = MOV.spans_from_boundaries(systems, [systems[1]])
        self.assertEqual(spans, [
            {"number": 1, "first_page": 0, "first_system": 0,
             "last_page": 0, "last_system": 0},
            {"number": 2, "first_page": 0, "first_system": 1,
             "last_page": 1, "last_system": 0},
        ])


# ─────────────────────────────────────────────────────────────────────────────
# The decision, over a real (if tiny) Log
# ─────────────────────────────────────────────────────────────────────────────


class TestASystemWithSeveralCuesTogetherIsAStart(unittest.TestCase):
    """Tempo heading + meter statement + a full-label reset, all on the
    SAME system -- the brief's own worked shape."""

    def _build(self):
        log = Log()
        _staff_lines(log, 0, 0, 3)          # movement 1's own opening system
        _staff_lines(log, 0, 1, 3)          # the candidate movement-2 start
        _tempo_word(log, 0, 1)
        _meter_statement(log, 0, 1, 3)
        _margin_labels(log, 0, 1, ["Violino I", "Violino II", "Viola"])
        return log

    def test_it_decides_two_movements(self):
        v = _decide(self._build())
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "detected")
        self.assertEqual(v.value, [
            {"number": 1, "first_page": 0, "first_system": 0,
             "last_page": 0, "last_system": 0},
            {"number": 2, "first_page": 0, "first_system": 1,
             "last_page": 0, "last_system": 1},
        ])

    def test_the_boundary_system_names_its_own_fired_cues(self):
        v = _decide(self._build())
        boundary = v.detail["boundaries"][0]
        self.assertEqual(boundary["system"], R.system(0, 1).to_key())
        self.assertEqual(set(boundary["cues"]),
                         {"tempo_word", "meter_statement", "label_reset"})


class TestATempoWordAloneIsNotAStart(unittest.TestCase):
    """⚠️ THE CONTROL THAT CAN FAIL. A single cue -- exactly the shape a
    mid-movement tempo change prints (CLAUDE.md's own Litolff p.62 example)
    -- must NOT cross the threshold. An implementation that treated any one
    cue as sufficient fails this test and only this test."""

    def _build(self):
        log = Log()
        _staff_lines(log, 0, 0, 3)
        _staff_lines(log, 0, 1, 3)
        _tempo_word(log, 0, 1)
        # No meter statement, no label reset, no indent row at all.
        return log

    def test_it_abstains_rather_than_declaring_a_second_movement(self):
        v = _decide(self._build())
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_boundary_detected")

    def test_the_tempo_cue_alone_is_visible_in_the_refusal(self):
        v = _decide(self._build())
        cues = v.detail["cues_by_system"][R.system(0, 1).to_key()]
        self.assertTrue(cues["tempo_word"])
        self.assertFalse(cues["meter_statement"])
        self.assertFalse(cues["label_reset"])


class TestHumanMovementsOverridesDetection(unittest.TestCase):
    """A human `--movements` wins even where detection would otherwise have
    called the same system a start on its own evidence."""

    def _build(self):
        log = Log()
        _staff_lines(log, 0, 0, 3)
        _staff_lines(log, 0, 1, 3)
        _tempo_word(log, 0, 1)
        _meter_statement(log, 0, 1, 3)
        _margin_labels(log, 0, 1, ["Violino I", "Violino II", "Viola"])
        _human_spans(log, [
            {"number": 1, "first_page": 0, "first_system": None,
             "last_page": 3, "last_system": None}])
        return log

    def test_detection_abstains_in_favour_of_the_human_answer(self):
        v = _decide(self._build())
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "human_spans_supplied")

    def test_the_meter_carry_reads_the_HUMAN_spans_not_the_detected_ones(self):
        """The integration seam this item's brief flagged as possibly
        needing a non-obvious ordering: `rhythm._movement_spans` reads the
        GATHER observation first and never even asks for the verdict."""
        log = self._build()
        log.freeze()
        meter_spec = adjudicate.REGISTRY[Q.METER]
        ev = adjudicate.Evidence(log, DOC, meter_spec)
        self.assertEqual(rhythm_mod._movement_spans(ev),
                         ({"number": 1, "first_page": 0,
                           "first_system": None, "last_page": 3,
                           "last_system": None},))
        key_spec = adjudicate.REGISTRY[Q.PART_KEY]
        ev2 = adjudicate.Evidence(log, DOC, key_spec)
        self.assertEqual(header_mod._movement_spans(ev2),
                         rhythm_mod._movement_spans(ev))


class TestDetectionFallsBackToTheCarriesWhenDecided(unittest.TestCase):
    """With NO human `--movements`, a DECIDED detection verdict reaches the
    meter/key carries through `ev.verdict()` -- which only works because
    `adjudicate.ORDER` runs `movement_start` before them."""

    def _build(self):
        log = Log()
        _staff_lines(log, 0, 0, 3)
        _staff_lines(log, 0, 1, 3)
        _tempo_word(log, 0, 1)
        _meter_statement(log, 0, 1, 3)
        _margin_labels(log, 0, 1, ["Violino I", "Violino II", "Viola"])
        return log

    def test_the_meter_carry_sees_the_detected_spans(self):
        log = self._build()
        _decide(log)   # files the movement_start VERDICT; log stays frozen
        meter_spec = adjudicate.REGISTRY[Q.METER]
        ev = adjudicate.Evidence(log, DOC, meter_spec)
        self.assertEqual(rhythm_mod._movement_spans(ev), (
            {"number": 1, "first_page": 0, "first_system": 0,
             "last_page": 0, "last_system": 0},
            {"number": 2, "first_page": 0, "first_system": 1,
             "last_page": 0, "last_system": 1}))


class TestARecordWithNoCuesIsOneMovement(unittest.TestCase):
    """No direction word, no meter glyph, no margin label anywhere -- the
    record this whole item must leave untouched. Byte-identical export
    follows from the carries reading `()` exactly as they did before
    `movement_start` existed, which is what the second test here checks
    directly rather than round-tripping a whole MusicXML file for it."""

    def _build(self):
        log = Log()
        _staff_lines(log, 0, 0, 3)
        _staff_lines(log, 0, 1, 3)
        return log

    def test_it_abstains_with_no_boundary_detected(self):
        v = _decide(self._build())
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_boundary_detected")
        self.assertEqual(v.detail["systems_checked"], 1)

    def test_the_carries_still_read_the_single_movement_default(self):
        log = self._build()
        _decide(log)
        meter_spec = adjudicate.REGISTRY[Q.METER]
        ev = adjudicate.Evidence(log, DOC, meter_spec)
        self.assertEqual(rhythm_mod._movement_spans(ev), ())
        key_spec = adjudicate.REGISTRY[Q.PART_KEY]
        ev2 = adjudicate.Evidence(log, DOC, key_spec)
        self.assertEqual(header_mod._movement_spans(ev2), ())

    def test_a_single_system_document_is_too_few_to_check(self):
        log = Log()
        _staff_lines(log, 0, 0, 3)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "too_few_systems")


class TestExportReadsADecidedVerdictFromA_LoadedRecordToo(unittest.TestCase):
    """`tools.omr.staged` CLI's own multi-file export split, and the
    standalone `tools.omr.staged.export --movements`-less re-export of an
    already-gathered record, both go through `movements.spans_from_result`
    on the loaded JSON dict -- never through a live `Evidence`. That
    function used to look at `observations` only, so a DETECTED boundary
    (a VERDICT) was invisible to it even though the ADJUDICATE decision
    that found it had already run on every gather."""

    def _result_for(self, log):
        return {"record": log.to_json()}

    def test_a_decided_detection_verdict_drives_the_split(self):
        log = Log()
        _staff_lines(log, 0, 0, 3)
        _staff_lines(log, 0, 1, 3)
        _tempo_word(log, 0, 1)
        _meter_statement(log, 0, 1, 3)
        _margin_labels(log, 0, 1, ["Violino I", "Violino II", "Viola"])
        _decide(log)
        spans = MV.spans_from_result(self._result_for(log))
        self.assertEqual([s["number"] for s in spans], [1, 2])

    def test_a_human_observation_still_wins_over_a_recorded_verdict(self):
        """Cannot happen today (the decision itself abstains the moment a
        human observation exists, so the two never coexist) -- checked
        anyway, because `spans_from_result` re-derives its own answer from
        the JSON rather than trusting that invariant from a distance."""
        log = Log()
        _staff_lines(log, 0, 0, 3)
        _staff_lines(log, 0, 1, 3)
        _human_spans(log, [{"number": 1, "first_page": 0,
                            "first_system": None, "last_page": 9,
                            "last_system": None}])
        result = self._result_for(log)
        result["record"]["verdicts"].append({
            "id": "vrd:999999", "subject": DOC.to_key(),
            "quantity": Q.MOVEMENT_SPANS, "outcome": "decided",
            "value": [{"number": 1, "first_page": 0, "first_system": None,
                      "last_page": 0, "last_system": None},
                     {"number": 2, "first_page": 1, "first_system": None,
                      "last_page": 9, "last_system": None}],
            "decider": "adjudicate_movement_start", "reason": "detected",
            "considered": [], "used": [], "missing": [], "declined": [],
            "excluded": [], "correlated": [], "candidates": [], "basis": [],
            "margin": None, "supersedes": None, "detail": {}})
        spans = MV.spans_from_result(result)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["last_page"], 9)

    def test_no_verdict_and_no_observation_is_still_empty(self):
        log = Log()
        _staff_lines(log, 0, 0, 3)
        result = self._result_for(log)
        self.assertEqual(MV.spans_from_result(result), ())


class TestTheDecisionIsWiredCorrectly(unittest.TestCase):
    def test_it_is_not_a_stub_and_declares_what_it_reads(self):
        self.assertFalse(SPEC.stub)
        for q in (Q.DIRECTION_WORD, Q.METER_GLYPH, Q.MARGIN_LABEL,
                 Q.STAFF_LINES, Q.STAFF_EXTENT, Q.MOVEMENT_SPANS):
            self.assertIn(q, SPEC.wants)

    def test_it_runs_before_the_meter_and_key_decisions(self):
        order = list(adjudicate.ORDER)
        i = order.index(Q.MOVEMENT_SPANS)
        self.assertLess(i, order.index(Q.METER))
        self.assertLess(i, order.index(Q.KEY_SIGNATURE))
        self.assertLess(i, order.index(Q.SYSTEM_KEY))


if __name__ == "__main__":
    unittest.main()
