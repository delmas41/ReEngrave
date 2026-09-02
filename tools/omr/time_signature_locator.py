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

## Common time, and cut common — which is NOT a template

`C` is read, as a single glyph two spaces tall centred on the middle line,
padded into the same four-space box so the search stays one-dimensional. It is
easily the strongest reading in the corpus — five common-time pages at 0.745 to
0.761, against 0.50 to 0.62 for the scanned digit meters.

**Cut common is read too, as of 2026-09-01, but not by searching for it.** The
08 work built the `timeSigCutCommon` template and withheld it, on the ground
that a C with a stroke through it correlates with any vertical ink crossing any
rounded blob — it claimed a meter on seven systems that print none. What it
could not know is what the withholding cost, because no page in that corpus
printed a real cut common. Fifteen of the 97 dossier works open on one, and on
those pages the reader does not abstain: **it reads `C`**, unanimously, at 0.58
(Mozart 40, 11 staves of 11) and 0.56 (Brahms 4, 13 of 13), so a 2/2 page ships
as 4/4 with every bar measured against a meter twice too long.

Adding the template fails BOTH ways and the second is the instructive one
(`benchmarks/omr-timesig-2026-09/sweep_cutC.json`): nine false systems, and it
STILL loses to plain `C` on the real cut-common pages. That is not a tuning
problem. A `C` is a SUBSET of a cut-C's ink, so on a real ¢ both templates match
and the one with less ink to account for scores higher; NCC does not reward a
template for the extra ink it explains. No threshold between two scores fixes
that.

So the question is asked by POSITION instead, the way the clef locator's false
positives were finally separated: **a cut common is a common with a stroke
through the middle, and a plain C's middle is hollow** (its aperture faces
right). Once `C` has won at some x, the centre fifth of the matched box is
measured over the glyph's own two-space height. Over 87 staves that matched C
across both corpora (`probe_cut_stroke.py`):

| what the page prints | staves | centre-column fill |
|---|--:|---|
| cut common | 24 | **1.00 every one** |
| common | 57 | 0.00–0.30 |
| nothing (matched C anyway) | 6 | 0.00–0.48 |

The gap runs 0.48 to 1.00 with nothing in it, and every threshold from 0.50 to
1.00 gives the same answer — a plateau, which is what a constant read off a gap
should look like. `cut_stroke_min_fill` sits at 0.75, the middle of it.

**This adds no false-positive surface at all, by construction.** The cut reading
rides on a `C` that already cleared the threshold and the vote; nothing new
enters the search, so a page that abstains today still abstains and a page that
reads 3/4 still reads 3/4. The only outcome that can change is a `C` becoming a
`C|`. That is why the template stays out of `DEFAULT_METERS` — the 08 measurement
of what putting it in costs is still correct.

2/2 spelled in digits is read as it always was, which is how the Mahler fixture
prints it.

## What it does not read

Only the FIRST meter of a system. A mid-system meter change is not looked for,
and will keep whatever the detector says about it.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Iterable, Sequence

import cv2
import numpy as np

from tools.omr.header_ink import staff_metrics
from tools.omr.symbol_library.loader import SymbolLibrary
from tools.omr.types import MeasureCell

#: Meters worth searching for, as `(numerator, denominator, raw)`. Every one is
#: a real repertoire meter and the denominators are all note values; adding
#: implausible pairs costs accuracy rather than coverage, because a wrong
#: template that happens to fit some ink is a wrong ANSWER, where a missing
#: template is only an abstention.
#:
#: `C` is the letter form of 4/4, kept distinct from the digit spelling because
#: `raw` should say what the page prints.
#:
#: **Cut common is deliberately absent, and is read anyway.** Searching for it
#: was measured twice and refused twice: on 2026-08-31 for reading a meter on
#: seven systems that print none, and on 2026-09-01 for ALSO losing to plain `C`
#: on the two pages that really print one — a `C` is a subset of a cut-C's ink,
#: so the smaller template wins. `_looks_cut` reads the stroke by position after
#: `C` has won instead, which adds nothing to this list and so adds no way for
#: the search to go wrong. See the module docstring.
DEFAULT_METERS: tuple[tuple[int, int, str], ...] = (
    (2, 2, "2/2"), (3, 2, "3/2"), (4, 2, "4/2"),
    (2, 4, "2/4"), (3, 4, "3/4"), (4, 4, "4/4"), (5, 4, "5/4"), (6, 4, "6/4"),
    (7, 4, "7/4"), (9, 4, "9/4"), (12, 4, "12/4"),
    (3, 8, "3/8"), (5, 8, "5/8"), (6, 8, "6/8"), (7, 8, "7/8"), (9, 8, "9/8"),
    (12, 8, "12/8"),
    (6, 16, "6/16"), (9, 16, "9/16"), (12, 16, "12/16"),
    (4, 4, "C"),
)

