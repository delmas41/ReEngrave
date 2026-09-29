"""Read the printed BAR NUMBER above a system's first bar.

Engravers print a small numeral above the first bar of a system (sometimes
every N bars) so a rehearsal or a correction can be found by eye. Nothing in
this tree carried that numeral before ROADMAP 2.13; the file's own cumulative
bar count is a SEPARATE witness -- see
`tools.omr.staged.export._printed_bar_number_check` -- and the two are
compared, never merged, and never used to renumber or insert a bar.

**Tesseract only, no server.** The margin-label cascade
(`contextual._labels_for_page`) goes text-layer -> Surya -> Tesseract ->
Vision because an instrument NAME needs a real vocabulary reader; a bar
number is 1-4 ASCII digits, which is exactly Tesseract's own
digit-whitelist mode and needs neither a Python 3.10 venv nor a subprocess
server. This module never asks for Surya, so a `--no-surya` run is
untouched by it and never needs to fall back -- there is nothing to fall
back FROM.

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
