"""ROADMAP 2.169 `OMR_STEM_PAIR_AT_HEAD` (repair token `pair_head_end`): a stroke that ENDS at a notehead is that head's stem, and the
accidental-pair rule may not delete it. Synthetic cells (no PDF, no weights).

Convention under test (CONVENTION ASSUMED, NOT CONFIRMED with Sean): a stem ends at its head; an accidental's strokes reach past the
head at BOTH ends, or lie on the accidental's own box. The three things that must stay true: flag off = the shipped finder to the
stroke; a sharp's stroke beside a real stem is still condemned; a stroke merely crossing a head box mid-run is not a stem.
"""
from __future__ import annotations

import numpy as np

from tools.omr.line_detection import (
    STEM_PAIR_AT_HEAD_ENV,
    _drop_paired_strokes,
    _stroke_ends_in_a_head,
    detect_stems,
    staged_stem_finder,
    stem_pair_at_head_enabled,
)
from tools.omr.types import MeasureCell

SPACING = 100
LINE_YS = [100, 200, 300, 400, 500]
TOKEN = frozenset({"pair_head_end"})


def _cell(paint, width: int = 900) -> MeasureCell:
    img = np.full((900, width), 255, dtype=np.uint8)
    paint(img)
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, width, 900),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
    )


def _two_close_strokes(img) -> None:
    """Two verticals 0.55 space apart, both 3.2 spaces tall (x 300 and 355, y 180-500)."""
    img[180:500, 300:308] = 0
    img[180:500, 355:363] = 0


#: Heads whose rows contain the strokes' BOTTOM end (500): the LEFT stroke's head spans x 250-340, the RIGHT stroke's 320-410.
HEAD_LEFT = (250.0, 450.0, 90.0, 100.0)
HEAD_RIGHT = (345.0, 450.0, 90.0, 100.0)
#: A head box in the MIDDLE of the strokes' rows: neither end stands in it (a sharp's stroke crossing a head, not a stem).
HEAD_MID = (250.0, 300.0, 90.0, 100.0)


def _boxes(strokes):
    return sorted((s.x_canonical, s.y_canonical, s.width_canonical, s.height_canonical) for s in strokes)


class _Box:
    def __init__(self, x, y, w, h):
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h


class TestPremise:
    def test_the_pair_rule_deletes_both_strokes_of_the_fixture(self):
        cell = _cell(_two_close_strokes)
        assert detect_stems(cell, drop_accidental_pairs=False)
        assert detect_stems(cell) == []


class TestFlagOff:
    def test_default_is_off(self, monkeypatch):
        monkeypatch.delenv(STEM_PAIR_AT_HEAD_ENV, raising=False)
        assert stem_pair_at_head_enabled() is False
        assert "pair_head_end" not in staged_stem_finder()

    def test_env_on_adds_the_token_only(self, monkeypatch):
        monkeypatch.setenv(STEM_PAIR_AT_HEAD_ENV, "1")
        assert "pair_head_end" in staged_stem_finder()
        monkeypatch.delenv(STEM_PAIR_AT_HEAD_ENV)
        on = staged_stem_finder()
        assert on - {"pair_head_end"} == staged_stem_finder() - {"pair_head_end"}

    def test_off_with_heads_supplied_is_the_shipped_finder(self):
        cell = _cell(_two_close_strokes)
        assert _boxes(detect_stems(cell)) == _boxes(
            detect_stems(cell, noteheads=[HEAD_LEFT, HEAD_RIGHT], stem_finder=frozenset()))

    def test_token_without_heads_changes_nothing(self):
        """The legacy path passes no detections: `noteheads=None` is no rescue, never an empty one."""
        cell = _cell(_two_close_strokes)
        assert detect_stems(cell, stem_finder=TOKEN) == []
        assert detect_stems(cell, noteheads=[], stem_finder=TOKEN) == []


