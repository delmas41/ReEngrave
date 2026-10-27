"""ROADMAP 2.213: a stacked beam's bar takes its x extent from its OWN ink (flag `OMR_BEAM_OWN_EXTENT`).

Brahms p19 `glyph/19/0/13/0/8` (2.206d tile 9): with the eraser fix ON the primary beam stays whole, so primary and secondary bar are ONE connected
component and every band got the component's full x extent; the secondary then appeared to reach the dotted eighth's stem and `rhythm._beam_levels`
read a second level. Fixture: a primary bar over the whole group, a secondary bar over its right part only, the two joined by ink bleed.
"""

from __future__ import annotations

import numpy as np

from tools.omr.line_detection import detect_beams
from tools.omr.types import MeasureCell

LINE_YS = [100, 200, 300, 400, 500]


def _cell() -> MeasureCell:
    img = np.full((800, 900), 255, dtype=np.uint8)
    img[150:198, 195:705] = 0          # primary bar, whole group
    img[210:258, 250:705] = 0          # secondary bar, right part only
    img[196:212, 250:410] = 0          # the bleed joining them (wider than the opening kernel)
    img[150:560, 195:205] = 0          # stem of the first note (the dotted eighth)
    img[150:560, 695:705] = 0
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, 900, 800),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
    )


def test_off_every_bar_takes_the_component_extent(monkeypatch):
    monkeypatch.delenv("OMR_BEAM_OWN_EXTENT", raising=False)
    beams = detect_beams(_cell())
    assert len(beams) == 2
    assert all(b.x_canonical <= 205 for b in beams)       # secondary reaches the first stem: the defect


def test_on_the_secondary_bar_starts_at_its_own_ink(monkeypatch):
    monkeypatch.setenv("OMR_BEAM_OWN_EXTENT", "1")
    beams = sorted(detect_beams(_cell()), key=lambda b: b.y_canonical)
    assert len(beams) == 2
    primary, secondary = beams
    assert primary.x_canonical <= 205 and primary.x_canonical + primary.width_canonical >= 700
    assert secondary.x_canonical > 300                  # not the dotted eighth's stem at 195
    assert secondary.x_canonical + secondary.width_canonical >= 700
    # the dotted eighth's head column (x 220) is covered by one bar only
    covering = [b for b in beams if b.x_canonical <= 220 <= b.x_canonical + b.width_canonical]
    assert len(covering) == 1


def _cell_stem_in_bridge() -> MeasureCell:
    """Brahms p19 `glyph/19/0/12/0/5` (Sean: a 16th): the secondary bar really starts AT the first 16th's stem (x 300), but ink bleed at the stem's foot
    bridges the two bars for 40 px, so the first column where the bars read separately is 340."""
    img = np.full((800, 900), 255, dtype=np.uint8)
    img[150:198, 195:705] = 0
    img[210:258, 300:705] = 0
    img[196:212, 300:340] = 0           # the bridge, from the stem's foot
    img[150:560, 195:205] = 0
    img[150:560, 300:312] = 0           # the first 16th's stem, inside the bridge
    img[150:560, 695:705] = 0
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, 900, 800),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
    )


def test_on_the_secondary_bar_reaches_the_stem_it_ends_on(monkeypatch):
    monkeypatch.setenv("OMR_BEAM_OWN_EXTENT", "1")
    beams = sorted(detect_beams(_cell_stem_in_bridge()), key=lambda b: b.y_canonical)
    assert len(beams) == 2
    secondary = beams[1]
    assert secondary.x_canonical <= 306                 # the stem at 300, not 340 where the bars part
    assert secondary.x_canonical > 250                  # and not the dotted eighth's stem at 195
    covering = [b for b in beams if b.x_canonical <= 306 <= b.x_canonical + b.width_canonical]
    assert len(covering) == 2                           # the stem's own column carries both levels