#: `raw` values that are drawn as one glyph centred on the staff rather than as
#: two stacked rows of digits, and the SMuFL name of that glyph.
LETTER_METERS = {"C": "timeSigCommon", "C|": "timeSigCutCommon"}


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

    #: Fraction of the matched `C`'s own height that must be inked down its
    #: centre column for the reading to become a cut common. Read off a gap, not
    #: tuned: 24 cut staves all measure 1.00 and the highest non-cut of 63
    #: measures 0.48, and every threshold in 0.50–1.00 gives the same answer.
    cut_stroke_min_fill: float = 0.75

    #: Width of that centre column, as a fraction of the matched box either side
    #: of its middle. A stroke is drawn through the centre; the C's own arcs are
    #: at the edges, so this must stay well clear of them.
    cut_stroke_centre_frac: float = 0.10

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
    #: What the page prints: "3/4", or "C"/"C|" for the letter forms. Part of
    #: the vote's key, so a page cannot average a C and a 4/4 into one answer.
    raw: str = ""

    @property
    def symbol(self) -> str | None:
        """"common" / "cut" when a LETTER form was matched, else None.

        This is the same fact `rhythm.parse_time_signature` sets from a
        `timeSigCommon` / `timeSigCutCommon` DETECTION, and it is set here on the
        same terms: the letter glyph itself was matched, so the glyph is what was
        read. `raw` is not evidence for it — a 4/4 spelled in digits also carries
        no symbol — which is why this is derived from the letter forms alone and
        never from the numbers. `export.to_musicxml` writes it as MusicXML's
        `symbol=` attribute, and musicdiff charges 3 edits per staff when it
        disagrees with the truth, so dropping it is not cosmetic.
        """
        if self.raw not in LETTER_METERS:
            return None
        return "cut" if self.raw == "C|" else "common"

    def as_dict(self, source: str = "header_reader") -> dict[str, object]:
        out: dict[str, object] = {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "raw": self.raw,
            "source": source,
            "score": round(self.score, 4),
        }
        if self.symbol is not None:
            out["symbol"] = self.symbol
        return out


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


@lru_cache(maxsize=4)
def _letter_templates(em_px: int) -> dict[str, np.ndarray]:
    """Ink-positive rasters for the C and cut-C glyphs, keyed by SMuFL name."""
    library = SymbolLibrary.load()
    wanted = set(LETTER_METERS.values())
    return {
        entry.smufl_name: (255 - entry.load_image()).astype(np.uint8)
        for entry in library.entries
        if entry.smufl_name in wanted and entry.size_px == em_px
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
    em_px: int, meters: tuple[tuple[int, int, str], ...]
) -> tuple[tuple[tuple[int, int, str], np.ndarray], ...]:
    """One template per meter, exactly four staff spaces tall.

    Digit meters are the numerator's row stacked over the denominator's. The
    letter forms are a single glyph two spaces tall, centred on the staff's
    middle line — so it is padded into the same four-space box, which keeps the
    search one-dimensional for both kinds.

    Bravura's digits overshoot two staff spaces by a pixel or two, so a stack is
    assembled at the glyphs' natural size and then resized to the four-space box.
    Assembling it directly into a 4x`space` box instead clips the taller digits,
    which is how this was first written and why `timeSig2` lost its foot.
    """
    digits = _digit_templates(em_px)
    letters = _letter_templates(em_px)
    space = em_px / 4.0
    target_h = int(round(4 * space))
    out = []
    for numerator, denominator, raw in meters:
        if raw in LETTER_METERS:
            glyph = letters.get(LETTER_METERS[raw])
            if glyph is None:
                continue  # library predates the letter forms; abstain on them
            stacked = np.zeros((glyph.shape[0] * 2, glyph.shape[1]), np.uint8)
            y = (stacked.shape[0] - glyph.shape[0]) // 2
            stacked[y:y + glyph.shape[0], :] = glyph
            width = glyph.shape[1]
        else:
            top = _row(digits, str(numerator))
            bottom = _row(digits, str(denominator))
            width = max(top.shape[1], bottom.shape[1])
            half = max(top.shape[0], bottom.shape[0])
            stacked = np.zeros((half * 2, width), np.uint8)
            for glyphs, y0 in ((top, 0), (bottom, half)):
                y = y0 + (half - glyphs.shape[0]) // 2
                x = (width - glyphs.shape[1]) // 2
                stacked[y:y + glyphs.shape[0], x:x + glyphs.shape[1]] = glyphs
        target_w = max(2, int(round(width * target_h / stacked.shape[0])))
        out.append((
            (numerator, denominator, raw),
            cv2.resize(stacked, (target_w, target_h), interpolation=cv2.INTER_AREA),
        ))
    return tuple(out)


