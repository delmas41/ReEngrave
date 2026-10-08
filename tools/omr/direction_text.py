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
      -> Surya AND Tesseract two free OCR rungs, on a word-sized crop
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
- **It abstains without an OCR rung.** No venv and no Tesseract means no
  directions, and the rest of the transcription is unchanged — the same
  degradation `staff_labels_surya` has. With either one it still runs; see
  `default_readers` for why it asks BOTH when both are there.
"""
from __future__ import annotations

import logging
import os
import re
import time
import dataclasses
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
    #: How far below a staff to reach WHEN NOTHING BOUNDS THE GAP — the last
    #: staff on the page, or the last of a system, where the band would
    #: otherwise run to the paper's edge.
    #:
    #: ⚠️ It is NOT a cap on the ordinary case, and it used to be, which cost
    #: five of the seven printed directions on one scanned page. Inside a
    #: system the gap between two staves belongs to the upper one entirely —
    #: there is no other claimant — so the band runs the whole way to the next
    #: staff. Beethoven 5's Litolff engraving puts 7 staff spaces between some
    #: staves and prints `arco` and `dolce` 3.5 to 7 spaces down, past a
    #: 3-space reach. The engraved benchmark never showed it because LilyPond
    #: sets its directions tight under the staff.
    below_spaces: float = 5.0   # was 3.0: Brahms p12 `dim.` printed 3.4 spaces under a system's last staff (2026-10-08)
    #: Clear of the staff lines themselves by this much, so the band never
    #: contains the line ink it would otherwise have to erase.
    clearance_spaces: float = 0.10   # was 0.25: Brahms p12 `dim.` printed 0.2 spaces under its staff (2026-10-08)

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
    #: ...except a dynamic glyph with ink hard against it on BOTH sides at its
    #: own row, which is not a glyph but a letter of a word.
    #:
    #: A dynamic `p` and the `p` of `espr.` are the same letter in the same
    #: family, so the detector reads the middle of that word as `dynamicP` at
    #: confidence 0.87 — correctly, on the evidence it has. Blanking it took
    #: `espr. e legato` off two of Brahms's four string staves, worth 56 edits,
    #: and it did so only after an unrelated detection change; before that the
    #: same word survived on all four. A reader whose recall turns on which
    #: boxes the detector happened to draw is not a reader.
    #:
    #: What separates the two cases is a GAP, not a shape: the letters of one
    #: word touch, while a dynamic beside a word stands clear of it. Measured
    #: on the Brahms page, `f` sits about 1.7 spaces from the `legato` beside
    #: it and `es` sits against the `p` inside `espr.` with nothing between.
    #: Half a space is well inside that.
    #:
    #: Only dynamics are excused, and deliberately: a notehead in a beamed run
    #: also has ink on both sides, and letting the test excuse THOSE would put
    #: the notes back into the very mask that exists to have them taken out.
    inside_word_gap_spaces: float = 0.9   # was 0.5: Brahms p7 `espr.` letters read as dynamics, 0.5-0.9 sp apart; a real dynamic stands 1.7 clear (2026-10-08)
    #: A detection wider than this is a SPAN, not a glyph, and its bounding box
    #: is not blanked.
    #:
    #: Blanking a box erases everything inside it, which is right for a glyph —
    #: the box IS the glyph — and wrong for a slur, whose box is the rectangle
    #: its arc travels through and is mostly paper. On a scanned Beethoven 5
    #: page a slur detected at 24.2 x 4.0 spaces (confidence 0.48) sat over the
    #: word `sempre` and erased all nine of its components; the word went from
    #: nine pieces of ink to none, and no filter downstream ever saw it.
    #:
    #: Four spaces sits in a gap the class space puts there. Measured over one
    #: scanned and one engraved page, the widest box in every GLYPH category:
    #:
    #:     notehead 3.2   clef 3.2   dynamic 2.6   flag 1.8   accidental 1.2
    #:     ---------------------------------------------------------------
    #:     pedal bracket 7.7   slur 24.2   staff 26.6   beam 37.2   restHBar 36.9
    #:
    #: Nothing is lost by leaving the spans in. Their ink is thin or enormous,
    #: which is exactly what `min_fill_ratio` and `max_glyph_width_spaces`
    #: refuse — the fill-ratio test was written for slurs in the first place.
    max_blank_width_spaces: float = 4.0
    #: A scan can fuse a whole italic word (`dim.`) into ONE component. Accepted as
    #: a word of `fused_word_weight` letters if it is at most this wide, at least
    #: this tall and fills this much of its box (a hairpin stroke is thin, an arc
    #: is sparse, a beamed group is taller than two spaces). Brahms p12, 2026-10-08.
    fused_word_max_width_spaces: float = 7.0
    fused_word_min_height_spaces: float = 0.9
    fused_word_min_fill: float = 0.45
    fused_word_weight: int = 3
    #: A dynamic glyph with ink touching its RIGHT edge and none on the left is
    #: the first letter of a word, not a dynamic: the `p` of `più` (Brahms p3,
    #: 2026-10-08: eight `più f`, every `p` blanked, the word reached the reader
    #: as `ui`). A true dynamic stands 1.7 spaces clear of a word beside it; the
    #: gap here is the width of a letter-space. Only the RIGHT edge, so a dynamic
    #: that merely ends against a stem or a slur on its left is still blanked.
    word_initial_gap_spaces: float = 0.35
    #: The tempo word at the HEAD of a system or the FOOT of its last staff
    #: (`Allegro`, `Adagio`) is set in larger, bolder type than an expression
    #: mark: its capital is 3.1 spaces tall on Brahms p3. In those two strips a
    #: letter may be this big; everywhere else `max_glyph_*_spaces` stands.
    tempo_strip_max_glyph_spaces: float = 3.6
    a_due_gap_spaces: float = 0.8


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
    """A candidate an OCR rung read and the lexicon accepted."""

    staff_index: int
    measure_index: int
    x_page: int
    text: str
    category: str
    placement: str
    terms: tuple[str, ...]
    #: Which rung supplied it. Kept in the exported JSON because the two rungs
    #: fail differently, so "who found this" is the first question to ask when
    #: a page's yield changes.
    reader: str = ""
    #: Dynamic tokens that are PART of this marking (`più f` -> ('f',)).
    dynamics: tuple[str, ...] = ()
    #: The detector's dynamic glyphs the marking includes, as
    #: `(cell_key, detector_index, (x, y, w, h))`: the same ink is the dynamic
    #: reader's AND this marking's, and is exported ONCE, as part of the marking.
    dynamic_links: tuple = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "staff_index": self.staff_index,
            "measure_index": self.measure_index,
            "x_page": self.x_page,
            "text": self.text,
            "category": self.category,
            "placement": self.placement,
            "terms": list(self.terms),
            "reader": self.reader,
            "dynamics": list(self.dynamics),
            "dynamic_links": [list(l[:2]) + [list(l[2])] for l in self.dynamic_links],
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


def _is_inside_a_word(mask: np.ndarray, box: tuple[int, int, int, int],
                      spacing: float, config: BandConfig) -> bool:
    """Is there ink hard against this box on BOTH sides, at its own rows?

    The test that tells a dynamic marking from a letter the detector read as
    one. See `BandConfig.inside_word_gap_spaces` for why it is a gap and not a
    shape.
    """
    x, y, w, h = box
    reach = max(2, int(round(config.inside_word_gap_spaces * spacing)))
    height, width = mask.shape
    top, bottom = max(0, y), min(height, y + h)
    if bottom <= top:
        return False
    left = mask[top:bottom, max(0, x - reach):max(0, x)]
    right = mask[top:bottom, min(width, x + w):min(width, x + w + reach)]
    if left.size and right.size and left.any() and right.any():
        return True
    # first letter of a word: ink hard against the right edge, nothing on the left
    near = max(1, int(round(config.word_initial_gap_spaces * spacing)))
    # (skip the first 3 px: a box clips its own glyph and leaves a speck there)
    touch = mask[top:bottom, min(width, x + w + 3):min(width, x + w + 3 + near)]
    return bool(touch.size and touch.any() and not (left.size and left.any()))


def _blank_detections(mask: np.ndarray, page_dict: dict[str, Any],
                      spacing: float, config: BandConfig) -> np.ndarray:
    """Erase every detected glyph from the mask.

    This is the step that makes the rest cheap. A conductor's page is mostly
    notes, and the pipeline has already found them and knows where they are in
    page pixels; subtracting them turns "find the text" into "find the ink".

    Two things are NOT blanked, both because a bounding box is the wrong shape
    for them: a SPAN wider than a glyph can be, whose box is mostly the paper
    its arc crosses (`max_blank_width_spaces`), and a `dynamic` sitting inside a
    run of letters, which is a letter (`inside_word_gap_spaces`).
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
                    if w > config.max_blank_width_spaces * spacing:
                        continue        # a span, not a glyph — see the config
                    if (det.get("category") == "dynamic"
                            and _is_inside_a_word(mask, (x, y, w, h),
                                                  spacing, config)):
                        continue
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
        if not (min_h <= h <= max_h):
            continue
        if w > max_w:
            # Too wide for a letter: only a FUSED WORD may pass (see BandConfig).
            if not (w <= config.fused_word_max_width_spaces * spacing
                    and h >= config.fused_word_min_height_spaces * spacing
                    and area >= config.fused_word_min_fill * w * h):
                continue
            out.append((x, y, w, h, area))
            continue
        if area < config.min_fill_ratio * w * h:
            continue
        out.append((x, y, w, h, area))
    return out


