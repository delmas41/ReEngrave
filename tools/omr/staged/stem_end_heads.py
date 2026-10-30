"""ROADMAP 2.179 -- a stem that carries no head is a note we have not seen; look closer at its end. STAGED GATHER (decides nothing).

Sean 2026-10-01 (DECISIONS, the 2.55 rescue): *"if there are stems then there are notes and the note heads will be connected to the
stems."* Sean 2026-10-19 (the detector principle): *"We take a big picture view ... and where it gets really crowded or hard to read.
We look closer."* A reader who sees a stem with nothing at its end does not conclude "no note": he looks again at the end, where the
head must be, and reads the blot that is there as the head. 2.179's census of the red bars (Litolff pp. 1,6,10,13,16) found the
commonest unseen symbol to be exactly that: a black head welded into a thick staff line, boxed by the detector at 0.05-0.25 (under the
production floor) or boxed as a whole/half rest (a black block between two lines), with its stem read by the CV stem finder.

ONE flag, `OMR_STEM_END_HEADS`, default ON (explicit 0/false/no/off disables). Per cell:
  (1) the CV stems of the cell (`line_detection.detect_lines`, the staged stem finder -- the same call the 2.55 rescue makes);
  (2) a stem is ORPHAN when no head box already on the cell (any reader) stands at either of its ends (the 2.55 window);
  (3) for an orphan stem, the SAME detector is re-run on the cell at `FLOOR`; a head-class box is a candidate where its centre sits at
      one END of that stem, on the side the stem convention puts the head (page-facts: stems up -> stem at the head's RIGHT, head at the
      bottom end; stems down -> stem at the head's LEFT, head at the top end). A block rest box (`restWhole` / `restHalf`, production or
      sub-floor) standing there is a candidate too, RE-READ as a black head (a rest never has a stem -- the convention
      `rest_has_a_stem` already refuses the rest by); the box is kept, its class becomes the black head of its staff position, and the
      detector's own class is carried as `read_from`.
  A stem standing inside another mark's box for most of its length (a quarter rest's body, a flat's stem, a clef bar, a dynamic's
      stroke) is that mark's, never an orphan; a whole-class box is never taken (a whole note has no stem); a candidate within about a
      space of a head already seen is never added (the first run's one judged regression: a second box beside a production half note).
  (4) one candidate per stem end (highest score); a candidate standing on a box of another symbol family at least as confident as it
      is dropped (the 2.172 merge rule: never overturn a confident production box); a production box is never changed or removed.
Kept boxes are APPENDED to the cell's `detections` under `READERS.RESCUE_STEM_HEAD` (the 2.53 pattern: every later reader and every
ADJUDICATE gate sees them as any glyph). Refused candidates are abstentions carrying score, class and why.

CONVENTION ASSUMED: every stem carries a head at one end, on the side its direction gives (page-facts "Stems", Sean). WHAT WOULD FALSIFY
IT: Sean's blind tiles on the new boxes (`out/print/2.179-review/`) showing that most are not heads (a stem that is a barline sliver,
a letter's upright, a rest's body). NOT CONFIRMED: `FLOOR` (0.05) and the window sizes are measurements on two plates (Litolff,
Brahms); they may only NARROW (add a candidate behind every gate) until a third publisher confirms them.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

STEM_END_HEADS_ENV = "OMR_STEM_END_HEADS"

#: the detector is re-read at this floor on a cell holding an orphan stem (2.172's `READ_FLOOR`; 2.179 census: welded heads 0.05-0.25)
FLOOR = 0.05
#: a head ALREADY at a stem end (makes it not an orphan): staff spaces either side of the stem / along it from the end (a stem is drawn
#: past its head's centre: 2.179 debug cells, heads 0.6-0.75 space from the CV end)
ORPHAN_HALF_WIDTH_SPACES = 0.9
ORPHAN_HALF_HEIGHT_SPACES = 1.0
#: a candidate head's centre at a stem end: across the stem on the convention's side (OWN side up to this far, the other side up to
#: `CROSS_SPACES` for a stem drawn through the head's edge), and this far along the stem from its end
SIDE_SPACES = 1.1
CROSS_SPACES = 0.25
END_SPACES = 1.0
#: a candidate whose centre is this close to a head already seen (across / along, staff spaces) is that head boxed again, or its
#: neighbour in the slot the stacked-head fit gives ONE head: never added (2.179 first run: a second box under a judged half note made
#: `stacked_head_duplicate` refuse the production one -- a confident production box must never be overturned)
BESIDE_ACROSS_SPACES = 0.6
BESIDE_ALONG_SPACES = 1.1
#: a CV stem standing inside another mark's box for at least this share of its length is that mark's own upright (the body of a
#: Breitkopf quarter rest, a flat's stem, a clef's bar, a dynamic's down-stroke), not a note's stem: never an orphan
OWNED_SHARE = 0.5
#: the marks whose box can own an upright stroke
_OWNER_PREFIXES = ("rest", "acc", "clef", "dynamic", "timeSig", "keyFlat", "keySharp", "keyNatural", "brace", "bracket", "repeat")
#: block rest classes that, at a stem end, are a black head boxed in the wrong class
BLOCK_RESTS = ("restWhole", "restHalf")
#: the families a candidate may not stand on when that box is at least as confident (never overturn a confident box)
_OTHER_FAMILY_PREFIXES = ("rest", "acc", "clef", "dynamic", "timeSig", "flag", "keyFlat", "keySharp", "keyNatural", "fermata",
                          "augmentationDot", "articStaccato", "brace", "bracket", "repeat")


def enabled() -> bool:
    """`OMR_STEM_END_HEADS`, default ON (Sean 2026-10-20); an explicit 0/false/no/off disables."""
    return os.environ.get(STEM_END_HEADS_ENV, "").strip().lower() not in ("0", "false", "no", "off")


def _box(d: Any) -> Tuple[float, float, float, float]:
    return (float(d.x_canonical), float(d.y_canonical),
            float(d.x_canonical + d.width_canonical), float(d.y_canonical + d.height_canonical))


def _centre(b: Sequence[float]) -> Tuple[float, float]:
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


def _iou(a: Sequence[float], b: Sequence[float]) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def same_ink(a: Sequence[float], b: Sequence[float]) -> bool:
    if _iou(a, b) >= 0.3:
        return True
    ca, cb = _centre(a), _centre(b)
    return (b[0] <= ca[0] <= b[2] and b[1] <= ca[1] <= b[3]) or (a[0] <= cb[0] <= a[2] and a[1] <= cb[1] <= a[3])


def is_head(name: str) -> bool:
    return str(name).startswith("notehead")


def stem_ends(s: Any) -> Tuple[float, float, float]:
    """`(x_centre, y_top, y_bottom)` of a CV stem in the cell's canonical frame."""
    x = float(s.x_canonical) + float(s.width_canonical) / 2.0
    return x, float(s.y_canonical), float(s.y_canonical) + float(s.height_canonical)


