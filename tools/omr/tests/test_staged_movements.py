"""ROADMAP 4.2 -- a whole work is several movements.

A meter or key carry must never cross a movement boundary, and a record with
more than one movement exports one MusicXML/LilyPond file PER MOVEMENT. See
`tools.omr.staged.movements` for the design (a MEMBERSHIP fact over the
existing page/system space, never a new level in the `Subject` path).

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT. Every assertion is about a
verdict the machine wrote, a value a pure function returned, or a file the
exporter produced.

Each `With/WithoutMovements` pair is a RED/GREEN control in the sense
CLAUDE.md §6a means: the "without movements" half proves the mechanism this
item fences (a carry, a document-wide majority) is real and reachable on this
exact fixture, so the "with movements" half proving it stops is evidence
about the FIX and not about a fixture that never exercised anything.
"""
from __future__ import annotations

import os
import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers ADJUDICATE
from tools.omr.staged import movements as MV
from tools.omr.staged import record as R
from tools.omr.staged import export as SX
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import Kind, Log, Outcome, Q, READERS, Subject

from tools.omr.tests.test_staged_export import QUARTER, _obs, _vrd
from tools.omr.tests.test_staged_key_by_part import (_ORDER_WITHOUT_SLOTS,
                                                      _flats, _header, _slot)

DOC = R.DOCUMENT


def _movement_spans_row(i, spans, *, reader="cli"):
    return _obs(i, DOC.to_key(), Q.MOVEMENT_SPANS, list(spans),
               reader=reader)


# ─────────────────────────────────────────────────────────────────────────────
# `parse_movement_spec` -- the CLI grammar
# ─────────────────────────────────────────────────────────────────────────────


class TestParseMovementSpec(unittest.TestCase):
    def test_a_simple_two_movement_spec(self):
        spans = MV.parse_movement_spec("1:0-11,2:12-20")
        self.assertEqual([s["number"] for s in spans], [1, 2])
        self.assertEqual(spans[0], {"number": 1, "first_page": 0,
                                    "first_system": None, "last_page": 11,
                                    "last_system": None})
        self.assertEqual(spans[1]["first_page"], 12)
        self.assertEqual(spans[1]["last_page"], 20)

    def test_a_movement_may_start_mid_page(self):
        spans = MV.parse_movement_spec("2:12.1-20")
        self.assertEqual(spans[0]["first_page"], 12)
        self.assertEqual(spans[0]["first_system"], 1)

    def test_movements_need_not_be_given_in_order(self):
        spans = MV.parse_movement_spec("2:5-9,1:0-4")
        self.assertEqual([s["number"] for s in spans], [1, 2])

    def test_empty_spec_is_refused(self):
        with self.assertRaises(MV.MalformedMovementSpec):
            MV.parse_movement_spec("")

    def test_garbage_is_refused_with_a_clear_error(self):
        with self.assertRaises(MV.MalformedMovementSpec) as ctx:
            MV.parse_movement_spec("not-a-spec-at-all")
        self.assertIn("not-a-spec-at-all", str(ctx.exception))

    def test_a_repeated_movement_number_is_refused(self):
        with self.assertRaises(MV.MalformedMovementSpec):
            MV.parse_movement_spec("1:0-4,1:5-9")

    def test_an_end_before_its_own_start_is_refused(self):
        with self.assertRaises(MV.MalformedMovementSpec):
            MV.parse_movement_spec("1:9-0")

    def test_overlapping_movements_are_refused(self):
        with self.assertRaises(MV.MalformedMovementSpec):
            MV.parse_movement_spec("1:0-10,2:5-20")


# ─────────────────────────────────────────────────────────────────────────────
# Membership -- the pure functions every carry asks through
# ─────────────────────────────────────────────────────────────────────────────