def _is_a_due_pair(run, spacing: float, config: BandConfig) -> bool:
    """Two letter-sized, letter-dense pieces close together: `a 2`.

    `a2` (both players of a shared staff, Sean 2026-10-08: read it) is TWO
    components, under the three a word needs. Admitted only as a pair that is
    small (each piece 0.45-1.8 spaces tall, the pair under 3.2 wide), tight (the
    gap under 0.8 spaces) and level (centres within 0.35 spaces) -- and then only
    a candidate: the lexicon still has to accept what the reader makes of it.
    """
    if len(run) != 2:
        return False
    a, b = sorted(run, key=lambda c: c[0])
    for x, y, w, h, area in (a, b):
        if not (0.45 * spacing <= h <= 2.0 * spacing):
            return False
        if area < 0.25 * w * h:
            return False
    gap = b[0] - (a[0] + a[2])
    width = (b[0] + b[2]) - a[0]
    level = abs((a[1] + a[3] / 2.0) - (b[1] + b[3] / 2.0))
    return (gap <= config.a_due_gap_spaces * spacing
            and width <= 4.0 * spacing and level <= 0.6 * spacing)


BASELINE_SPLIT_GAP_SPACES = 0.25
BASELINE_SPLIT_DROP_SPACES = 0.55


def _split_on_baseline(run, spacing: float, config: BandConfig):
    """Cut a run where a gap of at least a quarter space separates two groups
    whose letter centres differ by half a space or more: two WORDS on two
    baselines that the shared-line tolerance (0.9 spaces) had joined -- Litolff
    p6 `Basso` with `pizz.` printed a line lower beside it. A gap alone never
    cuts (`espr. e legato` has 1.4-1.7); the baseline step is what says another
    word. A part is kept only if it can be a word (3 letter pieces or the
    `a 2` pair), else the run stays whole."""
    ordered = sorted(run, key=lambda c: c[0])
    gap_min = BASELINE_SPLIT_GAP_SPACES * spacing
    drop_min = BASELINE_SPLIT_DROP_SPACES * spacing
    best = None
    for i in range(3, len(ordered) - 2):
        left, right = ordered[:i], ordered[i:]
        gap = right[0][0] - max(c[0] + c[2] for c in left)
        cl_all = [c[1] + c[3] / 2.0 for c in left]
        cr_all = [c[1] + c[3] / 2.0 for c in right]
        cl, cr = float(np.median(cl_all)), float(np.median(cr_all))
        if gap >= gap_min and abs(cl - cr) >= drop_min:
            # the cut that leaves each side on ONE baseline
            spread = float(np.var(cl_all) * len(cl_all) + np.var(cr_all) * len(cr_all))
            if best is None or spread < best[0]:
                best = (spread, i)
    if best is not None:
        i = best[1]
        return (_split_on_baseline(ordered[:i], spacing, config)
                + _split_on_baseline(ordered[i:], spacing, config))
    return [run]


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

    runs = [part for run in runs for part in _split_on_baseline(run, spacing, config)]
    max_w = config.max_glyph_width_spaces * spacing
    words = []
    for run in runs:
        weight = sum(config.fused_word_weight if c[2] > max_w else 1 for c in run)
        if weight < config.min_components and not _is_a_due_pair(run, spacing, config):
            continue
        x0 = min(c[0] for c in run)
        x1 = max(c[0] + c[2] for c in run)
        if x1 - x0 < config.min_word_width_spaces * spacing:
            continue
        y0 = min(c[1] for c in run)
        y1 = max(c[1] + c[3] for c in run)
        if y1 - y0 < config.min_word_height_spaces * spacing:
            continue
        words.append((x0, y0, x1, y1, weight))
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

        if following is None:
            # Nothing below: reach a fixed distance rather than to the paper.
            bottom = staff.bottom_y + config.below_spaces * spacing
        elif following.system_index != staff.system_index:
            # Two claimants — split the gap, and still do not run past the
            # fixed reach into whatever sits between systems.
            bottom = min(staff.bottom_y + config.below_spaces * spacing,
                         (staff.bottom_y + following.top_y) / 2.0)
        else:
            # One claimant. The whole gap is this staff's, however wide.
            bottom = following.top_y - clear
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
        last_of_system = max((x.staff_index for x in pws.staves
                              if x.system_index == staff.system_index
                              and x.top_y >= staff.top_y), default=-1) == staff.staff_index
        if placement == "above" or (placement == "below" and last_of_system):
            big = config.tempo_strip_max_glyph_spaces
            strip_config = dataclasses.replace(
                config, max_glyph_height_spaces=max(config.max_glyph_height_spaces, big),
                max_glyph_width_spaces=max(config.max_glyph_width_spaces, big))
        else:
            strip_config = config
        words = _cluster_into_words(
            _letter_components(band, spacing, strip_config), spacing, strip_config)
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

