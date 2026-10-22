"""The CLI must gather ONCE, including under --against."""
import sys, types, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import pipeline, gather as G


class TestTheDivergenceTableComesFromTheSameGather:
    def test_only_one_gather_happens_under_against(self, monkeypatch, tmp_path):
        calls = []
        real = G.gather

        def counting(*a, **k):
            calls.append(1)
            return real(*a, **k)

        monkeypatch.setattr(G, "gather", counting)
        monkeypatch.setattr(pipeline.gather, "gather", counting)

        legacy_json = tmp_path / "legacy.json"
        legacy_json.write_text('{"pages": []}')

        from tools.omr.staged import __main__ as M
        monkeypatch.setattr(pipeline, "prepare_pages", lambda *a, **k: [])
        out = tmp_path / "staged.json"
        M.main(["dummy.pdf", "--pages", "0", "--against", str(legacy_json),
                "--out", str(out)])

        assert len(calls) == 1, (
            f"gather ran {len(calls)} times; the divergence table must be "
            "built from the same log the adjudication describes")

    def test_divergence_is_present_when_legacy_is_given(self):
        res = pipeline.run_staged_on([], legacy={})
        assert "divergence" in res

    def test_divergence_is_absent_when_it_is_not(self):
        res = pipeline.run_staged_on([])
        assert "divergence" not in res
