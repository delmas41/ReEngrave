"""The time-signature reader's RUNNER-UP score, kept instead of destroyed.

`locate_time_signature` slides every candidate meter template over one strip and
keeps the argmax. Every other score died in the comparison that used it, so a
0.51 winner over a 0.50 runner-up and a 0.79 over a 0.31 arrived downstream as
the same fact — while the module's own docstring says a bare NCC score is usable
here ONLY because the templates are proportionally comparable, which is exactly
the assumption a margin lets someone check, and that `min_score` sits at 0.50
with a thin margin behind it.

Cells are DRAWN from the module's own templates rather than loaded, so the
reading is exercised end to end (rescale, strip, match, floor, cut-stroke test)
against a meter known by construction.

⚠️ Run RED four ways — see the mutations named on each class.
"""

from __future__ import annotations

import numpy as np
import pytest

from tools.omr.time_signature_locator import (
    DEFAULT_LOCATOR_CONFIG as CONFIG,
    LocatedTimeSignature,
    _meter_templates,
    locate_time_signature,
    read_system_time_signatures,
    vote_system_time_signature,
)
from tools.omr.types import MeasureCell


SPACING = CONFIG.template_em_px / 4.0


def _cell_printing(raw: str | None) -> MeasureCell:
    """A header cell drawn at exactly template scale, printing `raw` (or
    nothing at all)."""
    height, width = int(SPACING * 14), int(SPACING * 30)
    ink = np.zeros((height, width), np.uint8)
    top = int(SPACING * 4)
    if raw is not None:
        template = next(t for (_n, _d, r), t in
                        _meter_templates(CONFIG.template_em_px,
                                         tuple(CONFIG.meters)) if r == raw)
        x0 = int(SPACING * 2)
        ink[top:top + template.shape[0], x0:x0 + template.shape[1]] = template
    image = 255 - ink
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=image, image_no_staff=image, bbox_page_px=(0, 0, width, height),
        staff_line_ys_canonical=[top + i * int(SPACING) for i in range(5)],
        upscale_factor=1.0,
    )


class TestTheRunnerUpSurvives:
    """Run RED by deleting the `replace(best, runner_up_raw=...)` block."""

    def test_a_reading_carries_what_came_second(self):
        read = locate_time_signature(_cell_printing("2/4"))
        assert (read.numerator, read.denominator) == (2, 4)
        assert read.runner_up_raw is not None
        assert read.runner_up_score < read.score
        assert read.score_margin == pytest.approx(
            read.score - read.runner_up_score, abs=1e-6)

    def test_the_margin_is_a_REAL_number_and_not_a_formality(self):
        """On a clean 2/4 the second-best template still scores ~0.72 against a
        1.00 winner — so "the winner cleared 0.50" was never the interesting
        statement about this reading, and it was the only one available."""
        read = locate_time_signature(_cell_printing("2/4"))
        assert read.runner_up_score > 0.5      # ...it clears the floor too
        assert read.score_margin > 0.1

    def test_as_dict_carries_it_where_it_carries_the_score(self):
        read = locate_time_signature(_cell_printing("3/4"))
        out = read.as_dict()
        assert out["runner_up_raw"] == read.runner_up_raw
        assert out["score_margin"] == pytest.approx(read.score_margin, abs=1e-4)

    def test_a_reading_with_no_second_template_records_no_runner_up(self):
        """Recording must not invent one. Nothing is asserted where there is
        nothing to assert."""
        read = LocatedTimeSignature(numerator=2, denominator=4, score=0.9,
                                    x_canonical=0, raw="2/4")
        assert read.runner_up_raw is None
        assert "runner_up_raw" not in read.as_dict()


class TestTheRefusalKeepsItsTable:
    """The return value of a refusal is None and can carry nothing, so the
    table goes in the trace. Run RED by deleting the `if trace is not None`
    block in `locate_time_signature`."""

    def test_a_page_printing_no_meter_records_what_it_scored(self):
        trace: dict = {}
        assert locate_time_signature(_cell_printing(None), trace=trace) is None
        assert trace["cleared_floor"] is False
        assert trace["floor"] == pytest.approx(CONFIG.min_score)
        # It scored every template it could fit, and every one of those numbers
        # used to be lost the moment the floor was applied.
        assert trace["n_templates"] > 1
        assert trace["scores"], "the table that was refused"

    def test_the_table_is_ordered_the_way_the_argmax_ordered_it(self):
        """A record that could disagree with the decision would be worse than
        none: the first row must be the meter that was actually returned."""
        trace: dict = {}
        read = locate_time_signature(_cell_printing("6/8"), trace=trace)
        assert trace["cleared_floor"] is True
        assert trace["scores"][0]["raw"] == read.raw
        assert trace["scores"][0]["score"] >= trace["scores"][1]["score"]