#: Upscale a crop until one staff space is at least this many pixels.
#:
#: The reader is MARGINAL at the size a 600-dpi page gives it, and marginal in
#: a way that looks like a hard failure. Measured on the one Brahms staff whose
#: `espr. e legato` came back empty — a crop no worse to a human eye than the
#: three identical ones that read fine:
#:
#:     as printed (124 x 625 px)     ''
#:     upscaled 2x                   'espr. e legato'
#:     top 15% trimmed off           'espr. e legato'
#:
#: Expressed in staff spaces rather than pixels because that is what makes it
#: independent of `--dpi`: at 600 dpi a space is 41 px and this doubles it,
#: while a 300-dpi page gets the 4x it needs to reach the same place. Capped,
#: so a tiny miniature-score space cannot ask for a 20x enlargement.
MIN_CROP_SPACING_PX = 80.0
MAX_CROP_UPSCALE = 4.0


def crop_for(page: PageImage, candidate: TextCandidate,
             spacing: float, erase: np.ndarray | None = None) -> np.ndarray:
    """The candidate's own pixels, padded and enlarged, from the ORIGINAL render.

    Not from the subtracted mask: the mask has holes where the detections were
    blanked, and a letter that overlapped one would arrive with a bite out of
    it. The subtraction decides WHERE to look, never what the reader sees.
    """
    pad_x = int(round(CROP_PAD_X_SPACES * spacing))
    pad_y = int(round(CROP_PAD_Y_SPACES * spacing))
    x0, y0, x1, y1 = candidate.bbox_page
    h, w = page.rgb.shape[:2]
    cy0, cy1 = max(0, y0 - pad_y), min(h, y1 + pad_y)
    cx0, cx1 = max(0, x0 - pad_x), min(w, x1 + pad_x)
    crop = page.rgb[cy0:cy1, cx0:cx1]
    if erase is not None and crop.size:
        # The PAD exists to recover letters the filters dropped; it must not
        # re-admit ink the detector named as something else (Brahms `p dolce`:
        # the `p` came back and the reading was `v dolce`). Inside the
        # candidate's own box nothing is touched.
        drop = erase[cy0:cy1, cx0:cx1] > 0
        drop[max(0, y0 - cy0):max(0, y1 - cy0), max(0, x0 - cx0):max(0, x1 - cx0)] = False
        if drop.any():
            crop = crop.copy()
            crop[drop] = 255
    scale = min(MAX_CROP_UPSCALE, MIN_CROP_SPACING_PX / max(1.0, spacing))
    if scale <= 1.0 or crop.size == 0:
        return crop
    return cv2.resize(crop, None, fx=scale, fy=scale,
                      interpolation=cv2.INTER_CUBIC)


#: The TIGHT retry crop: the candidate's own box plus this much, with EVERYTHING
#: else cut away and a white margin put back. The standard crop pads 1.3 spaces
#: sideways to recover a dropped first letter, and on a scan that pad brings in
#: the barline, the neighbouring notehead and staff-line stubs -- `cresc.`
#: between two barlines came back from Surya as '' or as `CRESC. CRESC. CRESC.`
#: and from the same box cut tight as `cresc.` (Litolff p4/p6 and Brahms p12,
#: 2026-10-08: 12 of 13 retried crops that a person reads at a glance).
TIGHT_PAD_X_SPACES = 0.25
TIGHT_PAD_Y_SPACES = 0.2
TIGHT_MARGIN_SPACES = 1.0


def tight_crop_for(page: PageImage, candidate: TextCandidate,
                   spacing: float) -> np.ndarray:
    px = int(round(TIGHT_PAD_X_SPACES * spacing))
    py = int(round(TIGHT_PAD_Y_SPACES * spacing))
    x0, y0, x1, y1 = candidate.bbox_page
    h, w = page.rgb.shape[:2]
    crop = page.rgb[max(0, y0 - py):min(h, y1 + py),
                    max(0, x0 - px):min(w, x1 + px)]
    m = int(round(TIGHT_MARGIN_SPACES * spacing))
    white = (255,) * (crop.shape[2] if crop.ndim == 3 else 1)
    crop = cv2.copyMakeBorder(crop, m, m, m, m, cv2.BORDER_CONSTANT,
                              value=white if crop.ndim == 3 else 255)
    scale = min(MAX_CROP_UPSCALE, MIN_CROP_SPACING_PX / max(1.0, spacing))
    if scale <= 1.0 or crop.size == 0:
        return crop
    return cv2.resize(crop, None, fx=scale, fy=scale,
                      interpolation=cv2.INTER_CUBIC)


