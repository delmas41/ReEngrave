"""ROADMAP 2.245 -- a detector box is tested against its OWN class's printed size before it stands as that kind (flag `OMR_BOX_KIND_SIZE`,
default OFF). STAGED ADJUDICATE, PURE: imports nothing from the pipeline.

THE CAUSE (benchmarks/wrong-kind-boxes-2026-10/FINDINGS.md). Sean's tiles found four marks GATHER filed as the wrong kind. In every one
the detector boxed ONE ink under several classes, and a low-confidence twin of the wrong class (0.26-0.29 in three of the four) was taken
as a mark of its class: the claim layers (the stroke owner's claimants, the page owner's marks, the system-arc reader) take a detector
box's CLASS as its KIND and never ask whether the box itself has that kind's printed size or its ink that kind's shape. Brahms p5
`glyph/5/0/4/4/15` is a `noteheadBlackOnLine` box 5.2 x 1.5 spaces -- exactly the slur four other boxes already name -- and ADJUDICATE
kept it as a head. A head is printed at most 1.69 spaces wide (SMuFL `noteheadWhole`; `noteheadBlack` 1.18): a box that wide holds no
single head.

THE RULE (this module): a head-class box at least `HEAD_BOX_MAX_W_SP` wide cannot be one head. The number is the stroke owner's own
convention size for a head's ink (`stroke_owner.HEAD_MAX_W_SP`: "a head 1.3 wide; fused to its ledger (~2.2) it is still the head's
blob"), not a cut tuned to a count: 1.8x the widest printed head. CONVENTION ASSUMED: one head is printed at most a whole note's width.
WHAT WOULD FALSIFY IT: a real single head boxed 3 or more spaces wide (a double-whole breve with its side bars is 2.5) -- Sean's tiles
in out/print/2.245-tiles. NOT CONFIRMED by Sean.

Consumer (flag ON): `adjudicate_notehead_is_not_a_notehead` refuses the box `wider_than_a_head`, LAST among its refusals (it speaks
only where every other rule would keep the box). Nothing is invented (rule 8). NOT read by the stroke owner: measured, a size veto there
lost real Litolff eighths -- a wide box over MERGED heads is the only claimant big enough to hold the fused head blob -- and where the
wide box stands on non-head ink (a slur, a beam) the per-stroke `shape_fit` already refuses it. Other lanes read the same predicate where they take a box as a mark (the page owner,
2.240; the accidental's whole-mark test, 2.242) -- see FINDINGS.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

ENV = "OMR_BOX_KIND_SIZE"
#: default OFF. Deny-list form: once the default flips to "1", only an explicit off-word disables it.
DEFAULT = "0"
OFF_WORDS = ("0", "false", "no", "off", "")

#: a head's ink is at most this wide (staff spaces): `stroke_owner.HEAD_MAX_W_SP`, the convention the owner already reads a head's
#: blob by. Read from there so the two never disagree.
from .stroke_owner import HEAD_MAX_W_SP as HEAD_BOX_MAX_W_SP  # noqa: E402

REASON_WIDE = "wider_than_a_head"


def enabled() -> bool:
    """`OMR_BOX_KIND_SIZE` (ROADMAP 2.245), default OFF."""
    return os.environ.get(ENV, DEFAULT).strip().lower() not in OFF_WORDS


def is_head_class(cls: object) -> bool:
    return str(cls or "").lower().startswith("notehead")


def head_box_misfit(cls: object, w_sp: float, h_sp: float) -> Optional[Tuple[str, float]]:
    """`(reason, margin)` when a head-class box cannot be ONE head by its own size, else None. `margin` = how far past the bound, staff
    spaces (positive = refused by this much). Not a head class, or no size: None (the rule says nothing)."""
    if not is_head_class(cls) or not w_sp or w_sp <= 0:
        return None
    if w_sp >= HEAD_BOX_MAX_W_SP:
        return REASON_WIDE, float(w_sp) - HEAD_BOX_MAX_W_SP
    return None


# ── round 2 (Sean 2026-10-31 "Send back for a second round") ─────────────────────────────────────────────────────────────────────────────
# 1. A WIDE HEAD BOX IS READ, NOT REFUSED FLAT. Sean's tiles 4 ("an eighth and a natural") and 10 ("three eighth notes") hold real notes.
#    GATHER reads the head-shaped ink INSIDE the box (`head_blobs`): the staff-erased raster opened by a kernel thicker than a stem, a
#    natural's or an arc's line and a beam's ~0.5, but thinner than a head, so only head-thick blobs survive. Each found head no other head
#    box of the cell already stands on gets its OWN box (`split_wide_heads`, appended after the detector's boxes: every existing glyph
#    index is unchanged). The wide box is then the REMAINDER and ADJUDICATE refuses it (`wider_than_a_head`); where the inside is not
#    readable (head-thick ink bigger than one head: fused heads) ADJUDICATE abstains and counts it (`wide_box_unread`, rule 8).

#: the opening kernel (staff spaces). CONVENTION ASSUMED (engraving sizes: a beam ~0.5 thick, a stem / natural / arc line ~0.1-0.2, a
#: filled head ~1.0 tall). WHAT WOULD FALSIFY IT: a beam thicker than 0.7 sp survives the opening -- the size window below still refuses
#: it as a head unless it is head-sized.
OPEN_SP = 0.7
#: a found blob is ONE head when its size is a head's (SMuFL noteheadBlack 1.18 x 1.0; the stroke owner's HEAD_MAX_H_SP 1.6)
HEAD_BLOB_W_SP = (0.8, 2.0)
HEAD_BLOB_H_SP = (0.65, 1.6)
REASON_UNREAD = "wide_box_unread"


def head_blobs(ink, sp: float):
    """`(blobs, unread)`: the head-sized ink blobs (x, y, w, h, crop px) of a boolean ink crop (True = ink) after an opening `OPEN_SP`
    across; `unread` = a surviving blob too big for one head (fused heads: how many cannot be told)."""
    import numpy as np
    import cv2
    ink = np.asarray(ink, dtype=np.uint8)
    if sp <= 0 or ink.size == 0 or not ink.any():
        return [], False
    k = max(3, int(round(OPEN_SP * sp)))
    op = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, _lab, stats, _ = cv2.connectedComponentsWithStats(op, connectivity=8)
    blobs, unread = [], False
    for i in range(1, n):
        x, y, w, h = (int(v) for v in stats[i, :4])
        ws, hs = w / sp, h / sp
        if HEAD_BLOB_W_SP[0] <= ws <= HEAD_BLOB_W_SP[1] and HEAD_BLOB_H_SP[0] <= hs <= HEAD_BLOB_H_SP[1]:
            blobs.append((x, y, w, h))
        elif ws > HEAD_BLOB_W_SP[1] or hs > HEAD_BLOB_H_SP[1]:
            unread = True
    return blobs, unread


def _inside(px: float, py: float, d) -> bool:
    return d.x_canonical <= px <= d.x_canonical + d.width_canonical and d.y_canonical <= py <= d.y_canonical + d.height_canonical


def split_wide_heads(dets, img_no_staff, sp: float):
    """GATHER, flag ON: `(dets_out, info)`. `dets_out` = `dets` unchanged and in order, plus one new detection per head found inside a
    wide head box that no other (not wide) head box of the cell stands on (the wide box's class and confidence). `info` = {index: detail}
    for the GLYPH_BOX rows: on a wide box `{"box_kind": {"heads": n, "added": [...], "unread": bool}}`, on an added box
    `{"box_kind": {"split_from": index}}`. No raster or no unit: nothing changes (no `box_kind` on the row: ADJUDICATE abstains)."""
    import dataclasses
    import numpy as np
    out = list(dets)
    info = {}
    if img_no_staff is None or not sp or sp <= 0:
        return out, info
    img = np.asarray(img_no_staff)
    if img.ndim != 2:
        return out, info
    narrow_heads = [d for d in dets if is_head_class(d.smufl_name) and d.width_canonical / sp < HEAD_BOX_MAX_W_SP]
    for i, d in enumerate(dets):
        if not is_head_class(d.smufl_name) or d.width_canonical / sp < HEAD_BOX_MAX_W_SP:
            continue
        x0, y0 = max(0, int(d.x_canonical)), max(0, int(d.y_canonical))
        x1 = min(img.shape[1], int(d.x_canonical + d.width_canonical))
        y1 = min(img.shape[0], int(d.y_canonical + d.height_canonical))
        if x1 <= x0 or y1 <= y0:
            continue
        blobs, unread = head_blobs(img[y0:y1, x0:x1] == 0, sp)
        added = []
        for (bx, by, bw, bh) in blobs:
            cx, cy = x0 + bx + bw / 2.0, y0 + by + bh / 2.0
            if any(_inside(cx, cy, o) for o in narrow_heads):
                continue
            out.append(dataclasses.replace(d, x_canonical=int(x0 + bx), y_canonical=int(y0 + by), width_canonical=int(bw),
                                           height_canonical=int(bh)))
            info[len(out) - 1] = {"box_kind": {"split_from": i}}
            added.append(len(out) - 1)
        info[i] = {"box_kind": {"heads": len(blobs), "added": added, "unread": bool(unread)}}
    return out, info


# 3. AN ARC BOWS. A tie or slur is a curve; a straight trace 3+ spaces long is a hairpin's leg or a beam (Sean's 2.245 tiles 6, 7, 11:
#    3/3 "part of a hairpin"). Read by the system-arc reader (`arcs_system.gather_system_arcs`) before it files an arc.
ARC_MIN_LEN_SP = 3.0
#: measured on the frozen sample (`benchmarks/wrong-kind-boxes-2026-10/straight_arcs.py`): 18 of the 19 Brahms traces under this bow
#: over 3+ sp are hairpin legs (the 19th and Litolff's one: a cut arc piece). A cut measured on two plates: it only REFUSES the arc
#: (the trace is not filed as an arc), never reads the ink as anything else.
ARC_MIN_BOW_SP = 0.15
REASON_STRAIGHT = "trace_does_not_bow"


def trace_bow(trace, sp: float):
    """`(length_sp, bow_sp)` of a `Q.SYSTEM_ARC` trace `[[x, y_top, y_bottom], ...]`: the centre line's largest distance from its chord."""
    if not trace or len(trace) < 2 or not sp:
        return 0.0, 0.0
    xs = [float(t[0]) for t in trace]
    cs = [(float(t[1]) + float(t[2])) / 2.0 for t in trace]
    span = max(1.0, xs[-1] - xs[0])
    bow = max(abs(c - (cs[0] + (cs[-1] - cs[0]) * (x - xs[0]) / span)) for x, c in zip(xs, cs))
    return (xs[-1] - xs[0]) / sp, bow / sp


def trace_is_not_an_arc(trace, sp: float) -> bool:
    length, bow = trace_bow(trace, sp)
    return length >= ARC_MIN_LEN_SP and bow < ARC_MIN_BOW_SP


# 4. A HAIRPIN IS WIDER THAN A LETTER. Every CV hairpin row narrower than this on the frozen sample is a letter ('c' of cresc., 'e' of
#    legato, 'B' of Basso: 9 of 9 on crops, Litolff 0.83-1.46 sp, Brahms 0.81-0.97 sp); the narrowest other row is 2.02 sp. A cut measured on
#    two plates, in that gap: it only REFUSES the reading (the row is not filed as a hairpin), never reads the ink as a word.
HAIRPIN_MIN_W_SP = 1.6
REASON_LETTER = "narrower_than_a_hairpin"
