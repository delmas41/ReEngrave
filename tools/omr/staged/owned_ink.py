"""ROADMAP 2.304 -- A READER IS NOT SHOWN INK ANOTHER READER OWNS (flag `OMR_TEXT_CROP_OWNED_INK`, default OFF). PATH: STAGED GATHER only (LEGACY never attaches the mask).

    Sean 2026-11-11: "Try it but I want a fix for future issues not something just specific to this scenario." CLAUDE.md 3, claim order (plan 2026-10-28 s9-10): the page-wide
    pass claims staff / barlines / brackets / clef-key-meter BEFORE words, and "a later reader may mark claimed ink but never take it". The text reader (OCR) still got the raw
    crop with that ink in it: a barline stroke beside or through a word was read as a letter, the lexicon refused the whole string (Litolff p8 `sempre piu: °`, 2.303 part 1), and
    the detector's m+p inside the unread line was written as a false `mp`. The rule is general -- a reader's input is its crop MINUS the pixels an earlier owner holds -- and the
    text reader is its first consumer.

`owned_ink_mask(page, rect, spacing, before_owner="word")` -- the pixels of `rect` (page px, x0, y0, x1, y1) that an owner EARLIER in `CLAIM_ORDER` than `before_owner` holds, as a bool
array, with the pixels of a mark that CROSSES the owned stroke given back to the mark. Pure given `attach` (below). A later consumer (an arc reader, the dynamic-letter reader) calls it
with its own `before_owner`; a new owner with geometry in the page is one more entry in `PROVIDERS`.

Owners with a provider today: `barline` (the pixels `page_strokes.carve_columns` carves along `barline_columns.fit_columns`' tilted lines -- the page stroke map's own barline rule,
not a new finder) and `staff_line` (long level runs inside a staff's band). No provider yet (nothing in a direction word's reach, measured 2026-11-11, benchmarks/
text-reader-owned-ink-2026-11): bracket, brace, clef, key, meter (all left of the first bar). A detector BOX is not an owner: the per-cell readers (notehead, accidental, stem, dynamic)
claim after words, and `crop_for` already whites a detection's ink outside the candidate's own box.

A MARK THAT TOUCHES THE OWNED STROKE KEEPS ITS INK (page-facts 3: "where a mark crosses a staff line, the crossing ink is the MARK's"). Owned pixels are given back in every row (barline: column
for a staff line) where ink that is NOT owned stands within `CROSS_REACH_SPACES` of the stroke on EITHER side, and `ATTACHED_GROW_SPACES` along the stroke beyond those rows: a letter passing
through the rule has ink on both sides, a letter standing ON it (the stem of the `p` of `sempre`, Litolff p8: the thin barline runs through it) has its bowl on one. What is taken is the
stroke's own run where no letter touches it -- above and below the word, between its letters, beside its last one. WHAT THIS CANNOT DO: a letter whose stroke IS the rule's pixels for several
rows (the descender of that `p`) loses them. And a stroke is taken only where it RUNS THROUGH the window (`THROUGH_COVER_MIN`): a stub of the carve ending inside it is left. CONVENTION ASSUMED:
a barline / staff line is one straight stroke. WHAT WOULD FALSIFY IT: a READ word that changes text or is lost with the flag on (the lane's `words changed` list), a rule remnant read as a letter.

The flag value is a list of owners to take: `1` = barline; `1,staff_line` adds staff lines (a SEPARATE arm, 2.304: staff lines under a word were never measured); `staff_line` alone.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

DERIVED_CHECK = False
ENV = "OMR_TEXT_CROP_OWNED_INK"
#: plan 2026-10-28 s10: structure (staff, barlines, brackets) -> system registers (clef, key, meter) -> text -> dynamics -> arcs -> repeats
CLAIM_ORDER = ("staff_line", "barline", "bracket", "brace", "clef", "key", "meter", "word", "dynamic", "arc", "repeat")
#: the owners `ENV` may name (those with a provider below)
KINDS = ("barline", "staff_line")
#: a rule's soft edge: the pixels either side of the carved stroke (across it only), in staff spaces (>= 1 px)
HALO_SPACES = 0.06
#: a mark TOUCHES the stroke when ink that is not owned stands this near either side of it in the same row (spaces, >= 2 px); the pixels of the stroke in those rows, and this far along the
#: stroke beyond them (a letter's stroke thickness, spaces, >= 1 px), are the mark's
CROSS_REACH_SPACES = 0.12
ATTACHED_GROW_SPACES = 0.15
#: a staff line's long level run, in spaces (the opening kernel), and how far outside a staff's lines the band reaches
LINE_RUN_SPACES = 3.0
LINE_BAND_SPACES = 0.6
#: an owned stroke is taken only where it runs through this share of the window along its own length, bridging scan breaks of this many spaces
THROUGH_COVER_MIN = 0.9
THROUGH_GAP_SPACES = 0.25
#: the page's ink, as the OCR sees it (`direction_text._page_ink`)
INK_GRAY_MAX = 180


def kinds_enabled() -> Tuple[str, ...]:
    """The owners the flag takes, in claim order; () when the flag is off (the default). `1`/`on` = barline; `staff_line` and `barline` name an owner."""
    v = os.environ.get(ENV, "").strip().lower()
    if v in ("", "0", "false", "no", "off"):
        return ()
    got = set()
    for tok in (t.strip() for t in v.replace(";", ",").split(",")):
        if tok in ("1", "true", "yes", "on", "replace"):
            got.add("barline")
        elif tok in KINDS:
            got.add(tok)
    return tuple(k for k in CLAIM_ORDER if k in got)


def enabled() -> bool:
    return bool(kinds_enabled())


def replace_mode() -> bool:
    """`replace` among the flag's tokens: the crop MINUS the owned ink is read INSTEAD of the plain crop, on every look. Default (`1`): a RETRY only -- a candidate nothing was accepted from is
    read once more from the crop minus the owned ink, exactly the 2.254 r3 pattern (a letter that stands ON a rule loses its stroke with it: Litolff p9 `pizz.`, and here the `i` of `piu` on
    a thin barline; measured 2026-11-12, Litolff p8, replace mode lost 4 READ words and gained 4)."""
    return "replace" in [t.strip() for t in os.environ.get(ENV, "").strip().lower().replace(";", ",").split(",")]


class OwnedInk:
    """What `attach` hangs on the page: the page-sized owner masks, built once per page, and the one question a crop builder asks (`mask`). The builder in the shared `direction_text`
    calls the METHOD, so the shared reader imports nothing from `staged/`."""

    def __init__(self, page: Any, masks: Dict[str, np.ndarray], kinds: Sequence[str], halo_px: int, reach_px: int, replace: bool = False):
        self.page, self.masks, self.kinds, self.halo_px, self.reach_px = page, masks, tuple(kinds), int(halo_px), int(reach_px)
        self.replace = bool(replace)

    def mask(self, rect: Sequence[int], spacing: float = 0.0, before_owner: str = "word") -> Optional[np.ndarray]:
        return owned_ink_mask(self.page, rect, spacing, before_owner)


def _ink(page: Any, rect: Sequence[int] = None) -> np.ndarray:
    import cv2
    rgb = page.rgb if rect is None else page.rgb[rect[1]:rect[3], rect[0]:rect[2]]
    gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY) if rgb.ndim == 3 else rgb
    return gray < INK_GRAY_MAX


def _barline_mask(pws: Any, sp: float, halo: int) -> np.ndarray:
    """The page stroke map's barline rule: what `page_strokes.carve_columns` takes out of the raster along each fitted column, widened across the rule by `halo`, where the render is ink."""
    import cv2
    from . import barline_columns as BC
    from . import page_strokes as PS
    binary = pws.page.binary
    canvas = binary.copy()
    PS.carve_columns(canvas, BC.fit_columns(pws), sp)
    carved = ((binary == 0) & (canvas != 0)).astype(np.uint8)
    if halo > 0 and carved.any():
        carved = cv2.dilate(carved, cv2.getStructuringElement(cv2.MORPH_RECT, (2 * halo + 1, 1)))
    return (carved > 0) & _ink(pws.page)


