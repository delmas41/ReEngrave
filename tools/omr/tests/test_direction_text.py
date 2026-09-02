"""Unit tests for the direction-text reader — the lexicon, the bands, the
letter filters, and the `<words>` that come out the far end.

The OCR itself is never called: `read_directions` takes its reader as an
argument precisely so the gate around it can be tested without a venv, and the
candidate step is pure CV so it can be tested on a drawn image.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import cv2
import numpy as np
import pytest

from tools.omr.direction_lexicon import lookup
from tools.omr.direction_text import (
    BandConfig,
    DEFAULT_BAND_CONFIG,
    DirectionText,
    TextCandidate,
    _bands_for_page,
    _cluster_into_words,
    _letter_components,
    _measure_at,
    attach_to_page,
    crop_for,
    find_candidates,
    read_directions,
)
from tools.omr.export import measure_direction_words, to_musicxml
from tools.omr.types import PageImage, PageWithStaves, Staff

SPACING = 40.0


# ─── the lexicon ────────────────────────────────────────────────────────────


class TestLexicon:
    @pytest.mark.parametrize("text,category", [
        ("legato", "expression"),
        ("pesante", "expression"),
        ("Allegro", "tempo"),
        ("cresc.", "dynamic"),
        ("molto", "expression"),
    ])
    def test_a_single_term_is_a_direction(self, text, category):
        hit = lookup(text)
        assert hit is not None and hit.category == category

    def test_a_phrase_of_terms_and_connectives_is_accepted(self):
        assert lookup("espr. e legato") is not None
        assert lookup("Un poco sostenuto") is not None
        assert lookup("Allegro con brio") is not None

    def test_a_phrase_takes_its_most_specific_category(self):
        """`Un poco sostenuto` is a tempo mark, and `poco` matches first."""
        assert lookup("Un poco sostenuto").category == "tempo"

    def test_connectives_alone_are_not_a_direction(self):
        """Three slurs read as letters must not become `e e e`."""
        assert lookup("e e e") is None
        assert lookup("a") is None
        assert lookup("con") is None

    @pytest.mark.parametrize("text", [
        "Symphony No.1",          # a title — digits
        "(d = 108)",              # a metronome mark read by OCR
        "Brahms, Johannes",       # a composer
        "Flute 1",                # a margin label
        "IIII",                   # a beam group
        "",
    ])
    def test_noise_is_refused(self, text):
        assert lookup(text) is None

    def test_the_text_comes_back_unchanged(self):
        """The metric scores printed characters, so nothing is normalised."""
        assert lookup("Un poco sostenuto").text == "Un poco sostenuto"

    def test_a_long_run_on_is_refused(self):
        assert lookup("legato legato legato legato legato legato legato") is None

    def test_a_word_repeated_immediately_is_a_decoder_repeating_itself(self):
        """One `arco.` on a scanned page came back from the language-model rung
        as `arco. arco. arco. arco.`, and every token was a real term. The
        other rung read the same crop as `arco.`."""
        assert lookup("arco. arco. arco.") is None
        assert lookup("sempre sempre") is None

    def test_a_repeat_with_a_connective_between_is_real_music(self):
        """ADJACENT, not anywhere — `poco a poco` is a marking."""
        assert lookup("poco a poco") is not None
        assert lookup("cresc. poco a poco") is not None

    def test_english_glue_is_not_a_connective(self):
        """`and` was glue once, and its only measured effect was to pass a
        scanned `a Tempo.` misread as `a Tempo. and`."""
        assert lookup("a Tempo. and") is None
        assert lookup("a Tempo.") is not None


# ─── letter components ──────────────────────────────────────────────────────


class TestLetterComponents:
    def _blank(self):
        return np.zeros((int(4 * SPACING), int(30 * SPACING)), np.uint8)

    def test_a_letter_sized_blob_is_kept(self):
        mask = self._blank()
        cv2.rectangle(mask, (100, 40), (120, 70), 255, -1)
        assert len(_letter_components(mask, SPACING, DEFAULT_BAND_CONFIG)) == 1

    def test_a_slur_is_refused_by_its_fill_ratio(self):
        """The test that does the work: a long thin arc fills a fortieth of
        its own box, a letter a fifth."""
        mask = self._blank()
        cv2.ellipse(mask, (600, 120), (400, 40), 0, 180, 360, 255, 3)
        assert _letter_components(mask, SPACING, DEFAULT_BAND_CONFIG) == []

    def test_a_staff_line_fragment_is_refused_by_its_height(self):
        mask = self._blank()
        cv2.rectangle(mask, (100, 50), (300, 52), 255, -1)
        assert _letter_components(mask, SPACING, DEFAULT_BAND_CONFIG) == []

    def test_a_bold_capital_still_counts_as_a_letter(self):
        """`Un poco sostenuto`'s `U` is 1.79 x 1.65 spaces — larger than any
        letter in `legato`, and dropping it cost the whole phrase."""
        mask = self._blank()
        cv2.rectangle(mask, (100, 20), (100 + int(1.79 * SPACING),
                                        20 + int(1.65 * SPACING)), 255, -1)
        assert len(_letter_components(mask, SPACING, DEFAULT_BAND_CONFIG)) == 1


# ─── clustering ─────────────────────────────────────────────────────────────


def _letter(x, y=40, w=25, h=35):
    return (x, y, w, h, int(0.6 * w * h))


class TestClustering:
    def test_adjacent_letters_become_one_word(self):
        letters = [_letter(x) for x in (100, 130, 160, 190)]
        words = _cluster_into_words(letters, SPACING, DEFAULT_BAND_CONFIG)
        assert len(words) == 1 and words[0][4] == 4

    def test_letters_on_different_rows_stay_apart(self):
        letters = [_letter(x, y=40) for x in (100, 130, 160)]
        letters += [_letter(x, y=400) for x in (100, 130, 160)]
        assert len(_cluster_into_words(letters, SPACING, DEFAULT_BAND_CONFIG)) == 2

    def test_a_component_from_another_row_does_not_break_a_word(self):
        """The bug this exists for: components arrive in x order, so anything
        at another height that falls between two letters used to take over the
        chain and split the word. It split `Un poco sostenuto` at a 6px gap."""
        letters = [_letter(100), _letter(130), _letter(160),
                   _letter(175, y=900),            # a mark far below, in between
                   _letter(190), _letter(220)]
        words = _cluster_into_words(letters, SPACING, DEFAULT_BAND_CONFIG)
        rows = [w for w in words if w[1] < 500]
        assert len(rows) == 1 and rows[0][4] == 5

    def test_a_two_letter_cluster_is_refused(self):
        assert _cluster_into_words([_letter(100), _letter(130)],
                                   SPACING, DEFAULT_BAND_CONFIG) == []

    def test_a_flat_run_is_refused_by_the_cluster_height(self):
        """Six pieces of a broken rule pass the letter tests one at a time and
        cluster into something 11 spaces wide and a fifth of a space high."""
        pieces = [_letter(x, y=40, w=25, h=8) for x in range(100, 400, 50)]
        assert _cluster_into_words(pieces, SPACING, DEFAULT_BAND_CONFIG) == []


# ─── bands ──────────────────────────────────────────────────────────────────


def _staff(index, top, system=0, x0=100, x1=2000):
    return Staff(page_index=0, staff_index=index,
                 line_ys=[top + i * int(SPACING) for i in range(5)],
                 x_start=x0, x_end=x1, system_index=system)


def _pws(staves, height=4000, width=2200):
    rgb = np.full((height, width, 3), 255, np.uint8)
    page = PageImage(pdf_path="x.pdf", page_index=0, dpi=600, rgb=rgb,
                     binary=np.full((height, width), 255, np.uint8))
    return PageWithStaves(page=page, staves=staves)


class TestBands:
    def test_one_below_band_per_staff_and_one_above_the_system(self):
        pws = _pws([_staff(0, 500), _staff(1, 1000), _staff(2, 1500)])
        bands = _bands_for_page(pws, DEFAULT_BAND_CONFIG)
        assert [p for _s, p, _t, _b in bands].count("above") == 1
        assert [p for _s, p, _t, _b in bands].count("below") == 3

    def test_bands_never_overlap(self):
        """A word offered to two staves would be charged twice — once as the
        one we invented and once as the one we missed."""
        pws = _pws([_staff(0, 500), _staff(1, 1000, system=0),
                    _staff(2, 2000, system=1), _staff(3, 2600, system=1)])
        spans = sorted((t, b) for _s, _p, t, b in
                       _bands_for_page(pws, DEFAULT_BAND_CONFIG))
        for (_t0, b0), (t1, _b1) in zip(spans, spans[1:]):
            assert b0 <= t1, f"bands overlap at {b0} > {t1}"

    def test_the_gap_between_systems_is_split_at_its_midpoint(self):
        """Between two systems both claims are live — the word could be under
        the last part of one or over the first part of the next. The midpoint
        answers that once instead of a distance rule answering it differently
        on every page. (It is a CAP: neither band ever reaches past its own
        `above_spaces` / `below_spaces`, so the systems here sit close enough
        for the midpoint to be the binding constraint.)"""
        pws = _pws([_staff(0, 500), _staff(1, 800, system=1)])
        bands = {(s.staff_index, p): (t, b) for s, p, t, b in
                 _bands_for_page(pws, DEFAULT_BAND_CONFIG)}
        midpoint = (500 + 4 * SPACING + 800) / 2
        assert bands[(0, "below")][1] == pytest.approx(midpoint, abs=1)
        assert bands[(1, "above")][0] == pytest.approx(midpoint, abs=1)


# ─── measure attribution ────────────────────────────────────────────────────


class TestMeasureAttribution:
    SPANS = [(0, 100, 500), (1, 500, 900), (2, 900, 1300)]

    @pytest.mark.parametrize("x,expected", [(120, 0), (600, 1), (1000, 2)])
    def test_a_word_lands_in_the_measure_it_starts_in(self, x, expected):
        assert _measure_at(self.SPANS, x) == expected

    def test_a_word_past_the_last_barline_stays_in_the_last_measure(self):
        assert _measure_at(self.SPANS, 5000) == 2

    def test_a_word_left_of_the_first_barline_goes_to_the_first_measure(self):
        assert _measure_at(self.SPANS, 0) == 0


# ─── candidates end to end, on a drawn page ─────────────────────────────────


def _page_dict(staff_indices, measure_bounds, detections_by_staff=None):
    return {"systems": [{"staves": [
        {"staff_index": i,
         "measures": [{"measure_index": m,
                       "bbox_page_px": [x0, 0, x1, 4000],
                       "upscale_factor": 1.0,
                       "detections": (detections_by_staff or {}).get(i, [])}
                      for m, (x0, x1) in enumerate(measure_bounds)]}
        for i in staff_indices]}]}


class TestFindCandidates:
    def _page_with_word(self, text_y, detections=None):
        staves = [_staff(0, 500), _staff(1, 1200)]
        pws = _pws(staves)
        for x in range(300, 480, 30):
            cv2.rectangle(pws.page.rgb, (x, text_y), (x + 22, text_y + 34),
                          (0, 0, 0), -1)
        return pws

    def test_a_word_below_a_staff_is_found_and_attributed(self):
        pws = self._page_with_word(text_y=700)
        page_dict = _page_dict([0, 1], [(100, 1000), (1000, 2000)])
        found = find_candidates(pws, page_dict)
        assert len(found) == 1
        assert found[0].staff_index == 0
        assert found[0].placement == "below"
        assert found[0].measure_index == 0

    def test_ink_inside_a_detection_is_subtracted(self):
        """Everything the detector found is already accounted for — a page of
        noteheads must propose nothing. (Glyph-sized boxes: a single 200px box
        would be five staff spaces wide, which is a span, not a glyph.)"""
        pws = self._page_with_word(text_y=700)
        page_dict = _page_dict(
            [0, 1], [(100, 1000), (1000, 2000)],
            {0: [{"bbox_page": [290, 690, 110, 60]},
                 {"bbox_page": [400, 690, 110, 60]}]})
        assert find_candidates(pws, page_dict) == []

    def test_a_span_is_not_blanked_and_does_not_swallow_a_word(self):
        """A slur's box is the rectangle its arc travels through, mostly paper.
        On a scanned Beethoven 5 page one detected at 24 x 4 spaces sat over
        `sempre` and erased all nine of its components. No glyph is that wide —
        the widest in the class space is a notehead at 3.2 — and a span's own
        ink is refused downstream by the fill-ratio test instead."""
        pws = self._page_with_word(text_y=700)
        page_dict = _page_dict(
            [0, 1], [(100, 1000), (1000, 2000)],
            {0: [{"bbox_page": [250, 680, 400, 80], "category": "structural",
                  "class": "slur"}]})
        found = find_candidates(pws, page_dict)
        assert len(found) == 1 and found[0].staff_index == 0

    def test_a_dynamic_inside_a_word_is_not_subtracted(self):
        """A dynamic `p` and the `p` of `espr.` are the same letter in the same
        family, so the detector reads the middle of that word as `dynamicP` at
        confidence 0.87. Blanking it took the word off two Brahms staves —
        56 edits — and only after an unrelated detection change."""
        pws = self._page_with_word(text_y=700)
        page_dict = _page_dict(
            [0, 1], [(100, 1000), (1000, 2000)],
            # A box over one letter in the middle of the run, with letters
            # hard against it on both sides.
            {0: [{"bbox_page": [360, 700, 22, 34], "category": "dynamic"}]})
        found = find_candidates(pws, page_dict)
        assert len(found) == 1 and found[0].staff_index == 0

    def test_a_dynamic_standing_clear_of_a_word_is_subtracted(self):
        """And the case that must keep working: `f` sits about 1.7 spaces from
        the `legato` beside it, so blanking it leaves `legato` to be read
        alone. Excusing it would give the reader `f legato`, which the lexicon
        refuses — and there are eight of those on the page."""
        staves = [_staff(0, 500), _staff(1, 1200)]
        pws = _pws(staves)
        cv2.rectangle(pws.page.rgb, (200, 700), (222, 734), (0, 0, 0), -1)
        for x in range(300, 480, 30):
            cv2.rectangle(pws.page.rgb, (x, 700), (x + 22, 734), (0, 0, 0), -1)
        page_dict = _page_dict(
            [0, 1], [(100, 1000), (1000, 2000)],
            {0: [{"bbox_page": [200, 700, 22, 34], "category": "dynamic"}]})
        found = find_candidates(pws, page_dict)
        assert len(found) == 1
        assert found[0].bbox_page[0] >= 290, "the lone dynamic was kept"

    def test_ink_in_the_margin_is_ignored(self):
        """Left of the staff's start is where the instrument name is printed."""
        staves = [_staff(0, 500, x0=600), _staff(1, 1200, x0=600)]
        pws = _pws(staves)
        for x in range(300, 480, 30):
            cv2.rectangle(pws.page.rgb, (x, 700), (x + 22, 734), (0, 0, 0), -1)
        page_dict = _page_dict([0, 1], [(600, 1000), (1000, 2000)])
        assert find_candidates(pws, page_dict) == []

    def test_above_a_staff_only_the_first_measure_is_read(self):
        """A movement heading is centred on the page; a tempo mark is
        left-aligned to the music. That is what separates them, and no
        vertical reach does — Mahler's title sits closer to its staff than
        Beethoven's direction does to that one."""
        pws = _pws([_staff(0, 500)])
        for x in range(1400, 1580, 30):        # centred, i.e. in measure 1
            cv2.rectangle(pws.page.rgb, (x, 350), (x + 22, 384), (0, 0, 0), -1)
        page_dict = _page_dict([0], [(100, 1000), (1000, 2000)])
        assert find_candidates(pws, page_dict) == []

        loose = BandConfig(above_first_measure_only=False)
        assert len(find_candidates(pws, page_dict, config=loose)) == 1


