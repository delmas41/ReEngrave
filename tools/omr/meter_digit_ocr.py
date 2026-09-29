"""Read the printed time-signature NUMERALS off the plate by OCR.

ROADMAP 2.29. `time_signature_locator` matches a Bravura NCC template against
the whole digit stack and is measured to confuse "8" for "4" on Brahms 1/i
Breitkopf `317803` (the plate's own strokes are a poor match to the template
at this weight -- ROADMAP 2.12h/2.12i). This module is a SECOND, INDEPENDENT
reader of the same ink: Tesseract, restricted to digits, reading the
numerator and denominator as two SEPARATE crops rather than one stacked
template match.

**Why this is independent of the template reader, not a second copy of it**
(CLAUDE.md §10, "two witnesses off the same raster fall silent together"):
the two readers disagree about MECHANISM, not merely about which pixels they
look at. `time_signature_locator` slides a whole rasterised glyph over the
strip and takes the best normalized cross-correlation against a fixed
Bravura shape; a plate whose engraving differs from that shape in weight or
proportion is exactly the case NCC is weak at, and "8" sliding into "4"'s
own template is a shape confusion. Tesseract reads STROKE TOPOLOGY (an LSTM
trained on printed digit shapes broadly, not one publisher's font) and does
not compare against a fixed template at all -- so the failure mode that
sinks the template reader on this plate (a font whose "8" is unusually close
to Bravura's "4") has no reason to sink this one too, and the two readers
failing TOGETHER would need a second, different explanation before being
trusted as agreement. That is asserted here and tested, not merely claimed:
`tools/omr/tests/test_staged_meter_ocr.py` exercises this module directly on
crops of the SAME plate `time_signature_locator` mis-reads.

**Not read here**: `C` / cut-C (`timeSigCommon` / `timeSigCutCommon`) are
drawn as ONE glyph, not two stacked digit rows, and are a SYMBOL rather than
digits -- `time_signature_locator` already owns them and this module never
tries.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: a time
signature's numerator and denominator are printed symmetric about the
staff's own MIDDLE line, so splitting a crop there separates them cleanly.
This would be falsified by a signature engraved off-centre on some plate, or
one whose numerator/denominator differ enough in height that the middle
line does not fall between their strokes -- neither has been checked against
a real plate; the split point here is geometry, never re-derived from ink.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from . import bar_number_text as _bar_number_text

#: Denominators an engraver actually prints (`time_signature_locator.
#: DEFAULT_METERS`'s own vocabulary, restated here as a PLAUSIBILITY floor
#: rather than imported, because this filter must survive Tesseract reading
#: a value that reader's own template table would never propose -- e.g. "7"
#: -- and refuse it on the same terms it refuses "128"). `C`/cut-C are
#: SYMBOLS, not digits, and are never read by this module (see docstring).
PLAUSIBLE_DENOMINATORS = frozenset((1, 2, 4, 8, 16, 32))

#: A numerator above this is Tesseract inventing a stroke, not a plate
#: printing it — the same floor `bar_number_from_text` applies to a bar
#: count, sized to the repertoire rather than to any one plate.
PLAUSIBLE_NUMERATOR_MAX = 16


@dataclass(frozen=True)
class LocatedMeterOCR:
    numerator: int
    denominator: int
    numerator_confidence: float
    denominator_confidence: float

    def as_dict(self, source: str = "meter_ocr") -> dict:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "source": source,
            "numerator_confidence": round(self.numerator_confidence, 1),
            "denominator_confidence": round(self.denominator_confidence, 1),
        }


def available() -> bool:
    """Is there a working Tesseract to call? Same rung `bar_number_text`
    uses -- one Tesseract install, two callers."""
    return _bar_number_text.available()


def read_meter_digits(image, *, split_row: Optional[int] = None,
                      trace: Optional[dict] = None
                      ) -> Optional[LocatedMeterOCR]:
    """OCR a crop that stacks a numerator over a denominator.

    `image` is a numerator-over-denominator crop (a header window, a
    mid-staff bar-head window, or a 2.12l witness pair's own bounding box —
    this function does not care which; the caller names the SOURCE in the
    quantity it files, not this one). `split_row` is a row index INTO
    `image` — the caller's own middle staff line, in the SAME pixel frame as
    `image` — not a page coordinate. `None` splits at the image's own
    vertical midpoint, for a caller with no staff geometry of its own (e.g.
    a tight bounding box already cropped to the two digits).

    Returns `None` where either half is not read as exactly one run of
    digits, or where the reading fails the plausibility filter — this
    function ABSTAINS rather than guesses (CLAUDE.md rule 6), and it is the
    CALLER's job to tell "Tesseract found nothing" apart from "found
    something implausible" if that distinction matters downstream (both are
    `None` here on purpose: this module answers "is there a plausible meter
    here", not "why not").
    """
    if image is None or getattr(image, "size", 0) == 0:
        return None
    height = image.shape[0]
    if height < 2:
        return None
    mid = int(split_row) if split_row is not None else height // 2
    mid = max(1, min(height - 1, mid))
    top, bottom = image[:mid], image[mid:]

    num = _read_run(top)
    den = _read_run(bottom)
    if trace is not None:
        trace["numerator_read"] = num
        trace["denominator_read"] = den
    if num is None or den is None:
        return None
    num_text, num_conf = num
    den_text, den_conf = den
    n = _bar_number_text.bar_number_from_text(num_text)
    d = _bar_number_text.bar_number_from_text(den_text)
    if trace is not None:
        trace["numerator_parsed"] = n
        trace["denominator_parsed"] = d
    if n is None or d is None:
        return None
    if d not in PLAUSIBLE_DENOMINATORS or not (1 <= n <= PLAUSIBLE_NUMERATOR_MAX):
        # ⚠️ NOT KEYED "reason" — a caller's own `log.abstain(reason=...)`
        # already owns that word, and a trace dict splatted alongside it
        # (as `gather._gather_meter_ocr_header` does) would collide.
        if trace is not None:
            trace["implausible"] = True
        return None
    return LocatedMeterOCR(numerator=n, denominator=d,
                           numerator_confidence=num_conf,
                           denominator_confidence=den_conf)


def _read_run(half_image) -> Optional[Tuple[str, float]]:
    """One half of the stack -> `(digit text, mean confidence)`, or `None`.

    Delegates the actual OCR call to `bar_number_text.read_crop` — the SAME
    Tesseract config (digit whitelist, `--psm 7`, no upscale — that module's
    own measured choice, not re-derived here) — because a meter numeral and
    a bar numeral are the same kind of ink asking the same question of
    Tesseract: "what digits, if any, are printed in this small crop".
    """
    return _bar_number_text.read_crop(half_image)
