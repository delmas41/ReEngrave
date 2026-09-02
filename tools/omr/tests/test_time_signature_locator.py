"""The header meter reader, and the vote that decides whether to believe it."""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from tools.omr.rhythm import drop_uncorroborated_meter_changes
from tools.omr.time_signature_locator import (
    DEFAULT_LOCATOR_CONFIG,
    DEFAULT_METERS,
    LocatedTimeSignature,
    TimeSignatureLocatorConfig,
    _digit_templates,
    _letter_templates,
    _meter_templates,
    locate_time_signature,
    vote_system_time_signature,
)
from tools.omr.types import MeasureCell

CELL_W, CELL_H = 600, 400
SPACING = 24
STAFF_LINES = [140, 164, 188, 212, 236]  # five lines, four spaces


def _blank() -> np.ndarray:
    img = np.full((CELL_H, CELL_W), 255, dtype=np.uint8)
    for y in STAFF_LINES:
        cv2.line(img, (0, y), (CELL_W - 1, y), 0, 2)
    return img


def _paste_meter(img: np.ndarray, numerator: str, denominator: str, x: int) -> None:
    """Draw a real time signature: the Bravura digits, each filling two spaces.

    Using the same glyphs the reader matches against makes this a test of the
    SEARCH — that it finds the meter, at the right place, and does not find one
    that is not there — rather than of how well Bravura resembles a scan, which
    is what `benchmarks/omr-timesig-2026-08/` measures.
    """
    digits = _digit_templates(DEFAULT_LOCATOR_CONFIG.template_em_px)
    half = 2 * SPACING
    for text, y0 in ((numerator, STAFF_LINES[0]), (denominator, STAFF_LINES[2])):
        glyph = digits[text]
        scaled = cv2.resize(glyph, (int(glyph.shape[1] * half / glyph.shape[0]), half),
                            interpolation=cv2.INTER_AREA)
        region = img[y0:y0 + half, x:x + scaled.shape[1]]
        region[:] = np.minimum(region, 255 - scaled)


def _paste_letter(img: np.ndarray, smufl_name: str, x: int) -> None:
    """Draw a letter-form meter: one glyph two spaces tall, centred on the staff."""
    glyph = _letter_templates(DEFAULT_LOCATOR_CONFIG.template_em_px)[smufl_name]
    height = 2 * SPACING
    scaled = cv2.resize(glyph, (int(glyph.shape[1] * height / glyph.shape[0]), height),
                        interpolation=cv2.INTER_AREA)
    y0 = STAFF_LINES[1]
    region = img[y0:y0 + height, x:x + scaled.shape[1]]
    region[:] = np.minimum(region, 255 - scaled)


def _cell(img: np.ndarray) -> MeasureCell:
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=-1,
        image=img, image_no_staff=img,
        bbox_page_px=(0, 0, CELL_W, CELL_H),
        staff_line_ys_canonical=list(STAFF_LINES),
        upscale_factor=1.0,
    )


class TestTemplates:
    def test_composite_is_four_staff_spaces_tall(self):
        em = DEFAULT_LOCATOR_CONFIG.template_em_px
        for _meter, template in _meter_templates(em, ((2, 4, "2/4"), (12, 8, "12/8"))):
            assert template.shape[0] == round(4 * em / 4)

    def test_two_digit_numerator_is_wider_than_one(self):
        em = DEFAULT_LOCATOR_CONFIG.template_em_px
        built = dict(_meter_templates(em, ((2, 4, "2/4"), (12, 8, "12/8"))))
        assert built[(12, 8, "12/8")].shape[1] > built[(2, 4, "2/4")].shape[1]

    def test_digits_are_not_clipped_by_the_stack(self):
        # Bravura's digits overshoot two staff spaces by a pixel or two. Building
        # the composite straight into a 4-space box cropped the taller ones — the
        # foot came off `timeSig2` — so the stack is assembled at natural size and
        # resized afterwards. A clipped glyph still matches something, which is
        # why this is a test and not a comment.
        em = DEFAULT_LOCATOR_CONFIG.template_em_px
        digits = _digit_templates(em)
        template = dict(_meter_templates(em, ((2, 4, "2/4"),)))[(2, 4, "2/4")]
        expected = digits["2"].sum() + digits["4"].sum()
        scale = (template.shape[0] / 2) / digits["2"].shape[0]
        assert template.sum() > 0.75 * expected * scale ** 2


class TestReadsAMeter:
    def test_finds_a_two_four(self):
        img = _blank()
        _paste_meter(img, "2", "4", x=200)
        read = locate_time_signature(_cell(img))
        assert read is not None
        assert (read.numerator, read.denominator) == (2, 4)

    def test_finds_a_six_eight(self):
        img = _blank()
        _paste_meter(img, "6", "8", x=200)
        read = locate_time_signature(_cell(img))
        assert read is not None
        assert (read.numerator, read.denominator) == (6, 8)

    def test_reports_where_it_found_it(self):
        img = _blank()
        _paste_meter(img, "3", "4", x=310)
        read = locate_time_signature(_cell(img))
        assert read is not None
        assert abs(read.x_canonical - 310) <= SPACING

    def test_finds_common_time(self):
        img = _blank()
        _paste_letter(img, "timeSigCommon", x=200)
        read = locate_time_signature(_cell(img))
        assert read is not None
        assert (read.numerator, read.denominator, read.raw) == (4, 4, "C")

    def test_cut_common_is_not_searched_for(self):
        # Built, measured, withheld: it read a meter on seven systems printing
        # none. Its glyph is still in the library, so this guards the decision
        # rather than the absence of a template.
        assert all(raw != "C|" for _n, _d, raw in DEFAULT_METERS)

    def test_empty_staff_reads_nothing(self):
        read = locate_time_signature(_cell(_blank()))
        assert read is None

    def test_a_barline_is_not_a_one(self):
        # The vertical rule at a system's left edge correlates with `timeSig1`,
        # which is how the first version of this read every staff of Beethoven 5
        # p.1 as 1/1 before the search was constrained to the staff's height.
        img = _blank()
        cv2.rectangle(img, (12, STAFF_LINES[0]), (18, STAFF_LINES[-1]), 0, -1)
        assert locate_time_signature(_cell(img)) is None


