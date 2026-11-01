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
# 1. A WIDE HEAD BOX IS READ FOR HEADS OF A HEAD'S OWN SHAPE (round 3, Sean 2026-10-31 "Rework it all together - get it solid then land").
#    Round 2 opened the ink with a 0.7 sp disc and kept any head-SIZED blob. Sean's r2 tiles: 2 of 4 split heads right (5, 8); wrong 2 --
#    a flag's curl at a stem tip (tile 2) and a C clef's bowl (tile 10), both thick enough to survive the opening and head-sized; and two
#    refused remainders held real notes (tile 3 a head under a slur, tile 6 a HALF note: its ring is thinner than the disc, so the opening
#    erased it). CAUSE: size is not shape -- a blob was taken as a head because it was head-SIZED; a head is also head-SHAPED, on the staff
#    grid, and not at a stem's flag end or inside a clef. So, per blob (in the cell's canonical px, the cell's own staff space):
#      * holes are FILLED before the opening, so a hollow head's ring becomes a solid oval and survives (filled and hollow heads alike);
#      * SIZE: 0.9-1.9 x 0.7-1.5 sp; SHAPE: fills >= 0.6 of its box (an oval fills ~0.79; a flag's curl or a clef bowl's crescent less),
#        width/height 0.9-2.2;
#      * GRID: its centre on a line or space position (within `GRID_TOL_STEPS` of a half-step), measured on the cell's own lines;
#      * NOT A FLAG: a stem touching it whose OTHER end holds a head (a detector head box or another found head) -- the flag hangs off the
#        stem's end, the head sits at the other end (page-facts: stems);
#      * NOT A CLEF: no detector clef box over it, and its own ink holds no THICK vertical bar (`CLEF_BAR_SP` thick, `CLEF_BAR_LEN_SP`
#        tall: a C clef's bars, a double barline; a stem is ~0.15 thick).
#    A blob that passes every test is a head: added as its own box unless a head box already stands on it. A head-sized blob that fails the
#    grid, or is vetoed as a flag or clef piece, or a fused blob bigger than one head, makes the box UNREAD: it abstains (`wide_box_unread`)
#    and EXPORT writes no note for it (rhythm's duration abstains). The box is REFUSED as the remainder only when every head-shaped blob
#    inside it is accounted for (added, or under its own head box) and nothing unsure is left -- a remainder never takes a head with it.

OPEN_SP = 0.7
LINE_GAP_SP = 0.3
#: the remainder's harder look: a hollow head's ring opened on both sides by the staff-line erase closes at this size
REMAINDER_CLOSE_SP = 0.45
#: ... and the ink in that core's box is a head's (a ring is ~half ink; a slur closed onto a line remnant encloses mostly paper)
REMAINDER_INK_MIN = 0.3
HEAD_BLOB_W_SP = (0.9, 1.9)
HEAD_BLOB_H_SP = (0.7, 1.5)
HEAD_FILL_MIN = 0.6
HEAD_ASPECT = (0.9, 2.2)
GRID_TOL_STEPS = 0.3
STEM_MIN_SP = 2.5
CLEF_BAR_SP = 0.35
CLEF_BAR_LEN_SP = 2.5
CLEF_NEAR_SP = 0.6
REASON_UNREAD = "wide_box_unread"


def _runs_vertical(mask, min_len):
    """Columns' vertical runs of ink at least `min_len` px: [(x, y0, y1)]."""
    import numpy as np
    out = []
    for x in range(mask.shape[1]):
        col = mask[:, x]
        if not col.any():
            continue
        d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
        for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if b - a >= min_len:
                out.append((x, int(a), int(b)))
    return out


def _stem_xs(stems, sp):
    """Cluster vertical-run columns into stems: [(x_centre, y0, y1)]."""
    out = []
    for x, a, b in sorted(stems):
        if out and x - out[-1][3] <= max(2, 0.1 * sp) and min(b, out[-1][2]) > max(a, out[-1][1]):
            px0, py0, py1, _px1 = out[-1]
            out[-1] = (px0, min(py0, a), max(py1, b), x)
        else:
            out.append((x, a, b, x))
    return [((s[0] + s[3]) / 2.0, s[1], s[2]) for s in out]


