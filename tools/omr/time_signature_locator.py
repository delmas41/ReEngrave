"""Read a staff's time signature from its header, by shape rather than class.

The clef got a CV locator and the key signature got a slot-table geometry
reader, both because the detector could not be relied on for them. The meter
never got one, and it is the worst-served of the three: on a real orchestral
scan the detector finds no time-signature digit anywhere in the header, so
`rhythm.parse_time_signature` has nothing to parse and the page reports `null`
— after which `export.to_musicxml` writes 4/4 onto whatever the page actually
is. Measured on page 1 of the IMSLP Beethoven 5 (a 2/4 movement, with `2` over
`4` printed legibly on all twelve staves): zero header detections, and the five
`timeSig4` boxes the detector DID fire were barline fragments in the middles of
bars 6 to 12, which `_dominant_detected_meter` then propagated as common time
across the page. Confidently wrong, from ink that is not a time signature.

## What is read

A time signature is a shape with an unusually rigid geometry, and this reads
that geometry instead of classifying glyphs:

  - it spans the STAFF exactly — numerator in the upper two spaces, denominator
    in the lower two, so its vertical placement is known before the search;
  - the two halves are horizontally centred on each other;
  - the digits are SMuFL glyphs, and this repo already ships Bravura
    `timeSig0`-`timeSig9` templates (`tools/omr/symbol_library/`).

So the search is one-dimensional. A composite template is built per candidate
meter — the numerator's digits laid out in the top half, the denominator's in
the bottom, scaled so four staff spaces of template match four staff spaces of
page — and slid along the header window in x only. The best normalised
cross-correlation wins.

Because the vertical extent is pinned to the staff, a match cannot be a
notehead (one space tall) or an instrument name (outside the staff, wrong
proportions). That is what makes a bare NCC score usable here when it would not
be on a free search.

## Why NCC alone, and how the threshold was chosen

Two other discriminators were measured and REJECTED, both because they moved
with the printing rather than with the answer:

  *Ink coverage* — the fraction of template ink actually inked on the page.
  Separates well on one corpus and not across corpora: a scan's heavy 19th
  century type covers 0.86-0.97 of the glyph while LilyPond's thin engraving
  covers 0.72-0.79, and the engraved TRUE reads therefore score below the
  scanned FALSE ones.

  *Whitespace gutters* — blank columns either side, on the theory that a meter
  is isolated from the key signature and the first note. True reads measured
  0.00-0.33 and false reads 0.00-1.00. It does not separate at all.

NCC survived both corpora: true reads 0.50-0.62 on the scan and 0.69-0.79 on
engraved pages, against 0.31-0.49 for every false read on pages that print no
meter. `min_score` sits at 0.50, and the honest statement of the margin is that
the closest pair is a single staff — the scan's weakest true read at 0.505
against the strongest false one at 0.492.

**That margin is not what the decision rests on.** A meter is printed on every
staff of a system at the same x, so the reading is a VOTE
(`vote_system_time_signature`): a meter must be read on at least half the
system's staves before it is believed. The false reads that reach 0.49 do so on
pages where the whole system sits below the bar, and one staff drifting over it
cannot carry a page. The vote is the mechanism; the threshold only decides who
gets to vote.

## What it does not read

`timeSigCommon` and `timeSigCutCommon` — the C and ¢ glyphs — are not in the
symbol library, so a common-time page gets no reading here and abstains. That
is not a gap in coverage the way it looks: the detector reads those two glyphs
well (they are distinctive, and unlike the digits they are not confusable with
a barline), and `rhythm.parse_time_signature` already has a path for them. This
reader exists for the case the detector cannot do.

It also reads only the FIRST meter of a system. A mid-system meter change is
not looked for, and will keep whatever the detector says about it.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Sequence

import cv2
import numpy as np

from tools.omr.header_ink import staff_metrics
from tools.omr.symbol_library.loader import SymbolLibrary
from tools.omr.types import MeasureCell

#: Meters worth searching for. Every one is a real repertoire meter and the
#: denominators are all note values; adding implausible pairs costs accuracy
#: rather than coverage, because a wrong template that happens to fit some ink
#: is a wrong ANSWER, where a missing template is only an abstention.
DEFAULT_METERS: tuple[tuple[int, int], ...] = (
    (2, 2), (3, 2), (4, 2),
    (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4), (9, 4), (12, 4),
    (3, 8), (5, 8), (6, 8), (7, 8), (9, 8), (12, 8),
    (6, 16), (9, 16), (12, 16),
)


@dataclass(frozen=True)
class TimeSignatureLocatorConfig:
    #: Bravura em size to take digit templates at. The em is four staff spaces,
    #: so a digit is `template_em_px / 2` tall and the page is rescaled to suit.
    template_em_px: int = 120

    #: Minimum NCC for a staff's reading to be allowed into the vote. See the
    #: module docstring for the two corpora this is drawn from and for why the
    #: vote, not this number, is what makes the result safe.
    min_score: float = 0.50

    #: A meter must be read on this fraction of the system's staves. Real
    #: meters are printed on all of them; the false reads that clear
    #: `min_score` are scattered ones and twos.
    min_staff_fraction: float = 0.5

    #: ...and on at least this many, so a two-staff system cannot be decided by
    #: a single reading.
    min_staves: int = 2

    #: Vertical slack around the staff, in staff spaces. Time-signature digits
    #: overshoot the top and bottom lines slightly in most faces.
    band_pad_spaces: float = 0.5

    meters: tuple[tuple[int, int], ...] = DEFAULT_METERS


DEFAULT_LOCATOR_CONFIG = TimeSignatureLocatorConfig()


@dataclass(frozen=True)
class LocatedTimeSignature:
    numerator: int
    denominator: int
    score: float
    #: Left edge of the match, in the header cell's canonical pixels. Used by
    #: the vote only for reporting; agreement is on the meter, not the place.
    x_canonical: int

    @property
    def raw(self) -> str:
        return f"{self.numerator}/{self.denominator}"

    def as_dict(self, source: str = "header_reader") -> dict[str, object]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "raw": self.raw,
            "source": source,
            "score": round(self.score, 4),
        }


@lru_cache(maxsize=4)
def _digit_templates(em_px: int) -> dict[str, np.ndarray]:
    """Ink-positive Bravura digit rasters, keyed by the digit character."""
    library = SymbolLibrary.load()
    return {
        entry.smufl_name[-1]: (255 - entry.load_image()).astype(np.uint8)
        for entry in library.entries
        if entry.smufl_name.startswith("timeSig")
        and entry.size_px == em_px
        and entry.smufl_name[-1].isdigit()
    }


def _row(digits: dict[str, np.ndarray], text: str) -> np.ndarray:
    """Lay out a multi-digit number left to right, vertically centred."""
    glyphs = [digits[c] for c in text]
    height = max(g.shape[0] for g in glyphs)
    row = np.zeros((height, sum(g.shape[1] for g in glyphs)), np.uint8)
    x = 0
    for glyph in glyphs:
        y = (height - glyph.shape[0]) // 2
        row[y:y + glyph.shape[0], x:x + glyph.shape[1]] = glyph
        x += glyph.shape[1]
    return row


@lru_cache(maxsize=8)
def _meter_templates(
    em_px: int, meters: tuple[tuple[int, int], ...]
) -> tuple[tuple[tuple[int, int], np.ndarray], ...]:
    """One stacked template per meter, exactly four staff spaces tall.

    Bravura's digits overshoot two staff spaces by a pixel or two, so the
    composite is assembled at the glyphs' natural size and then resized to the
    four-space box. Assembling it directly into a 4x`space` box instead clips
    the taller digits, which is how this was first written and why `timeSig2`
    lost its foot.
    """
    digits = _digit_templates(em_px)
    space = em_px / 4.0
    out = []
    for numerator, denominator in meters:
        top = _row(digits, str(numerator))
        bottom = _row(digits, str(denominator))
        width = max(top.shape[1], bottom.shape[1])
        half = max(top.shape[0], bottom.shape[0])
        stacked = np.zeros((half * 2, width), np.uint8)
        for glyphs, y0 in ((top, 0), (bottom, half)):
            y = y0 + (half - glyphs.shape[0]) // 2
            x = (width - glyphs.shape[1]) // 2
            stacked[y:y + glyphs.shape[0], x:x + glyphs.shape[1]] = glyphs
        target_h = int(round(4 * space))
        target_w = max(2, int(round(width * target_h / stacked.shape[0])))
        out.append((
            (numerator, denominator),
            cv2.resize(stacked, (target_w, target_h), interpolation=cv2.INTER_AREA),
        ))
    return tuple(out)


def locate_time_signature(
    cell: MeasureCell,
    *,
    config: TimeSignatureLocatorConfig = DEFAULT_LOCATOR_CONFIG,
    min_score: float | None = None,
) -> LocatedTimeSignature | None:
    """Read the time signature in one staff's header cell, or return None.

    `cell` is a header cell from `staff_header.extract_header_cell` — the crop
    running from the staff's left edge to the first barline, which is where a
    meter is printed and, on degraded prints, is NOT the same region as the
    staff-start measure cell.

    `min_score` overrides the configured threshold. Benchmarks pass 0.0 to see
    the near-misses; production should not.
    """
    floor = config.min_score if min_score is None else min_score
    metrics = staff_metrics(cell)
    if metrics is None:
        return None
    spacing, top_y, bottom_y = metrics
    if spacing <= 0:
        return None

    image = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if image is None:
        return None
    if image.ndim == 3:
        image = image[:, :, 0]

    # Rescale so one staff space on the page is one staff space of template.
    # Staff lines are already gone in `image_no_staff`; the digits sit ON those
    # lines, so matching the variant that still has them scores the barline as a
    # `1` more readily than it scores the real meter (measured: two of twelve
    # staves on Beethoven 5 p.1 matched at x=0).
    scale = (config.template_em_px / 4.0) / spacing
    ink = cv2.resize((255 - image).astype(np.uint8), None, fx=scale, fy=scale,
                     interpolation=cv2.INTER_AREA)

    pad = int(round(config.band_pad_spaces * config.template_em_px / 4.0))
    y0 = max(0, int(round(top_y * scale)) - pad)
    y1 = min(ink.shape[0], int(round(bottom_y * scale)) + pad)
    strip = ink[y0:y1, :]
    if strip.size == 0:
        return None

    best: LocatedTimeSignature | None = None
    for (numerator, denominator), template in _meter_templates(
        config.template_em_px, tuple(config.meters)
    ):
        if template.shape[0] > strip.shape[0] or template.shape[1] > strip.shape[1]:
            continue
        response = cv2.matchTemplate(strip, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, location = cv2.minMaxLoc(response)
        if best is None or score > best.score:
            best = LocatedTimeSignature(
                numerator=numerator,
                denominator=denominator,
                score=float(score),
                x_canonical=int(round(location[0] / scale)),
            )
    if best is None or best.score < floor:
        return None
    return best


def vote_system_time_signature(
    reads: Sequence[LocatedTimeSignature | None],
    *,
    n_staves: int | None = None,
    config: TimeSignatureLocatorConfig = DEFAULT_LOCATOR_CONFIG,
) -> dict[str, object] | None:
    """Reconcile one system's per-staff readings into a meter, or abstain.

    A meter is printed on every staff of a system, so agreement across staves is
    the evidence — not the strength of any one reading. The winner must be read
    on `min_staff_fraction` of the system's staves and on at least `min_staves`
    of them, and must be unopposed by another meter with as many votes.

    `n_staves` defaults to `len(reads)`; pass it when `reads` has already been
    filtered so the denominator stays the size of the system.
    """
    total = len(reads) if n_staves is None else n_staves
    if total <= 0:
        return None
    votes: Counter[tuple[int, int]] = Counter(
        (r.numerator, r.denominator) for r in reads if r is not None
    )
    if not votes:
        return None
    ranked = votes.most_common()
    (numerator, denominator), count = ranked[0]
    if len(ranked) > 1 and ranked[1][1] == count:
        return None  # a tie is not a reading
    needed = max(config.min_staves, int(round(config.min_staff_fraction * total)))
    if count < needed:
        return None
    winners = [r for r in reads
               if r is not None and (r.numerator, r.denominator) == (numerator, denominator)]
    scores = sorted(r.score for r in winners)
    return {
        "numerator": numerator,
        "denominator": denominator,
        "raw": f"{numerator}/{denominator}",
        "source": "header_reader",
        "votes": count,
        "voters": total,
        "median_score": round(scores[len(scores) // 2], 4),
    }


def read_system_time_signatures(
    header_cells: dict[int, MeasureCell],
    staves_by_system: dict[int, Iterable[int]],
    *,
    config: TimeSignatureLocatorConfig = DEFAULT_LOCATOR_CONFIG,
) -> dict[int, dict[str, object]]:
    """Read and vote a meter for each system that has one, keyed by system.

    Systems with no agreed meter are simply absent from the result — a system
    printing no time signature (every system after the first, in most scores)
    is the common case, not an error.
    """
    out: dict[int, dict[str, object]] = {}
    for system_index, staff_indices in staves_by_system.items():
        indices = list(staff_indices)
        reads = [
            locate_time_signature(header_cells[i], config=config)
            if i in header_cells else None
            for i in indices
        ]
        meter = vote_system_time_signature(reads, n_staves=len(indices), config=config)
        if meter is not None:
            out[system_index] = meter
    return out