def is_orphan(stem: Any, head_boxes: Sequence[Sequence[float]], space: float) -> bool:
    """No head box's centre within the 2.55 window of either end of `stem`."""
    x, yt, yb = stem_ends(stem)
    dx, dy = ORPHAN_HALF_WIDTH_SPACES * space, ORPHAN_HALF_HEIGHT_SPACES * space
    for b in head_boxes:
        cx, cy = _centre(b)
        if abs(cx - x) <= dx and (abs(cy - yt) <= dy or abs(cy - yb) <= dy):
            return False
    return True


def owned_by_a_mark(stem: Any, owners: Sequence[Sequence[float]], space: float) -> bool:
    """The stem's x is inside an owner box (with a tenth of a space to spare) and the box covers `OWNED_SHARE` of its length."""
    x, yt, yb = stem_ends(stem)
    pad = 0.1 * space
    length = max(yb - yt, 1.0)
    for b in owners:
        if b[0] - pad <= x <= b[2] + pad:
            if max(0.0, min(yb, b[3]) - max(yt, b[1])) >= OWNED_SHARE * length:
                return True
    return False


def at_stem_end(b: Sequence[float], stem: Any, space: float) -> Optional[str]:
    """`"bottom"` (stem up: head at the bottom end, LEFT of the stem), `"top"` (stem down: head at the top end, RIGHT of the stem), or
    None. A head's centre is beside the stem by about half a head width, so the own-side band is wide and the far side narrow."""
    x, yt, yb = stem_ends(stem)
    cx, cy = _centre(b)
    own, cross, along = SIDE_SPACES * space, CROSS_SPACES * space, END_SPACES * space
    if abs(cy - yb) <= along and x - own <= cx <= x + cross:
        return "bottom"
    if abs(cy - yt) <= along and x - cross <= cx <= x + own:
        return "top"
    return None