#: A reader takes a list of crops (BGR arrays) and returns one string each,
#: empty where it read nothing. Both OCR rungs have this signature.
Reader = Callable[[list[np.ndarray]], list[str]]


def page_is_engraved(page: PageImage) -> bool:
    """Is this page born-digital vector, rather than a photograph of paper?

    Cheap enough to ask per page — it reads the PDF's own structure and renders
    nothing. An engraver emits the notes as VECTOR PATHS; a scanner emits one
    raster covering the sheet. Measured over the three benchmark fixtures and
    fourteen IMSLP editions, the two populations do not touch:

                             vector paths   images   image cover
        engraved  (3)          467-2058        0         0.00
        scanned  (14)             0-1        1-2      0.86-1.41

    ⚠️ **The obvious signal does not work.** Print noise ought to show up as
    mid-grey pixels a vector render has none of, and it does not separate them
    at all: 0.098-0.216 of the engraved pages against 0.009-0.978 of the scans,
    thoroughly overlapped. Embedded FONTS are no better — several scans carry
    nine of them, for the OCR text layer someone attached later.

    **Answers False on any doubt, and the asymmetry is the whole design.** A
    page wrongly called scanned costs about 140 ms a crop; a page wrongly called
    engraved loses the second reader on material where it supplies half the
    readings, and loses it silently. So this has to PROVE born-digital — vector
    paths present and no page-sized raster — and anything else, including a
    hybrid, a blank page or a PDF it cannot open, is treated as a scan.
    """
    pdf_path = getattr(page, "pdf_path", None)
    if not pdf_path:
        return False
    try:
        import fitz                                          # noqa: PLC0415

        with fitz.open(pdf_path) as doc:
            index = getattr(page, "page_index", 0)
            if not 0 <= index < doc.page_count:
                return False
            pdf_page = doc[index]
            if not pdf_page.get_drawings():
                return False
            area = abs(pdf_page.rect.width * pdf_page.rect.height) or 1.0
            for image in pdf_page.get_images(full=True):
                for rect in pdf_page.get_image_rects(image[0]) or []:
                    if abs(rect.width * rect.height) / area > 0.5:
                        return False    # a page-sized raster: scanned, or hybrid
    except Exception as exc:                                  # noqa: BLE001
        logger.debug("could not classify %s: %s", pdf_path, exc)
        return False
    return True


#: A scan carries 0-1 vector drawings; an engraving carries 467-2058. The
#: populations do not touch and this sits in the gap -- it is READ OFF the
#: measurement in `page_is_engraved`'s own docstring, not chosen. An OCR text
#: layer someone attached later adds fonts, not drawings, which is why the
#: font count was refused as a signal there and the drawing count survives.
SCAN_MAX_DRAWINGS = 8

#: Total image coverage of the sheet. A TILED scan has no single big raster,
#: so the one-image test above cannot prove it. Taken from
#: `OMR_WEIGHT_ROUTING`'s own measured rule -- "total coverage >= 0.95 on
#: every scan measured, incl. one tiled into 8 strips" (CLAUDE.md) -- rather
#: than fitted here, so the two classifications cannot drift apart.
SCAN_MIN_TOTAL_COVER = 0.95


def page_is_scanned(page: PageImage) -> bool:
    """Is this page PROVABLY a photograph of paper?

    ⚠️⚠️ NOT `not page_is_engraved(page)`, AND THE DIFFERENCE IS THE WHOLE
    POINT. That function answers False on any doubt, so its negation is
    "not proven vector" -- which is true of a hybrid, a blank page, a PDF
    that will not open, and a page with no `pdf_path` at all. Using it to
    decide whether to SKIP work would skip on every one of those, silently,
    and the failure would look exactly like a document that prints no words.
    Both functions must prove their own side; between them sits an ambiguous
    band that neither claims, and a caller must treat that band as unknown.

    The proof is two-sided and both halves are required: a page-sized raster
    (a scanner emits one sheet-covering image) AND essentially no vector
    drawings. Measured populations, from `page_is_engraved`:

                             vector paths   images   image cover
        engraved  (3)          467-2058        0         0.00
        scanned  (14)             0-1        1-2      0.86-1.41

    ⚠️ False on any doubt, exactly as its mirror is. A page wrongly called
    scanned loses the direction reader on material where it may be worth
    144 edits; a page wrongly called engraved merely pays for a reader it
    did not need. The asymmetry runs the same way for both functions --
    each refuses to claim its own side without proof -- which is why they
    are two functions and not one tri-state whose middle nobody reads.
    """
    pdf_path = getattr(page, "pdf_path", None)
    if not pdf_path:
        return False
    try:
        import fitz                                          # noqa: PLC0415

        with fitz.open(pdf_path) as doc:
            index = getattr(page, "page_index", 0)
            if not 0 <= index < doc.page_count:
                return False
            pdf_page = doc[index]
            if len(pdf_page.get_drawings()) > SCAN_MAX_DRAWINGS:
                return False          # vector art: engraved, or a hybrid
            area = abs(pdf_page.rect.width * pdf_page.rect.height) or 1.0
            total = 0.0
            for image in pdf_page.get_images(full=True):
                for rect in pdf_page.get_image_rects(image[0]) or []:
                    cover = abs(rect.width * rect.height) / area
                    if cover > 0.5:
                        return True   # one sheet-covering raster
                    total += cover
            # ⚠️ A TILED SCAN HAS NO SINGLE BIG IMAGE, and refusing it here
            # would leave the commonest residue unclaimed: measured over 180
            # library pages the only scans this function could not prove were
            # a Chaminade printing cut into TEN strips (max cover 0.11, total
            # 1.1) and two near the boundary. CLAUDE.md already records the
            # same shape and the same fix for `OMR_WEIGHT_ROUTING` -- "one
            # tiled into 8 strips", total coverage >= 0.95 on every scan
            # measured -- so this is that rule reused at its own measured
            # threshold, not a second convention invented here.
            if total >= SCAN_MIN_TOTAL_COVER:
                return True
    except Exception as exc:                                  # noqa: BLE001
        logger.debug("could not classify %s: %s", pdf_path, exc)
        return False
    return False


