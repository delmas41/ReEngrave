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
    #:
    #: 0.5 until 2026-09-01, and half a system is nothing like what agreement on
    #: a printed meter looks like. Measured over the 13 systems that produce a
    #: reading across both corpora: every one of the 12 CORRECT readings is
    #: agreed by **0.909 of its system or more** (the worst are 10/11, 11/12 and
    #: 25/27, all pages with an unreadable staff or two), and the one WRONG
    #: reading — Beethoven 3 i, whose `3` matches Bravura's `6` on a Litolff
    #: plate — is agreed by exactly **6 of 12**. Every value from 0.55 to 0.90
    #: gives the identical verdict table, so this is a plateau read off a gap
    #: with nothing in it and 0.70 is its middle.
    min_staff_fraction: float = 0.70

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

    #: ROADMAP 2.72. Read the DENOMINATOR from its own half of the stack,
    #: against only the denominators a meter with the stack's numerator can
    #: have, once the whole-stack match has said where the stack is. See
    #: `_split_reading` for what that fixes and why it is not a retune.
    split_halves: bool = True

    #: How far, in staff spaces, either side of the whole-stack match the halves
    #: may look for their digits. The stack match has already placed the column;
    #: this is only the slack for its two halves not sharing one x.
    split_column_slack_spaces: float = 0.5

    #: How far, in staff spaces, the denominator's centre may sit from the
    #: stack's centre and still be that stack's second row. A time signature
    #: centres its two rows on each other (module docstring); a digit found in
    #: another column is unrelated ink, not this meter's denominator.
    split_centre_tol_spaces: float = 0.6

    #: ROADMAP 2.72, `locate_meter_by_halves`: the weaker half's correlation a
    #: bar-head reading must reach. It is the header reader's OWN floor
    #: (`min_score`), not a new number, and it was checked rather than fitted:
    #: over 1,830 mid-staff windows on ten real scanned pages that print no
    #: change it answers 3 (0.16%) and no column has two staves agree; the 14
    #: windows of Brahms 1/i's printed `6/8` score 0.52-0.62. The staves'
    #: agreement (`rhythm.METER_TEMPLATE_AT_BAR_MIN_STAVES`), not this number,
    #: is still what a change is believed on.
    bar_head_half_floor: float = 0.50


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
    #: The meter that scored SECOND, and by how much it lost. `locate_time
    #: _signature` slides every candidate template over the same strip and kept
    #: only the argmax, so a 0.51 winner over a 0.50 runner-up and a 0.79 over a
    #: 0.31 arrived downstream as the same fact. The module docstring is already
    #: explicit that "a bare NCC score is usable here" only because the
    #: templates are proportionally comparable — which is exactly the assumption
    #: a margin lets someone check. None where only one template fitted the
    #: strip. RECORD ONLY: the vote does not read them, and `symbol` still comes
    #: from `raw` alone.
    runner_up_raw: str | None = None
    runner_up_score: float | None = None
    score_margin: float | None = None
    #: ROADMAP 2.72. What the whole-stack match alone had said WHERE the bottom
    #: half read a different denominator (None where they agree), and how far
    #: the denominator's own winner (read from the bottom half, see
    #: `_split_reading`) led its runner-up, on that half's own scale (None on a
    #: reading the half did not touch: a letter form, or a denominator outside
    #: the stack's column). RECORD ONLY, like the runner-up.
    stack_raw: str | None = None
    denominator_margin: float | None = None

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
        if self.runner_up_raw is not None:
            out["runner_up_raw"] = self.runner_up_raw
            out["runner_up_score"] = round(self.runner_up_score, 4)
            out["score_margin"] = round(self.score_margin, 4)
        if self.stack_raw is not None:
            out["stack_raw"] = self.stack_raw
        if self.denominator_margin is not None:
            out["denominator_margin"] = round(self.denominator_margin, 4)
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