class TestVote:
    def _read(self, numerator, denominator, score=0.6, raw=None):
        return LocatedTimeSignature(numerator, denominator, score, 100,
                                    raw or f"{numerator}/{denominator}")

    def test_agreement_carries_the_system(self):
        reads = [self._read(2, 4) for _ in range(8)] + [None, None]
        meter = vote_system_time_signature(reads)
        assert meter is not None and meter["raw"] == "2/4"
        assert meter["votes"] == 8 and meter["voters"] == 10

    def test_a_lone_reading_does_not(self):
        reads = [self._read(2, 4)] + [None] * 9
        assert vote_system_time_signature(reads) is None

    def test_a_tie_is_not_a_reading(self):
        reads = [self._read(2, 4), self._read(3, 4)]
        assert vote_system_time_signature(reads) is None

    def test_two_staff_system_needs_both(self):
        assert vote_system_time_signature([self._read(4, 4), None]) is None
        meter = vote_system_time_signature([self._read(4, 4), self._read(4, 4)])
        assert meter is not None and meter["raw"] == "4/4"

    def test_nothing_read_is_silence_not_a_guess(self):
        assert vote_system_time_signature([None] * 12) is None

    def test_denominator_of_system_is_the_system(self):
        # Callers that pre-filter must not shrink the denominator, or a system
        # where one staff of twelve read a meter would look unanimous.
        reads = [self._read(2, 4)]
        assert vote_system_time_signature(reads, n_staves=12) is None

    def test_threshold_keeps_weak_readings_out(self):
        config = TimeSignatureLocatorConfig(min_score=0.9)
        img = _blank()
        _paste_meter(img, "2", "4", x=200)
        assert locate_time_signature(_cell(img), config=config) is None


def _system(staff_meters):
    """A system whose staves carry the given per-measure meters."""
    staves = []
    for index, meters in enumerate(staff_meters):
        staves.append({"staff_index": index, "measures": [
            {"measure_index": i,
             "time_signature": None if m is None else
             {"numerator": m[0], "denominator": m[1], "raw": f"{m[0]}/{m[1]}"}}
            for i, m in enumerate(meters)
        ]})
    return {"staves": staves}


class TestUncorroboratedMeterChanges:
    def test_one_staff_changing_mid_system_is_reverted(self):
        # Beethoven 5 p.1 in miniature: eleven staves in 2/4 and one that picks
        # up a 4/4 in bar 3 from a barline fragment, which then owns every bar
        # after it and outvotes the truth.
        meters = [[(2, 4)] * 6 for _ in range(11)]
        meters.append([(2, 4)] * 3 + [(4, 4)] * 3)
        page = {"systems": [_system(meters)]}
        assert drop_uncorroborated_meter_changes(page) == 3
        last = page["systems"][0]["staves"][11]["measures"]
        assert all(m["time_signature"]["raw"] == "2/4" for m in last)

    def test_a_change_the_system_agrees_on_is_kept(self):
        meters = [[(2, 4)] * 3 + [(3, 4)] * 3 for _ in range(12)]
        page = {"systems": [_system(meters)]}
        assert drop_uncorroborated_meter_changes(page) == 0
        for staff in page["systems"][0]["staves"]:
            assert staff["measures"][4]["time_signature"]["raw"] == "3/4"

    def test_the_opening_meter_is_never_a_change(self):
        meters = [[(2, 4)] * 4 for _ in range(3)]
        meters[0] = [(7, 8)] * 4          # one staff simply read a different meter
        page = {"systems": [_system(meters)]}
        assert drop_uncorroborated_meter_changes(page) == 0

    def test_a_staff_with_no_earlier_meter_reverts_to_nothing(self):
        meters = [[None] * 4 for _ in range(11)]
        meters.append([None, None, (4, 4), (4, 4)])
        page = {"systems": [_system(meters)]}
        assert drop_uncorroborated_meter_changes(page) == 0  # no prior meter: no change

    @pytest.mark.parametrize("n_staves", [2, 5, 20])
    def test_returns_the_number_of_measures_it_touched(self, n_staves):
        meters = [[(2, 4)] * 8 for _ in range(n_staves)]
        meters[0] = [(2, 4)] * 5 + [(9, 8)] * 3
        page = {"systems": [_system(meters)]}
        # Three measures, whatever the system's size — including a two-staff
        # one, where `needed` floors at 2 and a change one staff saw alone is
        # still uncorroborated. That is the right reading of a piano score: a
        # meter change is printed on both staves.
        assert drop_uncorroborated_meter_changes(page) == 3
