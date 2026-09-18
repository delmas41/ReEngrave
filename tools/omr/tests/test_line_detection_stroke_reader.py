"""`OMR_STEM_STROKE`: a stem read from a COLUMN PROFILE, not from a component.

Synthetic cells, so these run without LilyPond, a PDF or weights. The shape
under test is the one `benchmarks/omr-stem-ink-2026-09/rejection_census.py`
names as the largest bucket on both publishers: **a component EXISTS and is
the wrong SHAPE** — 683 of 793 (86%) on Litolff and 1,132 of 1,529 (74%) on
Breitkopf. A notehead fused to its own stem is measured at the NOTEHEAD's
width and the width cap throws the stem away with the blob.

⚠️ THE FIRST TEST IS THE ONE THAT MATTERS AND IT IS THE FLAG-OFF IDENTITY.
`line_detection.py` is on the path every arm of that benchmark proves faithful
before it reports a delta (783/783 cells, 1,920 = 1,920 strokes). If the
flag-off set ever moves, those instruments break and the failure looks like
theirs. Its positive control is beside it: the flag-ON set must DIFFER on the
same cell, or the identity test is passing because the reader does nothing.
"""

from __future__ import annotations

import numpy as np
import pytest

from tools.omr.line_detection import (
    STEM_STROKE_AGREE_SPACES,
    _column_stroke_bands,
    _binary_ink,
    detect_stems,
    stem_stroke_enabled,
)
from tools.omr.types import MeasureCell


SPACING = 100
LINE_YS = [100, 200, 300, 400, 500]


def _cell(paint, width: int = 900) -> MeasureCell:
    img = np.full((900, width), 255, dtype=np.uint8)
    paint(img)
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, width, 900),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
    )


def _fused_note(img, x: int, head_y: int) -> None:
    """A notehead FUSED into a mass, with its own stem rising out of it.

    ⚠️ THE FIRST VERSION OF THIS FIXTURE WAS NOT FUSED AND ITS OWN PREMISE
    TEST CAUGHT IT. A notehead is one staff space tall and the opening kernel
    is 1.6 spaces, so a bare head is ERASED and its stem survives as its own
    component -- `detect_stems` finds it and there is nothing to recover. A
    component comes out `too WIDE` on a real plate only when the head has
    merged with something that makes the mass TALLER than the kernel: a beam
    stub, a ledger line, the neighbour above. So the mass here is 1.8 spaces
    tall and 1.5 wide, which survives the opening joined to the stem and is
    then thrown away by the 0.6-space width cap -- the census's largest
    bucket, built to its stated shape.
    """
    half = int(SPACING * 0.75)
    img[head_y - int(0.9 * SPACING):head_y + int(0.9 * SPACING),
        x - half:x + half] = 0
    sx = x + half - 8
    img[head_y - int(3.5 * SPACING):head_y, sx - 7:sx + 7] = 0


def _bands(cell, **kw):
    src = cell.image_no_staff
    return _column_stroke_bands(
        _binary_ink(src), SPACING, cell.width,
        min_height_lines=2.0, max_height_lines=8.0, max_width_lines=0.6, **kw)


class TestTheFlagIsOffAndOffIsIdentical:

    def test_the_flag_is_OFF_by_default(self, monkeypatch):
        monkeypatch.delenv("OMR_STEM_STROKE", raising=False)
        assert stem_stroke_enabled() is False

    @pytest.mark.parametrize("word", ["0", "", "off", "no", "false",
                                      "yess", "ON!", "2"])
    def test_only_an_explicit_ON_word_turns_it_on(self, monkeypatch, word):
        """A DEFAULT-OFF flag needs an ALLOW-LIST, so anything unrecognised --
        a typo included -- must leave it OFF. A deny-list here would let
        `OMR_STEM_STROKE=yess` switch a document onto an unpriced GATHER
        change."""
        monkeypatch.setenv("OMR_STEM_STROKE", word)
        assert stem_stroke_enabled() is False

    @pytest.mark.parametrize("word", ["1", "true", "yes", "on", "ON", " on "])
    def test_an_ON_word_turns_it_on(self, monkeypatch, word):
        monkeypatch.setenv("OMR_STEM_STROKE", word)
        assert stem_stroke_enabled() is True

    def test_flag_off_is_IDENTICAL_and_flag_on_DIFFERS(self, monkeypatch):
        """The identity, with the control that gives it teeth.

        ⚠️ Asserting only that OFF equals OFF passes when the reader is dead.
        The second half is the positive control: on this same cell the ON set
        must differ, or the first half means nothing.
        """
        cell = _cell(lambda img: _fused_note(img, 400, 700))
        monkeypatch.delenv("OMR_STEM_STROKE", raising=False)
        off = detect_stems(cell)
        monkeypatch.setenv("OMR_STEM_STROKE", "1")
        on = detect_stems(cell)

        def key(v):
            return sorted((d.x_canonical, d.y_canonical, d.width_canonical,
                           d.height_canonical) for d in v)

        assert key(off) == key(detect_stems(cell, enable_stroke_reader=False))
        assert key(on) != key(off), (
            "the reader added nothing on the fixture, so the identity test "
            "above is vacuous")
        assert key(off) == [k for k in key(off) if k in key(on)], (
            "the reader is ADDITIVE: every flag-off stroke must survive")