#: a hollow head's hole is at most this big (staff spaces^2 / side): only holes this small are filled -- the paper a beam, two stems
#: and a row of heads enclose is NOT a head's hole (round 3: filling it fused Litolff's three beamed eighths into one block)
HOLE_MAX_SP2 = 0.6
HOLE_MAX_SIDE_SP = 1.1


def _fill_small_holes(mask, sp):
    import numpy as np
    from scipy import ndimage as ndi
    holes = ndi.binary_fill_holes(mask) & ~mask
    lab, n = ndi.label(holes)
    out = mask.copy()
    if n:
        sl = ndi.find_objects(lab)
        areas = ndi.sum(holes, lab, index=np.arange(1, n + 1))
        for i, (s_, a) in enumerate(zip(sl, areas), 1):
            hh, ww = s_[0].stop - s_[0].start, s_[1].stop - s_[1].start
            if a <= HOLE_MAX_SP2 * sp * sp and max(hh, ww) <= HOLE_MAX_SIDE_SP * sp:
                out[s_] |= (lab[s_] == i)
    return out


def read_heads(ink, sp: float, staff_top: float, origin=(0, 0), head_boxes=(), clef_boxes=(), box=None):
    """Head-shaped blobs in a boolean ink region (True = ink). `origin` = the region's top-left in cell px; `box` = (x0, y0, x1, y1) of the
    wide box in cell px (only blobs centred inside it count); `head_boxes` = (x0, y0, x1, y1) of the cell's own (not wide) head boxes;
    `clef_boxes` = the cell's detector clef boxes. Returns `(heads, unread, vetoed, covered)`: heads as (x, y, w, h, hollow) in cell px;
    unread True when something head-like could not be read; vetoed = [(x, y, w, h, why)]; covered = blobs a head box already stands on."""
    import numpy as np
    import cv2
    from scipy import ndimage as ndi
    ink = np.asarray(ink, dtype=bool)
    if sp <= 0 or not ink.any():
        return [], False, [], []
    ox, oy = origin
    # a hollow head on a line loses part of its ring to the staff-line erase: bridge gaps a staff line thick (vertically) before filling
    gap = max(2, int(round(LINE_GAP_SP * sp)))
    closed = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, gap))) > 0
    filled = _fill_small_holes(closed, sp)
    # CORES: erode by a disc thinner than a head and thicker than a beam / stem / arc; each core is grown back on its own
    k = max(3, int(round(OPEN_SP * sp)))
    disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    lab, n = ndi.label(cv2.erode(filled.astype(np.uint8), disc) > 0)
    r = k // 2
    comp_lab, _ = ndi.label(ink, structure=np.ones((3, 3)))
    stems = _stem_xs(_runs_vertical(ink, int(STEM_MIN_SP * sp)), sp)
    bar_k = cv2.getStructuringElement(cv2.MORPH_RECT, (max(2, int(round(CLEF_BAR_SP * sp))), max(3, int(round(CLEF_BAR_LEN_SP * sp)))))
    heads, vetoed, covered, unread = [], [], [], False
    half = sp / 2.0
    hb = [tuple(b) for b in head_boxes]

    def in_box(px, py, b):
        return b[0] <= px <= b[2] and b[1] <= py <= b[3]

    cands = []
    for i in range(1, n + 1):
        cys, cxs = np.nonzero(lab == i)
        x0, x1 = max(0, cxs.min() - r), min(ink.shape[1], cxs.max() + 1 + r)
        y0, y1 = max(0, cys.min() - r), min(ink.shape[0], cys.max() + 1 + r)
        ws, hs = (x1 - x0) / sp, (y1 - y0) / sp
        if ws > HEAD_BLOB_W_SP[1] and HEAD_BLOB_H_SP[0] <= hs <= HEAD_BLOB_H_SP[1]:
            # MERGED heads in a row (Litolff): a band one head tall whose stems stand at a head's spacing is that many heads, cut at
            # the middles between its stems; otherwise it stays one blob (and is unread below)
            sx = sorted(s[0] for s in stems if x0 - 0.3 * sp <= s[0] <= x1 + 0.3 * sp
                        and (abs(s[1] - y0) <= 0.5 * sp or abs(s[2] - y1) <= 0.5 * sp or y0 <= s[1] <= y1 or y0 <= s[2] <= y1))
            if len(sx) >= 2 and all(HEAD_BLOB_W_SP[0] * sp <= b - a <= HEAD_BLOB_W_SP[1] * sp for a, b in zip(sx, sx[1:])):
                cuts = [x0] + [int((a + b) / 2.0) for a, b in zip(sx, sx[1:])] + [x1]
                cands.extend((a, y0, b, y1, True) for a, b in zip(cuts, cuts[1:]))
                continue
        cands.append((x0, y0, x1, y1, False))
    for x0, y0, x1, y1, cut in cands:
        w, h = x1 - x0, y1 - y0
        cx, cy = ox + (x0 + x1) / 2.0, oy + (y0 + y1) / 2.0
        if box is not None and not in_box(cx, cy, box):
            continue
        ws, hs = w / sp, h / sp
        if ws < HEAD_BLOB_W_SP[0] * 0.7 and hs < HEAD_BLOB_H_SP[0] * 0.7:
            continue                                               # a crumb: nothing
        rec = (int(ox + x0), int(oy + y0), int(w), int(h))
        if any(in_box(cx, cy, b) for b in hb):
            covered.append(rec)                                    # its own head box stands on it: accounted for
            continue
        if ws > HEAD_BLOB_W_SP[1] or hs > HEAD_BLOB_H_SP[1]:
            unread = True                                          # head-thick ink bigger than one head
            vetoed.append(rec + ("bigger_than_a_head",))
            continue
        if not (HEAD_BLOB_W_SP[0] <= ws and HEAD_BLOB_H_SP[0] <= hs):
            continue                                               # smaller than a head: not a head
        sub = filled[y0:y1, x0:x1]
        fill = float(sub.sum()) / float(max(1, w * h))
        aspect = ws / hs
        if not cut and (fill < HEAD_FILL_MIN or not (HEAD_ASPECT[0] <= aspect <= HEAD_ASPECT[1])):
            unread = True
            vetoed.append(rec + ("not_head_shaped",))
            continue
        pos = (cy - staff_top) / half
        if abs(pos - round(pos)) > GRID_TOL_STEPS:
            unread = True
            vetoed.append(rec + ("off_the_staff_grid",))
            continue
        if any(in_box(cx, cy, b) for b in clef_boxes):
            unread = True
            vetoed.append(rec + ("in_a_clef_box",))
            continue
        ys, xs = np.nonzero(sub & ink[y0:y1, x0:x1])
        comp_ids = set(np.unique(comp_lab[ys + y0, xs + x0])) - {0}
        comp = np.isin(comp_lab, list(comp_ids))
        # only the ink beside the blob (a clef's bar stands within a space of its bowl; a beamed group's far stems, a barline do not count)
        nx0, nx1 = max(0, int(x0 - CLEF_NEAR_SP * sp)), min(ink.shape[1], int(x1 + CLEF_NEAR_SP * sp))
        if cv2.morphologyEx(comp[:, nx0:nx1].astype(np.uint8), cv2.MORPH_OPEN, bar_k).any():
            unread = True
            vetoed.append(rec + ("thick_bar_in_its_ink",))
            continue
        flag = False
        others = [((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0) for b in hb] + [(hx + hw / 2.0, hy + hh / 2.0) for hx, hy, hw, hh, _ in heads]
        for sxc, sy0, sy1 in stems:
            if not (x0 - 0.3 * sp <= sxc <= x1 + 0.3 * sp):
                continue
            at_top = abs(sy0 - y0) <= 0.4 * sp or y0 <= sy0 <= y1
            at_bottom = abs(sy1 - y1) <= 0.4 * sp or y0 <= sy1 <= y1
            if not (at_top or at_bottom):
                continue
            far_y = oy + (sy1 if at_top else sy0)
            if any(abs(hx - (ox + sxc)) <= 1.2 * sp and abs(hy - far_y) <= 1.0 * sp for hx, hy in others):
                flag = True
                break
        if flag:
            unread = True
            vetoed.append(rec + ("flag_end_of_a_stem",))
            continue
        hollow = bool((sub & ~ink[y0:y1, x0:x1]).sum() > 0.15 * max(1, sub.sum()))
        heads.append(rec + (hollow,))
    if not unread and box is not None:
        # THE REMAINDER MAY NOT TAKE A HEAD WITH IT (round 3, Sean's tiles 3 and 6): close harder (a hollow head whose ring the line erase
        # opened on both sides, tile 6's half), fill, and look for a head-sized core no found or covered head explains -> unread
        k2 = max(3, int(round(REMAINDER_CLOSE_SP * sp)))
        f2 = _fill_small_holes(cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE,
                                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k2, k2))) > 0, sp)
        lab2, n2 = ndi.label(cv2.erode(f2.astype(np.uint8), disc) > 0)
        known = [(hx, hy, hx + hw, hy + hh) for hx, hy, hw, hh, _ in heads] + [(c[0], c[1], c[0] + c[2], c[1] + c[3]) for c in covered] + hb
        for i in range(1, n2 + 1):
            cys, cxs = np.nonzero(lab2 == i)
            x0, x1, y0, y1 = cxs.min() - r, cxs.max() + 1 + r, cys.min() - r, cys.max() + 1 + r
            cx, cy = ox + (x0 + x1) / 2.0, oy + (y0 + y1) / 2.0
            if not in_box(cx, cy, box) or any(min(x1 + ox, b[2]) - max(x0 + ox, b[0]) > 0 and min(y1 + oy, b[3]) - max(y0 + oy, b[1]) > 0
                                               for b in known):
                continue                                   # it touches a head already read or boxed: that head's ink
            share = float(ink[max(0, y0):y1, max(0, x0):x1].mean()) if y1 > y0 and x1 > x0 else 0.0
            if HEAD_BLOB_W_SP[0] * 0.8 <= (x1 - x0) / sp <= HEAD_BLOB_W_SP[1] and HEAD_BLOB_H_SP[0] * 0.8 <= (y1 - y0) / sp <= HEAD_BLOB_H_SP[1] \
                    and share >= REMAINDER_INK_MIN:
                unread = True
                vetoed.append((int(ox + x0), int(oy + y0), int(x1 - x0), int(y1 - y0), "head_ink_left_in_the_remainder"))
    return heads, unread, vetoed, covered


