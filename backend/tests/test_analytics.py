"""Tests for analytics module."""

import pytest
from dataclasses import dataclass
from typing import Optional
from modules.analytics import _generate_suggestions, _assign_split


# ---------------------------------------------------------------------------
# Fake KnowledgePattern for testing
# ---------------------------------------------------------------------------

@dataclass
class FakePattern:
    instrument: Optional[str]
    difference_type: str
    occurrence_count: int
    accept_count: int
    reject_count: int
    edit_count: int = 0


# ---------------------------------------------------------------------------
# _generate_suggestions
# ---------------------------------------------------------------------------

class TestGenerateSuggestions:
    def test_suggests_auto_accept_for_high_accept_rate(self):
        patterns = [FakePattern("violin", "note", 10, 10, 0)]
        suggestions = _generate_suggestions(patterns)
        assert any("auto-accept" in s.lower() for s in suggestions)
        assert any("violin" in s for s in suggestions)

    def test_suggests_prompt_review_for_high_reject_rate(self):
        patterns = [FakePattern("piano", "rhythm", 10, 0, 10)]
        suggestions = _generate_suggestions(patterns)
        assert any("prompt" in s.lower() for s in suggestions)
        assert any("rhythm" in s for s in suggestions)

    def test_no_suggestion_below_threshold(self):
        # Only 4 occurrences — below the 5-occurrence minimum
        patterns = [FakePattern("piano", "note", 4, 4, 0)]
        suggestions = _generate_suggestions(patterns)
        assert len(suggestions) == 0

    def test_no_suggestion_for_mixed_rate(self):
        # 50% accept rate — neither high enough for auto-accept nor low enough for prompt review
        patterns = [FakePattern("piano", "note", 10, 5, 5)]
        suggestions = _generate_suggestions(patterns)
        assert len(suggestions) == 0

    def test_zero_occurrence_skipped(self):
        patterns = [FakePattern("piano", "note", 0, 0, 0)]
        suggestions = _generate_suggestions(patterns)
        assert len(suggestions) == 0

    def test_none_instrument_shows_all_instruments(self):
        patterns = [FakePattern(None, "dynamic", 10, 10, 0)]
        suggestions = _generate_suggestions(patterns)
        assert any("all instruments" in s for s in suggestions)

    def test_multiple_patterns(self):
        patterns = [
            FakePattern("violin", "note", 20, 20, 0),   # suggest auto-accept
            FakePattern("piano", "beam", 20, 0, 20),     # suggest prompt review
        ]
        suggestions = _generate_suggestions(patterns)
        assert len(suggestions) == 2


# ---------------------------------------------------------------------------
# _assign_split
# ---------------------------------------------------------------------------

class TestAssignSplit:
    def test_returns_valid_split_values(self):
        from modules import analytics
        analytics._split_counter = 0
        for _ in range(30):
            result = _assign_split()
            assert result in ("train", "val", "test")

    def test_approximate_80_10_10_ratio(self):
        from modules import analytics
        analytics._split_counter = 0
        counts = {"train": 0, "val": 0, "test": 0}
        n = 100
        for _ in range(n):
            counts[_assign_split()] += 1
        # Allow ±5% tolerance
        assert 75 <= counts["train"] <= 85
        assert 8 <= counts["val"] <= 12
        assert 8 <= counts["test"] <= 12

    def test_test_on_multiples_of_10(self):
        from modules import analytics
        analytics._split_counter = 9  # next call increments to 10
        result = _assign_split()
        assert result == "test"

    def test_val_on_9_mod_10(self):
        from modules import analytics
        analytics._split_counter = 8  # next call increments to 9
        result = _assign_split()
        assert result == "val"