#: Belt-and-braces wall-time guard per crop (s): a crop still silent after this
#: reads as "" and the next crop goes on. Normal crops take 0.1-3 s.
DIRECTION_CROP_TIMEOUT_S = 20.0


#: Surya's output ceiling for ONE word crop grows with the crop's width, so a
#: short word cannot produce long output: cap = BASE + PER_SPACE x width in
#: staff spaces (a crop is enlarged to MIN_CROP_SPACING_PX per space, so the
#: width in spaces is `shape[1] / MIN_CROP_SPACING_PX`). Measured on the 10
#: held-out scan pages (benchmarks/omr-local-staff-2026-09 FINDINGS, 2026-10-08):
#: reading time 355 s -> 148 s, no word lost against the uncapped reader. A FIXED
#: 64-token cap lost `arco` on Brahms p12 on the old crop; this one keeps it on
#: the current crop, and the 20 s guard below stays as the backstop.
DIRECTION_CAP_BASE = 32
DIRECTION_CAP_PER_SPACE = 4


def word_token_cap(crop) -> int:
    return DIRECTION_CAP_BASE + int(round(
        DIRECTION_CAP_PER_SPACE * crop.shape[1] / MIN_CROP_SPACING_PX))


def _surya_word_reader(crops):
    from . import staff_labels_surya
    return staff_labels_surya.read_crops_text(
        crops, max_tokens=word_token_cap,
        crop_timeout_s=DIRECTION_CROP_TIMEOUT_S)


#: A TIGHT crop holds one word and white margin, so Surya's output ceiling can be
#: lower still: about 2 characters a staff space is generous for an italic word
#: (`cresc.` is 6 characters in ~4 spaces), and a looping decoder on a crop with
#: no word in it stops sooner. cap = BASE + PER_SPACE x width in spaces.
TIGHT_CAP_BASE = 8
TIGHT_CAP_PER_SPACE = 2


def tight_word_token_cap(crop) -> int:
    return TIGHT_CAP_BASE + int(round(
        TIGHT_CAP_PER_SPACE * crop.shape[1] / MIN_CROP_SPACING_PX))


def _surya_tight_word_reader(crops):
    from . import staff_labels_surya
    return staff_labels_surya.read_crops_text(
        crops, max_tokens=tight_word_token_cap,
        crop_timeout_s=DIRECTION_CROP_TIMEOUT_S)


_surya_word_reader.tight = _surya_tight_word_reader


def default_readers(page: PageImage | None = None) -> list[tuple[str, Reader]]:
    """The rungs to ask, in precedence order, skipping any that cannot run.

    **Both, not one, and the reason is measured rather than tidy.** On 74 crops
    cut from an 1870 Beethoven 5 scan
    (`benchmarks/omr-direction-text-2026-09/SCAN_2026-09-01.md`):

        rung                          crops read   lexicon-accepted
        surya                             21             11
        tesseract                         72              5   (raw)
        tesseract                         72             11   (rules stripped)
        surya OR tesseract                73             17

    The two fail in ways that do not overlap. Surya is an OCR interface over a
    language model: it either reads a crop or says nothing at all, and on that
    page it said nothing about 53 crops a person reads at a glance. Tesseract
    reads almost everything and gets letters wrong INSIDE the word — `Crese.`,
    `CTeSC.` — which the lexicon then refuses. So neither dominates: swapping
    Surya out for Tesseract would have LOST recall (11 accepted to 5), and
    running both accepts half again as many as either.

    Precedence is Surya first. On the scan corpus there was not one crop where
    both accepted and named different words, so this rule has never yet been
    load-bearing — it is here so that the day it is, the answer is the rung
    whose accuracy the engraved benchmark measures, not the one whose errors
    are in-word. Disagreements are counted in the report rather than hidden.

    Each rung self-disables when its dependency is absent, so a machine with
    neither degrades to no directions rather than to an error — the same
    contract `staff_labels_surya` has had since it shipped.

    **A born-digital page is asked once, a scan twice.** Given a `page`, the
    second rung is dropped where `page_is_engraved` can prove the sheet is
    vector: on the engraved benchmark every accepted reading comes from Surya
    and Tesseract supplies none of the fifteen, so asking it there buys nothing
    and costs about 140 ms a crop. On the scan it supplies 21 of 44. The
    classifier answers False on any doubt, so the expensive direction — a scan
    read by one rung — needs a positive proof of engraving that a scan cannot
    produce.

    ⚠️ **That the second rung is worthless on born-digital pages is measured on
    THREE LilyPond fixtures**, which is a thin basis for a claim about every
    engraver. It is the reason this only ever drops the rung on a page that
    proves itself vector, and the reason the report records which rungs ran:
    a born-digital edition whose font defeats Surya would show up as candidates
    proposed and not accepted, with `readers` naming only one.

    `OMR_DIRECTION_READERS` overrides all of it — `surya`, `tesseract`, or a
    comma-separated pair. An explicit choice beats the classifier.
    """
    wanted = [n.strip().lower()
              for n in os.environ.get("OMR_DIRECTION_READERS", "").split(",")
              if n.strip()]
    readers: list[tuple[str, Reader]] = []
    if not wanted or "surya" in wanted:
        try:
            from . import staff_labels_surya
            if staff_labels_surya.available():
                readers.append(("surya", _surya_word_reader))
        except Exception as exc:                              # noqa: BLE001
            logger.debug("surya rung unavailable: %s", exc)
    # Only ever DROP the second rung, and only where the page proves itself
    # born-digital — never drop the first, which would leave a page unread.
    engraved = bool(readers) and page is not None and page_is_engraved(page)
    if not wanted and engraved:
        return readers
    if not wanted or "tesseract" in wanted:
        try:
            from . import staff_labels_tesseract
            if staff_labels_tesseract.available():
                readers.append(
                    ("tesseract", staff_labels_tesseract.read_crops_text))
        except Exception as exc:                              # noqa: BLE001
            logger.debug("tesseract rung unavailable: %s", exc)
    return readers


