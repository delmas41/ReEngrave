"""Tests for main._mean_omr_confidence_for_page — the real (non-hardcoded)
confidence fed into FlaggedDifference.audiveris_confidence and, from there,
into apply_auto_accept.

Importing `main` mounts a StaticFiles app on Settings().upload_dir, so the
upload/export dirs are pointed at a throwaway tmp directory *before* import
rather than touching the repo's ./uploads.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from typing import Optional

import pytest

_tmp_root = tempfile.mkdtemp(prefix="reengrave-test-")
os.environ.setdefault("UPLOAD_DIR", os.path.join(_tmp_root, "uploads"))
os.environ.setdefault("EXPORT_DIR", os.path.join(_tmp_root, "exports"))
os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)
os.makedirs(os.environ["EXPORT_DIR"], exist_ok=True)

from main import _mean_omr_confidence_for_page  # noqa: E402


@dataclass
class FakeScore:
    """Stand-in for database.models.Score — only the field the function reads."""
    metadata_json: Optional[dict]


def _omr_json_with_confidences(tmp_path, page_confidences: dict[int, list[float]]) -> str:
    """Write a minimal transcribe.py-shaped OMR JSON with the given
    page_index -> [detection confidences] mapping.
    """
    pages = []
    for page_index, confidences in page_confidences.items():
        detections = [{"class": "noteheadBlack", "confidence": c} for c in confidences]
        pages.append({
            "page_index": page_index,
            "systems": [{
                "staves": [{
                    "measures": [{"detections": detections}],
                }],
            }],
        })
    path = os.path.join(tmp_path, "score.omr.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"pages": pages}, f)
    return path


class TestMeanOmrConfidenceForPage:
    def test_computes_mean_for_requested_page(self, tmp_path):
        omr_json_path = _omr_json_with_confidences(str(tmp_path), {0: [0.8, 0.9, 0.7]})
        score = FakeScore(metadata_json={"omr_json_path": omr_json_path})

        # page_number is 1-based; page_index 0 in the JSON is page 1.
        result = _mean_omr_confidence_for_page(score, page_number=1)
        assert result == pytest.approx(0.8)

    def test_different_pages_have_independent_confidence(self, tmp_path):
        omr_json_path = _omr_json_with_confidences(
            str(tmp_path), {0: [1.0, 1.0], 1: [0.2, 0.2]}
        )
        score = FakeScore(metadata_json={"omr_json_path": omr_json_path})

        assert _mean_omr_confidence_for_page(score, page_number=1) == pytest.approx(1.0)
        assert _mean_omr_confidence_for_page(score, page_number=2) == pytest.approx(0.2)

    def test_missing_omr_json_path_falls_back_to_half(self):
        score = FakeScore(metadata_json={})
        assert _mean_omr_confidence_for_page(score, page_number=1) == 0.5

    def test_no_metadata_json_falls_back_to_half(self):
        score = FakeScore(metadata_json=None)
        assert _mean_omr_confidence_for_page(score, page_number=1) == 0.5

    def test_nonexistent_file_falls_back_to_half(self):
        score = FakeScore(metadata_json={"omr_json_path": "/no/such/file.json"})
        assert _mean_omr_confidence_for_page(score, page_number=1) == 0.5

    def test_malformed_json_falls_back_to_half(self, tmp_path):
        path = os.path.join(str(tmp_path), "bad.omr.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        score = FakeScore(metadata_json={"omr_json_path": path})
        assert _mean_omr_confidence_for_page(score, page_number=1) == 0.5

    def test_page_with_no_detections_falls_back_to_half(self, tmp_path):
        omr_json_path = _omr_json_with_confidences(str(tmp_path), {0: []})
        score = FakeScore(metadata_json={"omr_json_path": omr_json_path})
        assert _mean_omr_confidence_for_page(score, page_number=1) == 0.5

    def test_page_not_found_in_json_falls_back_to_half(self, tmp_path):
        omr_json_path = _omr_json_with_confidences(str(tmp_path), {0: [0.9]})
        score = FakeScore(metadata_json={"omr_json_path": omr_json_path})
        # Only page_index 0 exists — page_number=5 -> page_index 4, missing.
        assert _mean_omr_confidence_for_page(score, page_number=5) == 0.5
