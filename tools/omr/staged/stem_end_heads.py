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