# ─── the gate, with a stubbed reader ────────────────────────────────────────


class TestCropping:
    def test_a_crop_is_enlarged_until_a_staff_space_is_legible(self):
        """The reader is marginal at the size a 600-dpi page gives it, and
        marginal in a way that looks like a hard failure: one Brahms crop read
        as nothing at 124 px tall and as `espr. e legato` at twice that."""
        pws = _pws([_staff(0, 500), _staff(1, 1200)])
        candidate = TextCandidate(staff_index=0, measure_index=0,
                                  bbox_page=(300, 700, 480, 734),
                                  placement="below", n_components=6)
        small = crop_for(pws.page, candidate, spacing=SPACING)
        assert small.shape[0] > (734 - 700), "crop was not enlarged"

    def test_an_already_large_crop_is_left_alone(self):
        """A page rendered at a higher DPI needs no help, and resampling it
        would only cost time."""
        pws = _pws([_staff(0, 500), _staff(1, 1200)])
        candidate = TextCandidate(staff_index=0, measure_index=0,
                                  bbox_page=(300, 700, 480, 734),
                                  placement="below", n_components=6)
        big = crop_for(pws.page, candidate, spacing=200.0)
        pad_y = int(round(0.45 * 200.0))
        assert big.shape[0] == (734 - 700) + 2 * pad_y