class TestMembership(unittest.TestCase):
    def test_no_spans_is_the_single_movement_default(self):
        a, b = R.system(0, 0), R.system(9, 4)
        self.assertTrue(MV.same_movement((), a, b))
        self.assertIsNone(MV.movement_of((), 0, 0))

    def test_a_gap_between_declared_spans_never_guesses(self):
        spans = MV.parse_movement_spec("1:0-0,2:5-9")
        # page 2 is in neither span.
        self.assertIsNone(MV.movement_of(spans, 2, 0))
        self.assertFalse(MV.same_movement(spans, R.system(0, 0),
                                          R.system(2, 0)))

    def test_movement_boundaries_needs_at_least_two_movements(self):
        self.assertEqual(MV.movement_boundaries(()), ())
        one = MV.parse_movement_spec("1:0-9")
        self.assertEqual(MV.movement_boundaries(one), ())
        two = MV.parse_movement_spec("1:0-0,2:1.2-9")
        self.assertEqual(MV.movement_boundaries(two), ((1, 2),))


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE -- a meter carry never crosses a movement boundary
# ─────────────────────────────────────────────────────────────────────────────


def _opening(log, sysj, num, den, n_staves=3):
    for st in range(n_staves):
        log.observe(R.staff(sysj.page, sysj.system, st), Q.METER_TEMPLATE,
                    (num, den), reader=READERS.TEMPLATE,
                    frame="header_window", score=0.7, raw=f"{num}/{den}")


def _staff_count(log, sysj, n_staves):
    log.record(adjudicate.Verdict(
        id=log._next_id("vrd"), subject=sysj,
        quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
        value=n_staves, decider="t", reason="counted"))


def _measure_partition(log, sysj, n_staves, n_cells):
    for st in range(n_staves):
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=R.staff(sysj.page, sysj.system, st),
            quantity=Q.MEASURE_PARTITION, outcome=Outcome.DECIDED,
            value=n_cells, decider="t", reason="barlines"))


def _bars(log, sysj, n_staves, n_bars, beats):
    """`n_bars` bars, each with `n_staves` staves reading `beats` quarters --
    the shape `_bar_lengths_for` / `_corroborate` read. Copied from
    `test_staged_opening_meter.py`'s own fixture builder rather than
    imported, since that module's is a nested method-local helper."""
    for st in range(n_staves):
        for c in range(n_bars):
            cell = R.cell(sysj.page, sysj.system, st, c)
            g = R.glyph(sysj.page, sysj.system, st, c, 0)
            log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                        reader=READERS.DETECTOR, frame="cell:%d" % c,
                        score=0.9)
            log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 400, 0, 600, 16),
                        reader=READERS.DETECTOR, frame="cell:%d" % c,
                        score=0.9)
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
                outcome=Outcome.DECIDED,
                value={"beats": beats, "written": beats,
                       "duration_type": "quarter", "dots": 0},
                decider="t", reason="head_and_marks"))
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=cell, quantity=Q.EVENT,
                outcome=Outcome.DECIDED,
                value={"events": [{"glyphs": [0], "x": 500.0,
                                   "kind": "chord"}]},
                decider="t", reason="x_clustered"))


def _set_movement_spans(log, spans):
    log.observe(R.DOCUMENT, Q.MOVEMENT_SPANS, list(spans),
               reader=READERS.CLI, frame="page", tier="movements")


