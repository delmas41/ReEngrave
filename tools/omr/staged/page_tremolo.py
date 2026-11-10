"""ROADMAP 2.276 -- TREMOLO SLASHES READ ONCE ON THE PAGE, THEIR INK CLAIMED ONCE (STAGED GATHER; flag `OMR_PAGE_TREMOLO`, default ON (Sean 2026-11-09 "Land"; "0" turns it off)).

    Sean 2026-11-08: "I don't think we have tackled trem slashes yet. I think that should be a CV treatment on the page read."
    benchmarks/tremolo-claim-2026-11/FINDINGS.md; CLAUDE section 3 (claim order: a later reader may mark claimed ink but never take it).

CAUSE. A tremolo slash had no page claim: the detector has `tremolo1`-`5` classes and has never fired one (0 of 34,115 detections), so the slash's ink was
only ever a detector NOTEHEAD box (or a flag / beam / rest box) per cell, and a per-head rule (2.49 / 2.71 / 2.137 / 2.270) refused each box afterwards,
one by one, reading a per-cell per-stem row (`Q.STEM_SLASH`) that twin cells read twice. LESSON: a mark the detector cannot box must be read by the page
pass; leaving it to the per-box refusals means every later reader meets the ink first.

WHAT. The slash finder GATHER already owned (`gather.stem_slashes`, 2.71) run ONCE per page on the page raster (`page_strokes` canvas, staff lines erased), over the
page map's vertical strokes (a stem is one stroke on the page, so a stem two padded cells both saw is read once). A slash is the ink out of BOTH sides of a stem
on one thick line at an angle. Nothing in it tests the ENDS (page-facts: a slash is square-cut, a head round): 2.214 showed the stroke is not the mark, so
the ends cannot be read off a stroke the stem cut trimmed; this reader is the crossing reader of 2.71, claimed.

ORDER (benchmarks/tremolo-claim-2026-11/RULES.md, pre-registered; FINDINGS holds the result). The reader is handed the detector's notehead boxes ("after the noteheads":
`stem_slashes`' own `at_a_head` veto), because read blind to them it took 15 real heads on six pages (Litolff 6/13/16, Brahms 12/15/16) that read with them it did not. The CLAIM is
still filed BEFORE the head claim and the layer "tremolo" stands before "head" in `claim_order.LAYERS`: a head box standing on a slash's ink is a LATER box than the claim, so
the one generic rule (ROADMAP 2.277: a later box whose ink an earlier claim holds is refused BY that claim) consumes it with no special code. No reader here refuses a head box.

ROUND 3 (Sean 2026-11-09 tiles 5, 6, 10: a beam piece and two dynamic p's claimed or nearly claimed as slashes). CAUSE: the finder was handed the detector's NOTEHEAD boxes only, but
Sean's reading order (2026-10-16: notehead, stem, beam or flag, shared stem, then "trem slash or anything else" that never overturns an earlier answer) and the claim order (dynamics
first) put a beam, a flag and a dynamic BEFORE a slash. Both marks WERE read (the detector's `beam` box and `dynamicP` letter box cover 0.89 / 0.96 of the candidate) and nobody CLAIMED
them first: a letter inside a staff's line band is "milestone 4" for the word claim (counted, not claimed), and no page-wide beam claim stands before this one (`page_beams` is OFF and
runs after). LESSON: the order micro test handed the reader one earlier family (heads) because heads were the question; the residue it listed ("a p, two small marks") was the other
families. FIX AT THE SOURCE: `held_boxes` hands the finder every earlier read of those families and a candidate with `HELD_SHARE_MIN` (the register's cut, 0.5) of its box inside one is refused
(`held_by_earlier_read`): it never takes ink an earlier mark's read holds. No angle or thickness cut is touched. Measured on the 12 r2 tiles: the 9 real slashes are covered 0.00 by any such box.

WHAT IT FILES (a claim, nothing else). One `Q.CLAIMED_AREA` row per slash, on the page's subject: value = the page stroke ordinals the slash's ink owns (`[]` where the
slash is fused with ink the map did not cut), `detail`: `owner` "tremolo", `unit` "page_ink", `standing` "READ", `source` "page_tremolo", `page_strokes`, `area`
(the slash's page box), `centreline`, `stem` (the stem stroke's ordinal), `angle_deg`, `thickness_px`, `thickness_ratio`. The census (stems read, slashes, each refusal reason) is printed
with `--progress`, not filed (nothing reads it; the wiring check would list it). `claim_order.LAYERS` carries the owner as the layer "tremolo". It decides no meaning: a slash is never a note, a value or a
rest, and is not bound to the stem's note (a later step).

CONVENTION ASSUMED (2.71, Sean 2026-10-09/15): a slash is a thick angled line crossing both sides of one stem. WHAT WOULD FALSIFY IT: a real notehead pair either side of a stem
(a second) read as a slash. NOT CONFIRMED beyond the two plates.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

DERIVED_CHECK = False
ENV = "OMR_PAGE_TREMOLO"
OWNER = "tremolo"
UNIT = "page_ink"
SOURCE = "page_tremolo"
#: a vertical page stroke is a stem for this reader from this length (`page_heads.STEM_MIN_LEN_SP`: 1.5)
STEM_MIN_LEN_SP = 1.5
#: a stroke the slash's box holds this much of (its own box's area inside the slash's box) is the slash's (the register's cover cut, `claims.INSIDE_SHARE_MIN`)
OWN_SHARE_MIN = 0.5
#: other stems near this one (spaces either side) that the finder's `joins_another_stem` test looks at
NEIGHBOUR_SPACES = 6.0
HEAD_PREFIX = "notehead"
#: ROADMAP 2.276 r3 (Sean 2026-10-16, the reading order: notehead, stem, beam or flag, shared stem, THEN "trem slash or anything else -- a later step reads the earlier
#: steps' answers and never overturns them"; CLAUDE section 3, dynamics claim first): the detector's reads of marks that stand EARLIER in that order than a slash and
#: that the finder was never handed in r2 -- a dynamic LETTER (`gather._DYNAMIC_LETTER_CLASSES`), a `beam`, a flag (`flag*`). A candidate with at least `HELD_SHARE_MIN`
#: of its own box inside one of their boxes is that mark's ink, not a slash. The cut is the register's own (`claims.INSIDE_SHARE_MIN`, 0.5), not a number tuned here.
BEAM_CLASS = "beam"
FLAG_PREFIX = "flag"
HELD_SHARE_MIN = 0.5
#: ROADMAP 2.276 r2 (Sean 2026-11-09: "could never be a trem slash because it is on the opposite side of the end of the stem"): the stem END test, from ink alone.
#: A head end is a heavy blob beside the stem within `END_ZONE_SP` of the stem's end: on one side at least `END_MIN_ROWS_SP` of rows wide (a row holding
#: `END_ROW_SP` of ink), `END_MIN_AREA_SP2` of ink, reaching less than `END_MAX_REACH_SP` (a beam or a neighbour runs on to the window's edge).
END_ZONE_SP = 1.4
END_WINDOW_SP = 1.7
END_ROW_SP = 0.6
END_MIN_ROWS_SP = 0.9
END_MIN_AREA_SP2 = 1.0
END_MAX_REACH_SP = 1.69


def enabled() -> bool:
    return os.environ.get(ENV, "1").strip().lower() not in ("0", "false", "no", "off")


def stems_of(strokes: Sequence[Any]) -> List[Tuple[int, Tuple[float, float, float, float]]]:
    """`(ordinal, (x, y, w, h))` of every vertical page stroke at least `STEM_MIN_LEN_SP` long, page px."""
    out = []
    for i, s in enumerate(strokes):
        if s.kind == "vertical" and s.length_sp >= STEM_MIN_LEN_SP:
            x, y, w, h = s.box
            out.append((i, (float(x), float(y), float(w), float(h))))
    return out


def _end_blob(ink: Any, stem: Tuple[float, float, float, float], sp: float, end: str) -> bool:
    """True where `end` ("top" / "bottom") of the stem carries a heavy blob to one side (module doc, END_*): the ink of a head, measured on the page raster.
    Pure; a window the page edge cuts reads what is there."""
    import numpy as np
    x, y, w, h = stem
    H, W = ink.shape
    x0, x1 = int(round(x)), int(round(x + w))
    pad, zone, slack = int(round(END_WINDOW_SP * sp)), int(round(END_ZONE_SP * sp)), int(round(0.3 * sp))
    e = int(round(y)) if end == "top" else int(round(y + h))
    ya, yb = (e - slack, e + zone) if end == "top" else (e - zone, e + slack)
    ya, yb = max(0, ya), min(H, yb)
    for side in ("L", "R"):
        a = ink[ya:yb, max(0, x0 - pad):max(0, x0)] if side == "L" else ink[ya:yb, min(W, x1 + 1):min(W, x1 + 1 + pad)]
        if a.size == 0:
            continue
        cols = np.nonzero(a.any(axis=0))[0]
        if not len(cols):
            continue
        rows = int((a.sum(axis=1) >= END_ROW_SP * sp).sum())
        reach = ((a.shape[1] - cols.min()) if side == "L" else (cols.max() + 1)) / sp
        if rows >= END_MIN_ROWS_SP * sp and float(a.sum()) / (sp * sp) >= END_MIN_AREA_SP2 and reach <= END_MAX_REACH_SP:
            return True
    return False


def head_end_verdict(ink: Any, stem: Tuple[float, float, float, float], slash_y: float, sp: float) -> str:
    """The stem end test (module doc): "refuse" where the slash's centre `slash_y` lies within `END_ZONE_SP` of the stem's HEAD end or past it, "ok" where the head end
    was told and the slash lies on the shaft away from it, "abstain" where the ink cannot tell the head end (a blob at both ends: a chord or a fused neighbour; at neither).
    It never refuses on a guess."""
    x, y, w, h = stem
    top, bot = _end_blob(ink, stem, sp, "top"), _end_blob(ink, stem, sp, "bottom")
    if top == bot:
        return "abstain"
    if top:
        return "refuse" if slash_y <= y + END_ZONE_SP * sp else "ok"
    return "refuse" if slash_y >= y + h - END_ZONE_SP * sp else "ok"


def held_share(box: Sequence[float], held: Sequence[Tuple[float, float, float, float]]) -> float:
    """The largest share of `box` `(x0, y0, x1, y1)` that lies inside one box of `held` (`(x, y, w, h)` page px). Pure."""
    area = max(1e-9, (box[2] - box[0]) * (box[3] - box[1]))
    best = 0.0
    for hx, hy, hw, hh in held:
        ix = min(box[2], hx + hw) - max(box[0], hx)
        iy = min(box[3], hy + hh) - max(box[1], hy)
        if ix > 0 and iy > 0:
            best = max(best, ix * iy / area)
    return best


def read_page(ink: Any, stems: Sequence[Tuple[int, Tuple[float, float, float, float]]], heads: Sequence[Tuple[float, float, float, float]], sp: float, line_px: float,
              held: Sequence[Tuple[float, float, float, float]] = ()) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """The finder over every stem of the page. `ink` is the page raster as a bool array (True = ink); `heads` are `(x, y, w, h)` page px boxes of the detector's noteheads
    (empty = order A: the finder knows no head). Returns the passing slashes (each with its stem's ordinal) and the refusal-reason counts. Pure."""
    from .gather import stem_slashes
    slashes: List[Dict[str, Any]] = []
    reasons: Dict[str, int] = {}
    reach = NEIGHBOUR_SPACES * sp
    for k, (ordn, box) in enumerate(stems):
        near = [b for j, (_o, b) in enumerate(stems)
                if j != k and abs((b[0] + b[2] / 2.0) - (box[0] + box[2] / 2.0)) <= reach and b[1] <= box[1] + box[3] + sp and b[1] + b[3] >= box[1] - sp]
        got = stem_slashes(ink, box, sp, line_px, near, heads)
        for s in got:
            r = s.get("reason")
            reasons[str(r)] = reasons.get(str(r), 0) + 1
            if r is None and held_share(s["box"], held) >= HELD_SHARE_MIN:
                reasons["held_by_earlier_read"] = reasons.get("held_by_earlier_read", 0) + 1
                continue
            if r is None:
                verdict = head_end_verdict(ink, box, float(s.get("y", 0.0)), sp)
                reasons["end:" + verdict] = reasons.get("end:" + verdict, 0) + 1
                if verdict == "refuse":
                    reasons["at_head_end"] = reasons.get("at_head_end", 0) + 1
                    continue
                d = {kk: v for kk, v in s.items() if not kk.startswith("_")}
                d["stem"] = ordn
                d["stem_box"] = list(box)
                slashes.append(d)
    return slashes, reasons


def own_strokes(slash: Dict[str, Any], boxes: Sequence[Sequence[float]], kinds: Sequence[str], stem: int) -> List[int]:
    """The page strokes the slash's ink owns: a stroke that is not the stem, not a vertical or a rule, and whose own box lies at least `OWN_SHARE_MIN` inside the slash's box."""
    sx0, sy0, sx1, sy1 = slash["box"]
    out = []
    for i, b in enumerate(boxes):
        if i == stem or kinds[i] in ("vertical", "barline"):
            continue
        x0, y0, x1, y1 = b
        ix, iy = min(x1, sx1) - max(x0, sx0), min(y1, sy1) - max(y0, sy0)
        a = max(1e-9, (x1 - x0) * (y1 - y0))
        if ix > 0 and iy > 0 and ix * iy / a >= OWN_SHARE_MIN:
            out.append(i)
    return out


def _detector_boxes(cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]], keep: Any) -> List[Tuple[float, float, float, float]]:
    """Every detector box of the page whose class `keep(smufl_name)` accepts, `(x, y, w, h)` page px (twins from two cells stay twins: the finder asks only where a box lies)."""
    from .record import Subject
    from .gather import _page_box
    cell_by_key = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    out = []
    for ck, dets in detections.items():
        sub = Subject.from_key(ck)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        for d in dets:
            if not keep(str(d.smufl_name)):
                continue
            pb = _page_box(c, d)
            if pb is not None:
                out.append((float(pb[0]), float(pb[1]), float(pb[2] - pb[0]), float(pb[3] - pb[1])))
    return out