def _says(word):
    """A stub rung that reads `word` from every crop."""
    return lambda crops: [word] * len(crops)


class TestReadDirections:
    def _setup(self):
        staves = [_staff(0, 500), _staff(1, 1200)]
        pws = _pws(staves)
        for x in range(300, 480, 30):
            cv2.rectangle(pws.page.rgb, (x, 700), (x + 22, 734), (0, 0, 0), -1)
        return pws, _page_dict([0, 1], [(100, 1000), (1000, 2000)])

    def test_a_lexicon_hit_is_kept(self):
        pws, page_dict = self._setup()
        out, info = read_directions(pws, page_dict,
                                    readers=[("stub", _says("legato"))])
        assert [d.text for d in out] == ["legato"]
        assert info["n_accepted"] == 1 and info["by_reader"] == {"stub": 1}

    def test_ocr_noise_is_refused_and_reported(self):
        """Precision and recall cost the same, so the reader that guesses
        trades one for the other at par."""
        pws, page_dict = self._setup()
        out, info = read_directions(pws, page_dict,
                                    readers=[("stub", _says("IIII"))])
        assert out == [] and info["rejected"] == ["IIII"]

    def test_an_empty_read_is_not_an_error(self):
        pws, page_dict = self._setup()
        out, info = read_directions(pws, page_dict,
                                    readers=[("stub", _says(""))])
        assert out == [] and info["n_read"] == 0

    def test_no_candidates_means_the_reader_is_never_called(self):
        pws = _pws([_staff(0, 500)])
        page_dict = _page_dict([0], [(100, 1000)])

        def explode(_crops):
            raise AssertionError("reader called with nothing to read")

        assert read_directions(pws, page_dict,
                               readers=[("boom", explode)])[0] == []

    def test_with_no_rung_available_it_abstains_rather_than_fails(self):
        pws, page_dict = self._setup()
        out, info = read_directions(pws, page_dict, readers=[])
        assert out == [] and info["n_accepted"] == 0
        assert info["reason"] == "no OCR rung available"