def read_directions(pws: PageWithStaves, page_dict: dict[str, Any], *,
                    readers: Sequence[tuple[str, Reader]] | None = None,
                    scan_order: bool = False,
                    config: BandConfig = DEFAULT_BAND_CONFIG,
                    ) -> tuple[list[DirectionText], dict[str, Any]]:
    """Every direction on the page, plus a report of what happened.

    The report is returned rather than logged because the numbers that matter —
    how many candidates the CV proposed, how many each rung read, and how many
    the lexicon accepted — are the only way to tell a page with no text from a
    reader that could not run, and they look identical in the output otherwise.
    """
    candidates = find_candidates(pws, page_dict, config=config)
    info: dict[str, Any] = {
        "n_candidates": len(candidates),
        "n_read": 0,
        "n_accepted": 0,
        "rejected": [],
        "by_reader": {},
        "conflicts": [],
    }
    if not candidates:
        return [], info

    if readers is None:
        readers = default_readers(pws.page)
    info["readers"] = [name for name, _fn in readers]
    info["page_is_engraved"] = page_is_engraved(pws.page)
    if not readers:
        info["reason"] = "no OCR rung available"
        return [], info

    spacing = float(np.median([_spacing(s) for s in pws.staves]))
    raw = _page_ink(pws.page)
    blanked = _blank_detections(raw, page_dict, spacing, config)
    erase = ((raw > 0) & (blanked == 0)).astype(np.uint8) * 255
    if (scan_order and len(readers) > 1
            and any(n == "tesseract" for n, _fn in readers)):
        return _read_scan_flow(pws, page_dict, candidates, readers, spacing, erase,
                               blanked, config, info)
    crops = [crop_for(pws.page, c, spacing, erase=erase) for c in candidates]

    # Every rung reads every crop. Running the later ones only where the first
    # came back empty would be cheaper and would measure something else: a rung
    # that DISAGREES is worth knowing about, and the count below is how that
    # ever surfaces.
    read: list[tuple[str, list[str]]] = []
    for name, fn in readers:
        try:
            read.append((name, list(fn(crops))))
        except Exception as exc:                              # noqa: BLE001
            logger.warning("direction reader %s failed: %s", name, exc)
            info.setdefault("failed_readers", {})[name] = f"{type(exc).__name__}: {exc}"

    accepted_at: dict[int, DirectionText] = {}
    for index, candidate in enumerate(candidates):
        texts = [(name, texts[index]) for name, texts in read
                 if index < len(texts) and texts[index]]
        if texts:
            info["n_read"] += 1
        hits = [(name, text, lexicon_lookup(text)) for name, text in texts]
        accepted = [(name, hit) for name, _text, hit in hits if hit is not None]
        if not accepted:
            info["rejected"].extend(text for _name, text in texts)
            continue

        winner_name, hit = accepted[0]
        distinct = {h.text.strip().lower().rstrip(".") for _n, h in accepted}
        if len(distinct) > 1:
            info["conflicts"].append({
                "staff": candidate.staff_index,
                "measure": candidate.measure_index,
                "readings": {name: h.text for name, h in accepted},
                "took": winner_name,
            })
        info["by_reader"][winner_name] = info["by_reader"].get(winner_name, 0) + 1
        accepted_at[index] = DirectionText(
            staff_index=candidate.staff_index,
            measure_index=candidate.measure_index,
            x_page=candidate.x_page,
            text=hit.text,
            category=hit.category,
            placement=candidate.placement,
            terms=hit.terms,
            reader=winner_name,
            dynamics=hit.dynamics,
        )

    _link_dynamics(page_dict, candidates, accepted_at, spacing)
    out = [accepted_at[i] for i in sorted(accepted_at)]
    info["n_accepted"] = len(out)
    info["candidates"] = candidates
    return out, info


#: A crop is worth the slow reader's time on the retry only if the cheap one saw
#: LETTERS in it: at least this many alphabetic characters. Staff-line debris and
#: beamed notes read as `FEE'?` or `TTY!`; a word, however garbled, reads as 3+.
RETRY_MIN_LETTERS = 3

#: Wall time (s) after which the slow rung stops taking the STANDARD crop of
#: candidates its tight crop failed on. The tight pass has run on every
#: lettered crop by then; this only trims the fallback, and only on the
#: densest plates (Brahms p7/p12 spent 32-36 s without it).
SLOW_WIDE_BUDGET_S = 17.0


#: How far, in staff spaces, a sibling word may sit from the word it echoes and
#: still be "at the same x": the same cresc. is engraved in the same bar on
#: every staff but not always on the same pixel (Litolff p4: 0 to 4 spaces).
SIBLING_X_SLACK_SPACES = 3.0