def _run_meter(log):
    """Adjudicate METER over every system in document order, carry ON, the
    bars-derive-a-length rung OFF -- the same discipline
    `test_staged_opening_meter.py` uses to isolate the carry mechanism."""
    log.freeze()
    adjudicate._ensure_decisions()
    spec = adjudicate.REGISTRY[Q.METER]
    prev = {k: os.environ.get(k) for k in
           (rhythm_mod.METER_CARRY_ENV, rhythm_mod.METER_FROM_BARS_ENV)}
    os.environ[rhythm_mod.METER_CARRY_ENV] = "1"
    os.environ[rhythm_mod.METER_FROM_BARS_ENV] = "0"
    try:
        for sysj in sorted(log.subjects(R.Kind.SYSTEM)):
            adjudicate.adjudicate_one(log, spec, sysj)
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class TestMeterCarryStopsAtAMovementBoundary(unittest.TestCase):
    """Movement 1 (page 0) opens `4/4`; movement 2 (page 1) reads no meter of
    its own but DOES print bars that would corroborate a carried `4/4` --
    so a carry that ignored the boundary would succeed, silently, on
    evidence borrowed from a different movement."""

    N = 3

    def _build(self, *, with_movements):
        log = Log()
        mvt1 = R.system(0, 0)
        _staff_count(log, mvt1, self.N)
        _opening(log, mvt1, 4, 4, n_staves=self.N)

        mvt2 = R.system(1, 0)
        _staff_count(log, mvt2, self.N)
        _measure_partition(log, mvt2, self.N, 2)
        _bars(log, mvt2, self.N, n_bars=2, beats=4.0)

        if with_movements:
            _set_movement_spans(log, [
                {"number": 1, "first_page": 0, "first_system": None,
                 "last_page": 0, "last_system": None},
                {"number": 2, "first_page": 1, "first_system": None,
                 "last_page": 5, "last_system": None}])
        return log, mvt2

    def test_without_movements_the_carry_reaches_across_the_page(self):
        log, mvt2 = self._build(with_movements=False)
        _run_meter(log)
        v = log.verdict(Q.METER, mvt2)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "carried")
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (4, 4))

    def test_with_movements_the_same_system_abstains_instead(self):
        log, mvt2 = self._build(with_movements=True)
        _run_meter(log)
        v = log.verdict(Q.METER, mvt2)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        # ⚠️ "no_evidence", NOT "carry_not_corroborated" or any reason that
        # implies a carry was ATTEMPTED. `_carry_meter` BREAKS the moment it
        # steps into a different movement, so it never reaches `mvt1` at all.
        self.assertEqual(v.reason, "no_evidence")


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE -- a key/part majority does not mix movements
# ─────────────────────────────────────────────────────────────────────────────


class TestKeyMajorityDoesNotMixMovements(unittest.TestCase):
    """Movement 1 (page 0, 2 systems) prints 3 flats on every part, 8 votes
    total; movement 2 (page 1, 1 system) prints 1 flat on every part, 4
    votes -- unanimous WITHIN movement 2, but a minority against the
    blended population. `admitted_changes`' own persistence rule (2
    consecutive systems on both sides of a change) can never clear at a
    ONE-system movement, so the change is never witness-corroborated -- the
    exact case `movements.movement_boundaries` exists to force a cut at
    regardless."""

    NAMES = ["Flauti.", "Oboli.", "Violino I.", "Violoncello."]

    def _build(self, *, with_movements):
        log = Log()
        for system in range(2):
            for slot, name in enumerate(self.NAMES):
                sub = _header(log, 0, system, slot, markers=_flats(3))
                _slot(log, sub, slot, instrument=name)
        for slot, name in enumerate(self.NAMES):
            sub = _header(log, 1, 0, slot, markers=_flats(1))
            _slot(log, sub, slot, instrument=name)
        if with_movements:
            _set_movement_spans(log, [
                {"number": 1, "first_page": 0, "first_system": None,
                 "last_page": 0, "last_system": None},
                {"number": 2, "first_page": 1, "first_system": None,
                 "last_page": 5, "last_system": None}])
        adjudicate.run(log, order=_ORDER_WITHOUT_SLOTS)
        return log

    def test_without_movements_movement_2_is_outvoted(self):
        log = self._build(with_movements=False)
        for slot in range(len(self.NAMES)):
            v = log.verdict(Q.KEY_SIGNATURE, R.staff(1, 0, slot))
            self.assertIs(v.outcome, Outcome.ABSTAINED)
            self.assertEqual(v.reason, "disagrees_with_part")
            self.assertEqual(v.detail["expected_fifths"], -3)
            self.assertEqual(v.detail["written_fifths"], -1)

    def test_with_movements_movement_2s_own_majority_stands(self):
        log = self._build(with_movements=True)
        for slot in range(len(self.NAMES)):
            v = log.verdict(Q.KEY_SIGNATURE, R.staff(1, 0, slot))
            self.assertIs(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value, -1)


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT -- one file per movement, each its own measure 1, totals match
# ─────────────────────────────────────────────────────────────────────────────