class TestTheVoteRecordsItsOpposition:
    """⚠️ The record goes in `trace`, NOT in the returned meter dict.

    `transcribe` copies that dict onto every measure of the system, so a scalar
    added to it is written once per bar — which cost 9% of the scan page's
    result JSON while these four rode in it. Pinned below, because the cheap
    place to put a record is exactly the expensive place to put it.

    Run RED by deleting the `if trace is not None` block in
    `vote_system_time_signature`.
    """

    @staticmethod
    def _read(raw, num, den, score, margin=0.2):
        return LocatedTimeSignature(numerator=num, denominator=den, score=score,
                                    x_canonical=0, raw=raw,
                                    runner_up_raw="9/4",
                                    runner_up_score=score - margin,
                                    score_margin=margin)

    def test_the_meter_that_came_second_in_VOTES_is_named(self):
        reads = [self._read("3/4", 3, 4, 0.7)] * 3 + [self._read("6/8", 6, 8, 0.9)]
        trace: dict = {}
        meter = vote_system_time_signature(reads, trace=trace)
        assert (meter["numerator"], meter["denominator"]) == (3, 4)
        assert trace["runner_up_meter"] == "6/8"
        assert trace["runner_up_votes"] == 1

    def test_the_winners_own_template_margins_are_summarised(self):
        """A different question from the vote margin: a system where every
        staff reads 3/4 at 0.61 over a 0.60 runner-up and one where they read it
        over a 0.20 agree equally, and are not equally sure."""
        reads = [self._read("3/4", 3, 4, 0.7, margin=m) for m in (0.05, 0.3, 0.4)]
        trace: dict = {}
        vote_system_time_signature(reads, trace=trace)
        assert trace["median_score_margin"] == pytest.approx(0.3)
        assert trace["min_score_margin"] == pytest.approx(0.05)

    def test_an_unopposed_vote_names_no_runner_up(self):
        trace: dict = {}
        vote_system_time_signature([self._read("3/4", 3, 4, 0.7)] * 3,
                                   trace=trace)
        assert "runner_up_meter" not in trace

    def test_the_METER_DICT_carries_no_record_at_all(self):
        """The per-bar cost, pinned. Anything added to this dict is written
        once per measure of the system; a record belongs where the vote is
        recorded once."""
        reads = [self._read("3/4", 3, 4, 0.7)] * 3 + [self._read("6/8", 6, 8, 0.9)]
        meter = vote_system_time_signature(reads, trace={})
        for key in ("runner_up_meter", "runner_up_votes",
                    "median_score_margin", "min_score_margin"):
            assert key not in meter, f"{key} would be copied onto every bar"


class TestTheSystemEvidenceReachesAnAbstainingSystem:
    """Run RED by deleting the `if evidence is not None` block in
    `read_system_time_signatures`."""

    def test_a_system_that_votes_no_meter_still_records_its_tables(self):
        """The case the return value structurally cannot hold: a system with no
        agreed meter is simply absent from the result, and that is where the
        per-staff scores are most worth having."""
        cells = {0: _cell_printing(None), 1: _cell_printing(None)}
        evidence: dict = {}
        out = read_system_time_signatures(cells, {0: [0, 1]}, evidence=evidence)
        assert out == {}
        assert evidence[0]["voted"] is False
        assert set(evidence[0]["staves"]) == {0, 1}
        assert evidence[0]["staves"][0]["cleared_floor"] is False

    def test_a_system_that_votes_records_them_too(self):
        cells = {0: _cell_printing("2/4"), 1: _cell_printing("2/4")}
        evidence: dict = {}
        out = read_system_time_signatures(cells, {0: [0, 1]}, evidence=evidence)
        assert (out[0]["numerator"], out[0]["denominator"]) == (2, 4)
        assert evidence[0]["voted"] is True
        assert evidence[0]["staves"][1]["cleared_floor"] is True
        # The vote's own record rides here, once per system.
        assert "median_score_margin" in evidence[0]["vote"]