def sibling_candidates(pws, page_dict, blanked, candidates, accepted_at,
                       spacing, config) -> list[TextCandidate]:
    """Windows to LOOK in: the same word, at the same x, on the other staves.

    A word read in one bar of a system is very often printed again in that bar
    on the other instruments (`cresc.` over a whole string choir). Where the
    first look found nothing on such a staff, this proposes ONE candidate there:
    the ink in the staff's own band within `SIBLING_X_SLACK_SPACES` of the
    word's x, found with relaxed letter tests, its box widened to at least the
    echoed word's width.

    ⚠️ It is a place to look, never an assumption: the candidate is read by the
    same OCR rungs and counts only if the LEXICON accepts what they read. Part
    names (`Basso`) are not echoed -- each staff prints its own.
    """
    staves = {s.staff_index: s for s in pws.staves}
    staff_dicts = _staff_dicts(page_dict)
    bands: dict[int, list[tuple[str, int, int]]] = {}
    for staff, placement, y_top, y_bottom in _bands_for_page(pws, config):
        bands.setdefault(staff.staff_index, []).append((placement, y_top, y_bottom))
    relaxed = dataclasses.replace(config, min_fill_ratio=0.10,
                                  min_glyph_height_spaces=0.15,
                                  min_components=2)
    slack = SIBLING_X_SLACK_SPACES * spacing
    per_system: dict[int, list[tuple[TextCandidate, DirectionText]]] = {}
    for i, d in accepted_at.items():
        if d.category == "part" and d.terms != ("a2",):
            continue
        c = candidates[i]
        if c.staff_index in staves:
            per_system.setdefault(staves[c.staff_index].system_index, []).append((c, d))
    out: list[TextCandidate] = []
    for system_index, items in per_system.items():
        items.sort(key=lambda t: t[0].bbox_page[0])
        groups: list[list[tuple[TextCandidate, DirectionText]]] = []
        for item in items:
            if groups and item[0].bbox_page[0] - groups[-1][0][0].bbox_page[0] <= slack:
                groups[-1].append(item)
            else:
                groups.append([item])
        for group in groups:
            gx0 = float(np.median([c.bbox_page[0] for c, _d in group]))
            gwidth = float(np.median([c.bbox_page[2] - c.bbox_page[0] for c, _d in group]))
            for staff in (s for s in pws.staves if s.system_index == system_index):
                sd = staff_dicts.get(staff.staff_index)
                spans = _measure_spans(sd) if sd else []
                if not spans:
                    continue
                if any(c.staff_index == staff.staff_index
                       and abs(c.bbox_page[0] - gx0) <= slack
                       for i, c in ((j, candidates[j]) for j in accepted_at)):
                    continue                  # that staff already has its word
                sp = _spacing(staff)
                for placement, y_top, y_bottom in bands.get(staff.staff_index, []):
                    if placement == "above":
                        continue              # the head-of-system strip is the finder's
                    x_lo = max(int(staff.x_start), int(gx0 - slack))
                    x_hi = min(int(staff.x_end), int(gx0 + gwidth + slack))
                    if x_hi - x_lo < 4 or y_bottom - y_top < 4:
                        continue
                    window = blanked[y_top:y_bottom, x_lo:x_hi]
                    comps = _letter_components(window, sp, relaxed)
                    if len(comps) < 2:
                        continue
                    hx0 = min(c[0] for c in comps); hx1 = max(c[0] + c[2] for c in comps)
                    hy0 = min(c[1] for c in comps); hy1 = max(c[1] + c[3] for c in comps)
                    if hy1 - hy0 < config.min_word_height_spaces * sp:
                        continue
                    bx0 = min(x_lo + hx0, int(gx0 - 0.3 * sp))
                    bx1 = max(x_lo + hx1, int(gx0 + gwidth + 0.3 * sp))
                    box = (max(0, bx0), y_top + hy0, bx1, y_top + hy1)
                    m = _measure_at(spans, box[0])
                    if m is None:
                        continue
                    out.append(TextCandidate(staff.staff_index, m, box, placement,
                                             len(comps)))
    return out


DYNAMIC_LINK_REACH_SPACES = 1.5


def _link_dynamics(page_dict, candidates, accepted_at, spacing) -> None:
    """Tie each marking that CONTAINS a dynamic (`più f`) to the detector's
    dynamic glyph(s) standing beside or inside its box, and flag those glyphs
    `in_direction_word` so the dynamic reader does not export them a second
    time. A dynamic the OCR read but no glyph stands beside stays unlinked: the
    marking keeps its letters, nothing is lost, nothing is counted twice."""
    reach = DYNAMIC_LINK_REACH_SPACES * spacing
    staves = _staff_dicts(page_dict)
    for i, d in list(accepted_at.items()):
        if not d.dynamics:
            continue
        sd = staves.get(d.staff_index)
        if sd is None:
            continue
        x0, y0, x1, y1 = candidates[i].bbox_page
        links = []
        for m in sd.get("measures", []):
            for k, det in enumerate(m.get("detections", [])):
                if det.get("category") != "dynamic" or det.get("in_direction_word"):
                    continue
                bx = det.get("bbox_page")
                if not bx:
                    continue
                dx, dy, dw, dh = (float(v) for v in bx)
                if (dx + dw >= x0 - reach and dx <= x1 + reach
                        and dy + dh >= y0 - 0.5 * spacing and dy <= y1 + 0.5 * spacing):
                    det["in_direction_word"] = True
                    links.append((det.get("cell_key"),
                                  det.get("detector_index", k),
                                  (int(dx), int(dy), int(dw), int(dh))))
        if links:
            accepted_at[i] = dataclasses.replace(d, dynamic_links=tuple(links))


def _drop_overlapping_readings(candidates, accepted_at) -> None:
    """Two readings of the same ink on one staff are ONE word, not two: keep the
    one cut from the smaller box (`piu` over `piu f`), because the metric charges
    a second copy exactly what it charges a missed word."""
    keys = sorted(accepted_at)
    for a_i, i in enumerate(keys):
        for j in keys[a_i + 1:]:
            if i not in accepted_at or j not in accepted_at:
                continue
            a, b = candidates[i], candidates[j]
            if a.staff_index != b.staff_index:
                continue
            ax0, ay0, ax1, ay1 = a.bbox_page
            bx0, by0, bx1, by1 = b.bbox_page
            if min(ax1, bx1) > max(ax0, bx0) and min(ay1, by1) > max(ay0, by0):
                area = lambda c: (c[2] - c[0]) * (c[3] - c[1])
                del accepted_at[i if area(a.bbox_page) > area(b.bbox_page) else j]


def _give_a_due_to_the_staff_below(pws, page_dict, candidates, accepted_at) -> None:
    """`a 2` is printed OVER the notes of the staff it governs, in the gap above
    them, so the band that found it (the staff above's `below` strip) names the
    wrong part. Where the next staff of the same system starts nearer than the
    last one ended, the word is that staff's."""
    ordered = sorted(pws.staves, key=lambda s: s.top_y)
    by_index = {s.staff_index: s for s in ordered}
    for i, d in list(accepted_at.items()):
        if d.terms != ("a2",):
            continue
        c = candidates[i]
        staff = by_index.get(c.staff_index)
        if staff is None:
            continue
        later = [s for s in ordered if s.top_y > staff.top_y]
        if not later or later[0].system_index != staff.system_index:
            continue
        nxt = later[0]
        y = c.bbox_page[3]
        if abs(nxt.top_y - y) >= abs(y - staff.bottom_y):
            continue
        sd = _staff_dicts(page_dict).get(nxt.staff_index)
        m = _measure_at(_measure_spans(sd), c.bbox_page[0]) if sd else None
        if m is None:
            continue
        accepted_at[i] = dataclasses.replace(d, staff_index=nxt.staff_index,
                                             measure_index=m)
        candidates[i] = dataclasses.replace(c, staff_index=nxt.staff_index,
                                            measure_index=m)