@lru_cache(maxsize=8)
def _half_templates(
    em_px: int, texts: tuple[str, ...]
) -> dict[str, np.ndarray]:
    """One digit-row raster per number string, at the SAME scale `_meter_templates`
    puts that number at inside the four-space stack.

    A stack is assembled at the glyphs' natural size and resized by
    `4 spaces / (2 * tallest glyph)`; a half is the same row at the same factor,
    so a half-template is exactly the top (or bottom) half of what the stack
    template for that number would have been, not a differently-scaled digit.
    """
    digits = _digit_templates(em_px)
    space = em_px / 4.0
    target_h = int(round(4 * space))
    tallest = max(g.shape[0] for g in digits.values())
    factor = target_h / (2.0 * tallest)
    out: dict[str, np.ndarray] = {}
    for text in texts:
        if not all(c in digits for c in text):
            continue
        row = _row(digits, text)
        out[text] = cv2.resize(
            row,
            (max(2, int(round(row.shape[1] * factor))),
             max(2, int(round(row.shape[0] * factor)))),
            interpolation=cv2.INTER_AREA)
    return out


def _half_scores(
    strip: np.ndarray,
    templates: dict[str, np.ndarray],
    *,
    half: int,
    pad: int,
    space: float,
    x_lo: int,
    x_hi: int,
) -> dict[str, tuple[float, float]]:
    """Each candidate number's best NCC in ONE half of the stack, and where.

    `half` is 0 for the numerator (the upper two spaces) and 1 for the
    denominator (the lower two). The search is the column `[x_lo, x_hi)` and
    the strip's own vertical slack (`pad`, half a space -- the slack the
    whole-stack match slides over, so a stack that matches slid by that much
    has halves that do too).

    Returns `{text: (score, centre_x)}` in strip pixels.
    """
    out: dict[str, tuple[float, float]] = {}
    slack = max(1, pad)
    half_h = int(round(2 * space))
    x_lo = max(0, x_lo)
    x_hi = min(strip.shape[1], x_hi)
    for text, tpl in templates.items():
        th, tw = tpl.shape
        top = pad + half * half_h + (half_h - th) // 2
        y0 = max(0, top - slack)
        y1 = min(strip.shape[0], top + th + slack)
        sub = strip[y0:y1, x_lo:x_hi]
        if sub.shape[0] < th or sub.shape[1] < tw:
            continue
        response = cv2.matchTemplate(sub, tpl, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(response)
        out[text] = (float(score), x_lo + loc[0] + tw / 2.0)
    return out


def _split_reading(
    strip: np.ndarray,
    best: "LocatedTimeSignature",
    best_at: tuple[tuple[int, int], tuple[int, int]],
    pad: int,
    config: TimeSignatureLocatorConfig,
    trace: dict[str, object] | None,
) -> "LocatedTimeSignature":
    """Re-read the DENOMINATOR from the bottom half's own ink.

    ROADMAP 2.72 (Brahms 1/i Breitkopf: a printed `9/8` read `9/4` on ten
    staves of fourteen, every one with a runner-up within 0.09).

    **Why the stack match alone gets a denominator wrong.** One normalised
    correlation is taken over the whole four-space stack at ONE x, so the
    numerator's width and weight set where the template sits and the
    denominator is scored wherever that leaves it; and both halves feed ONE
    number, so a numerator that matches well carries a denominator that does
    not. Measured on the plate, the denominator's own half separates `8` from
    `4` where the stack does not: on all 10 staves that read a meter the best
    `8` leads the best `4` by 0.22-0.33 in correlation, where the stack's own
    winner (`9/4`) led its runner-up by 0.04-0.09. Nothing about the
    denominator's ink changed; it was being asked a question about the
    numerator's.

    **What this does and does not change.**

    * The stack match still decides THAT a meter stands here, WHERE, and the
      NUMERATOR (its score against `min_score` is the gate it always was), so
      no staff that abstained reads now and none that read is lost: nothing
      new enters the search, which is the property the cut-common read was
      built to keep. ⚠️ THE NUMERATOR IS NOT RE-READ, ON MEASUREMENT: a first
      cut re-read both halves and changed 10 of 496 staves on the 11-source
      corpus -- 4 right to wrong, 2 wrong to right, 4 wrong to wrong -- and
      every change but one was a NUMERATOR (Beethoven 5's two `2/4` became
      `4/4`; Beethoven 3's `3` over a Litolff plate moved among `3`, `6` and
      `9`). A lone numeral's correlation is a weaker witness than the stack's,
      where the denominator beneath it disambiguates. The denominator is the
      half the stack under-reads, so it is the half re-read.
    * Among the listed meters that keep the stack's numerator, the bottom
      half's own best correlation picks the denominator. The vocabulary is
      `config.meters`, so a pair the repertoire list does not hold cannot be
      produced.
    * Where the winning denominator does not stand in the stack's own column
      (centre further than `split_centre_tol_spaces` from the stack's), it is
      not this stack's second row and the stack's reading stands, untouched.
    * A letter form (`C`, `C|`) is one glyph and has no halves; it is returned
      as it was.

    No threshold here was fitted: the column slack and the centring tolerance
    are geometric (half a space; a time signature centres its rows), and the
    one comparison made is between candidate denominators, never against a
    score.
    """
    if best.raw in LETTER_METERS:
        return best
    (x0, _y0), (_th, tw) = best_at
    space = config.template_em_px / 4.0
    slack = int(round(config.split_column_slack_spaces * space))
    x_lo, x_hi = x0 - slack, x0 + tw + slack
    same_numerator = [(n, d, raw) for n, d, raw in config.meters
                      if raw not in LETTER_METERS and n == best.numerator]
    dens = tuple(sorted({str(d) for _n, d, _r in same_numerator}))
    bottom = _half_scores(strip, _half_templates(config.template_em_px, dens),
                          half=1, pad=pad, space=space, x_lo=x_lo, x_hi=x_hi)
    if trace is not None:
        trace["denominator_scores"] = {
            k: round(v[0], 4) for k, v in
            sorted(bottom.items(), key=lambda kv: -kv[1][0])}
    stack_centre = x0 + tw / 2.0
    tol = config.split_centre_tol_spaces * space
    ranked = sorted(
        ((raw, n, d, bottom[str(d)][0]) for n, d, raw in same_numerator
         if str(d) in bottom and abs(bottom[str(d)][1] - stack_centre) <= tol),
        key=lambda r: -r[3])
    if not ranked:
        return best
    raw, n, d, score = ranked[0]
    margin = (score - ranked[1][3]) if len(ranked) > 1 else score
    # ⚠️ `score`, `runner_up_*` and `score_margin` STAY ON THE STACK SCALE and
    # keep describing what the floor was applied to -- that a meter stands
    # here. The denominator's own evidence rides beside them, on ITS scale.
    return replace(
        best, numerator=n, denominator=d, raw=raw,
        stack_raw=best.raw if raw != best.raw else None,
        denominator_margin=margin)


def _ink_strip(
    cell: MeasureCell, config: TimeSignatureLocatorConfig
) -> tuple[np.ndarray, int, float] | None:
    """The staff's band of `cell`, as ink-positive pixels at template scale.

    Returns `(strip, pad, scale)` or None where the cell has no usable
    five-line staff. `pad` is the slack, in strip pixels, above and below the
    four-space stack that the strip carries; `scale` is strip pixels per cell
    pixel.
    """
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
    return strip, pad, scale


def locate_time_signature(
    cell: MeasureCell,
    *,
    config: TimeSignatureLocatorConfig = DEFAULT_LOCATOR_CONFIG,
    min_score: float | None = None,
    trace: dict[str, object] | None = None,
) -> LocatedTimeSignature | None:
    """Read the time signature in one staff's header cell, or return None.

    `cell` is a header cell from `staff_header.extract_header_cell` — the crop
    running from the staff's left edge to the first barline, which is where a
    meter is printed and, on degraded prints, is NOT the same region as the
    staff-start measure cell.

    `min_score` overrides the configured threshold. Benchmarks pass 0.0 to see
    the near-misses; production should not.

    `trace`, when given, is filled with the whole score table and the floor —
    including on the refusals, where the return value can carry nothing. RECORD
    ONLY: no threshold and no verdict depends on it.
    """
    floor = config.min_score if min_score is None else min_score
    prepared = _ink_strip(cell, config)
    if prepared is None:
        return None
    strip, pad, scale = prepared

    best: LocatedTimeSignature | None = None
    best_at: tuple[tuple[int, int], tuple[int, int]] | None = None
    #: Every candidate's score, in template order. The argmax below keeps one
    #: number and drops the rest, so the runner-up — the only thing that says
    #: whether the winner WON or merely came first — was being destroyed inside
    #: the comparison that used it.
    scores: list[tuple[str, float]] = []
    for (numerator, denominator, raw), template in _meter_templates(
        config.template_em_px, tuple(config.meters)
    ):
        if template.shape[0] > strip.shape[0] or template.shape[1] > strip.shape[1]:
            continue
        response = cv2.matchTemplate(strip, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, location = cv2.minMaxLoc(response)
        scores.append((raw, float(score)))
        if best is None or score > best.score:
            best = LocatedTimeSignature(
                numerator=numerator,
                denominator=denominator,
                score=float(score),
                x_canonical=int(round(location[0] / scale)),
                raw=raw,
            )
            best_at = (location, template.shape)
    if trace is not None:
        trace["floor"] = floor
        # Every template that fitted the strip, best first. Ties keep template
        # order, exactly as the argmax above does, so ranked[0] IS `best`.
        trace["scores"] = [
            {"raw": r, "score": round(v, 4)}
            for r, v in sorted(scores, key=lambda rv: -rv[1])
        ]
        trace["n_templates"] = len(scores)
        trace["cleared_floor"] = bool(best is not None and best.score >= floor)
    if best is None or best.score < floor:
        # ⚠️ A REFUSAL, and the near-miss is the interesting half: `min_score`
        # sits at 0.50 and the module docstring says outright that the honest
        # statement of that margin is thin. The trace carries the table that was
        # refused; the return value cannot, because there is none.
        return None
    # The runner-up, attached to the reading it lost to. `_meter_templates`
    # yields one template per (numerator, denominator, raw), so second place is
    # a different METER and not another crop of the same one.
    ranked = sorted(scores, key=lambda rv: -rv[1])
    if len(ranked) > 1:
        best = replace(best, runner_up_raw=ranked[1][0],
                       runner_up_score=ranked[1][1],
                       score_margin=ranked[0][1] - ranked[1][1])
    # ROADMAP 2.72: the stack match said a meter stands here; the two halves
    # say which. See `_split_reading`.
    if config.split_halves and best_at is not None:
        best = _split_reading(strip, best, best_at, pad, config, trace)
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


def locate_meter_by_halves(
    cell: MeasureCell,
    *,
    config: TimeSignatureLocatorConfig = DEFAULT_LOCATOR_CONFIG,
    min_half_score: float | None = None,
    trace: dict[str, object] | None = None,
) -> LocatedTimeSignature | None:
    """Read a meter off a window that has NO header's worth of evidence, from
    the numerator's and the denominator's OWN halves, or return None.

    ROADMAP 2.72. This is the reader for a mid-staff BAR HEAD (a printed meter
    CHANGE), where `locate_time_signature`'s whole-stack match under-reads: on
    Brahms 1/i Breitkopf's `6/8` at bar 9 the stack scores 0.44-0.51 on all
    fourteen staves (the floor is 0.50, so two read) and names `6/4` or `9/8`
    on most of the rest, while the weaker of the two halves scores 0.52-0.62
    on every one and all fourteen name `6/8`. The heavy scan's strokes are a
    poor match to the Bravura stack as one shape and a good match to each
    digit as one shape.

    Each half is searched across the whole window, against only the numbers a
    listed meter has there; a meter is a pair whose two rows stand in one
    column (`split_centre_tol_spaces`); its score is the WEAKER of its two
    halves (a meter needs both rows, so a strong numerator cannot carry a
    missing denominator); the best pair is the reading, and it stands only if
    that weaker half reaches `min_half_score`.

    ⚠️ THE FLOOR IS NOT WHERE THE SAFETY LIVES, and it is documented as such in
    the one place it is used (`gather.gather_meter_at_bars`): a bar head is an
    empty window almost everywhere, so a single staff's answer here is
    never believed on its own -- the system's staves must agree on the same
    meter at the same bar (`rhythm.METER_TEMPLATE_AT_BAR_MIN_STAVES`).

    `trace`, when given, takes both halves' score tables.
    """
    floor = config.bar_head_half_floor if min_half_score is None else min_half_score
    prepared = _ink_strip(cell, config)
    if prepared is None:
        return None
    strip, pad, scale = prepared
    space = config.template_em_px / 4.0
    digit_meters = [(n, d, raw) for n, d, raw in config.meters
                    if raw not in LETTER_METERS]
    nums = tuple(sorted({str(n) for n, _d, _r in digit_meters}))
    dens = tuple(sorted({str(d) for _n, d, _r in digit_meters}))
    top = _half_scores(strip, _half_templates(config.template_em_px, nums),
                       half=0, pad=pad, space=space, x_lo=0, x_hi=strip.shape[1])
    bottom = _half_scores(strip, _half_templates(config.template_em_px, dens),
                          half=1, pad=pad, space=space, x_lo=0, x_hi=strip.shape[1])
    if trace is not None:
        trace["floor"] = floor
        trace["numerator_scores"] = {
            k: round(v[0], 4) for k, v in
            sorted(top.items(), key=lambda kv: -kv[1][0])}
        trace["denominator_scores"] = {
            k: round(v[0], 4) for k, v in
            sorted(bottom.items(), key=lambda kv: -kv[1][0])}
    tol = config.split_centre_tol_spaces * space
    ranked = []
    for n, d, raw in digit_meters:
        t, b = top.get(str(n)), bottom.get(str(d))
        if t is None or b is None or abs(t[1] - b[1]) > tol:
            continue
        ranked.append((min(t[0], b[0]), raw, n, d, t, b))
    if not ranked:
        return None
    ranked.sort(key=lambda r: -r[0])
    score, raw, n, d, t, b = ranked[0]
    if trace is not None:
        trace["best"] = {"raw": raw, "score": round(score, 4),
                         "numerator": round(t[0], 4),
                         "denominator": round(b[0], 4)}
    if score < floor:
        return None
    runner = ranked[1] if len(ranked) > 1 else None
    return LocatedTimeSignature(
        numerator=n, denominator=d, score=float(score),
        x_canonical=int(round((t[1] + b[1]) / 2.0 / scale)),
        raw=raw,
        runner_up_raw=runner[1] if runner else None,
        runner_up_score=runner[0] if runner else None,
        score_margin=(score - runner[0]) if runner else None,
    )


def vote_system_time_signature(
    reads: Sequence[LocatedTimeSignature | None],
    *,
    n_staves: int | None = None,
    config: TimeSignatureLocatorConfig = DEFAULT_LOCATOR_CONFIG,
    trace: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Reconcile one system's per-staff readings into a meter, or abstain.

    A meter is printed on every staff of a system, so agreement across staves is
    the evidence — not the strength of any one reading. The winner must be read
    on `min_staff_fraction` of the system's staves and on at least `min_staves`
    of them, and must be unopposed by another meter with as many votes.

    ⚠️ **Strength is not the tie-break either, and that was measured rather than
    assumed.** On the one page where the majority is wrong, Beethoven 3 i, the
    CORRECT `3/4` reads score higher than the winning `6/4` ones (median 0.620
    against 0.561), so ranking by median score picks the right answer there. It
    was tried on the full corpus and buys exactly nothing: `3/4` is read on 3
    staves of 12, so the agreement gate refuses it anyway and the page abstains
    under either rule. Identical verdict table, one documented principle
    weakened — refused.

    `n_staves` defaults to `len(reads)`; pass it when `reads` has already been
    filtered so the denominator stays the size of the system.

    `trace`, when given, takes the RECORD of the vote — the meter that came
    second and the winners' own template margins. Deliberately not the returned
    meter dict: that dict is copied onto every measure of the system, so a
    record placed in it is written once per bar.
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
    # ⚠️ THE RECORD GOES IN `trace`, NOT IN `out`. This dict is the METER, and
    # `transcribe` copies it onto every measure of the system — so a scalar
    # added here is written once per bar, which on a 112-measure scan page cost
    # 9% of the result JSON when these four rode along in it. They are records
    # about ONE vote and belong where the vote is recorded once.
    #
    # ⚠️ Worth stating for the record rather than fixing here: `votes`,
    # `voters` and `median_score` are already in `out` and are records by the
    # same argument, so they are duplicated per bar too. That pattern is
    # inherited, not invented — and the reasoning that moved these four
    # condemns those three.
    #
    # Two runners-up, and they are different questions. `runner_up_meter` is the
    # meter that came second in VOTES — the opposition the agreement gate had to
    # clear. `median_score_margin` is the median, over the winning staves, of how
    # far each staff's own reading beat the second-best TEMPLATE on that staff:
    # a system where every staff read 3/4 at 0.61 against a 0.60 runner-up and
    # one where they read it at 0.61 against 0.20 agree equally and are not
    # equally sure. RECORD ONLY — `median_score` is documented as deliberately
    # NOT a tie-break here, and neither of these is either.
    if trace is not None:
        if len(ranked) > 1:
            trace["runner_up_meter"] = ranked[1][0][2]
            trace["runner_up_votes"] = ranked[1][1]
        margins = sorted(r.score_margin for r in winners
                         if r.score_margin is not None)
        if margins:
            trace["median_score_margin"] = round(margins[len(margins) // 2], 4)
            trace["min_score_margin"] = round(margins[0], 4)
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
    evidence: dict[int, dict[str, object]] | None = None,
) -> dict[int, dict[str, object]]:
    """Read and vote a meter for each system that has one, keyed by system.

    Systems with no agreed meter are simply absent from the result — a system
    printing no time signature (every system after the first, in most scores)
    is the common case, not an error.

    `evidence`, when given, is filled per system with each staff's own score
    table. It is separate from the return value BECAUSE of the sentence above:
    a system that abstained produces no row here, and an abstention is where the
    tables are most worth having.
    """
    out: dict[int, dict[str, object]] = {}
    for system_index, staff_indices in staves_by_system.items():
        indices = list(staff_indices)
        traces: dict[int, dict[str, object]] = {}
        reads = []
        for i in indices:
            if i not in header_cells:
                reads.append(None)
                continue
            trace: dict[str, object] = {}
            reads.append(locate_time_signature(header_cells[i], config=config,
                                               trace=trace))
            traces[i] = trace
        vote_trace: dict[str, object] = {}
        meter = vote_system_time_signature(reads, n_staves=len(indices),
                                           config=config, trace=vote_trace)
        if evidence is not None:
            # Kept per SYSTEM whether or not the vote reached a meter — a system
            # that abstained is the case where the per-staff tables are most
            # worth having, and it is exactly the case that reaches no `out` row.
            evidence[system_index] = {
                "voted": meter is not None,
                "vote": vote_trace,
                "staves": traces,
            }
        if meter is not None:
            out[system_index] = meter
    return out