def _staff_line_mask(pws: Any, sp: float) -> np.ndarray:
    """Long level runs of ink inside each staff's band (top line - 0.6 sp .. bottom line + 0.6 sp), across the staff's own x range: the lines as they are PRINTED, so a tilted scan is followed."""
    import cv2
    ink = _ink(pws.page)
    out = np.zeros(ink.shape, bool)
    h, w = ink.shape
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, int(round(LINE_RUN_SPACES * sp))), 1))
    for s in pws.staves:
        s_sp = max(1.0, float(s.line_spacing_px))
        y0, y1 = max(0, int(s.top_y - LINE_BAND_SPACES * s_sp)), min(h, int(s.bottom_y + LINE_BAND_SPACES * s_sp) + 1)
        x0, x1 = max(0, int(s.x_start)), min(w, int(s.x_end) + 1)
        if y1 <= y0 or x1 <= x0:
            continue
        band = ink[y0:y1, x0:x1].astype(np.uint8)
        op = cv2.morphologyEx(band, cv2.MORPH_OPEN, k)
        if op.any():
            op = cv2.dilate(op, np.ones((3, 1), np.uint8))          # the line's soft edge, across it only
            out[y0:y1, x0:x1] |= (op > 0) & ink[y0:y1, x0:x1]
    return out


