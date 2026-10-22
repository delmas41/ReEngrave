"""Find a 1st/2nd-ending (volta) bracket above a system, and read its numeral.

ROADMAP 2.85. The detector (DeepScores v2, 208 classes) has no volta class --
`repeatDot` is its only repeat symbol -- so a bracket printed over a 1st or 2nd
ending had no subject anywhere in the record, and the exporter counted the
1st-ending bars straight through: +2 to every later bar number on Breitkopf
Brahms 1 from pdf p10 (DECISIONS 2026-10-10, the print's own 188 -> 194 -> 205).

**What a volta bracket is on the page** (how a human reads it): a long, thin,
straight HORIZONTAL stroke a few staff spaces above a system's top staff, with
a short VERTICAL hook hanging down from its left end, and the ending's numeral
("1.", "2.") written just inside the hook, under the stroke. A 1st ending
usually closes with a second hook at its right end; a last ending is often left
OPEN (no right hook) -- both are printed, both are measured here, neither is
assumed.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: the stroke lies
0.4-7 staff spaces above the top staff line, is at least `MIN_LENGTH_SPACES`
long and at most `MAX_THICKNESS_SPACES` thick, and its hook hangs at least
`MIN_HOOK_SPACES` -- measured on Breitkopf 317803 pdf p10 system 1 (two
brackets, hooks 2.8 and 2.9 spaces; the flat stretches of slurs and ties in
the same band have no hook at all, 0.0). A plate that prints the bracket
further up than seven spaces (over very high ledger notes), or draws it
dashed, would be missed -- a miss files nothing, never a wrong bracket.

**Two readers, kept apart.** `find_brackets` is CV geometry over the raster;
`read_numeral` is Tesseract over the crop inside the left hook. They are two
signals on two crops and the GATHER caller files them under two quantities.
This module decides nothing: which bars an ending covers, and which ending a
bracket is, are ADJUDICATE's (`adjudicators/structure.adjudicate_endings`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

#: The band searched, in staff spaces ABOVE the top staff's top line.
BAND_TOP_SPACES = 7.0
BAND_BOTTOM_SPACES = 0.4
#: A horizontal opening of this length keeps only straight runs at least this
#: long; slurs survive only along their flattest stretch.
MIN_WIDTH_SPACES = 3.0
#: The stroke's own thickness: a beam above the staff is ~0.5 space thick and
#: slanted; a volta stroke measured 0.33-0.36 (it carries slight tilt).
MAX_THICKNESS_SPACES = 0.6
#: A hook is a vertical run hanging down from the stroke's end. Measured 2.8-2.9
#: on the Brahms brackets and 0.0 on every slur/tie in the same band; a tuplet
#: bracket's hook is well under one space.
MIN_HOOK_SPACES = 1.2
#: How far from the stroke's end a hook column may stand (it is drawn AT the
#: end; the opening can shave a few pixels off the stroke).
HOOK_REACH_SPACES = 0.6
#: A volta hook hangs in the air: it stops short of the staff. A "hook" that
#: runs on into the staff is a STEM under a beam, or a barline under an
#: undetected staff line -- measured over both acceptance movements
#: (43 pages): every one of the 106 non-bracket candidates whose hook passed
#: `MIN_HOOK_SPACES` had a run reaching the top line or beyond (the Litolff
#: p7/p10/p12 "hooks" are 31-98 spaces long), while the two Brahms brackets'
#: hooks end 3.3 spaces above it.
HOOK_CLEARANCE_SPACES = 0.5
#: A bracket covers at least one bar. The 106 non-bracket candidates of that
#: census were 1.8-5.9 spaces long apart from the three Litolff staff-line
#: runs (killed by the clearance above); the brackets were 30.6 and 37.6.
MIN_LENGTH_SPACES = 6.0


@dataclass(frozen=True)
class Bracket:
    """One horizontal stroke above a system, with its measured hooks.

    All coordinates are PAGE pixels. `left_hook`/`right_hook` are the length
    of the vertical run hanging from each end, in staff spaces (0.0 = none).
    """
    x0: int
    x1: int
    y: int
    thickness: int
    left_hook: float
    right_hook: float

    def as_value(self) -> dict:
        return {"x0": self.x0, "x1": self.x1, "y": self.y,
                "thickness": self.thickness,
                "left_hook": round(self.left_hook, 2),
                "right_hook": round(self.right_hook, 2)}


def _hook(binary, x: int, y_line_top: int, y_line_bottom: int, space: float,
          side: str, y_floor: float) -> float:
    """Longest dark vertical run that starts IN the stroke and goes down, in
    staff spaces -- 0.0 when the longest run reaches `y_floor` (the staff's
    top line less the clearance): that is a stem or a barline, not a hook."""
    h, w = binary.shape
    reach = int(round(HOOK_REACH_SPACES * space))
    near = max(1, int(round(0.15 * space)))
    if side == "L":
        cols = range(max(0, x - near), min(w, x + reach))
    else:
        cols = range(max(0, x - reach), min(w, x + near))
    best = 0
    reached_floor = False
    for cx in cols:
        col = binary[:, cx]
        # the run must touch the stroke: start from the first dark pixel in
        # the stroke's rows and walk down
        start = None
        for yy in range(max(0, y_line_top), min(h, y_line_bottom + 1)):
            if col[yy]:
                start = yy
                break
        if start is None:
            continue
        yy = start
        while yy < h and col[yy]:
            yy += 1
        if yy - start > best:
            best = yy - start
            reached_floor = yy >= y_floor
    return 0.0 if reached_floor else best / space


def find_brackets(gray, line_ys: Sequence[float], x_start: float,
                  x_end: float) -> List[Bracket]:
    """Every long thin horizontal stroke above this staff that has a hook.

    `gray` is the page image (2-D uint8, or 3-channel); `line_ys` the top
    staff's five line positions. Returns brackets left to right. A stroke
    with NO hook at either end is not returned -- it is a slur's flat
    stretch, a ledger run or a beam, and this reader has nothing to say
    about it (it is not a volta bracket candidate under any convention).
    """
    import numpy as np
    import cv2

    arr = np.asarray(gray)
    if arr.ndim == 3:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    ys = [float(v) for v in line_ys]
    if len(ys) < 2:
        return []
    space = (ys[-1] - ys[0]) / (len(ys) - 1)
    if space <= 0:
        return []
    H, W = arr.shape
    y0 = max(0, int(ys[0] - BAND_TOP_SPACES * space))
    y1 = max(0, int(ys[0] - BAND_BOTTOM_SPACES * space))
    x0 = max(0, int(x_start - 2 * space))
    x1 = min(W, int(x_end + space))
    if y1 <= y0 or x1 <= x0:
        return []
    binary = (arr < 128).astype(np.uint8)
    band = binary[y0:y1, x0:x1]
    k = cv2.getStructuringElement(
        cv2.MORPH_RECT, (max(3, int(MIN_WIDTH_SPACES * space)), 1))
    opened = cv2.morphologyEx(band, cv2.MORPH_OPEN, k)
    n, _lab, stats, _ = cv2.connectedComponentsWithStats(opened, 8)
    out: List[Bracket] = []
    for i in range(1, n):
        bx, by, bw, bh, _area = (int(v) for v in stats[i])
        if bw < MIN_LENGTH_SPACES * space or bh > MAX_THICKNESS_SPACES * space:
            continue
        gx0, gx1, gy = bx + x0, bx + x0 + bw - 1, by + y0
        floor = ys[0] - HOOK_CLEARANCE_SPACES * space
        lh = _hook(binary, gx0, gy, gy + bh, space, "L", floor)
        rh = _hook(binary, gx1, gy, gy + bh, space, "R", floor)
        if max(lh, rh) < MIN_HOOK_SPACES:
            continue
        out.append(Bracket(x0=gx0, x1=gx1, y=gy, thickness=bh,
                           left_hook=lh, right_hook=rh))
    out.sort(key=lambda b: b.x0)
    return out


def numeral_crop_box(bracket: Bracket, space: float
                     ) -> Tuple[int, int, int, int]:
    """Page-pixel box `(x0, y0, x1, y1)` where the ending's numeral sits:
    just right of the left hook, just under the stroke."""
    return (int(bracket.x0 + 0.5 * space),
            int(bracket.y + bracket.thickness + 0.1 * space),
            int(bracket.x0 + 3.2 * space),
            int(bracket.y + 3.0 * space))


#: Digits and the period an engraver writes after an ending number.
_TESSERACT_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789."


def read_numeral(gray, box: Tuple[int, int, int, int]
                 ) -> Optional[Tuple[str, float]]:
    """Tesseract over the numeral crop: `(text, mean confidence 0-100)` or
    None where it read nothing. Interprets nothing (that is ADJUDICATE's).

    The crop is binarised and given a white border -- Tesseract reads a glyph
    touching its frame edge as nothing (measured: the unpadded Brahms "2."
    read empty, padded it reads "2.").
    """
    import numpy as np
    import cv2
    import pytesseract
    from PIL import Image

    arr = np.asarray(gray)
    if arr.ndim == 3:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    x0, y0, x1, y1 = box
    H, W = arr.shape
    x0, x1 = max(0, x0), min(W, x1)
    y0, y1 = max(0, y0), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return None
    crop = arr[y0:y1, x0:x1]
    im = np.where(crop < 128, 0, 255).astype(np.uint8)
    im = cv2.copyMakeBorder(im, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    data = pytesseract.image_to_data(Image.fromarray(im),
                                     config=_TESSERACT_CONFIG,
                                     output_type=pytesseract.Output.DICT)
    words, confs = [], []
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
    return "".join(words), (sum(confs) / len(confs) if confs else 0.0)
