"""Tests for claude_vision module."""

import pytest
from modules.claude_vision import _parse_claude_response, build_comparison_prompt


class TestParseClaudeResponse:
    def test_valid_json_with_difference(self):
        text = '{"has_difference": true, "difference_type": "note", "description": "missing note", "confidence": 0.9, "is_omr_error": true}'
        result = _parse_claude_response(text)
        assert result is not None
        assert result["difference_type"] == "note"
        assert result["confidence"] == 0.9

    def test_no_difference_returns_none(self):
        text = '{"has_difference": false, "difference_type": "note", "description": "", "confidence": 0.1, "is_omr_error": false}'
        assert _parse_claude_response(text) is None

    def test_strips_markdown_fences(self):
        text = '```json\n{"has_difference": true, "difference_type": "rhythm", "description": "wrong note value", "confidence": 0.8, "is_omr_error": true}\n```'
        result = _parse_claude_response(text)
        assert result is not None
        assert result["difference_type"] == "rhythm"

    def test_extracts_json_from_prose(self):
        text = 'Looking at the images, I can see a clear difference. {"has_difference": true, "difference_type": "dynamic", "description": "missing forte", "confidence": 0.75, "is_omr_error": true} End of analysis.'
        result = _parse_claude_response(text)
        assert result is not None
        assert result["difference_type"] == "dynamic"

    def test_invalid_json_returns_none(self):
        assert _parse_claude_response("not json at all") is None

    def test_empty_string_returns_none(self):
        assert _parse_claude_response("") is None


class TestBuildComparisonPrompt:
    def test_includes_metadata(self):
        metadata = {"title": "Moonlight Sonata", "composer": "Beethoven", "era": "classical", "instrument": "piano"}
        prompt = build_comparison_prompt(metadata, measure_num=5)
        assert "Moonlight Sonata" in prompt
        assert "Beethoven" in prompt
        assert "classical" in prompt
        assert "piano" in prompt
        assert "5" in prompt

    def test_includes_json_schema_instructions(self):
        prompt = build_comparison_prompt({}, measure_num=1)
        assert "has_difference" in prompt
        assert "difference_type" in prompt
        assert "confidence" in prompt

    def test_unknown_metadata_graceful(self):
        prompt = build_comparison_prompt({}, measure_num=1)
        assert "Unknown" in prompt
