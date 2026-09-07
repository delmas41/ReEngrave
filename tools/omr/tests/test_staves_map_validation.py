"""The confirmation UI must refuse exactly what the merge step refuses.

⚠️ THE GAP THESE TESTS CLOSE. `merge_additions` proves a map by running
`page_normalise.normalise` on the row's own trimmed truth before it writes
`works.json`. Until 2026-09-07 the UI (`server.py`) re-implemented only the
CHEAP structural checks — every part named once, no part named twice, every
staff decided — and never called `page_normalise` at all. So a row could go
green staff by staff, be marked `done`, and refuse at merge time with the
human's whole confirmation pass already spent. Two `page_normalise` faults did
exactly that to Mahler p3 and p4 (`benchmarks/omr-page-normalise-fixes-2026-09/
FINDINGS.md`).

The repair is one shared prover — `merge_additions.prove_normalises` — called
by both. A second implementation would reopen the gap one level down, so the
first test here is an ANTI-DRIFT source assertion in the shape of
`TestEventlessMeasureKeepsItsMarks`: both call sites must exist.

⚠️ AND THE SECOND PRIORITY IS ABOVE THE FIRST: a validation failure must never
cost a verdict. Sean's decisions are irreplaceable human work and the proof is
a nicety beside them, so a prover that RAISES must leave the verdict saved and
say only that the check could not run.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MAPS = ROOT / "benchmarks" / "omr-staves-map-2026-09"
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"


def _load(name: str, directory: Path):
    path = directory / f"{name}.py"
    if not path.is_file():
        pytest.skip(f"{path} not present")
    for d in (SCAN, MAPS):
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _score(tmp_path: Path, n_parts: int = 3) -> Path:
    from music21 import note, stream

    score = stream.Score()
    for i, pitch in enumerate(("C5", "E5", "G5")[:n_parts]):
        part = stream.Part(id=f"P{i}")
        part.partName = f"P{i}"
        m = stream.Measure(number=1)
        m.append(note.Note(pitch, quarterLength=4.0))
        part.append(m)
        score.append(part)
    out = tmp_path / "truth.musicxml"
    score.write("musicxml", fp=str(out))
    return out


# ------------------------------------------------------------- anti-drift

class TestOneProverServesBothCallers:
    """⚠️ Verified to fail when either call site is removed."""

    def test_the_prover_exists_and_runs_page_normalise(self):
        src = (MAPS / "merge_additions.py")
        if not src.is_file():
            pytest.skip("merge_additions.py not present")
        text = src.read_text()
        assert "def prove_normalises(" in text
        body = text.split("def prove_normalises(", 1)[1].split("\ndef ", 1)[0]
        assert "page_normalise.normalise(" in body, \
            "the shared prover must be the thing that calls page_normalise"

    def test_the_merge_step_asks_it(self):
        src = MAPS / "merge_additions.py"
        if not src.is_file():
            pytest.skip("merge_additions.py not present")
        text = src.read_text()
        after = text.split("def check_row(", 1)[1].split("\ndef ", 1)[0]
        assert "prove_normalises(" in after, \
            "check_row must prove the map through the shared prover"

    def test_the_confirmation_ui_asks_it_too(self):
        src = MAPS / "server.py"
        if not src.is_file():
            pytest.skip("server.py not present")
        text = src.read_text()
        assert "from merge_additions import prove_normalises" in text, \
            "the UI must import the SHARED prover, never re-implement it"
        assert "prove_normalises(" in text
        assert "prover.wait(" in text, \
            "`done` must consult the proof, not only the cheap checks"

    def test_the_ui_does_not_reimplement_page_normalise(self):
        src = MAPS / "server.py"
        if not src.is_file():
            pytest.skip("server.py not present")
        text = src.read_text()
        assert "page_normalise.normalise(" not in text, \
            ("a second call site is a second implementation waiting to drift "
             "— go through prove_normalises")


# ------------------------------------------------ what the prover decides

class TestTheSharedProver:

    def test_it_accepts_a_map_that_normalises(self, tmp_path, monkeypatch):
        ma = _load("merge_additions", MAPS)
        truth = _score(tmp_path)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (truth, None))
        got = ma.prove_normalises(
            "row", [{"name": "A", "parts": [0, 1]}, {"name": "B", "parts": [2]}])
        assert got["ok"] is True
        assert got["unavailable"] is False
        assert got["normalised"]["n_source_parts"] == 3
        assert got["normalised"]["n_output_parts"] == 2

    def test_it_refuses_a_map_page_normalise_refuses(self, tmp_path, monkeypatch):
        """The map is shapely and complete-looking and still cannot merge."""
        ma = _load("merge_additions", MAPS)
        truth = _score(tmp_path)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (truth, None))
        got = ma.prove_normalises("row", [{"name": "A", "parts": [0, 1]}])
        assert got["ok"] is False
        assert got["unavailable"] is False, \
            "a REFUSAL is not an unavailable check — the two are acted on " \
            "differently by the two callers"
        assert "IncompleteMap" in got["problem"]

    def test_a_missing_fixture_is_unavailable_not_a_refusal(self, monkeypatch):
        ma = _load("merge_additions", MAPS)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (None, None))
        got = ma.prove_normalises("row", [{"name": "A", "parts": [0]}])
        assert got["ok"] is False
        assert got["unavailable"] is True


# ------------------------------------- what the UI does with that verdict

class TestDoneIsBlockedByTheSameThing:

    def test_a_refused_proof_blocks_done(self):
        srv = _load("server", MAPS)
        got = srv.done_problems(
            {"problems": []},
            {"state": "refused", "problem": "page_normalise REFUSED this map: x"})
        assert got and "REFUSED" in got[0]

    def test_a_proof_that_could_not_run_does_NOT_block_done(self):
        """⚠️ Deliberate asymmetry with `check_row`, which DOES refuse on it.

        The UI writes only the additions file; blocking Sean's keystroke over a
        fixture missing from this machine would cost more than it protects, and
        the merge step still refuses before anything reaches `works.json`.
        """
        srv = _load("server", MAPS)
        assert srv.done_problems(
            {"problems": []},
            {"state": "unavailable", "problem": "no truth on disk"}) == []

    def test_structural_problems_still_block(self):
        srv = _load("server", MAPS)
        got = srv.done_problems({"problems": ["3 staves not yet decided"]},
                                {"state": "ok", "problem": None})
        assert got == ["3 staves not yet decided"]

    def test_both_problems_are_reported_together(self):
        """Never one at a time: a human fixing the first should see the second."""
        srv = _load("server", MAPS)
        got = srv.done_problems({"problems": ["a"]},
                                {"state": "refused", "problem": "b"})
        assert got == ["a", "b"]


# ------------------------------------------------- the priority above all

class TestAProofFailureNeverCostsAVerdict:

    def test_a_prover_that_raises_is_reported_not_propagated(self):
        srv = _load("server", MAPS)
        prover = srv.Prover()

        def boom(*a, **k):
            raise RuntimeError("music21 exploded")

        got = prover._compute("row", [{"name": "A", "parts": [0]}], None)
        assert isinstance(got, dict)
        srv.prove_normalises = boom            # module-level, what _compute calls
        got = prover._compute("row", [{"name": "A", "parts": [0]}], None)
        assert got["state"] == "unavailable"
        assert "could not run" in got["problem"]
        assert srv.done_problems({"problems": []}, got) == [], \
            "a check that fell over must not block the human"

    def test_the_verdict_is_stored_before_any_proof_is_asked_for(self):
        """SOURCE-level: `store.save()` precedes `check(...)` in every mutator.

        A behavioural test would only exercise whichever path its fixture
        happens to take; this asserts the ordering that makes the property
        true for all of them.
        """
        src = MAPS / "server.py"
        if not src.is_file():
            pytest.skip("server.py not present")
        text = src.read_text()
        for route in ("def api_patch(", "def api_insert(", "def api_delete("):
            body = text.split(route, 1)[1].split("\n    @app.", 1)[0]
            assert "store.save()" in body, f"{route} must persist"
            assert body.index("store.save()") < body.index("check(seed, st)"), \
                f"{route} asks for validation BEFORE it saves — a proof that " \
                f"raised could then cost a verdict"

    def test_the_fingerprint_ignores_verdicts(self):
        """The confirmation keystroke must not re-run the proof.

        A pass is ~20 verdict keystrokes per row and one map, so keying the
        cache on the MAP (name + parts) is what keeps the UI at ~3 ms.
        """
        srv = _load("server", MAPS)
        a = [{"name": "A", "parts": [0, 1], "verdict": "pending"}]
        b = [{"name": "A", "parts": [0, 1], "verdict": "confirmed"}]
        assert srv.Prover.fingerprint("r", a) == srv.Prover.fingerprint("r", b)
        c = [{"name": "A", "parts": [0]}]
        assert srv.Prover.fingerprint("r", a) != srv.Prover.fingerprint("r", c)