def _looks_cut(
    strip: np.ndarray,
    origin: tuple[int, int],
    shape: tuple[int, int],
    config: TimeSignatureLocatorConfig,
) -> bool:
    """Is there a vertical stroke through the middle of this matched `C`?

    `origin` is the match's `(x, y)` in `strip`, `shape` its `(h, w)`. The
    template is four staff spaces tall and the letter glyph occupies the middle
    two of them (`_meter_templates` pads it there), so the glyph's own height is
    the middle half of the box — which is what the fill is measured over, not the
    padded box, or the padding would halve every reading.

    A row counts as inked if anything in the centre column is inked, not if the
    mean is high: the stroke is thin and a degraded print thins it further, while
    a mean would make the answer depend on stroke weight, which is exactly the
    kind of quantity the 08 work found moves with the printing rather than the
    answer (see the ink-coverage discriminator it rejected).
    """
    x, y = origin
    height, width = shape
    box = strip[y:y + height, x:x + width]
    if box.size == 0:
        return False
    glyph_top = int(round(height * 0.25))
    glyph_bottom = int(round(height * 0.75))
    half = config.cut_stroke_centre_frac
    x0 = int(round(width * (0.5 - half)))
    x1 = int(round(width * (0.5 + half)))
    column = box[glyph_top:glyph_bottom, x0:x1]
    if column.size == 0:
        return False
    inked_rows = (column.max(axis=1) > 127).mean()
    return bool(inked_rows >= config.cut_stroke_min_fill)


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
    best_at: tuple[tuple[int, int], tuple[int, int]] | None = None
    for (numerator, denominator, raw), template in _meter_templates(
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
                raw=raw,
            )
            best_at = (location, template.shape)
    if best is None or best.score < floor:
        return None
    # A cut common is a common with a stroke through it, and the stroke is read
    # by POSITION after the fact rather than searched for — searching for it
    # loses to plain `C` on real cut-common pages, because a C is a subset of a
    # cut-C's ink. Nothing new enters the search, so nothing new can be found
    # where there is no meter at all.
    if best.raw == "C" and best_at is not None and _looks_cut(
        strip, best_at[0], best_at[1], config
    ):
        best = replace(best, numerator=2, denominator=2, raw="C|")
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
    votes: Counter[tuple[int, int, str]] = Counter(
        (r.numerator, r.denominator, r.raw) for r in reads if r is not None
    )
    if not votes:
        return None
    ranked = votes.most_common()
    (numerator, denominator, raw), count = ranked[0]
    if len(ranked) > 1 and ranked[1][1] == count:
        return None  # a tie is not a reading
    needed = max(config.min_staves, int(round(config.min_staff_fraction * total)))
    if count < needed:
        return None
    winners = [r for r in reads if r is not None
               and (r.numerator, r.denominator, r.raw) == (numerator, denominator, raw)]
    scores = sorted(r.score for r in winners)
    out: dict[str, object] = {
        "numerator": numerator,
        "denominator": denominator,
        "raw": raw,
        "source": "header_reader",
        "votes": count,
        "voters": total,
        "median_score": round(scores[len(scores) // 2], 4),
    }
    # The glyph is part of the meter and the exporter writes it (MusicXML
    # `symbol=`); the winners all read the same `raw`, so they all read the same
    # glyph. See `LocatedTimeSignature.symbol`.
    if winners[0].symbol is not None:
        out["symbol"] = winners[0].symbol
    return out


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