class TestUnionOfRungs:
    """The two rungs fail differently, which is the whole reason for both.

    Surya is silent or right; Tesseract reads nearly everything and gets
    letters wrong inside the word. Measured on an 1870 scan, either alone
    accepts 11 of 74 crops and the union accepts 17.
    """

    def _setup(self):
        staves = [_staff(0, 500), _staff(1, 1200)]
        pws = _pws(staves)
        for x in range(300, 480, 30):
            cv2.rectangle(pws.page.rgb, (x, 700), (x + 22, 734), (0, 0, 0), -1)
        return pws, _page_dict([0, 1], [(100, 1000), (1000, 2000)])

    def test_the_second_rung_reads_what_the_first_is_silent_on(self):
        pws, page_dict = self._setup()
        out, info = read_directions(pws, page_dict, readers=[
            ("surya", _says("")), ("tesseract", _says("sempre"))])
        assert [d.text for d in out] == ["sempre"]
        assert info["by_reader"] == {"tesseract": 1}
        assert out[0].reader == "tesseract"

    def test_the_first_rung_wins_when_both_read_the_same_word(self):
        pws, page_dict = self._setup()
        out, info = read_directions(pws, page_dict, readers=[
            ("surya", _says("legato")), ("tesseract", _says("legato"))])
        assert len(out) == 1 and out[0].reader == "surya"
        assert info["conflicts"] == []

    def test_a_disagreement_is_recorded_and_the_first_rung_wins(self):
        """Never seen on the scan corpus — 17 accepted, no crop where both
        named different words. The rule exists for the day it happens, and
        the count is how anyone would find out."""
        pws, page_dict = self._setup()
        out, info = read_directions(pws, page_dict, readers=[
            ("surya", _says("legato")), ("tesseract", _says("dolce"))])
        assert [d.text for d in out] == ["legato"]
        assert len(info["conflicts"]) == 1
        assert info["conflicts"][0]["readings"] == {
            "surya": "legato", "tesseract": "dolce"}
        assert info["conflicts"][0]["took"] == "surya"

    def test_punctuation_alone_is_not_a_disagreement(self):
        """`cresc` and `cresc.` are the same mark; only the words matter."""
        pws, page_dict = self._setup()
        _out, info = read_directions(pws, page_dict, readers=[
            ("surya", _says("cresc.")), ("tesseract", _says("Cresc"))])
        assert info["conflicts"] == []

    def test_a_rung_that_throws_does_not_take_the_page_with_it(self):
        def boom(_crops):
            raise RuntimeError("tesseract exploded")

        pws, page_dict = self._setup()
        out, info = read_directions(pws, page_dict, readers=[
            ("surya", _says("legato")), ("tesseract", boom)])
        assert [d.text for d in out] == ["legato"]
        assert "tesseract" in info["failed_readers"]