def black_head_class(cy: float, top_y: float, half_step: float) -> str:
    """The black head spelling for a centre at canonical y `cy` (staff position by the cell's own lines)."""
    steps = int(round((cy - top_y) / half_step))
    return "noteheadBlackOnLine" if steps % 2 == 0 else "noteheadBlackInSpace"


def candidates_for_cell(stems: Sequence[Any], existing: Sequence[Any], rerun: Sequence[Any], grid: Tuple[float, float]
                        ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """Pure: `(kept, refused, n_orphans)`. `existing` = the cell's detections so far (any reader), `rerun` = the detector at `FLOOR`.
    Each kept dict: `det` (the detection, class possibly re-read), `stem_index`, `end`, `read_from` (detector class), `score`."""
    top_y, half_step = grid
    space = 2.0 * half_step
    heads = [_box(d) for d in existing if is_head(d.smufl_name)]
    owners = [_box(d) for d in existing if str(d.smufl_name).startswith(_OWNER_PREFIXES) and float(d.confidence) >= 0.25]
    orphans = [i for i, s in enumerate(stems) if is_orphan(s, heads, space) and not owned_by_a_mark(s, owners, space)]
    if not orphans:
        return [], [], 0
    others = [(_box(d), float(d.confidence)) for d in existing
              if str(d.smufl_name).startswith(_OTHER_FAMILY_PREFIXES) and not str(d.smufl_name).startswith(BLOCK_RESTS)]
    pool: List[Tuple[Any, bool]] = []          # (detection, is a production/earlier box re-read)
    for d in existing:
        if str(d.smufl_name).startswith(BLOCK_RESTS):
            pool.append((d, True))
    for d in rerun:
        n = str(d.smufl_name)
        if n.startswith("noteheadWhole"):
            continue                           # a whole note has no stem (page-facts): a whole-class box at a stem end is not one
        if (is_head(n) and float(d.confidence) < 0.25) or n.startswith(BLOCK_RESTS):
            if any(same_ink(_box(d), _box(e)) and str(e.smufl_name).startswith(BLOCK_RESTS) for e, _ in pool):
                continue                       # the rest the record already holds, boxed again
            pool.append((d, False))
    best: Dict[Tuple[int, str], Dict[str, Any]] = {}
    refused: List[Dict[str, Any]] = []
    for d, from_record in pool:
        b = _box(d)
        if any(same_ink(b, h) for h in heads):
            continue                           # a head already stands on this ink (it is not unseen)
        cx, cy = _centre(b)
        beside = any(abs(cx - hx) <= BESIDE_ACROSS_SPACES * space and abs(cy - hy) <= BESIDE_ALONG_SPACES * space
                     for hx, hy in (_centre(h) for h in heads))
        for si in orphans:
            end = at_stem_end(b, stems[si], space)
            if end is None:
                continue
            conf = float(d.confidence)
            if beside:
                refused.append({"det": d, "why": "beside_a_seen_head", "score": conf, "stem_index": si, "end": end})
                continue
            blocker = next((oc for ob, oc in others if same_ink(b, ob) and oc >= conf), None)
            if blocker is not None:
                refused.append({"det": d, "why": "another_mark_stronger", "score": conf, "stem_index": si, "end": end})
                continue
            k = (si, end)
            if k not in best or conf > best[k]["score"]:
                best[k] = {"det": d, "stem_index": si, "end": end, "read_from": str(d.smufl_name), "score": conf,
                           "from_record": from_record}
    kept: List[Dict[str, Any]] = []
    for k in sorted(best):
        cand = best[k]
        if any(same_ink(_box(cand["det"]), _box(o["det"])) for o in kept):
            continue                           # one ink at two stem ends: once
        d = cand["det"]
        if not is_head(d.smufl_name):
            import dataclasses
            cy = _centre(_box(d))[1]
            d = dataclasses.replace(d, smufl_name=black_head_class(cy, top_y, half_step), category="notehead")
        cand["det"] = d
        kept.append(cand)
    return kept, refused, len(orphans)


def orphan_indices(stems: Sequence[Any], existing: Sequence[Any], space: float) -> List[int]:
    """The orphan stems `candidates_for_cell` looks at (no head at an end, not another mark's upright)."""
    heads = [_box(d) for d in existing if is_head(d.smufl_name)]
    owners = [_box(d) for d in existing if str(d.smufl_name).startswith(_OWNER_PREFIXES) and float(d.confidence) >= 0.25]
    return [i for i, s in enumerate(stems) if is_orphan(s, heads, space) and not owned_by_a_mark(s, owners, space)]


# ---------------------------------------------------------------------------------------------------------------------------------------
# lane-stem-end-head (Sean approved 2026-10-29): the head at an orphan stem's end READ from the page's own ink, beside the detector re-run.
#
# CAUSE (lane-barlines-1029, DECISIONS 2026-10-29): Litolff p9's real quarter at page px (1734, 2385) was found only by the 0.05 re-run;
# OFF it gave a 0.074 box, and with the corrected barline the cell crop starts at 1470 instead of 1526 and the re-run finds nothing. A
# 0.07 detector guess flips with any crop change: it is not reading. So the head is read where the convention puts it, on the PAGE
# raster GATHER already holds (`pws.page.binary`, no new image pass), with the head reader landed for fill (`head_ink.read_head_ink`:
# line-only trim, 1.6 sp cap), and the re-run kept only as a second witness.
#
# Flag `OMR_STEM_END_HEAD_INK`, default OFF (explicit 1/true/yes/on enables). Per orphan stem end:
#   * a head-sized SEED box (`HEAD_WIDTH_SPACES` x `HEAD_HEIGHT_SPACES`, the convention's head, from the staff space) on the side the
#     stem's direction gives (up-stem: head at the BOTTOM end, LEFT of the stem; down-stem: at the TOP end, RIGHT of it), centred on
#     the tip; `head_ink.read_head_ink` trims it to the head's own ink;
#   * it is a head only where the trimmed ink is ONE head (`not_one_head` None), OVAL (wider than tall, head-tall across at least a
#     head's minimum, `head_ink.MIN_SPACES`), ATTACHED (its stem-side edge within `CROSS_SPACES` of the stem, its centre at the end by
#     `at_stem_end`) and its fill read ('hollow' / 'filled');
#   * ink and re-run AGREE (same ink) -> the re-run's box is kept (as before); ink alone -> a box built on the trimmed ink; re-run alone
#     where the ink reads no head, or the two on different ink, or one head read at BOTH ends of one stem -> ABSTAIN with the
#     candidates (nothing appended);
#   * ink another mark of the cell already holds (an `_OTHER_FAMILY_PREFIXES` box at the production floor, or a head already seen) is
#     never taken.
# CONVENTION ASSUMED: a head stands at its stem's end on the side the stem's direction gives, an oval ~1.3 x 1.0 sp (page-facts "Stems";
# benchmarks/omr-notehead-width-2026-09). WHAT WOULD FALSIFY IT: Sean's blind tiles on ink-only heads showing beam ends, clef bodies,
# dynamics or tremolo slashes read as one head (2.210's list). NOT CONFIRMED beyond Litolff + Brahms.

STEM_END_HEAD_INK_ENV = "OMR_STEM_END_HEAD_INK"
#: the convention's head (benchmarks/omr-notehead-width-2026-09: 1.3-1.4 sp wide, one space tall); the seed only -- the ink trims it
HEAD_WIDTH_SPACES = 1.3
HEAD_HEIGHT_SPACES = 1.0
#: the production floor: another mark's box below it is not a claim on the ink
CLAIM_FLOOR = 0.25


def ink_enabled() -> bool:
    """`OMR_STEM_END_HEAD_INK`, default OFF."""
    return os.environ.get(STEM_END_HEAD_INK_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def seed_box(stem_x: float, tip_y: float, end: str, space: float) -> Tuple[float, float, float, float]:
    """Page px seed for the head at `end` of a stem at x `stem_x`: bottom end -> LEFT of the stem, top end -> RIGHT of it."""
    w, h = HEAD_WIDTH_SPACES * space, HEAD_HEIGHT_SPACES * space
    if end == "bottom":
        return (stem_x - w, tip_y - h / 2.0, stem_x, tip_y + h / 2.0)
    return (stem_x, tip_y - h / 2.0, stem_x + w, tip_y + h / 2.0)


class _PageStem:
    """A stem in PAGE px, shaped like a detection, so `at_stem_end` reads it unchanged."""
    def __init__(self, x: float, yt: float, yb: float):
        self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = x, yt, 0.0, yb - yt


def ink_head_at_end(page_binary: Any, stem_page: Tuple[float, float, float], end: str, space_px: float,
                    foreign_boxes: Sequence[Sequence[float]], slit_fn: Any, window_fn: Any = None) -> Dict[str, Any]:
    """Pure: the head read from the page ink at `end` ('bottom' | 'top') of a stem `(x, y_top, y_bottom)` in page px.
    Returns `{"head": bool, "why": None | reason, "trimmed", "value", "extent_sp", "oval_width_sp", "seed"}`."""
    from . import head_ink
    x, yt, yb = stem_page
    sp = float(space_px)
    seed = seed_box(x, yb if end == "bottom" else yt, end, sp)
    out: Dict[str, Any] = {"head": False, "why": None, "trimmed": None, "value": None, "extent_sp": None,
                           "oval_width_sp": None, "seed": [round(v, 1) for v in seed]}
    got = head_ink.read_head_ink(page_binary, seed, sp, foreign_boxes, slit_fn, window_fn)
    if got is None:
        out["why"] = "no_raster"
        return out
    out.update(trimmed=got.get("trimmed"), value=got.get("value"), extent_sp=got.get("extent_sp"),
               oval_width_sp=got.get("oval_width_sp"))
    if got.get("trimmed") is None:
        out["why"] = "no_head_ink"
        return out
    if got.get("not_one_head"):
        out["why"] = "not_one_head:" + str(got["not_one_head"])
        return out
    w_sp, h_sp = got["extent_sp"]
    if w_sp < h_sp or (got.get("oval_width_sp") or 0.0) < head_ink.MIN_SPACES:
        out["why"] = "not_oval"
        return out
    tx0, _ty0, tx1, _ty1 = got["trimmed"]
    cross = CROSS_SPACES * sp
    attached = (tx1 >= x - cross) if end == "bottom" else (tx0 <= x + cross)
    if not attached or at_stem_end(got["trimmed"], _PageStem(x, yt, yb), sp) != end:
        out["why"] = "not_at_stem_end"
        return out
    # Round 2 (Sean's tiles 8 and 11: part of a flat, a flag): a head's stem stands at its EDGE on the convention side (up-stem: the head's
    # right edge; down-stem: its left edge), so the head's ink never runs on past the stem by more than a stem drawn through its edge
    # (`CROSS_SPACES`, the band `at_stem_end` already allows). A flat's bowl hangs on the far side of its own stem (stem LEFT, bowl right),
    # and a flag leaves the stem tip on the far side -- the "stem" then stands INSIDE the ink. Measured, not tuned: Litolff p4 real quarter
    # 0.16 sp past, the flat 0.50, the flag 0.28 (narrow margin; the far-side reach is filed on every read for the next look).
    far = ((tx1 - x) if end == "bottom" else (x - tx0)) / sp
    out["far_side_sp"] = round(far, 3)
    if far > CROSS_SPACES:
        out["why"] = "stem_inside_the_ink"
        return out
    if got.get("value") is None:
        out["why"] = "fill_unread"
        return out
    out["head"] = True
    return out


def combine(det_box_page: Optional[Sequence[float]], ink: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    """Pure: `(verdict, why)` for one stem end -- `agree` (keep the re-run box), `ink_only` (a box on the ink), `abstain`, or `none`."""
    ink_head = bool(ink and ink.get("head"))
    if det_box_page is not None and ink_head:
        if same_ink(det_box_page, ink["trimmed"]):
            return "agree", "ink_and_rerun_same_ink"
        return "abstain", "ink_and_rerun_on_different_ink"
    if det_box_page is not None:
        return "abstain", "rerun_only_ink_reads:" + str((ink or {}).get("why"))
    if ink_head:
        return "ink_only", "ink_only"
    return "none", str((ink or {}).get("why"))


def ink_head_class(value: str, cy: float, top_y: float, half_step: float) -> str:
    """The head class for an ink-read head: its fill ('filled' black, 'hollow' half -- it has a stem) at its staff position."""
    black = black_head_class(cy, top_y, half_step)
    return black if value == "filled" else black.replace("noteheadBlack", "noteheadHalf")


# ---------------------------------------------------------------------------------------------------------------------------------------
# lane-stem-end-head ROUND 2 (Sean 2026-10-29 tiles, out/print/stem-end-head/answers.json): ink-only heads were 4/7 real; the junk was a
# bar number (Brahms p14 "263"), key-signature flats in a system's first bar (Litolff p4) and a flag.
#
# CAUSE: the ink read runs EARLY in GATHER (beside the 0.05 re-run, before every per-box reader, which must measure its box), while the
# key/clef/meter claims, the arc claim and the whole-rest tier are filed or settled LATER (the register's claims at the end of GATHER, the
# stroke owner in ADJUDICATE). The read cannot move after them without its box missing every per-box GATHER reader (positions, ink,
# ownership: the gather order rule), so the DECISION moved instead: an ink-only head is a CANDIDATE in GATHER, and ADJUDICATE
# (`notehead_precision`) refuses it where any `Q.CLAIMED_AREA` row (any owner -- so a word claim counts the day it lands) or a claiming
# tier of the stroke owner holds its ink, and writes the rest GUESSED (blue) with candidates.

#: the stroke owner's claiming families (its tier 0, and the whole rest that claims before heads, Sean 2026-10-29)
CLAIM_FAMILIES = ("clef", "meter", "key_signature", "leading_column", "arc_trace", "barline", "whole_rest")
#: share of the box held by a claim (`claims.INSIDE_SHARE_MIN`, the register's one cut, restated: this module imports nothing)
CLAIM_SHARE_MIN = 0.5


def is_ink_only(detail: Optional[Dict[str, Any]]) -> bool:
    """A `Q.GLYPH_BOX` detail of a head the page ink alone read at a stem end (`OMR_STEM_END_HEAD_INK`, verdict `ink_only`)."""
    d = detail or {}
    return d.get("source") == "stem_end_head" and d.get("ink_verdict") == "ink_only"


def _share_inside(box: Sequence[float], area: Sequence[float]) -> float:
    w, h = float(box[2]) - float(box[0]), float(box[3]) - float(box[1])
    if w <= 0 or h <= 0:
        return 0.0
    iw = min(float(box[2]), float(area[2])) - max(float(box[0]), float(area[0]))
    ih = min(float(box[3]), float(area[3])) - max(float(box[1]), float(area[1]))
    return max(0.0, iw) * max(0.0, ih) / (w * h)


def claims_holding(rows: Sequence[Any], key: str, box_page: Optional[Sequence[float]], box_strokes: Optional[Sequence[int]],
                   cell: Optional[int]) -> List[Tuple[Any, Dict[str, Any]]]:
    """Pure: every `Q.CLAIMED_AREA` row, ANY owner, that holds the box `key` -- `unit: area`: the register measured at least
    `CLAIM_SHARE_MIN` of the box's ink inside it (or named it); where it measured nothing for the box (a claim filed before the box
    existed, e.g. the barline column), the share of the box's page area inside it. `unit: ink`: at least `CLAIM_SHARE_MIN` of the
    box's strokes (`Q.GLYPH_STROKES`, ordinals of its own `cell`) are the claim's (values `[ord, ...]` of the row's cell, or the arc
    claim's `[[cell, ord], ...]`). Decides nothing."""
    out: List[Tuple[Any, Dict[str, Any]]] = []
    mine = set(int(o) for o in (box_strokes or ()))
    for r in rows or ():
        d = getattr(r, "detail", None) or {}
        v = getattr(r, "value", None)
        if not isinstance(v, (list, tuple)) or (key and d.get("owner_glyph") == key):
            continue
        if d.get("unit") == "ink":
            if not mine:
                continue
            got = set()
            for it in v:
                if isinstance(it, (list, tuple)) and len(it) == 2:
                    if cell is not None and int(it[0]) == int(cell):
                        got.add(int(it[1]))
                elif isinstance(it, (int, float)) and d.get("cell") == cell:
                    got.add(int(it))
            share = len(got & mine) / float(len(mine))
            if share >= CLAIM_SHARE_MIN:
                out.append((r, {"unit": "ink", "owner": d.get("owner"), "share": round(share, 3)}))
            continue
        if d.get("unit") != "area":
            continue
        e = (d.get("boxes_inside") or {}).get(key)
        if e:
            share, how = (1.0 if e.get("named") else float(e.get("ink_share_inside", 0.0))), "ink_share"
        elif box_page is not None and len(v) == 4:
            share, how = _share_inside(box_page, v), "box_share"
        else:
            continue
        if share >= CLAIM_SHARE_MIN:
            out.append((r, {"unit": "area", "owner": d.get("owner"), "share": round(share, 3), "how": how}))
    return out


def stroke_claim(entry: Optional[Sequence[Any]]) -> Optional[str]:
    """Pure: the stroke owner's box entry `(verdict, lost)` -> the claiming family that took the box's ink, or None: the box owns nothing
    (`refused` / `contested`) and a stroke it covers was DECIDED to a claiming family (`CLAIM_FAMILIES`)."""
    if not entry or len(entry) < 2 or entry[0] not in ("refused", "contested"):
        return None
    for x in entry[1] or ():
        if len(x) >= 3 and x[1] == "decided" and x[2] in CLAIM_FAMILIES:
            return str(x[2])
    return None