def head_boxes(pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]]) -> List[Tuple[float, float, float, float]]:
    """Every detector notehead box of the page, `(x, y, w, h)` page px."""
    return _detector_boxes(cells, local, detections, lambda n: n.startswith(HEAD_PREFIX))


def held_boxes(pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]]) -> List[Tuple[float, float, float, float]]:
    """The detector's reads of marks that stand before a slash in the reading order (module doc, `HELD_SHARE_MIN`): dynamic letters, beams, flags."""
    from .gather import _DYNAMIC_LETTER_CLASSES
    return _detector_boxes(cells, local, detections, lambda n: n in _DYNAMIC_LETTER_CLASSES or n == BEAM_CLASS or n.startswith(FLAG_PREFIX))


def gather_page_tremolo(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]], pm: Any, *,
                        file: bool = True, progress: bool = False) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.276 (flag `OMR_PAGE_TREMOLO`, default ON (Sean 2026-11-09 "Land"; "0" turns it off)), STAGED GATHER. Reads the page's slashes once and files their claims (module doc). `file=False` reads only.
    Returns `(slashes, reasons)`, or None where the flag is off or there is no page map."""
    if not enabled() or pm is None or not getattr(pm, "strokes", None):
        return None
    import numpy as np
    from . import record as R
    from .record import Q, READERS
    from .gather import FRAME_PAGE
    t0 = time.time()
    p = int(getattr(pws.page, "page_index", 0))
    sub = R.page(p)
    ink = pm.assembly.canvas == 0
    sp = float(pm.sp)
    thick = [float(getattr(s, "median_line_thickness_px", 0) or 0) for s in pws.staves]
    line_px = float(np.median([t for t in thick if t > 0])) if any(t > 0 for t in thick) else 0.0
    stems = stems_of(pm.strokes)
    heads = head_boxes(pws, cells, local, detections)
    held = held_boxes(pws, cells, local, detections)
    res = read_page(ink, stems, heads, sp, line_px, held)
    boxes = [(float(s.box[0]), float(s.box[1]), float(s.box[0] + s.box[2]), float(s.box[1] + s.box[3])) for s in pm.strokes]
    kinds = [s.kind for s in pm.strokes]
    seconds = round(time.time() - t0, 2)
    if not file:
        return res
    slashes, reasons = res
    for s in slashes:
        won = own_strokes(s, boxes, kinds, s["stem"])
        log.observe(sub, Q.CLAIMED_AREA, won, reader=READERS.CV_PAGE_TREMOLO, frame=FRAME_PAGE, owner=OWNER, unit=UNIT, standing="READ", source=SOURCE,
                    how="stem_slash", page_strokes=won, contested=[], area=[round(float(v), 1) for v in s["box"]], centreline=s.get("centreline"), stem=s["stem"],
                    stem_box=s["stem_box"], angle_deg=s.get("angle_deg"), thickness_px=s.get("thickness_px"), thickness_ratio=s.get("thickness_ratio"))
    if progress:
        ends = {"told": 0, "both": 0, "neither": 0}
        for _o, b in stems:
            t, bt = _end_blob(ink, b, sp, "top"), _end_blob(ink, b, sp, "bottom")
            ends["told" if t != bt else "both" if t else "neither"] += 1
        print("  gather page tremolo p%s: %d slashes of %d stems, %d heads known, %d earlier reads held, refusals %s, head end told/both/neither %s, %s s"
              % (p, len(slashes), len(stems), len(heads), len(held), reasons, ends, seconds))
    return res
