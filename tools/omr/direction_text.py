"""Read the words printed inside a system — `legato`, `Allegro con brio` — by
subtracting everything the pipeline already knows and OCRing what is left.

`wrong direction` is 151 of the 1715 pooled edits on the orchestral benchmark
(8.8%), and unlike the beams, dots, dynamics and tuplets before it there is
nothing upstream to consume: the pipeline has no text detection at all. The
class that would have supplied one, `textDynamic`, is also the class that caused
the Phase 3.4 catastrophic forgetting — so this reads text WITHOUT the detector.

## The shape of it: subtract, then OCR, then gate

    ink in the band          everything printed between two staves
      minus detections       noteheads, rests, clefs, accidentals, dynamics …
      minus curves and rules slurs, ties, beams, stems, ledger lines, barlines
      = candidate clusters   letter-sized components grouped into words
      -> Surya               the free OCR rung, on a word-sized crop
      -> direction_lexicon   a term or a phrase of terms, or nothing

Every one of those steps except the OCR is arithmetic on data already in the
result, which is why this is a POST-PASS over the built page dicts rather than a
change to detection. `contextual` established that pattern and this follows it:
a failure is recorded, never raised, and a page where it finds nothing
serialises exactly as before.

## Why the band, and why per measure

The words are in the GAPS. Every direction on the three benchmark pages sits in
the strip between one staff's bottom line and the next staff's top line, or in
the strip above the first staff — because that is where engraving puts them, and
because a word printed across a staff would be unreadable. Restricting to the
band is what makes the subtraction tractable: inside the staff, ink is mostly
notes, and outside it, ink is mostly nothing.

The crop is cut per MEASURE and not per band for a mechanical reason. A band
across a 21-staff Brahms page is 5900x183 px — 32:1. An OCR model resizes its
input to a fixed frame, and at that aspect ratio a six-letter word survives as
about four pixels of height. Cut at the barlines the same word arrives at 4:1
and is legible. Measure attribution then comes for free: the crop already knows
which measure it is.

## What it will not do

- **It does not read what it cannot gate.** `direction_lexicon` accepts a term
  or a phrase of terms and nothing else. OMR-NED charges an invented direction
  its own character count exactly as it charges a missed one, so a reader that
  guesses pays for guessing at the same rate it is paid for reading.
- **It does not touch the letter dynamics.** `f`, `pp` and `sf` are drawn
  glyphs, the detector finds them, and `export.measure_dynamics` already emits
  them. The lexicon deliberately omits them so the two readers cannot both
  claim one mark.
- **It abstains without Surya.** No venv, no directions, and the rest of the
  transcription is unchanged — the same degradation `staff_labels_surya` has.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Sequence

import cv2
import numpy as np

from .direction_lexicon import DirectionHit
from .direction_lexicon import lookup as lexicon_lookup
from .types import PageImage, PageWithStaves, Staff

logger = logging.getLogger(__name__)


# ── Geometry, all in staff spaces ───────────────────────────────────────────
#
# Every constant here is a multiple of the staff space, because that is the only
# scale a page carries that survives a change of DPI, paper size or engraving
# size. The benchmark renders Brahms on A3 at 16pt and Beethoven on A4 at the
# same, and their pixel sizes differ by a third.

@dataclass(frozen=True)
class BandConfig:
    """Where to look, and what counts as a letter when we get there."""

    #: How far above the topmost staff of a system to reach.
    #:
    #: **No number here is safe on its own, and that was measured rather than
    #: guessed.** Ink above the first staff, in staff spaces above its top line
    #: (`probe_direction_bands.py`):
    #:
    #:     brahms      Un poco sostenuto  0-6.4    [ ] 6.9-11   title 21-25
    #:     beethoven   Allegro con brio   3.1-8.2                title 13-16
    #:     mahler      -- no direction --           title 6.6-9.9
    #:
    #: Mahler's TITLE sits closer to its staff than Beethoven's DIRECTION does
    #: to that one. The two populations overlap, so a reach that finds
    #: `Allegro con brio` necessarily also finds `Symphony No. 5`, and the
    #: distance is not what separates them. `above_first_measure_only` is.
    above_spaces: float = 8.0
    #: What DOES separate them, and it is position again rather than size: a
    #: heading is centred or right-aligned on the PAGE, while a direction is
    #: left-aligned to the music it starts. So above a staff — and only there,
    #: since a direction under a staff may legitimately appear anywhere — a
    #: candidate is required to begin inside the staff's first measure. On the
    #: three pages above that keeps both real directions and refuses all four
    #: heading blocks, which no vertical reach did.
    above_first_measure_only: bool = True
    #: How far below a staff to reach when nothing is under it — the last staff
    #: of a system, where there is no next staff to bound the band.
    below_spaces: float = 3.0
    #: Clear of the staff lines themselves by this much, so the band never
    #: contains the line ink it would otherwise have to erase.
    clearance_spaces: float = 0.25

    #: A letter's ink. Lowercase `o` is about half a space tall and an ascender
    #: about one; a staff-line fragment is 0.1 and is what the minimum rejects.
    #:
    #: The maxima are set by the largest letter that is still a letter, and a
    #: tempo mark is set larger than an expression mark: on the Brahms page the
    #: bold capital `U` of `Un poco sostenuto` is 1.79 x 1.65 spaces while the
    #: italic `l` of `legato` is 0.4 x 1.1. At 1.60 the `U` was dropped and the
    #: word arrived as `n poco sostenuto`, which the lexicon then refused. Two
    #: spaces admits it. What this does NOT rely on is the maxima excluding
    #: noteheads — the detection subtraction does that, and does it by knowing
    #: where they are rather than by hoping they are small.
    min_glyph_height_spaces: float = 0.18
    max_glyph_height_spaces: float = 2.00
    max_glyph_width_spaces: float = 2.00
    #: Ink per unit of bounding box. A letter fills a fifth of its box or more;
    #: a slur arc crossing the same box fills a fortieth. This is the test that
    #: separates text from the curves, and it is a RATIO so it does not care how
    #: long the curve is.
    min_fill_ratio: float = 0.16

    #: Letters this close, side by side, are one PHRASE — not one word. The
    #: unit here has to be the phrase because the lexicon reads phrases and the
    #: metric scores them: `espr. e legato` is one direction worth 14 edits,
    #: and cut into `espr.` / `e` / `legato` it is three crops of which the
    #: middle one is a connective the lexicon must refuse.
    #:
    #: Measured on the Brahms page, the gaps inside that phrase are 1.4 and 1.7
    #: spaces — wider than the printed word space, because the letters that
    #: would have bridged them (`p` under a slur, the abbreviating period) are
    #: dropped by the letter filters. So the threshold is set past those, and
    #: what stops it running away is that both sides must already have passed
    #: the letter tests and sit on the same row.
    word_gap_spaces: float = 2.20
    #: A word is at least this many letter components. Two is where a stray
    #: pair of accidental fragments starts to look like `at`, so three.
    min_components: int = 3
    #: And at least this wide, which rejects a tight cluster of small marks.
    min_word_width_spaces: float = 0.9
    #: And at least this TALL, measured over the whole cluster rather than one
    #: component. A word has ascenders and descenders and stands about 1.3-1.8
    #: spaces high; the thing this rejects is a broken horizontal rule, whose
    #: pieces each pass the letter tests individually and which then clusters
    #: into a run 11 spaces wide and 0.2 high. Measured on the Brahms page:
    #: every true direction 1.1-1.8, both false runs 0.2.
    min_word_height_spaces: float = 0.55

    #: Detections are blanked with this much padding, in staff spaces, because
    #: a bounding box clips the glyph it names — an augmentation dot's box
    #: routinely leaves its own edge behind as two-pixel specks.
    detection_pad_spaces: float = 0.18


DEFAULT_BAND_CONFIG = BandConfig()


@dataclass(frozen=True)
class TextCandidate:
    """A word-shaped cluster of ink, before anyone has tried to read it."""

    staff_index: int
    measure_index: int
    #: Page pixels, (x0, y0, x1, y1), tight on the ink.
    bbox_page: tuple[int, int, int, int]
    #: `above` when the cluster sits over its staff, `below` when under it.
    placement: str
    n_components: int

    @property
    def x_page(self) -> int:
        return self.bbox_page[0]


@dataclass(frozen=True)
class DirectionText:
    """A candidate that Surya read and the lexicon accepted."""

    staff_index: int
    measure_index: int
    x_page: int
    text: str
    category: str
    placement: str
    terms: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "staff_index": self.staff_index,
            "measure_index": self.measure_index,
            "x_page": self.x_page,
            "text": self.text,
            "category": self.category,
            "placement": self.placement,
            "terms": list(self.terms),
        }


# ── Step 1: the ink that is not already accounted for ───────────────────────

def _spacing(staff: Staff) -> float:
    return max(1.0, float(staff.line_spacing_px))


def _page_ink(page: PageImage) -> np.ndarray:
    """255 = ink. Taken from the render rather than `page.binary`, whose
    Sauvola windowing is tuned for staff lines and leaves italic text ragged."""
    gray = (cv2.cvtColor(page.rgb, cv2.COLOR_BGR2GRAY)
            if page.rgb.ndim == 3 else page.rgb)
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    return mask


def _blank_detections(mask: np.ndarray, page_dict: dict[str, Any],
                      spacing: float, config: BandConfig) -> np.ndarray:
    """Erase every detected glyph from the mask.

    This is the step that makes the rest cheap. A conductor's page is mostly
    notes, and the pipeline has already found them and knows where they are in
    page pixels; subtracting them turns "find the text" into "find the ink".
    """
    out = mask.copy()
    pad = int(round(config.detection_pad_spaces * spacing))
    height, width = mask.shape
    for system in page_dict.get("systems", []):
        for staff in system.get("staves", []):
            for measure in staff.get("measures", []):
                for det in measure.get("detections", []):
                    box = det.get("bbox_page")
                    if not box or len(box) != 4:
                        continue
                    x, y, w, h = (int(v) for v in box)
                    out[max(0, y - pad):min(height, y + h + pad),
                        max(0, x - pad):min(width, x + w + pad)] = 0
    return out


def _letter_components(mask: np.ndarray, spacing: float,
                       config: BandConfig) -> list[tuple[int, int, int, int, int]]:
    """(x, y, w, h, area) for every component that could be a letter.

    Three tests, and the order does not matter because they are independent:
    size in both axes, and how densely the component fills its own box. The
    fill test is the one doing the work — it is what a slur fails.
    """
    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(mask, 8)
    min_h = config.min_glyph_height_spaces * spacing
    max_h = config.max_glyph_height_spaces * spacing
    max_w = config.max_glyph_width_spaces * spacing

    out = []
    for i in range(1, n):
        x, y, w, h, area = (int(stats[i, k]) for k in range(5))
        if not (min_h <= h <= max_h) or w > max_w:
            continue
        if area < config.min_fill_ratio * w * h:
            continue
        out.append((x, y, w, h, area))
    return out


def _cluster_into_words(components: Sequence[tuple[int, int, int, int, int]],
                        spacing: float,
                        config: BandConfig) -> list[tuple[int, int, int, int, int]]:
    """Group letter components into words: (x0, y0, x1, y1, n_components).

    Horizontal proximity plus a shared baseline band. Vertical agreement is
    what stops a word joining the mark stacked above or below it — an italic
    `legato` and the `f` on the same line are one row of ink, while a `legato`
    and a stray fragment a space lower are not.

    **Every open run is a candidate, not just the most recent one.** Components
    arrive in x order and a page has several rows of ink at the same x, so the
    single-chain version broke a word in half whenever anything at another
    height happened to fall between two of its letters. That is not a rare
    case: it split `Un poco sostenuto` at a SIX-pixel gap, because a staff-top
    mark 200 px lower sat between the `c` and the `o` and took over the chain.
    """
    if not components:
        return []
    ordered = sorted(components, key=lambda c: c[0])
    gap = config.word_gap_spaces * spacing

    runs: list[list[tuple[int, int, int, int, int]]] = []
    for comp in ordered:
        centre = comp[1] + comp[3] / 2.0
        joined = False
        for run in reversed(runs):
            if comp[0] - max(c[0] + c[2] for c in run) > gap:
                continue
            # Centres within a space of each other: letters of one word share a
            # line even when their heights differ (`l` against `o`).
            if any(abs(centre - (c[1] + c[3] / 2.0)) <= 0.9 * spacing
                   for c in run):
                run.append(comp)
                joined = True
                break
        if not joined:
            runs.append([comp])

    words = []
    for run in runs:
        if len(run) < config.min_components:
            continue
        x0 = min(c[0] for c in run)
        x1 = max(c[0] + c[2] for c in run)
        if x1 - x0 < config.min_word_width_spaces * spacing:
            continue
        y0 = min(c[1] for c in run)
        y1 = max(c[1] + c[3] for c in run)
        if y1 - y0 < config.min_word_height_spaces * spacing:
            continue
        words.append((x0, y0, x1, y1, len(run)))
    return words


# ── Step 2: the bands, and which measure a word is in ───────────────────────

def _bands_for_page(pws: PageWithStaves,
                    config: BandConfig) -> list[tuple[Staff, str, int, int]]:
    """`(staff, placement, y_top, y_bottom)` for every strip worth reading.

    One band below every staff and one above the topmost staff of each system.
    Within a system the below-band owns the whole gap, because a word printed
    between two staves of one system belongs to the upper one — that is where
    engraving puts an expression mark, under the part it applies to.

    **The bands are made not to overlap, and that is the whole of the
    ownership question.** Where the next staff down starts a NEW system both
    claims are live: the word could be under the last part of one system or
    over the first part of the next. A distance rule would answer that, and it
    would answer it differently on every page. Splitting the gap at its midpoint
    answers it once, geometrically, and guarantees that no word is ever offered
    to two staves — which is what would cost double, since the metric charges
    an invented direction exactly what it charges a missed one.
    """
    height = pws.page.height
    ordered = sorted(pws.staves, key=lambda s: s.top_y)
    topmost_of_system = {}
    for staff in ordered:
        topmost_of_system.setdefault(staff.system_index, staff.staff_index)

    bands: list[tuple[Staff, str, int, int]] = []
    for i, staff in enumerate(ordered):
        spacing = _spacing(staff)
        clear = config.clearance_spaces * spacing
        previous = ordered[i - 1] if i else None
        following = ordered[i + 1] if i + 1 < len(ordered) else None

        if topmost_of_system.get(staff.system_index) == staff.staff_index:
            top = staff.top_y - config.above_spaces * spacing
            if previous is not None:
                top = max(top, (previous.bottom_y + staff.top_y) / 2.0)
            bands.append((staff, "above", int(max(0, top)),
                          int(staff.top_y - clear)))

        bottom = staff.bottom_y + config.below_spaces * spacing
        if following is not None:
            new_system = following.system_index != staff.system_index
            bottom = min(bottom, (staff.bottom_y + following.top_y) / 2.0
                         if new_system else following.top_y - clear)
        bands.append((staff, "below", int(staff.bottom_y + clear),
                      int(min(bottom, height))))

    return [(s, p, t, b) for s, p, t, b in bands if b - t >= 4]


def _measure_spans(staff_dict: dict[str, Any]) -> list[tuple[int, int, int]]:
    """`(measure_index, x0, x1)` for a staff, left to right."""
    spans = []
    for measure in staff_dict.get("measures", []):
        box = measure.get("bbox_page_px")
        if not box or len(box) != 4:
            continue
        spans.append((int(measure.get("measure_index", 0)), int(box[0]), int(box[2])))
    return sorted(spans, key=lambda s: s[1])


def _measure_at(spans: Sequence[tuple[int, int, int]], x: int) -> int | None:
    """Which measure `x` falls in. The word is attributed by its LEFT edge:
    a direction is printed starting where it applies, and an italic phrase runs
    right from there, sometimes past the barline it belongs before."""
    for index, x0, x1 in spans:
        if x0 <= x < x1:
            return index
    if spans and x >= spans[-1][2]:
        return spans[-1][0]
    if spans and x < spans[0][1]:
        return spans[0][0]
    return None


def _staff_dicts(page_dict: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out = {}
    for system in page_dict.get("systems", []):
        for staff in system.get("staves", []):
            out[int(staff.get("staff_index", -1))] = staff
    return out


def find_candidates(pws: PageWithStaves, page_dict: dict[str, Any], *,
                    config: BandConfig = DEFAULT_BAND_CONFIG,
                    ) -> list[TextCandidate]:
    """Word-shaped ink in the bands, with everything detected subtracted.

    Pure CV — no OCR, no lexicon, no subprocess. Split out so the recall of the
    candidate step can be measured on its own: a word this never proposes is a
    word no reader can find, and that is a different failure from one the OCR
    got wrong.
    """
    staves_by_index = _staff_dicts(page_dict)
    if not staves_by_index:
        return []
    spacing_page = float(np.median([_spacing(s) for s in pws.staves]))
    mask = _blank_detections(_page_ink(pws.page), page_dict,
                             spacing_page, config)

    out: list[TextCandidate] = []
    for staff, placement, y_top, y_bottom in _bands_for_page(pws, config):
        staff_dict = staves_by_index.get(staff.staff_index)
        if staff_dict is None:
            continue
        spans = _measure_spans(staff_dict)
        if not spans:
            continue
        # The band spans only the staff's own music. Left of `x_start` is the
        # margin, where the instrument name is printed — a reader let loose
        # there returns `Contrabassoon` as a direction.
        x0, x1 = max(0, int(staff.x_start)), min(mask.shape[1], int(staff.x_end))
        if x1 - x0 < 4:
            continue
        band = mask[y_top:y_bottom, x0:x1]
        if band.size == 0 or not band.any():
            continue
        spacing = _spacing(staff)
        words = _cluster_into_words(
            _letter_components(band, spacing, config), spacing, config)
        for wx0, wy0, wx1, wy1, n_comp in words:
            page_box = (x0 + wx0, y_top + wy0, x0 + wx1, y_top + wy1)
            measure_index = _measure_at(spans, page_box[0])
            if measure_index is None:
                continue
            if (placement == "above" and config.above_first_measure_only
                    and measure_index != spans[0][0]):
                continue
            out.append(TextCandidate(
                staff_index=staff.staff_index,
                measure_index=measure_index,
                bbox_page=page_box,
                placement=placement,
                n_components=n_comp,
            ))
    return out


# ── Step 3: read them ───────────────────────────────────────────────────────

#: How much to leave around a crop, in staff spaces. Wider across than down,
#: and the asymmetry is measured rather than tidy: the box is tight on the
#: components that SURVIVED the letter filters, so a word whose first letter
#: was dropped — an `l` fused into the slur above it, an `f` blanked with the
#: dynamic it touches — arrives cut off at the left. `legato` read as `egato`
#: is a lexicon miss, not a near miss. Vertically there is nothing to recover
#: and a taller crop only invites the staff line above into the frame.
CROP_PAD_X_SPACES = 1.3
CROP_PAD_Y_SPACES = 0.45


def crop_for(page: PageImage, candidate: TextCandidate,
             spacing: float) -> np.ndarray:
    """The candidate's own pixels, padded, from the ORIGINAL render.

    Not from the subtracted mask: the mask has holes where the detections were
    blanked, and a letter that overlapped one would arrive with a bite out of
    it. The subtraction decides WHERE to look, never what the reader sees.
    """
    pad_x = int(round(CROP_PAD_X_SPACES * spacing))
    pad_y = int(round(CROP_PAD_Y_SPACES * spacing))
    x0, y0, x1, y1 = candidate.bbox_page
    h, w = page.rgb.shape[:2]
    return page.rgb[max(0, y0 - pad_y):min(h, y1 + pad_y),
                    max(0, x0 - pad_x):min(w, x1 + pad_x)]


#: A reader takes a list of crops (BGR arrays) and returns one string each,
#: empty where it read nothing. `staff_labels_surya` supplies the default.
Reader = Callable[[list[np.ndarray]], list[str]]


def read_directions(pws: PageWithStaves, page_dict: dict[str, Any], *,
                    reader: Reader | None = None,
                    config: BandConfig = DEFAULT_BAND_CONFIG,
                    ) -> tuple[list[DirectionText], dict[str, Any]]:
    """Every direction on the page, plus a report of what happened.

    The report is returned rather than logged because the two numbers that
    matter — how many candidates the CV proposed and how many the lexicon
    accepted — are the only way to tell a page with no text from a reader that
    could not run, and they look identical in the output otherwise.
    """
    candidates = find_candidates(pws, page_dict, config=config)
    info: dict[str, Any] = {
        "n_candidates": len(candidates),
        "n_read": 0,
        "n_accepted": 0,
        "rejected": [],
    }
    if not candidates:
        return [], info

    if reader is None:
        from .staff_labels_surya import read_crops_text
        reader = read_crops_text

    spacing = float(np.median([_spacing(s) for s in pws.staves]))
    crops = [crop_for(pws.page, c, spacing) for c in candidates]
    texts = reader(crops)
    info["n_read"] = sum(1 for t in texts if t)

    out: list[DirectionText] = []
    for candidate, text in zip(candidates, texts):
        if not text:
            continue
        hit: DirectionHit | None = lexicon_lookup(text)
        if hit is None:
            info["rejected"].append(text)
            continue
        out.append(DirectionText(
            staff_index=candidate.staff_index,
            measure_index=candidate.measure_index,
            x_page=candidate.x_page,
            text=hit.text,
            category=hit.category,
            placement=candidate.placement,
            terms=hit.terms,
        ))
    info["n_accepted"] = len(out)
    return out, info


def attach_to_page(page_dict: dict[str, Any],
                   directions: Sequence[DirectionText]) -> int:
    """Write each direction onto the measure it belongs to. Returns how many
    landed.

    Stored on the MEASURE rather than collected page-side because that is where
    the exporter reads from, and because a direction whose measure cannot be
    found is a direction with nowhere to go — it is dropped here rather than
    carried forward to be placed by a guess later on.
    """
    staves = _staff_dicts(page_dict)
    placed = 0
    for direction in directions:
        staff = staves.get(direction.staff_index)
        if staff is None:
            continue
        for measure in staff.get("measures", []):
            if int(measure.get("measure_index", -1)) != direction.measure_index:
                continue
            measure.setdefault("direction_texts", []).append(direction.to_json())
            placed += 1
            break
    return placed
