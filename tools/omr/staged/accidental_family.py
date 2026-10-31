"""ROADMAP 2.201 -- ONE ACCIDENTAL FAMILY: the TYPE from the mark's own strokes, its ROLE from position (flag `OMR_ACCIDENTAL_FAMILY`, default ON,
needs `OMR_STROKE_MAP`). STAGED GATHER (the extent and the type, pure, here) + ADJUDICATE (`adjudicate_accidental_owner` reads the row detail).

PURE: no log, no cell. `gather.gather_accidental_family` is its stage; it hands in `stroke_map.Stroke` rows and the box.

THE CAUSE (benchmarks/omr-accidental-family-2026-10/FINDINGS.md, 58 of Sean's answered tiles): a natural read as a flat or a sharp is NOT, as a
first reading of Sean's 2.203 answers had it, a box that stops short of the lower stroke -- the detector's box holds BOTH of the natural's strokes
in most tiles; only a handful are cut. What is wrong is the CLASS, and the ink says the type plainly: a natural is two stems of which the RIGHT one
stands LOWER (its top 0.7-1.7 spaces below the left one's), a sharp is two stems side by side (the right one level or a little higher: -0.2 .. +0.06),
a flat is ONE stem with its bowl at the lower right. The few cut boxes (a natural's lower or upper stroke lost) are grown along the mark's own
strokes so the stagger is still measured.

CONVENTION ASSUMED (page-facts section 3; Sean 2026-10-23 "go with the stroke"): an accidental is drawn in its font's shape: a natural's left stem
rises above the square and its right stem hangs below it; a sharp's two stems stand level; a flat has one stem. WHAT WOULD FALSIFY IT: a plate
whose naturals are drawn with level stems, or whose sharps lean enough to stagger them by half a space. NOT CONFIRMED beyond Litolff and
Breitkopf (the cut-offs are a measurement on those two plates and may only NARROW until another publisher confirms them -- CLAUDE section 4).

WHAT THIS IS NOT: a new class source. It chooses only among flat / natural / sharp (the accidental family); a mark whose strokes do not say stays
`unclear` and the detector's own candidates stand. It never READs: the shape is a second reader of the same raster the detector read (CLAUDE section 5),
so what it picks is written GUESSED (blue) -- `READ_MARGIN` is None until Sean sets a bar on tiles.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

ENV = "OMR_ACCIDENTAL_FAMILY"
REASON = "accidental_family"


def enabled() -> bool:
    """`OMR_ACCIDENTAL_FAMILY`, default ON (Sean 2026-10-26); an explicit 0/false/no/off disables."""
    return os.environ.get(ENV, "1").strip().lower() not in ("0", "false", "no", "off")


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.247 -- ACCIDENTALS LABELLED BY THEIR SHAPE (flag `OMR_ACCIDENTAL_KIND`, default OFF, deny-list: only 1/true/yes/on enables)
# ─────────────────────────────────────────────────────────────────────────────
#: CONVENTION ASSUMED (Sean 2026-10-31, engraving): a natural is two offset uprights (left up, right down) joined by two slanted bars; a flat is
#: one upright with a BOWL at its lower end. "Sometimes the line that goes off the bottom of the natural is hard to see": a natural whose right
#: upright is lost below the lower bar leaves ONE stem + a closed SQUARE, which 2.201's flat test ("one stem + any piece to its right, low")
#: called a flat. The square and the bowl differ at the piece's TOP RIGHT: the natural's upper bar rises to the right and meets the right upright
#: in a CORNER (the piece's right quarter stands as high as its left part or higher); a flat's bowl has a rounded SHOULDER there (its right
#: quarter falls away below its highest point). WHAT WOULD FALSIFY IT: a plate whose flats have a square-topped bowl, or whose naturals' bars
#: are level. NOT CONFIRMED beyond Litolff and Breitkopf; the cut-off below is a measurement on those two plates, so it may only NARROW:
#: a stem + square is never DECIDED a natural here, it stops being a flat (`unclear`, candidates natural AND flat, written GUESSED).
KIND_ENV = "OMR_ACCIDENTAL_KIND"
#: a flat's bowl: its right quarter's top lies at least this far (spaces) BELOW the top of its left-middle part (a rounded shoulder);
#: synthetic flat 0.25, synthetic natural square -0.06 (median top of the right quarter vs the highest point of the left-middle).
FLAT_SHOULDER_MIN_SP = 0.15
#: a two-stem reading whose right stem's TOP is lower (natural-like) but whose BOTTOM ends this far above the left stem's bottom: the right
#: upright's lower stroke is faint/lost -- natural or (a bowl's right side read as a stem) flat; never sharp.
#: Not a new cut: it is 2.201's `STAGGER_REVERSE_MAX_SP` (the bound past which a reading stops being a natural), restated here.
FAINT_LOWER_REVERSE_SP = 0.25


def kind_enabled() -> bool:
    """`OMR_ACCIDENTAL_KIND` (ROADMAP 2.247), default OFF; only an explicit 1/true/yes/on enables."""
    return os.environ.get(KIND_ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def bowl_shoulder_sp(masks: Optional[Sequence[Any]], scale: float, sp: float,
                     ordinals: Sequence[int]) -> Optional[float]:
    """ROADMAP 2.247: how far the TOP of the right quarter of the piece(s) to the right of a flat-candidate stem lies BELOW the top of their
    left-middle part, in spaces (positive = a rounded shoulder = a bowl; <= 0 = a square corner = a natural's bars). The union of the pieces'
    own masks (`CellStrokes.masks`, reduced frame), never the box. None when no mask (cannot tell)."""
    import numpy as np
    if not masks or not ordinals:
        return None
    rows = [masks[i] for i in ordinals if 0 <= i < len(masks) and masks[i] is not None]
    if not rows:
        return None
    x0 = min(int(m[1]) for m in rows)
    y0 = min(int(m[2]) for m in rows)
    x1 = max(int(m[1]) + m[0].shape[1] for m in rows)
    y1 = max(int(m[2]) + m[0].shape[0] for m in rows)
    canvas = np.zeros((y1 - y0, x1 - x0), dtype=bool)
    for m, mx, my in rows:
        canvas[int(my) - y0:int(my) - y0 + m.shape[0], int(mx) - x0:int(mx) - x0 + m.shape[1]] |= m.astype(bool)
    w = canvas.shape[1]
    if w < 4:
        return None
    cols = canvas.any(axis=0)
    tops = np.where(cols, canvas.argmax(axis=0), canvas.shape[0])
    left = tops[int(0.15 * w):max(int(0.15 * w) + 1, int(0.5 * w))]
    right = tops[int(0.75 * w):]
    if left.size == 0 or right.size == 0 or not cols[int(0.75 * w):].any():
        return None
    sp_red = float(sp) * float(scale or 1.0)
    return round(float(np.median(right[right < canvas.shape[0]]) - left.min()) / max(1e-9, sp_red), 3)


#: A stroke is a stem of the mark at or above this length (staff spaces). A natural's hanging stem can be cropped to ~0.8 and still read.
STEM_MIN_SP = 0.5
#: ... and a stem the mark OWNS is at most this long: an accidental's longest stroke is a sharp's 3.5; the strokes the map found 4.1-7.4 long were an
#: accidental's stem fused to a note stem or a bar, which is not the accidental's to measure.
STEM_MAX_SP = 3.7
#: the mark is at most this tall after growing (a sharp is 3.0-3.5 spaces)
MAX_MARK_H_SP = 3.9
#: a vertical stroke with at least this share of its ink in the box is the mark's (the register's cut, `stroke_map.COVER_SHARE_MIN`, is 0.5);
#: a PARTLY covered stroke (grown) needs at least this share.
COVER_SHARE_MIN = 0.5
GROW_SHARE_MIN = 0.15
#: the two stems of a natural / sharp stand this far apart (x centre to centre, spaces): measured 0.44-0.63.
STEM_GAP_MIN_SP = 0.3
#: NATURAL: the right stem's top (or bottom) is at least this much LOWER than the left's; measured 0.69-1.69 on the naturals (one at 0.37 had a cropped
#: top, its bottom stagger was 0.81, hence the larger of the two ends).
NATURAL_STAGGER_MIN_SP = 0.45
#: SHARP: neither end staggers by more than this; measured -0.19 .. 0.06. Between the two cut-offs the stems are `unclear`.
SHARP_STAGGER_MAX_SP = 0.2
#: ... and neither end of a sharp has its right stem HIGHER than the left's by more than this (measured -0.19 at the most; tile 11 read -1.2 and -1.4: two
#: neighbouring marks, not one sharp).
SHARP_STAGGER_REVERSE_MAX_SP = 0.45
#: ... and a natural's other end is never HIGHER than the left's by more than this (a mirrored natural is not a natural).
STAGGER_REVERSE_MAX_SP = 0.25
#: FLAT: the one stem stands in the left part of the mark and its bowl (a piece to its right) lies in its lower part.
FLAT_STEM_X_FRACTION_MAX = 0.45
FLAT_BOWL_MIN_FRACTION = 0.40
#: Never READ (Sean's to set on blind tiles).
READ_MARGIN: Optional[float] = None

TYPES = ("flat", "natural", "sharp")
#: the detector class names the family files under (SMuFL spelling, lower-case compare); a double sign is the detector's candidate only
_TYPE_OF_CLASS = {"accidentalflat": "flat", "accidentaldoubleflat": "flat", "accidentalnatural": "natural", "accidentalsharp": "sharp",
                  "accidentaldoublesharp": "sharp", "keyflat": "flat", "keynatural": "natural", "keysharp": "sharp"}
_CLASS_OF_TYPE = {"flat": "accidentalFlat", "natural": "accidentalNatural", "sharp": "accidentalSharp"}
#: the key-series class for each type (the key marker run's shape names)
KEY_SHAPE_OF_TYPE = {"flat": "keyFlat", "natural": "keyNatural", "sharp": "keySharp"}


def is_family_class(name: str) -> bool:
    """Every accidental-family detector class, BOTH series: `accidental*` and `key*` (Sean 2026-10-22: one family, role by position)."""
    n = str(name or "").lower()
    return n.startswith("accidental") or n in _TYPE_OF_CLASS


def type_of_class(name: str) -> Optional[str]:
    """The detector's own type for a class (flat/natural/sharp), or None (anything else)."""
    return _TYPE_OF_CLASS.get(str(name or "").lower())


def class_of_type(t: str) -> Optional[str]:
    return _CLASS_OF_TYPE.get(t)


def reads(margin: Optional[float]) -> bool:
    return READ_MARGIN is not None and margin is not None and margin >= READ_MARGIN


def _union(boxes: Sequence[Sequence[float]]) -> List[float]:
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _sbox(s: Any) -> Tuple[float, float, float, float]:
    x, y, w, h = s.box
    return float(x), float(y), float(x + w), float(y + h)


def members_and_extent(box: Sequence[float], strokes: Sequence[Any], shares: Sequence[Tuple[int, float]], sp: float,
                       blocked: Sequence[int] = ()) -> Dict[str, Any]:
    """The strokes that ARE this mark and the box that holds all of them.

    `box` = the detector's (x0, y0, x1, y1) in the cell's canonical px; `strokes` = the cell's `stroke_map.Stroke` list; `shares` =
    `stroke_map.strokes_in_box(res, box)` = `[(ordinal, share)]`; `sp` = canonical px per staff space; `blocked` = ordinals a notehead / stem
    owns (never the mark's).

    1. MEMBERS: every stroke with at least `COVER_SHARE_MIN` of its ink in the box, unless blocked.
    2. GROWN: a VERTICAL stroke with at least `GROW_SHARE_MIN` in the box, whose own length is `STEM_MIN_SP`..`STEM_MAX_SP` (an accidental's
       own stroke, not one fused to a note stem), that touches no blocked stroke and whose x centre lies inside the box (+-0.2 space), is the
       mark's: the box grows along it to its end -- and only while the mark stays under `MAX_MARK_H_SP`.
    3. The grown box then takes every other non-blocked stroke at least `COVER_SHARE_MIN` inside it (a bar, a bowl).
    Returns `{"members": [ordinal...], "box": [x0,y0,x1,y1], "grown": bool, "grown_by": [ordinal...], "grown_sp": {"up","down"}}`."""
    blocked_set = set(int(b) for b in blocked)
    share_of = {int(i): float(s) for i, s in shares}
    members = [i for i, s in sorted(share_of.items()) if s >= COVER_SHARE_MIN and i not in blocked_set]
    x0, y0, x1, y1 = [float(v) for v in box]
    grown_by: List[int] = []
    cand: List[int] = []
    refused: List[int] = []         # vertical strokes through the box the mark may NOT claim (fused to a note stem, or a head's own): the type is then unclear
    for i, s in sorted(share_of.items()):
        if i in members or s < GROW_SHARE_MIN:
            continue
        st = strokes[i]
        if st.kind != "vertical":
            continue
        bx0, _by0, bx1, _by1 = _sbox(st)
        cx = (bx0 + bx1) / 2.0
        if not (x0 - 0.2 * sp <= cx <= x1 + 0.2 * sp):
            continue
        if i in blocked_set or not (STEM_MIN_SP <= st.length_sp <= STEM_MAX_SP) or any(int(j) in blocked_set for j, _c in st.touches):
            refused.append(i)
            continue
        cand.append(i)
    # a COVERED vertical stroke longer than any accidental stem (a sharp's stem fused to a note stem or to the mark above it: tile 9 of the 2.201 tiles) is
    # not the mark's to measure, and it must not simply vanish -- the type is then unclear, not whatever the remaining stem and bars look like
    for i in members:
        st = strokes[i]
        if st.kind == "vertical" and st.length_sp > STEM_MAX_SP:
            refused.append(i)
    ext = [x0, y0, x1, y1]
    # a covered stroke that runs past the box (a share of 0.5-0.95) also grows it
    for i in list(members):
        st = strokes[i]
        if st.kind == "vertical" and STEM_MIN_SP <= st.length_sp <= STEM_MAX_SP:
            bx0, by0, bx1, by1 = _sbox(st)
            trial = [min(ext[0], bx0), min(ext[1], by0), max(ext[2], bx1), max(ext[3], by1)]
            if trial != ext and (trial[3] - trial[1]) / sp <= MAX_MARK_H_SP:
                ext = trial
                grown_by.append(i)
    for i in cand:
        bx0, by0, bx1, by1 = _sbox(strokes[i])
        trial = [min(ext[0], bx0), min(ext[1], by0), max(ext[2], bx1), max(ext[3], by1)]
        if (trial[3] - trial[1]) / sp > MAX_MARK_H_SP:
            refused.append(i)
            continue
        ext = trial
        members.append(i)
        grown_by.append(i)
    # a stem that ends only a few pixels outside the box is rounding, not growth
    tol = 0.1 * sp
    if ext[0] >= x0 - tol and ext[1] >= y0 - tol and ext[2] <= x1 + tol and ext[3] <= y1 + tol:
        grown_by = []
    if grown_by:
        have = set(members)
        for j, st in enumerate(strokes):
            if j in have or j in blocked_set:
                continue
            bx0, by0, bx1, by1 = _sbox(st)
            iw, ih = min(bx1, ext[2]) - max(bx0, ext[0]), min(by1, ext[3]) - max(by0, ext[1])
            area = max(1e-9, (bx1 - bx0) * (by1 - by0))
            if iw > 0 and ih > 0 and iw * ih / area >= COVER_SHARE_MIN and st.length_sp <= STEM_MAX_SP:
                members.append(j)
    members = sorted(set(members))
    return {"members": members, "refused_vertical": sorted(set(refused)), "box": [round(v, 1) for v in ext], "grown": bool(grown_by), "grown_by": sorted(set(grown_by)),
            "grown_sp": {"up": round(max(0.0, y0 - ext[1]) / sp, 2), "down": round(max(0.0, ext[3] - y1) / sp, 2)}}


def read_type(strokes: Sequence[Any], members: Sequence[int], sp: float, refused_vertical: Sequence[int] = (),
              masks: Optional[Sequence[Any]] = None, scale: float = 1.0) -> Dict[str, Any]:
    """`flat | natural | sharp | unclear | unread` from the mark's own strokes, with the measured features and a signed margin.

    STEMS = member strokes that are vertical and at least `STEM_MIN_SP` long, not longer than `STEM_MAX_SP`, left to right by x centre.
      two stems at least `STEM_GAP_MIN_SP` apart: the right stem's LOWERNESS, top and bottom, against the left (`stagger_top_sp`, `stagger_bottom_sp`)
        natural   the larger of the two >= `NATURAL_STAGGER_MIN_SP` and the smaller not below `-STAGGER_REVERSE_MAX_SP`
        sharp     the larger of the two <= `SHARP_STAGGER_MAX_SP`
        else      unclear (the band between the cut-offs, or a mirrored natural)
      one stem: a FLAT when it stands in the left `FLAT_STEM_X_FRACTION_MAX` of the mark and a non-vertical piece lies to its right with its centre in the
        stem's lower part (the bowl); else unclear
      none or more than two: unread / unclear (a double sign, a merged pair, a stroke that is not an accidental's)
    ROADMAP 2.247 (flag `OMR_ACCIDENTAL_KIND`; `masks`/`scale` = the cell's `CellStrokes.masks`/`.scale`): the one-stem FLAT also needs a rounded
      shoulder on the piece (`bowl_shoulder_sp`), else `unclear` (`stem_and_square`); two stems with the right one's top LOWER but its bottom well
      ABOVE the left's (a natural's faint lower stroke) are `unclear` (`right_stem_lower_bottom_short`). Each such reading carries
      `shape_candidates` (natural + flat), which `guess_of` writes beside the detector's.
    `margin`: natural = larger stagger - cut-off, sharp = cut-off - larger stagger (positive = inside the clear zone), flat = None (structural)."""
    st = [strokes[i] for i in members]
    stems = sorted([s for s in st if s.kind == "vertical" and STEM_MIN_SP <= s.length_sp <= STEM_MAX_SP],
                   key=lambda s: _sbox(s)[0] + _sbox(s)[2])
    base: Dict[str, Any] = {"n_stems": len(stems), "n_members": len(st)}
    if not st:
        return {**base, "type": "unread", "why": "no_strokes", "margin": None}
    if not stems:
        return {**base, "type": "unclear", "why": "no_stem", "margin": None}
    if len(stems) == 1 and refused_vertical:
        # one stem and a SECOND vertical stroke through the box that the mark may not claim (fused to a note stem, a head's own): the second stem of a
        # natural or a sharp may be that one, so a lone stem is NOT a flat here (rule 8: cannot tell is not "flat")
        return {**base, "type": "unclear", "why": "second_stem_fused_or_owned", "margin": None, "refused_vertical": list(refused_vertical)}
    if len(stems) == 1:
        s = stems[0]
        sx0, sy0, sx1, sy1 = _sbox(s)
        ext = _union([_sbox(m) for m in st])
        width = max(1e-9, ext[2] - ext[0])
        xfrac = ((sx0 + sx1) / 2.0 - ext[0]) / width
        h = max(1e-9, sy1 - sy0)
        bowl = [m for m in st if m is not s and m.kind != "vertical" and (_sbox(m)[0] + _sbox(m)[2]) / 2.0 > (sx0 + sx1) / 2.0
                and ((_sbox(m)[1] + _sbox(m)[3]) / 2.0 - sy0) / h >= FLAT_BOWL_MIN_FRACTION]
        feat = {**base, "stem_x_fraction": round(xfrac, 3), "stem_len_sp": round(float(s.length_sp), 2), "bowl_pieces": len(bowl)}
        if xfrac <= FLAT_STEM_X_FRACTION_MAX and bowl and kind_enabled():
            # ROADMAP 2.247: a piece low and right of the stem is a bowl OR a natural's square (its right upright's lower stroke lost); only a
            # rounded shoulder at its top right is a bowl. A square corner, or a piece whose shape cannot be measured, is NOT a flat (rule 8).
            right_pieces = [members[k] for k, m in enumerate(st) if m is not s and m.kind != "vertical"
                            and (_sbox(m)[0] + _sbox(m)[2]) / 2.0 > (sx0 + sx1) / 2.0]
            shoulder = bowl_shoulder_sp(masks, scale, sp, right_pieces)
            feat = {**feat, "shoulder_sp": shoulder}
            if shoulder is None or shoulder < FLAT_SHOULDER_MIN_SP:
                return {**feat, "type": "unclear", "why": "stem_and_square" if shoulder is not None else "bowl_unmeasured",
                        "margin": None if shoulder is None else round(shoulder - FLAT_SHOULDER_MIN_SP, 3), "shape_candidates": ["natural", "flat"]}
            return {**feat, "type": "flat", "why": "one_stem_with_a_bowl", "margin": None}
        if xfrac <= FLAT_STEM_X_FRACTION_MAX and bowl:
            return {**feat, "type": "flat", "why": "one_stem_with_a_bowl", "margin": None}
        return {**feat, "type": "unclear", "why": "one_stem_no_bowl", "margin": None}
    if len(stems) > 2:
        return {**base, "type": "unclear", "why": "more_than_two_stems", "margin": None}
    left, right = stems
    lx0, ly0, lx1, ly1 = _sbox(left)
    rx0, ry0, rx1, ry1 = _sbox(right)
    gap = ((rx0 + rx1) - (lx0 + lx1)) / 2.0 / sp
    top, bot = (ry0 - ly0) / sp, (ry1 - ly1) / sp
    hi, lo = max(top, bot), min(top, bot)
    feat = {**base, "stagger_top_sp": round(top, 2), "stagger_bottom_sp": round(bot, 2), "stem_gap_sp": round(gap, 2),
            "stem_len_sp": [round(float(left.length_sp), 2), round(float(right.length_sp), 2)],
            "n_bars": sum(1 for m in st if m.kind == "horizontal")}
    if gap < STEM_GAP_MIN_SP:
        return {**feat, "type": "unclear", "why": "stems_too_close", "margin": None}
    if hi >= NATURAL_STAGGER_MIN_SP and lo >= -STAGGER_REVERSE_MAX_SP:
        return {**feat, "type": "natural", "why": "right_stem_lower", "margin": round(hi - NATURAL_STAGGER_MIN_SP, 3)}
    if kind_enabled() and top >= NATURAL_STAGGER_MIN_SP and bot < -FAINT_LOWER_REVERSE_SP:
        # ROADMAP 2.247: the natural's offset at the TOP, but the right upright stops short at the bottom (its lower stroke faint) -- a natural, or
        # a flat whose bowl side read as a stem; never a sharp. Not decided (the cut-offs are 2.201's, measured on two plates).
        return {**feat, "type": "unclear", "why": "right_stem_lower_bottom_short", "margin": round(bot + FAINT_LOWER_REVERSE_SP, 3),
                "shape_candidates": ["natural", "flat"]}
    if hi <= SHARP_STAGGER_MAX_SP and lo >= -SHARP_STAGGER_REVERSE_MAX_SP:
        return {**feat, "type": "sharp", "why": "stems_level", "margin": round(SHARP_STAGGER_MAX_SP - hi, 3)}
    if hi <= SHARP_STAGGER_MAX_SP:
        return {**feat, "type": "unclear", "why": "right_stem_much_higher", "margin": round(lo + SHARP_STAGGER_REVERSE_MAX_SP, 3)}
    return {**feat, "type": "unclear", "why": "stagger_between_cutoffs",
            "margin": round(-min(abs(hi - NATURAL_STAGGER_MIN_SP), abs(hi - SHARP_STAGGER_MAX_SP)), 3)}


def family_row(detector_class: str, box: Sequence[float], strokes: Sequence[Any], shares: Sequence[Tuple[int, float]], sp: float,
               blocked: Sequence[int] = (), rivals: Sequence[str] = (), masks: Optional[Sequence[Any]] = None,
               scale: float = 1.0) -> Dict[str, Any]:
    """The whole family measurement of ONE accidental-family box: extent + type + the detector's label KEPT as a recorded fact (never the filter) and
    its candidate types (the winner's and every merged rival's, in the family only). Plain JSON-able dict."""
    ext = members_and_extent(box, strokes, shares, sp, blocked)
    t = read_type(strokes, ext["members"], sp, ext["refused_vertical"], masks=masks, scale=scale)
    cands: List[str] = []
    for c in [detector_class] + [str(r) for r in rivals]:
        ty = type_of_class(c)
        if ty and ty not in cands:
            cands.append(ty)
    return {"type": t["type"], "why": t.get("why"), "margin": t.get("margin"),
            "features": {k: v for k, v in t.items() if k not in ("type", "why", "margin")},
            "box": ext["box"], "grown": ext["grown"], "grown_by": ext["grown_by"], "grown_sp": ext["grown_sp"], "members": ext["members"],
            "detector_class": str(detector_class), "detector_type": type_of_class(detector_class), "candidates": cands,
            "agrees_with_detector": (t["type"] == type_of_class(detector_class)) if t["type"] in TYPES else None}


def anchor_fraction(t: str) -> Optional[float]:
    """The staff-position anchor of each TYPE on the mark's own (grown) box: the font's, as `gather._ANCHOR_FRACTION` states for the classes
    (flat 0.715 -- its stem rises above the bowl; natural and sharp 0.5). A type the strokes did not name has none."""
    return {"flat": 0.715, "natural": 0.504, "sharp": 0.501}.get(t)


def guess_of(fam: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The GUESSED flag an accidental written through its family reading carries, or None where the reading only AGREES with a lone detector class.

    Nothing the strokes say is READ (`READ_MARGIN` is None): they are a second reader of the raster the detector read, so they count once, not twice
    (CLAUDE section 4). Agreement with ONE detector class is not new evidence and changes nothing (the accidental stays as it was: READ). A guess is
    written where (a) the strokes name a type the detector's box did not carry, (b) the detector offered more than one type for the ink, (c) the box
    was labelled `key*` (a role claim the position, not the label, now settles), or (d) the strokes cannot tell (`unclear`), whatever alteration
    the row then carries is the detector's candidate. Candidates: the chosen type first, then the rest, each with a support."""
    if not fam:
        return None
    t = fam.get("type")
    det_class = str(fam.get("detector_class") or "")
    cands = [str(c) for c in (fam.get("candidates") or ())]
    clear = t in TYPES
    chosen = t if clear else (fam.get("detector_type") or (cands[0] if cands else None))
    lone_agree = clear and cands == [t] and not det_class.lower().startswith("key")
    if lone_agree:
        return None
    order = [chosen] + [c for c in cands if c != chosen] if chosen else list(cands)
    if clear and t not in order:
        order = [t] + order
    # ROADMAP 2.247 (flag `OMR_ACCIDENTAL_KIND`; only its readings carry `shape_candidates`): the kinds the SHAPE could not tell apart join the
    # candidates, so a written guess shows both (never the class alone where the shape says "natural or flat").
    for c in ((fam.get("features") or {}).get("shape_candidates") or ()):
        if c not in order:
            order.append(c)
    out = []
    for i, c in enumerate(order):
        if c is None:
            continue
        out.append({"value": c, "support": (fam.get("margin") if (i == 0 and clear and fam.get("margin") is not None) else 1.0)})
    return {"candidates": out, "chosen": {"value": chosen}, "margin": fam.get("margin"), "why": fam.get("why")}