def _inside(px: float, py: float, d) -> bool:
    return d.x_canonical <= px <= d.x_canonical + d.width_canonical and d.y_canonical <= py <= d.y_canonical + d.height_canonical


def split_wide_heads(dets, img_no_staff, sp: float, staff_top: float = 0.0):
    """GATHER, flag ON: `(dets_out, info)`. `dets_out` = `dets` unchanged and in order, plus one new detection per head (`read_heads`)
    found inside a wide head box that no other (not wide) head box of the cell stands on (the wide box's class and confidence). `info` =
    {index: detail}: on a wide box `{"box_kind": {"heads": n, "added": [...], "unread": bool, "vetoed": [...]}}`, on an added box
    `{"box_kind": {"split_from": index, "hollow": bool}}`. No raster or no unit: nothing changes (the row has no `box_kind`: ADJUDICATE
    abstains)."""
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
    clefs = [(d.x_canonical, d.y_canonical, d.x_canonical + d.width_canonical, d.y_canonical + d.height_canonical)
             for d in dets if str(d.smufl_name).lower().startswith("clef")]
    for i, d in enumerate(dets):
        if not is_head_class(d.smufl_name) or d.width_canonical / sp < HEAD_BOX_MAX_W_SP:
            continue
        bx0, by0 = int(d.x_canonical), int(d.y_canonical)
        bx1, by1 = int(d.x_canonical + d.width_canonical), int(d.y_canonical + d.height_canonical)
        # the region: the box, widened by half a space and heightened by 4 spaces (stems and clef bars reach past it)
        rx0, ry0 = max(0, int(bx0 - 0.5 * sp)), max(0, int(by0 - 4 * sp))
        rx1, ry1 = min(img.shape[1], int(bx1 + 0.5 * sp)), min(img.shape[0], int(by1 + 4 * sp))
        if rx1 <= rx0 or ry1 <= ry0:
            continue
        hboxes = [(o.x_canonical, o.y_canonical, o.x_canonical + o.width_canonical, o.y_canonical + o.height_canonical) for o in narrow_heads]
        heads, unread, vetoed, covered = read_heads(img[ry0:ry1, rx0:rx1] == 0, sp, staff_top, origin=(rx0, ry0), head_boxes=hboxes,
                                                    clef_boxes=clefs, box=(bx0, by0, bx1, by1))
        added = []
        for (hx, hy, hw, hh, hollow) in heads:
            cx, cy = hx + hw / 2.0, hy + hh / 2.0
            if any(_inside(cx, cy, o) for o in narrow_heads):
                continue                               # a head box already stands on it (the detector's, or one split off before)
            nd = dataclasses.replace(d, x_canonical=int(hx), y_canonical=int(hy), width_canonical=int(hw), height_canonical=int(hh))
            out.append(nd)
            narrow_heads.append(nd)                    # two wide boxes over one head add it ONCE (Litolff p6 6/0/3/8)
            info[len(out) - 1] = {"box_kind": {"split_from": i, "hollow": hollow}}
            added.append(len(out) - 1)
        info[i] = {"box_kind": {"heads": len(heads), "added": added, "covered": len(covered), "unread": bool(unread),
                                "vetoed": [list(v) for v in vetoed]}}
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


