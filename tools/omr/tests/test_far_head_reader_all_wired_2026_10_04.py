"""lane-farhead-all-wired: the STAGED far-head reader turns on the through-head ON rule and the chord-blob split."""
import numpy as np

from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import ledger_grid as lg


def _spy(monkeypatch):
    # these two tests pin the run-2 (count-outward) path's wiring: select it
    monkeypatch.setitem(FH.READER_KEYWORDS, "note_first", False)
    seen = {}
    real = lg.derive_far_head_step

    def spy(*a, **kw):
        seen.update(kw)
        return real(*a, **kw)
    monkeypatch.setattr(lg, "derive_far_head_step", spy)
    return seen


def _read(chord=None):
    gray = np.full((200, 200), 255, np.uint8)
    lines = [100, 110, 120, 130, 140]
    for y in lines:
        gray[y, 10:190] = 0
    return FH.read_absolute_position(gray, lines, (90, 60, 104, 72), "glyph/0/0/0/0/0",
                                     [("glyph/0/0/0/0/0", (90, 60, 104, 72))], [],
                                     chord_split_rungs_y=chord)


def test_through_head_rule_is_on_in_the_far_head_path(monkeypatch):
    seen = _spy(monkeypatch)
    _read()
    assert seen.get("through_head_on_rung") is True


def test_chord_split_rungs_are_inserted_and_labelled(monkeypatch):
    _spy(monkeypatch)
    pos, reason = _read(chord=[90.0])
    assert "chord_split_rung" in reason


def test_chord_split_is_on_and_switchable():
    assert FH.CHORD_SPLIT is True
