"""Weight routing on the STAGED path (roadmap 3.2, first half).

Same style as `test_weight_routing.py` (the legacy seam): the routing
decision is a small pure-ish function with an injectable classifier, so
every branch is tested without loading a model or opening a PDF.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.omr.input_domain import DomainClassification, ENGRAVED, SCANNED, UNKNOWN
from tools.omr.staged.weight_routing import resolve_staged_weights
from tools.omr.transcribe import DEFAULT_WEIGHTS, ENGRAVED_WEIGHTS, _repo_root


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("OMR_WEIGHT_ROUTING", raising=False)
    monkeypatch.delenv("OMR_ENGRAVED_WEIGHTS", raising=False)


def _classifier(verdict: str):
    calls = []

    def classify(pdf_path, page_indices=None):
        calls.append({"pdf_path": pdf_path, "page_indices": page_indices})
        return DomainClassification(verdict, [], 1.0)

    classify.calls = calls
    return classify


class TestExplicitWeightsAlwaysPin:
    """A real path is unconditional -- routing never runs, whatever the
    other flags say. This is the compatibility guarantee: nothing about a
    `--weights <file>` invocation before this landed changes."""

    def test_real_path_pins_with_route_weights_false(self):
        weights, prov, cls = resolve_staged_weights(
            Path("x.pdf"), [0], weights="/some/real.pt",
            route_weights=False)
        assert weights == "/some/real.pt"
        assert prov is None
        assert cls is None

    def test_real_path_pins_even_with_route_weights_true(self):
        classify = _classifier(ENGRAVED)
        weights, prov, cls = resolve_staged_weights(
            Path("x.pdf"), [0], weights="/some/real.pt",
            route_weights=True, classify=classify)
        assert weights == "/some/real.pt"
        assert prov is None
        assert cls is None
        assert classify.calls == []  # never even asked


class TestOmittedWeightsWithoutRouteWeightsIsUnchanged:
    """The compatibility guarantee for the OTHER pre-existing behaviour:
    `--weights` omitted and `--route-weights` not given must still mean
    "no detector", exactly as before this module existed."""

    def test_bare_omission_is_a_pure_no_op(self):
        classify = _classifier(SCANNED)
        weights, prov, cls = resolve_staged_weights(
            Path("x.pdf"), [0], weights=None, route_weights=False,
            classify=classify)
        assert weights is None
        assert prov is None
        assert cls is None
        assert classify.calls == []


class TestRoutingFires:
    """`--weights auto` or (`weights=None`, `route_weights=True`) both
    route -- the CLI maps both spellings onto this same call."""

    @pytest.mark.parametrize("weights_arg", ["auto", None])
    def test_scanned_routes_to_default(self, weights_arg):
        weights, prov, cls = resolve_staged_weights(
            Path("x.pdf"), [0], weights=weights_arg, route_weights=True,
            classify=_classifier(SCANNED))
        assert weights == str(_repo_root() / DEFAULT_WEIGHTS)
        assert prov["mode"] == "routed"
        assert prov["verdict"] == SCANNED
        assert cls is not None and cls.verdict == SCANNED

    def test_engraved_routes_to_engraved_weights(self, monkeypatch, tmp_path):
        engraved = tmp_path / "engraved.pt"
        engraved.write_bytes(b"x")
        monkeypatch.setenv("OMR_ENGRAVED_WEIGHTS", str(engraved))
        weights, prov, cls = resolve_staged_weights(
            Path("x.pdf"), [0], weights="auto", route_weights=True,
            classify=_classifier(ENGRAVED))
        assert weights == str(engraved)
        assert prov["verdict"] == ENGRAVED
        assert cls.verdict == ENGRAVED

    def test_unknown_abstains_to_default(self):
        weights, prov, cls = resolve_staged_weights(
            Path("x.pdf"), [0], weights="auto", route_weights=True,
            classify=_classifier(UNKNOWN))
        assert weights == str(_repo_root() / DEFAULT_WEIGHTS)
        assert prov["verdict"] == UNKNOWN
        assert cls.verdict == UNKNOWN

    def test_classification_runs_exactly_once(self):
        """⚠️ THE WHOLE POINT OF THREADING `classify` THROUGH TO
        `_route_weights` AS A CONSTANT FUNCTION: routing must classify the
        PDF ONCE, not once for its own decision and again inside
        `_route_weights`."""
        classify = _classifier(SCANNED)
        resolve_staged_weights(Path("x.pdf"), [0, 1, 2], weights="auto",
                               route_weights=True, classify=classify)
        assert len(classify.calls) == 1


class TestNoWeightRoutingOverrides:
    """The literal escape the prep brief asked for: force OFF even where
    routing was explicitly requested, without touching bare omission."""

    def test_no_weight_routing_short_circuits_before_classifying(self):
        classify = _classifier(ENGRAVED)
        weights, prov, cls = resolve_staged_weights(
            Path("x.pdf"), [0], weights="auto", route_weights=True,
            no_weight_routing=True, classify=classify)
        assert weights == str(_repo_root() / DEFAULT_WEIGHTS)
        assert prov["mode"] == "disabled"
        assert cls is None
        assert classify.calls == []  # never classified -- the point of "off"

    def test_env_var_off_also_short_circuits(self, monkeypatch):
        monkeypatch.setenv("OMR_WEIGHT_ROUTING", "0")
        classify = _classifier(ENGRAVED)
        weights, prov, cls = resolve_staged_weights(
            Path("x.pdf"), [0], weights="auto", route_weights=True,
            classify=classify)
        assert weights == str(_repo_root() / DEFAULT_WEIGHTS)
        assert prov["mode"] == "disabled"
        assert classify.calls == []

    def test_no_weight_routing_has_no_effect_when_not_routing(self):
        """It only ever matters once routing was already requested."""
        weights, prov, cls = resolve_staged_weights(
            Path("x.pdf"), [0], weights=None, route_weights=False,
            no_weight_routing=True)
        assert weights is None
        assert prov is None


class TestOnRealSyntheticPDFsNoClassifierInjected:
    """Not a mock: builds a genuinely vector-heavy and a genuinely
    raster-heavy PDF with PyMuPDF and lets the REAL classifier
    (`input_domain.classify_pdf_domain`) decide, the way the CLI actually
    will tonight. `test_input_domain.py` owns the classifier's own
    boundary cases; this only checks that ROUTING wires to it correctly
    end to end."""

    def _vector_pdf(self, path):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        for i in range(200):
            y = 40 + (i % 150) * 5
            page.draw_line(fitz.Point(40, y), fitz.Point(500, y))
        doc.save(path)
        doc.close()
        return path

    def _scan_pdf(self, path):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        png = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40)).tobytes("png")
        page.insert_image(fitz.Rect(0, 0, page.rect.width, page.rect.height),
                          stream=png)
        doc.save(path)
        doc.close()
        return path

    def test_a_vector_pdf_routes_to_the_engraved_weights_name(self, tmp_path):
        pdf = self._vector_pdf(str(tmp_path / "engraved.pdf"))
        weights, prov, cls = resolve_staged_weights(
            pdf, [0], weights="auto", route_weights=True)
        assert prov["verdict"] == ENGRAVED
        assert Path(weights).name == Path(ENGRAVED_WEIGHTS).name

    def test_a_raster_pdf_routes_to_the_default_weights_name(self, tmp_path):
        pdf = self._scan_pdf(str(tmp_path / "scan.pdf"))
        weights, prov, cls = resolve_staged_weights(
            pdf, [0], weights="auto", route_weights=True)
        assert prov["verdict"] == SCANNED
        assert Path(weights).name == Path(DEFAULT_WEIGHTS).name

    def test_an_explicit_real_path_pins_regardless_of_the_pdf(self, tmp_path):
        pdf = self._vector_pdf(str(tmp_path / "engraved.pdf"))
        weights, prov, cls = resolve_staged_weights(
            pdf, [0], weights="/pinned/somewhere.pt", route_weights=True)
        assert weights == "/pinned/somewhere.pt"
        assert prov is None

    def test_a_missing_engraved_file_falls_back_soft_with_one_stderr_line(
            self, tmp_path, monkeypatch, capsys):
        """The legacy behaviour, exercised through the shared function: a
        vector PDF that classifies ENGRAVED but whose engraved-weights file
        does not exist on disk falls back to the default weights and prints
        ONE line to stderr rather than raising."""
        pdf = self._vector_pdf(str(tmp_path / "engraved.pdf"))
        monkeypatch.setenv("OMR_ENGRAVED_WEIGHTS",
                           str(tmp_path / "does-not-exist.pt"))
        weights, prov, cls = resolve_staged_weights(
            pdf, [0], weights="auto", route_weights=True)
        assert weights == str(_repo_root() / DEFAULT_WEIGHTS)
        assert "missing" in prov["reason"]
        err = capsys.readouterr().err
        assert err.count("\n") == 1
        assert "weight routing" in err


class TestTheImportIsSharedNeverCopied:
    """⚠️ Behavioural, not source-text (CLAUDE.md 6c bars a new
    `inspect.getsource`/AST test): if `weight_routing.py` ever restated the
    picking logic instead of importing `_route_weights`, an env override the
    LEGACY function honours would stop being honoured here. That is exactly
    `TestRoutingFires.test_engraved_routes_to_engraved_weights` above, which
    already sets `OMR_ENGRAVED_WEIGHTS` and checks the routed path follows
    it -- restated here as its own named claim rather than a new test."""

    def test_an_env_override_only_the_legacy_function_knows_about_still_works(
            self, monkeypatch, tmp_path):
        engraved = tmp_path / "custom.pt"
        engraved.write_bytes(b"x")
        monkeypatch.setenv("OMR_ENGRAVED_WEIGHTS", str(engraved))
        weights, prov, cls = resolve_staged_weights(
            Path("x.pdf"), [0], weights="auto", route_weights=True,
            classify=_classifier(ENGRAVED))
        assert weights == str(engraved)