# ─── attachment and export ──────────────────────────────────────────────────


def _direction(staff=0, measure=0, x=250, text="legato"):
    return DirectionText(staff_index=staff, measure_index=measure, x_page=x,
                         text=text, category="expression", placement="below",
                         terms=("legato",))


class TestAttachAndExport:
    def test_a_direction_lands_on_its_own_measure(self):
        page_dict = _page_dict([0], [(100, 1000), (1000, 2000)])
        assert attach_to_page(page_dict, [_direction(measure=1)]) == 1
        staff = page_dict["systems"][0]["staves"][0]
        assert "direction_texts" not in staff["measures"][0]
        assert staff["measures"][1]["direction_texts"][0]["text"] == "legato"

    def test_a_direction_on_a_staff_that_is_not_there_is_dropped(self):
        page_dict = _page_dict([0], [(100, 1000)])
        assert attach_to_page(page_dict, [_direction(staff=7)]) == 0

    def test_the_x_is_converted_into_the_cell_frame(self):
        """The reader works in page pixels and the exporter in the cell's
        canonical frame, which is what `x_position` is measured in."""
        measure = {"bbox_page_px": [100, 0, 500, 400], "upscale_factor": 2.0,
                   "direction_texts": [_direction(x=250).to_json()]}
        assert measure_direction_words(measure) == [(300.0, "words", "legato")]

    def test_a_measure_with_no_text_contributes_nothing(self):
        assert measure_direction_words({"bbox_page_px": [0, 0, 1, 1]}) == []

    def test_musicxml_carries_the_word_as_a_words_direction(self):
        """`<words>` and `<dynamics>` are different `<direction-type>` children
        and musicdiff scores them as different kinds — a word emitted as an
        `<other-dynamics>` would not pair with the truth at all."""
        result = {"pages": [{"page_index": 0, "systems": [{"system_index": 0,
            "staves": [{"staff_index": 0, "clef": "treble",
                        "key_signature": {"fifths": 0},
                        "time_signature": {"numerator": 4, "denominator": 4},
                        "measures": [{
                            "measure_index": 0,
                            "bbox_page_px": [0, 0, 400, 400],
                            "upscale_factor": 1.0,
                            "direction_texts": [_direction(x=10).to_json()],
                            "detections": [{
                                "class": "noteheadBlack", "category": "notehead",
                                "bbox": [50, 50, 20, 15],
                                "bbox_page": [50, 50, 20, 15],
                                "pitch": "C4", "duration_type": "quarter",
                                "duration_beats": 1.0, "dots": 0,
                                "confidence": 0.9}],
                        }]}]}]}]}
        root = ET.fromstring(to_musicxml(result))
        words = root.findall(".//direction/direction-type/words")
        assert [w.text for w in words] == ["legato"]

    def test_a_result_with_no_direction_text_is_unchanged(self):
        """The post-pass adds a key; a run without it must serialise exactly
        as it did before this existed."""
        base = {"pages": [{"page_index": 0, "systems": [{"system_index": 0,
            "staves": [{"staff_index": 0, "clef": "treble",
                        "key_signature": {"fifths": 0},
                        "time_signature": {"numerator": 4, "denominator": 4},
                        "measures": [{
                            "measure_index": 0,
                            "bbox_page_px": [0, 0, 400, 400],
                            "upscale_factor": 1.0,
                            "detections": [{
                                "class": "noteheadBlack", "category": "notehead",
                                "bbox": [50, 50, 20, 15],
                                "bbox_page": [50, 50, 20, 15],
                                "pitch": "C4", "duration_type": "quarter",
                                "duration_beats": 1.0, "dots": 0,
                                "confidence": 0.9}],
                        }]}]}]}]}
        assert "<words>" not in to_musicxml(base)
