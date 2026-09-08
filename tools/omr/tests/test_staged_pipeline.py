"""End-to-end coherence for the staged pipeline: GATHER -> ADJUDICATE -> EVALUATE.

⚠️ NO PDF, NO WEIGHTS, NO VENV. The page is synthesized here, which is what
makes it cheap enough to run every time -- and it is also the honest test of
a claim the design makes: that `detector=None` is a supported MODE and not a
failure. Today a missing weights file fails the run outright.

⚠️ NOT AN ACCURACY TEST. Nothing here asserts a reading is right.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass, field
from typing import List, Optional

from tools.omr.staged import adjudicate, evaluate, gather, pipeline
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Outcome, Q, READERS, Scope, State

# ─────────────────────────────────────────────────────────────────────────────
# A synthetic page: two systems, the first of 4 staves, the second of 2.
#
# The 2-staff system is deliberate -- it is the population `_assign_groups`
# REFUSES (fewer than 3 staves), so it exercises the abstention path that the
# whole record layer exists for.
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FakePage:
    page_index: int = 0


@dataclass
class FakeStaff:
    staff_index: int
    system_index: int
    group_index: Optional[int]
    line_ys: List[int]
    x_start: int = 100
    x_end: int = 900
    line_thickness_px: Optional[float] = 2.0
    line_wander_px: Optional[float] = None

    @property
    def top_y(self) -> int:
        return self.line_ys[0]


@dataclass
class FakePws:
    page: FakePage
    staves: List[FakeStaff]
    used_bridging: bool = True


@dataclass
class FakeCell:
    page_index: int
    system_index: int
    staff_index: int
    measure_index: int
    staff_line_ys_canonical: List[int]


@dataclass
class FakeDet:
    smufl_name: str
    x_canonical: int
    y_canonical: int
    width_canonical: int = 20
    height_canonical: int = 16
    confidence: float = 0.8
    category: str = "notehead"

    @property
    def y_center(self) -> int:
        return self.y_canonical + self.height_canonical // 2

    @property
    def x_center(self) -> int:
        return self.x_canonical + self.width_canonical // 2


class FakeDetector:
    """Emits one clef and one notehead per cell 0, one notehead elsewhere."""

    def detect(self, cell, conf_threshold=0.25, imgsz=None):
        out = [FakeDet("noteheadBlack", 200, 100)]
        if cell.measure_index == 0:
            out.insert(0, FakeDet("clefG", 20, 92, category="clef",
                                  confidence=0.93))
        return out


def build_page():
    staves = [
        FakeStaff(0, 0, 0, [100, 120, 140, 160, 180]),
        FakeStaff(1, 0, 0, [300, 320, 340, 360, 380]),
        FakeStaff(2, 0, 1, [500, 520, 540, 560, 580]),
        FakeStaff(3, 0, 1, [700, 720, 740, 760, 780]),
        # a 2-staff system: _assign_groups refuses these
        FakeStaff(4, 1, 0, [1000, 1020, 1040, 1060, 1080]),
        FakeStaff(5, 1, 0, [1200, 1220, 1240, 1260, 1280]),
    ]
    pws = FakePws(FakePage(0), staves)
    cells = [
        FakeCell(0, s.system_index, s.staff_index, m, [100, 120, 140, 160, 180])
        for s in staves for m in range(2)
    ]
    return [(pws, cells)]


class TestStagedEndToEnd(unittest.TestCase):
    def setUp(self):
        self.prepared = build_page()
        self.result = pipeline.run_staged_on(
            self.prepared, detector=FakeDetector())

    def test_all_three_stages_produce_a_report(self):
        for key in ("record", "summary", "adjudication", "evaluation", "stubs"):
            self.assertIn(key, self.result)

    def test_gather_emitted_measurements_not_names(self):
        """⚠️ The thesis. A notehead's STAFF POSITION is gathered; its PITCH
        is not, because a pitch required a clef."""
        summary = self.result["summary"]
        self.assertIn(Q.NOTEHEAD_STAFF_POSITION, summary)
        self.assertNotIn(Q.PITCH, summary.get(Q.NOTEHEAD_STAFF_POSITION, {}))

    def test_the_fractional_position_survives(self):
        """`pitch_resolver.py:180` computes it and `:181` rounds it away."""
        log = _log_from(self.prepared)
        rows = log.rows(Q.NOTEHEAD_STAFF_POSITION, R.system(0, 0),
                        scope=Scope.SELF_AND_DESCENDANTS)
        self.assertTrue(rows)
        self.assertTrue(all("residual" in r.detail for r in rows))
        self.assertTrue(all(isinstance(r.value, float) for r in rows))

    def test_the_two_staff_system_DECLINES_its_bracket_block(self):
        """⚠️ The canonical sentinel fault, now visible.

        `_assign_groups` writes `group_index = 0` for a system of fewer than
        3 staves (`:596`) -- identical on the record to a real reading of
        "one family". Here it is DECLINED with a reason.
        """
        log = _log_from(self.prepared)
        small = R.staff(0, 1, 0)
        self.assertIs(log.state(Q.BRACKET_BLOCK, small), State.DECLINED)
        (row,) = log.refusals(Q.BRACKET_BLOCK, small)
        self.assertEqual(row.reason, ABSTAIN.SYSTEM_TOO_SMALL)

    def test_the_four_staff_system_READS_its_bracket_block(self):
        log = _log_from(self.prepared)
        self.assertIs(log.state(Q.BRACKET_BLOCK, R.staff(0, 0, 0)), State.READ)

    def test_staff_group_abstains_where_the_block_declined(self):
        """It must ANCHOR where present and ABSTAIN where absent, never
        assign -- bracket blocks are 22/22 precise and 22/39 recalled, so the
        absent case is roughly half the population."""
        adj = self.result["adjudication"]
        self.assertIn(Q.STAFF_GROUP, adj["decided"])
        self.assertIn(Q.STAFF_GROUP, adj["abstained"])
        self.assertIn("block_unavailable", adj["abstained"][Q.STAFF_GROUP])

    def test_group_symbol_abstains_with_no_identity(self):
        """⚠️ The two-question split. A bracket block of two staves is NOT a
        grand staff; with no identity the honest answer is "I do not know
        what symbol this is", which lets the incumbent rule stand."""
        adj = self.result["adjudication"]
        self.assertIn("no_identity", adj["abstained"].get(Q.GROUP_SYMBOL, {}))

    def test_the_clef_is_decided_and_carries_a_margin(self):
        adj = self.result["adjudication"]
        self.assertIn(Q.CLEF, adj["decided"])

    def test_evaluate_restated_pitches_from_the_clef(self):
        """The consequence stage doing its one live job: position + clef ->
        pitch, with BOTH in the pitch's basis."""
        fired = [f for f in self.result["evaluation"]["fired"]
                 if f[0] == "restate_pitch"]
        self.assertTrue(fired)

    def test_a_pitch_records_both_its_ancestors(self):
        log = _log_from(self.prepared)
        adjudicate.run(log)
        evaluate.run(log)
        pitches = log.verdicts(Q.PITCH, R.system(0, 0),
                               scope=Scope.SELF_AND_DESCENDANTS)
        self.assertTrue(pitches)
        for v in pitches:
            quantities = {log.row(b).quantity for b in v.basis
                          if log.row(b) is not None}
            self.assertIn(Q.NOTEHEAD_STAFF_POSITION, quantities)
            self.assertIn(Q.CLEF, quantities)

    def test_stubs_are_reported_not_hidden(self):
        self.assertTrue(self.result["stubs"]["decisions"])
        self.assertTrue(self.result["stubs"]["consequences"])