class TestItReadsAStemInsideAFusedBlob:

    def test_the_component_reader_finds_NOTHING_on_the_fused_note(self):
        """The premise. If the component reader already found this stem the
        rest of the file would be testing nothing."""
        cell = _cell(lambda img: _fused_note(img, 400, 700))
        assert detect_stems(cell, enable_stroke_reader=False) == []

    def test_the_column_profile_finds_it(self):
        cell = _cell(lambda img: _fused_note(img, 400, 700))
        got = _bands(cell)
        assert len(got) == 1, f"expected one band, got {len(got)}"
        band = got[0]
        assert band.width_canonical <= int(SPACING * 0.6)
        assert 2.0 * SPACING <= band.height_canonical <= 8.0 * SPACING
        assert band.smufl_name == "stem" and band.category == "stem"

    def test_the_band_stands_at_the_head_EDGE_not_through_its_middle(self):
        """`[C9 + L10]`: the stem is at x = 0 or x = notehead width."""
        cell = _cell(lambda img: _fused_note(img, 400, 700))
        band = _bands(cell)[0]
        centre = band.x_canonical + band.width_canonical / 2
        assert centre > 400, (
            "the band must sit on the head's RIGHT edge, not at its centre")


class TestTheBandingRules:

    def test_a_wide_block_yields_no_band(self):
        """⚠️ THE ONE THIS FILE EXISTS FOR MOST. A block wider than the cap is
        CUT into strips, every strip agrees with its neighbours, and every
        strip passes height, width and the 3:1 aspect — so without the
        `capped` refusal a 2-space-wide blob comes out as three stems. That is
        the width cap's protection, restored inside a reader that no longer
        measures a component."""
        def paint(img):
            img[300:700, 300:500] = 0        # 2 spaces wide, 4 tall
        got = _bands(_cell(paint))
        assert got == [], f"a 2-space-wide block became {len(got)} stems"

    def test_a_column_holding_TWO_runs_takes_its_LONGEST(self):
        """Two notes stacked in one column are two runs. A first-to-last
        extent spans both; the longest-run primitive takes one."""
        def paint(img):
            img[200:450, 400:412] = 0        # 2.5 spaces
            img[600:880, 400:412] = 0        # 2.8 spaces, a gap between
        got = _bands(_cell(paint))
        assert got, "the probe found nothing at all"
        for b in got:
            assert b.height_canonical < 500, (
                "a band spanned both runs, so the extent rule was used")
        assert max(b.height_canonical for b in got) == pytest.approx(280, abs=6)

    def test_a_stroke_at_the_CELL_EDGE_is_refused(self):
        """A barline is the cleanest vertical stroke on the page, so the edge
        filter has to apply to the BAND's own x. 607 of Litolff's rejected
        components are edge components and 99.8% of them hold a clean band."""
        def paint(img):
            img[200:700, 10:24] = 0
        assert _bands(_cell(paint)) == []

    def test_a_stroke_too_TALL_is_refused(self):
        def paint(img):
            img[10:890, 400:412] = 0         # 8.8 spaces
        assert _bands(_cell(paint)) == []

    def test_a_stroke_too_SHORT_is_refused(self):
        def paint(img):
            img[400:550, 400:412] = 0        # 1.5 spaces
        assert _bands(_cell(paint)) == []

    def test_the_agree_tolerance_sits_on_a_plateau(self):
        """Not a tuned constant. Swept 0.10-0.60 the heads a band covers read
        293/287/287/286/284 on Litolff and 397 at every value on Breitkopf, so
        the fixture must be insensitive across that range too."""
        cell = _cell(lambda img: _fused_note(img, 400, 700))
        got = {g: len(_bands(cell, agree_spaces=g))
               for g in (0.10, 0.15, 0.25, 0.40, 0.60)}
        assert len(set(got.values())) == 1, got
        assert STEM_STROKE_AGREE_SPACES in (0.10, 0.15, 0.25, 0.40, 0.60)


class TestItNeverRunsWhenTheCellCannotAnswer:

    def test_no_ink_yields_nothing(self):
        assert _bands(_cell(lambda img: None)) == []

    def test_a_cell_with_no_spacing_is_refused_by_detect_stems(self, monkeypatch):
        monkeypatch.setenv("OMR_STEM_STROKE", "1")
        img = np.full((900, 900), 255, dtype=np.uint8)
        img[200:700, 400:412] = 0
        cell = MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            image=img, image_no_staff=img.copy(),
            bbox_page_px=(0, 0, 900, 900),
            staff_line_ys_canonical=[], upscale_factor=1.0,
        )
        monkeypatch.setattr("tools.omr.line_detection._staff_line_spacing",
                            lambda c: 1.0)
        assert detect_stems(cell) == []
