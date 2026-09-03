"""`transcribe()`'s scan-vs-engraved weight routing seam.

Same style as TestResolveClefWeights in test_transcribe_helpers.py: the
routing decision is a small pure-ish helper (`_route_weights`) with an
injectable classifier, so every branch is tested without loading a model or
opening a PDF. The classifier itself is tested in test_input_domain.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.omr.input_domain import (
    DEFAULT_CLASSIFY_PAGES,
    DomainClassification,
    ENGRAVED,
    SCANNED,
    UNKNOWN,
)
from tools.omr.transcribe import (
    DEFAULT_WEIGHTS,
    ENGRAVED_WEIGHTS,
    _repo_root,
    _route_weights,
    _weight_routing_enabled,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("OMR_WEIGHT_ROUTING", raising=False)
    monkeypatch.delenv("OMR_ENGRAVED_WEIGHTS", raising=False)


def _classifier(verdict: str):
    """A fake classify_pdf_domain recording how it was called."""
    calls: list = []

    def classify(pdf_path, page_indices=None):
        calls.append({"pdf_path": pdf_path, "page_indices": page_indices})
        return DomainClassification(verdict, [], 1.0)

    classify.calls = calls
    return classify


class TestRoutingEnabled:
    def test_on_by_default(self, monkeypatch):
        assert _weight_routing_enabled() is True

    @pytest.mark.parametrize("off", ["0", "false", "no", "off", "False", " 0 "])
    def test_off_values(self, monkeypatch, off):
        monkeypatch.setenv("OMR_WEIGHT_ROUTING", off)
        assert _weight_routing_enabled() is False

    @pytest.mark.parametrize("on", ["1", "true", "yes", ""])
    def test_on_values(self, monkeypatch, on):
        monkeypatch.setenv("OMR_WEIGHT_ROUTING", on)
        assert _weight_routing_enabled() is True


class TestRouteWeights:
    def test_disabled_routing_uses_default_and_never_classifies(self, monkeypatch):
        monkeypatch.setenv("OMR_WEIGHT_ROUTING", "0")
        classify = _classifier(ENGRAVED)
        weights, prov = _route_weights(Path("x.pdf"), [0], classify=classify)
        assert weights == str(_repo_root() / DEFAULT_WEIGHTS)
        assert prov["mode"] == "disabled"
        assert classify.calls == []

    def test_scanned_routes_to_default(self):
        weights, prov = _route_weights(Path("x.pdf"), [0],
                                       classify=_classifier(SCANNED))
        assert weights == str(_repo_root() / DEFAULT_WEIGHTS)
        assert prov["mode"] == "routed"
        assert prov["verdict"] == SCANNED
        assert "scan" in prov["reason"]

    def test_unknown_abstains_to_default(self):
        weights, prov = _route_weights(Path("x.pdf"), [0],
                                       classify=_classifier(UNKNOWN))
        assert weights == str(_repo_root() / DEFAULT_WEIGHTS)
        assert prov["verdict"] == UNKNOWN
        assert "unknown" in prov["reason"]

    def test_engraved_routes_to_engraved_weights(self, monkeypatch, tmp_path):
        engraved = tmp_path / "engraved.pt"
        engraved.write_bytes(b"pt")
        monkeypatch.setenv("OMR_ENGRAVED_WEIGHTS", str(engraved))
        weights, prov = _route_weights(Path("x.pdf"), [0],
                                       classify=_classifier(ENGRAVED))
        assert weights == str(engraved)
        assert prov["verdict"] == ENGRAVED
        assert prov["weights"] == str(engraved)

    def test_engraved_env_override_wins_over_constant(self, monkeypatch, tmp_path):
        # Same as above but asserting the constant is NOT consulted: the env
        # candidate exists, the in-tree ENGRAVED_WEIGHTS need not.
        engraved = tmp_path / "override.pt"
        engraved.write_bytes(b"pt")
        monkeypatch.setenv("OMR_ENGRAVED_WEIGHTS", str(engraved))
        weights, _ = _route_weights(Path("x.pdf"), [0],
                                    classify=_classifier(ENGRAVED))
        assert weights == str(engraved)
        assert weights != str(_repo_root() / ENGRAVED_WEIGHTS)

    def test_missing_engraved_weights_fall_back_soft(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("OMR_ENGRAVED_WEIGHTS", str(tmp_path / "absent.pt"))
        weights, prov = _route_weights(Path("x.pdf"), [0],
                                       classify=_classifier(ENGRAVED))
        assert weights == str(_repo_root() / DEFAULT_WEIGHTS)
        assert "missing" in prov["reason"]
        assert "absent.pt" in prov["reason"]
        # The fallback is loud on stderr, once, but never an exception.
        assert "engraved weights not found" in capsys.readouterr().err

    def test_classification_sample_is_capped(self):
        classify = _classifier(SCANNED)
        pages = list(range(DEFAULT_CLASSIFY_PAGES + 40))
        _route_weights(Path("x.pdf"), pages, classify=classify)
        assert classify.calls[0]["page_indices"] == pages[:DEFAULT_CLASSIFY_PAGES]

    def test_classifies_the_pages_being_transcribed(self):
        classify = _classifier(SCANNED)
        _route_weights(Path("x.pdf"), [7, 8, 9], classify=classify)
        assert classify.calls[0]["page_indices"] == [7, 8, 9]

    def test_provenance_is_json_ready_and_names_the_weights(self, monkeypatch):
        for verdict in (SCANNED, ENGRAVED, UNKNOWN):
            weights, prov = _route_weights(Path("x.pdf"), [0],
                                           classify=_classifier(verdict))
            json.dumps(prov)
            assert prov["weights"] == weights
            assert "classification" in prov

    def test_routed_paths_are_absolute(self):
        weights, _ = _route_weights(Path("x.pdf"), [0],
                                    classify=_classifier(SCANNED))
        assert Path(weights).is_absolute()