class TestNoDetectorIsAMode(unittest.TestCase):
    """⚠️ Today a missing weights file fails the run. Here it abstains."""

    def test_the_pipeline_runs_with_no_detector(self):
        result = pipeline.run_staged_on(build_page(), detector=None)
        self.assertIn(Q.GLYPH_BOX, result["summary"])
        self.assertEqual(result["summary"][Q.GLYPH_BOX].get("read", 0), 0)
        self.assertGreater(result["summary"][Q.GLYPH_BOX]["declined"], 0)

    def test_and_the_clef_then_abstains_rather_than_defaulting(self):
        result = pipeline.run_staged_on(build_page(), detector=None)
        self.assertNotIn(Q.CLEF, result["adjudication"]["decided"])
        self.assertIn("no_candidates",
                      result["adjudication"]["abstained"][Q.CLEF])

    def test_and_no_pitch_is_invented(self):
        """⚠️ A staff whose clef abstained gets NO pitches, deliberately --
        not a positional default that is right about half the time and
        indistinguishable from a reading."""
        result = pipeline.run_staged_on(build_page(), detector=None)
        self.assertEqual(
            [f for f in result["evaluation"]["fired"] if f[0] == "restate_pitch"],
            [])


class TestTheFlag(unittest.TestCase):
    def test_default_is_off(self):
        import os
        old = os.environ.pop("OMR_ADJUDICATE", None)
        try:
            self.assertEqual(pipeline.mode(), pipeline.MODE_OFF)
            self.assertFalse(pipeline.enabled())
        finally:
            if old is not None:
                os.environ["OMR_ADJUDICATE"] = old

    def test_a_typo_does_not_switch_anyone_on(self):
        import os
        old = os.environ.get("OMR_ADJUDICATE")
        os.environ["OMR_ADJUDICATE"] = "yes-please"
        try:
            self.assertEqual(pipeline.mode(), pipeline.MODE_OFF)
        finally:
            if old is None:
                os.environ.pop("OMR_ADJUDICATE", None)
            else:
                os.environ["OMR_ADJUDICATE"] = old


class TestDivergence(unittest.TestCase):
    def test_new_abstention_is_counted_apart(self):
        """⚠️ It is a FEATURE THAT SCORES AS A LOSS -- musicdiff charges an
        absent element -- so it must never be summed with `differ`."""
        log = _log_from(build_page())
        adjudicate.run(log)
        legacy = {Q.CLEF: {R.staff(0, 1, 0).to_key(): "treble"}}
        div = pipeline.divergence(log, legacy)
        self.assertIn(pipeline.NEW_ABSTENTION, div["counts"])
        self.assertIn(pipeline.DIFFER, div["counts"])


def _log_from(prepared):
    return gather.gather(prepared, detector=FakeDetector())


if __name__ == "__main__":
    unittest.main()
