"""Read the printed BAR NUMBER above a system's first bar.

Engravers print a small numeral above the first bar of a system (sometimes
every N bars) so a rehearsal or a correction can be found by eye. Nothing in
this tree carried that numeral before ROADMAP 2.13; the file's own cumulative
bar count is a SEPARATE witness -- see
`tools.omr.staged.export._printed_bar_number_check` -- and the two are
compared, never merged, and never used to renumber or insert a bar.

**Surya first, Tesseract under `--no-surya` (ROADMAP 2.13b).** This was
Tesseract-only on the reasoning that 1-4 ASCII digits are exactly
Tesseract's digit-whitelist mode. The whole-movement census refuted that:
on Breitkopf 22 of Tesseract's 35 decided numerals were wrong (see the
Surya block below for the figures). Surya is now asked first, on a wider
crop; Tesseract runs only when Surya was not asked for or cannot run, and
each files under its own reader name.

**One crop per system**, cut by the caller (`tools.omr.staged.gather.
gather_printed_bar_numbers`) directly above the system's topmost staff, from
`Staff.x_start` rightward a few staff spaces -- `x_start` is already past the
clef/key/meter margin (see that field's own docstring in `tools/omr/
types.py`), which is where a system-start numeral sits on both of this
item's gate pages.

**Digits only, one run.** `bar_number_from_text` rejects anything that is
not exactly one run of digits, so a rehearsal LETTER printed in the same
place on some editions, or two marks the crop caught together, are refused
rather than guessed at (CLAUDE.md rule 6: "connect, never guess").
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

#: `--psm 7`: treat the crop as ONE line, the same choice
#: `staff_labels_tesseract.PSM_LINE` makes for a direction crop and for the
#: same reason -- a bar number is a single short line, never a paragraph.
PSM = 7
#: A bar number is ASCII digits only. Nothing else an engraver prints in this
#: spot is digits -- a rehearsal letter, a tempo word, a metronome mark -- so
#: whitelisting before OCR runs is cheaper and more honest than accepting
#: those and filtering them out afterwards.
_TESSERACT_CONFIG = f"--psm {PSM} -c tessedit_char_whitelist=0123456789"
#: ⚠️ MEASURED, NOT ASSUMED, AND THE ANSWER SURPRISED. A first pass copied
#: `staff_labels_tesseract`'s own 2x/LANCZOS upscale and set this to 3;
#: against the REAL pipeline raster (not a `pdf2image` stand-in -- see
#: FINDINGS.md §2) that read 2 of 4 gate numerals, WORSE than reading the
#: crop at its native size. A sweep of {1,2,3,4,5} x {LANCZOS, BICUBIC,
#: NEAREST} on the same four crops found no config that reads all four --
#: one of them (Brahms p2's "15") never resolves under any tested
#: preprocessing, and is left as a measured Tesseract limitation, not a
#: bug -- but `1` (no resize at all) reads three of four and is the
#: cheapest correct choice, so it is the default rather than a
#: heavier-upscale guess.
UPSCALE = 1

_DIGITS_RE = re.compile(r"\d+")

# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.13b: the Surya rung, asked FIRST when the run asks for Surya.
#
# ⚠️ MEASURED ON BOTH ACCEPTANCE MOVEMENTS, every system, against the print
# (`benchmarks/omr-bar-number-2026-09/FINDINGS.md` §6). Tesseract on the
# 6-space crop: Breitkopf 13 right / 22 WRONG of 35 decided (the bold "1"
# read as "4", the leading "1" lost into the bracket's curl, the third digit
# clipped); Litolff 21 right / 7 wrong. Surya on an 8-space crop with this
# preparation: Breitkopf 34 right / 0 wrong, Litolff 27 right / 0 wrong.
# Where Surya reads nothing the caller asks NOTHING else: Tesseract on
# exactly those systems was 5 right / 7 wrong (CLAUDE.md rule 8).
# Tesseract stays the `--no-surya` reader, on its own 6-space crop,
# unchanged.
# ─────────────────────────────────────────────────────────────────────────────

#: The Surya crop's width, in staff spaces right of `Staff.x_start`. A
#: 3-digit Breitkopf numeral ends ~7 spaces in; 6 clipped it (229 read 22).
#: Swept 6/7/8 at 2x: 23/30/34 right on Breitkopf, 2/1/0 wrong.
SURYA_CROP_WIDTH_SPACES = 8.0
#: White border added round the crop before Surya sees it (2.85's recipe).
SURYA_PAD_PX = 60
#: Upscale after padding. 3x was swept and read fewer (24 vs 34).
SURYA_UPSCALE = 2
#: Generation cap per crop. 8 returns empty (2.85); 32 read no more than 16.
SURYA_MAX_TOKENS = 16


def surya_available() -> bool:
    """Is there a working Surya to call? Never raises."""
    try:
        from .staff_labels_surya import available as _available
        return bool(_available())
    except Exception:                                       # noqa: BLE001
        return False


def read_crops_surya(crops) -> list:
    """Surya's text for each RGB crop, `""` where it read nothing.

    One subprocess job for the whole list, so a page pays one dispatch.
    Raises whatever `staff_labels_surya.read_crops_text` raises -- telling
    "Surya failed" apart from "Surya read nothing" is the caller's job.
    """
    import cv2
    import numpy as np

    from . import staff_labels_surya as SL

    prepared = []
    for rgb in crops:
        arr = np.asarray(rgb)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if arr.ndim == 3 else (
            cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR))
        bgr = cv2.copyMakeBorder(bgr, SURYA_PAD_PX, SURYA_PAD_PX,
                                 SURYA_PAD_PX, SURYA_PAD_PX,
                                 cv2.BORDER_CONSTANT, value=(255, 255, 255))
        if SURYA_UPSCALE > 1:
            bgr = cv2.resize(bgr, None, fx=SURYA_UPSCALE, fy=SURYA_UPSCALE,
                             interpolation=cv2.INTER_CUBIC)
        prepared.append(bgr)
    texts = SL.read_crops_text(prepared, max_tokens=SURYA_MAX_TOKENS)
    return [(t or "").strip() for t in texts]


def available() -> bool:
    """Is there a working Tesseract to call?"""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except Exception:                                       # noqa: BLE001
        return False
    return True


def read_crop(image) -> Optional[Tuple[str, float]]:
    """OCR one crop for a bar number.

    Returns `(digit text, mean word confidence 0-100)`, or `None` where
    Tesseract read no text at all in the crop.

    ⚠️ `None` is "the rung ran and found no text" -- telling that apart from
    "the rung could not run" and from "what it read is not a number" (most
    often a rehearsal letter) is the CALLER's job (the GATHER four-state
    contract); this function hands back exactly what Tesseract said and
    interprets nothing.
    """
    import numpy as np
    import pytesseract
    from PIL import Image

    if image is None or getattr(image, "size", 0) == 0:
        return None
    arr = np.asarray(image)
    pil = Image.fromarray(arr).convert("L") if arr.ndim == 3 else Image.fromarray(arr)
    if UPSCALE > 1:
        pil = pil.resize((pil.width * UPSCALE, pil.height * UPSCALE), Image.LANCZOS)
    data = pytesseract.image_to_data(
        pil, config=_TESSERACT_CONFIG, output_type=pytesseract.Output.DICT)

    words = []
    confs = []
    for text, conf in zip(data.get("text", ()), data.get("conf", ())):
        text = (text or "").strip()
        if not text:
            continue
        words.append(text)
        try:
            c = float(conf)
        except (TypeError, ValueError):
            c = -1.0
        if c >= 0:
            confs.append(c)
    if not words:
        return None
    joined = "".join(words)
    mean_conf = sum(confs) / len(confs) if confs else 0.0
    return joined, mean_conf


def bar_number_from_text(text: str) -> Optional[int]:
    """The integer a printed numeral names, or `None` if `text` is not one.

    ⚠️ EXACTLY ONE RUN OF DIGITS, never a substring pulled out of longer ink.
    `"49"` -> 49; `"A"` (a rehearsal letter) -> `None`; `"12 3"` (two runs) ->
    `None`, because which one is the bar number is a guess this function
    refuses to make. `0` and anything past a page's plausible bar count are
    refused too: no system opens at bar 0, and a 5-digit reading is
    Tesseract inventing a stroke, not a page printing five thousand bars.
    """
    if not text:
        return None
    runs = _DIGITS_RE.findall(text)
    if len(runs) != 1:
        return None
    try:
        n = int(runs[0])
    except ValueError:
        return None
    if n <= 0 or n > 9999:
        return None
    return n