def _read_scan_flow(pws, page_dict, candidates, readers, spacing, erase,
                    blanked, config, info):
    """The reading order for a page that is not proven born-digital (a scan).

    Surya is the slow rung -- about 0.5 s a crop, and most of the candidates on
    a scanned conductor's page are not words at all (beams, ledger-line stubs,
    notehead clusters), which it spends the longest on. So the order is:

      1. Tesseract on the standard crop, then on the TIGHT crop
         (`tight_crop_for`), for every candidate (0.1 s a crop);
      2. Surya on the tight crop, then on the standard crop, ONLY for candidates
         where Tesseract saw `RETRY_MIN_LETTERS` or more letters in either crop
         and nothing is accepted yet.

    The lexicon decides every acceptance, exactly as ever -- no fuzzy matching,
    so a garbled reading is refused whichever crop it came from. What the gate
    can lose is a word Tesseract read as fewer than 3 letters on BOTH crops;
    `benchmarks/omr-direction-text-2026-09/misses` counts that against the
    ungated reader on the 10 review pages.
    """
    cheap = [(n, f) for n, f in readers if n == "tesseract"]
    slow = [(n, f) for n, f in readers if n != "tesseract"]
    n = len(candidates)
    wide: dict[int, np.ndarray] = {}
    tight: dict[int, np.ndarray] = {}

    def wide_crop(i):
        if i not in wide:
            wide[i] = crop_for(pws.page, candidates[i], spacing, erase=erase)
        return wide[i]

    def tight_crop(i):
        if i not in tight:
            tight[i] = tight_crop_for(pws.page, candidates[i], spacing)
        return tight[i]

    accepted_at: dict[int, DirectionText] = {}
    seen: dict[int, list[str]] = {i: [] for i in range(n)}

    spoke: set[int] = set()       # candidates the last `run` got any text for

    def run(rungs, indices, crop_of, suffix):
        spoke.clear()
        for name, fn in rungs:
            todo = [i for i in indices if i not in accepted_at]
            if not todo:
                return
            try:
                use = getattr(fn, "tight", fn)      # one word per crop: the lower ceiling
                texts = list(use([crop_of(i) for i in todo]))
            except Exception as exc:                          # noqa: BLE001
                logger.warning("direction reader %s failed: %s", name, exc)
                info.setdefault("failed_readers", {})[name] = f"{type(exc).__name__}: {exc}"
                continue
            for i, text in zip(todo, texts):
                if not text:
                    continue
                spoke.add(i)
                seen[i].append(text)
                hit = lexicon_lookup(text)
                if hit is None:
                    continue
                c = candidates[i]
                label = name + suffix
                accepted_at[i] = DirectionText(
                    staff_index=c.staff_index, measure_index=c.measure_index,
                    x_page=c.x_page, text=hit.text, category=hit.category,
                    placement=c.placement, terms=hit.terms, reader=label,
                    dynamics=hit.dynamics)
                info["by_reader"][label] = info["by_reader"].get(label, 0) + 1

    def read_indices(everyone):
        run(cheap, everyone, wide_crop, "")
        run(cheap, everyone, tight_crop, "-tight")
        lettered = [i for i in everyone if i not in accepted_at and
                    sum(ch.isalpha() for t in seen[i] for ch in t) >= RETRY_MIN_LETTERS]
        info["n_lettered"] = info.get("n_lettered", 0) + len(lettered)
        run(slow, lettered, tight_crop, "-tight")
        # The standard (wide) crop still gets its turn where the tight one
        # failed: it keeps the pad that recovers a dropped first letter, and
        # `p marc.` was read from it and not from the tight crop.
        # ... but only for crops the cheap rung saw a real run of letters in
        # (four in a row, `MATE`, `CTESC`): three-letter debris like `FEE'?` is
        # what a beamed group reads as, and the slow rung spends longest on it.
        strong = [i for i in lettered if i not in accepted_at and any(
            len(w) >= 4 for t in seen[i] for w in re.findall(r"[^\W\d_]+", t))]
        if time.perf_counter() - t_start <= SLOW_WIDE_BUDGET_S:
            run(slow, strong, wide_crop, "")
        else:
            info["slow_wide_skipped"] = info.get("slow_wide_skipped", 0) + len(strong)

    t_start = t0 = time.perf_counter()
    read_indices(list(range(n)))
    info["first_looks_s"] = round(time.perf_counter() - t0, 2)

    # SIBLINGS: where a word was read, look for the same word at the same x on
    # the other staves of its system (`sibling_candidates`).
    t0 = time.perf_counter()
    n_first = len(candidates)
    extra = sibling_candidates(pws, page_dict, blanked, candidates,
                               accepted_at, spacing, config)
    info["n_sibling_windows"] = len(extra)
    candidates.extend(extra)
    for i in range(n_first, len(candidates)):
        seen[i] = []
    read_indices(list(range(n_first, len(candidates))))
    # A sibling reading that lands on a word already read on that staff is a
    # second look at the same ink: keep the first.
    for i in range(n_first, len(candidates)):
        if i in accepted_at and any(
                j != i and j in accepted_at
                and candidates[j].staff_index == candidates[i].staff_index
                and abs(candidates[j].x_page - candidates[i].x_page) < 3 * spacing
                for j in list(accepted_at)):
            del accepted_at[i]
    info["n_sibling_read"] = sum(1 for i in accepted_at if i >= n_first)
    info["sibling_s"] = round(time.perf_counter() - t0, 2)
    _drop_overlapping_readings(candidates, accepted_at)
    _give_a_due_to_the_staff_below(pws, page_dict, candidates, accepted_at)
    _link_dynamics(page_dict, candidates, accepted_at, spacing)
    everyone = list(range(len(candidates)))
    info["n_read"] = sum(1 for i in everyone if seen[i])
    info["seen"] = {i: list(seen[i]) for i in everyone if i not in accepted_at}
    for i in everyone:
        if i not in accepted_at:
            info["rejected"].extend(seen[i])
    out = [accepted_at[i] for i in sorted(accepted_at)]
    info["n_accepted"] = len(out)
    info["candidates"] = candidates
    info["word_boxes"] = [candidates[i].bbox_page for i in sorted(accepted_at)]
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