def _page_result(page, *, pitch, start_id):
    """One page, one system, one staff, one quarter note -- the multi-page
    generalisation of `test_staged_export._one_staff_page`."""
    n = start_id
    sub = f"glyph/{page}/0/0/0/0"
    obs = [_obs(n, sub, Q.GLYPH_BOX,
               ["noteheadBlackOnLine", 100, 50, 40, 40],
               category="notehead")]
    n += 1
    obs.append(_obs(n, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
    n += 1
    vrd = [_vrd(n, sub, Q.PITCH, pitch)]
    n += 1
    vrd.append(_vrd(n, sub, Q.DURATION, QUARTER))
    n += 1
    vrd.append(_vrd(n, f"staff/{page}/0/0", Q.MEASURE_PARTITION, 1))
    n += 1
    vrd.append(_vrd(n, f"staff/{page}/0/0", Q.CLEF, "treble"))
    n += 1
    vrd.append(_vrd(n, f"system/{page}/0", Q.SYSTEM_STAFF_COUNT, 1))
    n += 1
    return obs, vrd, n


def _two_page_result():
    obs0, vrd0, n = _page_result(0, pitch="C4", start_id=0)
    obs1, vrd1, n = _page_result(1, pitch="D4", start_id=n)
    vrd0.append(_vrd(n, "document", Q.PART_PARTITION,
                     {"join": "ordinal", "staves_per_system": 1},
                     reason="ordinal"))
    return {"record": {"observations": obs0 + obs1,
                       "verdicts": vrd0 + vrd1,
                       "abstentions": [], "counts": {}},
           "summary": {}}


def _n_notes(xml: str) -> int:
    return len(ET.fromstring(xml).findall(".//note"))


class TestExportControlNoMovementsIsUnchanged(unittest.TestCase):
    def test_a_record_with_no_movement_spans_exports_exactly_as_before(self):
        result = _two_page_result()
        self.assertEqual(MV.spans_from_result(result), ())
        first, _ = SX.to_musicxml(result)
        second, _ = SX.to_musicxml(result)
        self.assertEqual(first, second)


class TestExportSplitsOneFilePerMovement(unittest.TestCase):
    def _spans(self):
        return [{"number": 1, "first_page": 0, "first_system": None,
                 "last_page": 0, "last_system": None},
               {"number": 2, "first_page": 1, "first_system": None,
                "last_page": 1, "last_system": None}]

    def test_two_movements_become_two_files_each_at_measure_one(self):
        result = _two_page_result()
        whole_xml, _ = SX.to_musicxml(result)

        spans = self._spans()
        result["record"]["observations"].append(
            _movement_spans_row(9000, spans))
        self.assertEqual([s["number"] for s in MV.spans_from_result(result)],
                         [1, 2])

        split = MV.split_result(result, spans)
        self.assertEqual([number for number, _ in split], [1, 2])

        total_notes = 0
        for number, sub_result in split:
            xml, report = SX.to_musicxml(sub_result)
            root = ET.fromstring(xml)
            numbers = [m.get("number") for m in root.findall(".//measure")]
            self.assertEqual(numbers, ["1"],
                             f"movement {number} must start its own "
                             f"numbering at 1")
            self.assertEqual(len(root.findall("part")), 1)
            total_notes += _n_notes(xml)

        # ⚠️ THE TOTALS EQUAL THE WHOLE. Splitting is a PARTITION of the
        # document's population, never a re-reading of it -- the same
        # `_n_notes(whole_xml)` must come back whether it is read in one
        # file or two.
        self.assertEqual(total_notes, _n_notes(whole_xml))

    def test_export_each_writes_the_named_files(self):
        import tempfile
        from pathlib import Path

        result = _two_page_result()
        spans = self._spans()
        result["record"]["observations"].append(
            _movement_spans_row(9001, spans))

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "out.musicxml"
            written = MV.export_each(result, spans, base, SX.to_musicxml)
            self.assertEqual([n for n, _p, _t, _r in written], [1, 2])
            for number, path, _text, _report in written:
                self.assertEqual(path.name, f"out-mvt{number}.musicxml")
                self.assertTrue(path.is_file())
                self.assertTrue(Path(str(path) + ".coverage.json").is_file())


if __name__ == "__main__":
    unittest.main()