# 5. A FIXED-SIZE GLYPH'S BOX IS NO BIGGER THAN THE GLYPH (2.247 hand-off; Sean's 2.242 tile 1 = this lane's case 4). An accidental is
#    printed at its SMuFL size (`glyphBBoxes`; double sharp 0.99 x 1.01 sp); a box more than `GLYPH_BOX_MAX_K` x that in either axis
#    holds more than the glyph (2.247: Litolff 42 of 51, Brahms 82 of 108 double-sharp boxes). Read where a box's CLASS blocks another
#    reader: the narrow-box eighth-rest reader (`claimed_by_another_class`).
#: 2.247's measured factor -- a tuned k: it only lets a box STOP BLOCKING; the eighth-rest reader still decides on the rest's own shape
GLYPH_BOX_MAX_K = 1.5
SIZED_PREFIXES = ("accidental",)
SMUFL_PATH = "tools/omr/annotate/static/bravura/bravura_metadata.json"
_SIZES: dict = {}


def printed_size(cls: object):
    """(w, h) staff spaces of the class's SMuFL glyph, or None (not a sized class / unknown)."""
    c = str(cls or "")
    if not c.lower().startswith(SIZED_PREFIXES):
        return None
    if not _SIZES:
        import json
        import pathlib
        bb = json.loads((pathlib.Path(__file__).resolve().parents[3] / SMUFL_PATH).read_text())["glyphBBoxes"]
        _SIZES.update({k: (v["bBoxNE"][0] - v["bBoxSW"][0], v["bBoxNE"][1] - v["bBoxSW"][1]) for k, v in bb.items()})
    return _SIZES.get(c)


def oversized_for_its_class(cls: object, w_sp: float, h_sp: float) -> bool:
    """True when a sized class's box is more than `GLYPH_BOX_MAX_K` x its printed glyph in width or height."""
    ps = printed_size(cls)
    if not ps or not w_sp or not h_sp:
        return False
    return w_sp > GLYPH_BOX_MAX_K * ps[0] or h_sp > GLYPH_BOX_MAX_K * ps[1]