class TestTheRepair:
    def test_two_strokes_each_ending_at_its_head_are_both_kept(self):
        cell = _cell(_two_close_strokes)
        kept = detect_stems(cell, noteheads=[HEAD_LEFT, HEAD_RIGHT], stem_finder=TOKEN)
        assert _boxes(kept) == _boxes(detect_stems(cell, drop_accidental_pairs=False))      # positive control: it moves

    def test_a_stem_beside_a_headless_stroke_is_kept_and_the_stroke_still_goes(self):
        """Subject only: the headless partner is condemned by the pair as it always was."""
        cell = _cell(_two_close_strokes)
        kept = detect_stems(cell, noteheads=[HEAD_LEFT], stem_finder=TOKEN)
        xs = sorted(s.x_canonical for s in kept)
        assert xs == [300]

    def test_a_stroke_crossing_a_head_mid_run_is_not_a_stem(self):
        """A sharp's stroke runs past the head at both ends: it overlaps the head box but ends in no head row."""
        cell = _cell(_two_close_strokes)
        assert detect_stems(cell, noteheads=[HEAD_MID], stem_finder=TOKEN) == []

    def test_a_stroke_on_an_accidental_box_is_never_exempt(self):
        cell = _cell(_two_close_strokes)
        acc = ("accidental", (290.0, 170.0, 85.0, 340.0))
        fin = TOKEN | {"pair_evidence"}
        assert detect_stems(cell, noteheads=[HEAD_LEFT, HEAD_RIGHT], marks=[acc], stem_finder=fin) == []

    def test_chord_stem_crossing_a_second_head_is_still_a_stem(self):
        cell = _cell(_two_close_strokes)
        upper = (250.0, 220.0, 90.0, 100.0)         # a second head on the left stroke's column, mid-run
        kept = detect_stems(cell, noteheads=[HEAD_LEFT, upper, HEAD_RIGHT], stem_finder=TOKEN)
        assert len(kept) == 2


class TestTheRelationDirectly:
    def test_none_reproduces_the_shipped_relation(self):
        a, b = _Box(300, 180, 8, 320), _Box(355, 180, 8, 320)
        assert _drop_paired_strokes([a, b], SPACING, 0.9, 0.6) == []
        assert _drop_paired_strokes([a, b], SPACING, 0.9, 0.6, on_head_end=None) == []

    def test_it_can_only_keep_more(self):
        a, b = _Box(300, 180, 8, 320), _Box(355, 180, 8, 320)
        off = _drop_paired_strokes([a, b], SPACING, 0.9, 0.6)
        for flags in ([False, False], [True, False], [False, True], [True, True]):
            on = _drop_paired_strokes([a, b], SPACING, 0.9, 0.6, on_head_end=flags)
            assert set(map(id, off)) <= set(map(id, on))

    def test_ends_in_a_head_needs_a_row_and_a_column(self):
        s = _Box(300, 180, 8, 320)
        assert _stroke_ends_in_a_head(s, [HEAD_LEFT], SPACING)
        assert not _stroke_ends_in_a_head(s, [HEAD_MID], SPACING)                    # rows hit mid-run only
        assert not _stroke_ends_in_a_head(s, [(600.0, 450.0, 90.0, 100.0)], SPACING)  # right rows, wrong columns
        assert not _stroke_ends_in_a_head(s, [], SPACING)
        assert not _stroke_ends_in_a_head(s, None, SPACING)


class TestChordStemRunningPastItsHead:
    """Sean's 2.167 tile 3: a 7.7-space down-stem whose ends stand in no detected head (the chord's far head is missed)."""

    def test_a_tall_stroke_through_a_head_is_kept_but_a_short_one_is_not(self):
        tall = _Box(300, 100, 8, 400)             # 4 spaces
        short = _Box(300, 180, 8, 320)            # 3.2 spaces: could be an accidental
        assert _stroke_ends_in_a_head(tall, [HEAD_MID], SPACING)
        assert not _stroke_ends_in_a_head(short, [HEAD_MID], SPACING)

    def test_a_tall_stroke_clear_of_every_head_column_is_not_exempt(self):
        assert not _stroke_ends_in_a_head(_Box(600, 100, 8, 400), [HEAD_MID], SPACING)
