"""ROADMAP 2.87: the stem finder's five repairs are ON by default on the STAGED path (Sean 2026-10-11: *"Land switch
on"*), and the LEGACY path is unchanged (frozen: `detect_lines(cell)` with no `stem_finder=` reads exactly as before).

`OMR_STEM_FINDER` unset -> the staged default set; set (even to "") -> exactly the names listed, so `OMR_STEM_FINDER=`
turns every repair off for an A/B and `OMR_STEM_FINDER=thin_run` prices one alone. `head_contact` is NOT in the default:
Sean's round-2 tiles 5-6 showed it narrowing two real eighths (FINDINGS hand-truth-score-2026-10 section 9.8).
"""
import pytest

from tools.omr import line_detection as LD
from tools.omr.staged import geometry as G

FIVE = {"thin_run", "pair_evidence", "attach_tolerance", "refuse_owned", "one_stem_per_head"}


def test_staged_default_is_the_five_repairs():
    assert set(LD.STEM_FINDER_STAGED_DEFAULT) == FIVE
    assert "head_contact" not in LD.STEM_FINDER_STAGED_DEFAULT


def test_unset_env_gives_staged_default_on_staged_readers(monkeypatch):
    monkeypatch.delenv(LD.STEM_FINDER_ENV, raising=False)
    assert LD.staged_stem_finder() == frozenset(FIVE)
    for name in FIVE - {"thin_run", "pair_evidence", "refuse_owned"}:
        assert G.stem_finder_repair_on(name), name
    assert G.attach_tolerance_on()
    assert not G.stem_finder_repair_on("head_contact")


def test_unset_env_leaves_legacy_default_empty(monkeypatch):
    """The shared reader's own default (what LEGACY's `detect_lines(cell)` reads) stays EMPTY."""
    monkeypatch.delenv(LD.STEM_FINDER_ENV, raising=False)
    assert LD.stem_finder_repairs() == frozenset()


@pytest.mark.parametrize("raw,want", [("", frozenset()), ("thin_run", frozenset({"thin_run"})),
                                      ("head_contact,thin_run", frozenset({"head_contact", "thin_run"}))])
def test_set_env_is_exactly_the_list(monkeypatch, raw, want):
    monkeypatch.setenv(LD.STEM_FINDER_ENV, raw)
    assert LD.staged_stem_finder() == want
    assert LD.stem_finder_repairs() == want


def test_detect_lines_forwards_stem_finder(monkeypatch):
    seen = {}

    def fake(cell, **kw):
        seen.update(kw)
        return []
    monkeypatch.setattr(LD, "detect_stems", fake)
    monkeypatch.setattr(LD, "detect_beams", lambda *a, **k: [], raising=False)
    try:
        LD.detect_lines(None, stem_finder=frozenset({"thin_run"}))
    except Exception:
        pass
    assert seen.get("stem_finder") == frozenset({"thin_run"})