def attach(pws: Any, kinds: Optional[Sequence[str]] = None) -> Optional[OwnedInk]:
    """Build the owner masks of `pws.page` for the flag's `kinds` (default: the flag's) and hang them on the page as `page.owned_ink` (the only change to the page object). Returns it, or
    None when the flag is off. The staff-line mask is ALWAYS built: a barline's neighbouring staff line is never a letter that crosses it."""
    kinds = tuple(kinds if kinds is not None else kinds_enabled())
    if not kinds:
        return None
    sp = float(np.median([s.line_spacing_px for s in pws.staves])) if pws.staves else 20.0
    halo = max(1, int(round(HALO_SPACES * sp)))
    reach = max(2, int(round(CROSS_REACH_SPACES * sp)))
    masks = {"staff_line": _staff_line_mask(pws, sp), "barline": _barline_mask(pws, sp, halo)}
    oi = OwnedInk(pws.page, masks, kinds, halo, reach, replace_mode())
    pws.page.owned_ink = oi
    return oi


def _through(mask: np.ndarray, vertical: bool, gap: int, cover: float) -> np.ndarray:
    """Only the strokes of `mask` that RUN THROUGH the window: a component (rows bridged over `gap` px of scan break) whose extent along the stroke is at least `cover` of the window's. A rule
    passes the whole window; a letter's stem that happens to stand on the column (or a stub of the rule ending inside the window) does not. (The carve of the page stroke map takes a letter's
    stroke where it lies on a barline column, because a column is carved row by row.)"""
    import cv2
    if not mask.any():
        return mask
    m = (mask if vertical else mask.T).astype(np.uint8)
    n = m.shape[0]
    closed = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((max(1, 2 * gap + 1), 1), np.uint8)) if gap > 0 else m
    cnt, lab, st, _c = cv2.connectedComponentsWithStats(closed, 8)
    keep = np.zeros(m.shape, bool)
    for i in range(1, cnt):
        if st[i][3] >= cover * n:
            keep |= lab == i
    keep &= m > 0
    return keep if vertical else keep.T


def _attached(owned: np.ndarray, rest: np.ndarray, vertical: bool, reach: int, grow: int) -> np.ndarray:
    """Per owned pixel: is it part of a mark that touches the owned stroke? True where, in the pixel's own row (a vertical stroke) / column (a level one), ink that is not owned stands within
    `reach` px of the stroke's run on EITHER side, and for `grow` px along the stroke beyond such rows (a letter's own stroke thickness). Such pixels are the mark's, not the owner's: a letter
    that crosses the stroke has ink on both sides; one that stands ON it (the stem of a `p` on a barline) has its bowl on one."""
    import cv2
    o, r = (owned, rest) if vertical else (owned.T, rest.T)
    mark = np.zeros(o.shape, np.uint8)
    h, w = o.shape
    for y in np.nonzero(o.any(axis=1))[0]:
        row = o[y]
        d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
        for a, b in zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]):
            if r[y, max(0, a - reach):a].any() or r[y, b:min(w, b + reach)].any():
                mark[y, a:b] = 1
    if grow > 0 and mark.any():
        mark = cv2.dilate(mark, np.ones((2 * grow + 1, 1), np.uint8))
    out = (mark > 0) & o
    return out if vertical else out.T


def owned_ink_mask(page: Any, rect: Sequence[int], spacing: float = 0.0, before_owner: str = "word") -> Optional[np.ndarray]:
    """The pixels of `rect` (x0, y0, x1, y1, page px) held by an owner earlier than `before_owner` in `CLAIM_ORDER` (and named by the flag), crossing marks given back. None when the page has
    no `attach`ed masks or nothing is owned there: the caller changes nothing."""
    oi = getattr(page, "owned_ink", None)
    if oi is None:
        return None
    x0, y0, x1, y1 = (int(v) for v in rect)
    h, w = page.rgb.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return None
    try:
        cut = CLAIM_ORDER.index(before_owner)
    except ValueError:
        cut = len(CLAIM_ORDER)
    use = [k for k in oi.kinds if CLAIM_ORDER.index(k) < cut]
    if not use:
        return None
    sub = {k: oi.masks[k][y0:y1, x0:x1] for k in ("barline", "staff_line")}
    gap = int(round(THROUGH_GAP_SPACES * spacing)) if spacing else 0
    taken = np.zeros((y1 - y0, x1 - x0), bool)
    for k in use:
        sub[k] = _through(sub[k], vertical=(k == "barline"), gap=gap, cover=THROUGH_COVER_MIN)
        taken |= sub[k]
    if not taken.any():
        return None
    ink = _ink(page, (x0, y0, x1, y1))
    reach = max(2, int(round(CROSS_REACH_SPACES * spacing))) if spacing else oi.reach_px
    rest = ink & ~sub["barline"] & ~sub["staff_line"]
    grow = max(1, int(round(ATTACHED_GROW_SPACES * spacing))) if spacing else 2
    give_back = np.zeros(taken.shape, bool)
    for k in use:
        give_back |= _attached(sub[k], rest, vertical=(k == "barline"), reach=reach, grow=grow)
    out = taken & ~give_back
    return out if out.any() else None
