"""Which INK a CELL-pass (pass 2) label claims (ROADMAP 2.287 round 3). Read-only on the page.

THE ORDER OF THE TWO PASSES. Pass 1 (``pageink``) claimed the page-wide marks. Pass 2 labels what is
LEFT: the ink that pass 1 did not claim, ``free = page ink minus the ink of every CONFIRMED pass-1 label``.
Claimed ink is final: a pass-2 label can never take a pixel pass 1 owns (a claim reads ``free`` and
nothing else -- there is no code path from a pass-2 shape to a pass-1 pixel).

A NOTE IS MERGED INK (head + stem + beam or flag are ONE connected piece, Litolff MERGES), so a rectangle
cannot say what it takes; the SHAPE does. The free ink is split ONCE into ROLES, each pixel in exactly one
(``cellink-1``), by shape, and a label takes only the pieces of the roles its KIND names:

  head      the ROUND blob: ink an opening by a 0.7 sp disk keeps (holes in a hollow head are filled for
            that test, never claimed), at least 0.8 sp wide and 0.65 sp tall. A bar, a stem, a flag, a
            dot, a flat's bowl is thinner or smaller and is never a head
  stem      the THIN VERTICAL run >= 1.5 sp tall, in a piece that holds a head (or a lone thin tall piece).
            A sharp's or a flat's own vertical stroke is NOT a stem: its piece holds no head
  ledger    a THIN HORIZONTAL run >= 1.5 sp long, not part of a thick bar or a head. A ledger line passes
            behind its head: the head keeps the middle, the ledger line is the stubs either side
  attached  the rest of a piece that holds a head: beams, flags, tremolo slashes (thick bars the stem
            carries) and anything else touching a note
  own       a piece that holds no head: accidentals, rests, dots, articulations, tuplet marks, fermatas
  edge      the FRINGE of a staff line: ink within 0.45 sp of a staff line, not in a vertical run of 0.3 sp or
            more (so no stem, head, beam, rest or accidental), left where the scanned line wanders or fattens
            past the band pass 1's staff label took

A shape is seen ACROSS a staff line: pass 1 took the staff-line pixels, which cuts every stem into
one-space stubs and a head on a line in half; the pixels a glyph crosses (free ink directly above AND below)
are put back for the shape test only (``bridge``), so a stem is one stem and a head on a line is one head.
Those pixels stay pass 1's: they are never claimed.

KIND -> ROLES. notehead: head. stem: stem. ledger: ledger. beam: attached. flag / tremolo: attached + own (a
flag or a slash is often printed a hair off its stem and so holds no head). dot /
accidental / rest / articulation / tuplet / other: own + attached. staffedge: edge (clipped at its box: a
fringe strand runs the width of the system). noise: every free pixel in the box.

THE BOX NEVER CUTS A PIECE (round 2's rule, kept): a RECTANGLE takes a connected piece of a role WHOLE
when at least half of it lies inside the box, and not at all when most of it lies outside -- so a head
box does not take the stem next to it (a different role), and a beam box does not take a neighbour's
flag. One exception, a CLUSTER of touching heads (a second, a chord on both sides of the stem): a head
piece much bigger than one head is clipped at the box (grown 0.15 sp), so one head's box takes one head.
A POLYGON takes every free pixel inside it, whatever its shape: the tool for a piece the roles got wrong.
Who owns a pixel two pass-2 labels reach: a CONFIRMED label over a pre-fill, then the TIGHTER shape.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from tools.omr.hand_truth.pagepass import shape_bbox

RULE_VERSION = "cellink-1"

ROLES = ("head", "stem", "ledger", "attached", "own", "edge")
ROLE_ID = {r: i + 1 for i, r in enumerate(ROLES)}
#: kind -> the roles it may take pieces of
KIND_ROLES: Dict[str, Tuple[str, ...]] = {
    "notehead": ("head",), "stem": ("stem",), "ledger": ("ledger",),
    "beam": ("attached",), "flag": ("attached", "own"), "tremolo": ("attached", "own"),
    "dot": ("own", "attached"), "accidental": ("own", "attached"), "rest": ("own", "attached"),
    "articulation": ("own", "attached"), "tuplet": ("own", "attached"), "other": ("own", "attached"),
    "staffedge": ("edge",), "noise": ROLES,
}
#: a head piece bigger than this many one-head areas is a CLUSTER and is clipped at the box
CLUSTER_HEADS = 1.7
MIN_PIECE_PX = 12
#: a single head's area / its convex hull's area is at least this (an ellipse is ~0.95; a joint of beams is not)
SOLIDITY_MIN = 0.88
#: the disk (in staff spaces) an opening must fit in to keep a blob as a head: a tilted head's short axis is ~0.75 sp
HEAD_DISK_SP = 0.7


def _odd(n: float) -> int:
    n = max(3, int(round(n)))
    return n if n % 2 else n + 1


def _disk(d: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))


def bridge_mask(free: np.ndarray, staff_line: np.ndarray, hb: int) -> np.ndarray:
    """Staff-line pixels (pass-1 ink) with free ink directly above AND below: where a stem, a note or a rest
    crosses a staff line. Used only so a glyph is seen whole across the line; never claimed."""
    k = 2 * int(hb) + 2
    f8 = free.view(np.uint8)
    above = cv2.dilate(f8, np.ones((k, 1), np.uint8), anchor=(0, k - 1)).astype(bool)
    below = cv2.dilate(f8, np.ones((k, 1), np.uint8), anchor=(0, 0)).astype(bool)
    return above & below & staff_line & ~free


@dataclass
class CellClaim:
    bbox: Tuple[int, int, int, int]      # x0, y0, x1, y1 (exclusive) in page px
    mask: np.ndarray                     # bool, bbox-shaped
    cut: bool = False                    # a head cluster clipped at the box, or a polygon

    @property
    def px(self) -> int:
        return int(self.mask.sum())


class CellInk:
    """The free ink (page ink minus confirmed pass-1 ink), split once into roles and connected pieces."""

    def __init__(self, free: np.ndarray, sp: float, staff_line: Optional[np.ndarray] = None,
                 line_thickness: float = 7.0, hb: int = 6):
        """``free``: ink pass 1 did not claim. ``staff_line``: the staff-line pixels (pass-1 ink). They are used
        ONLY to see shapes whole across a staff line -- a stem, a head or a beam cut by the line is one thing,
        and a beam lying on a line is as thick as it is -- never claimed: a claim reads ``free`` alone.
        ``line_thickness``: the staff lines' measured thickness in px (a ledger line is as thin; a beam is
        much thicker). ``hb``: half the staff-line band."""
        self.free = free if free.dtype == bool else free > 0
        self.h, self.w = self.free.shape
        self.sp = float(sp) if sp else 32.0
        self.staff_line = staff_line if staff_line is not None else np.zeros_like(self.free)
        self.bridge = bridge_mask(self.free, self.staff_line, hb)
        self.line_thickness = float(line_thickness)
        self._build()

    # ------------------------------------------------------------ the split
    def _build(self) -> None:
        sp = self.sp
        R = self.free | self.bridge        # work ink: the shape of things is seen across a staff line
        R8 = R.view(np.uint8)
        # a hollow head (half / whole) is a ring: fill its hole for the opening test only
        inv = (~R).view(np.uint8)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
        small = np.zeros(n, bool)
        # only a hole the size of a head's own interior: the gap between two beams is long and is not one
        small[1:] = (np.maximum(stats[1:, cv2.CC_STAT_WIDTH], stats[1:, cv2.CC_STAT_HEIGHT]) <= 1.0 * sp) & \
            (stats[1:, cv2.CC_STAT_AREA] >= 40)
        filled = R | small[lab]
        # a HOLLOW head's interior (a half or whole note): a hole at least 0.3 sp across in both directions and
        # 100 px (a flat's bowl is smaller; a sharp's holes are slits), taken with its neighbours of one head
        # (a ledger line across the head splits the interior in two) when they hold 200 px together
        wid, hei = stats[:, cv2.CC_STAT_WIDTH], stats[:, cv2.CC_STAT_HEIGHT]
        hole_ok = small & (np.minimum(wid, hei) >= 0.3 * sp) & (stats[:, cv2.CC_STAT_AREA] >= 100)
        holes = hole_ok[lab]
        del lab, inv
        head0 = cv2.morphologyEx(filled.view(np.uint8), cv2.MORPH_OPEN, _disk(_odd(HEAD_DISK_SP * sp)))
        vopen = cv2.morphologyEx(R8, cv2.MORPH_OPEN, np.ones((int(round(1.5 * sp)), 1), np.uint8))
        stem_cols = cv2.dilate(vopen, np.ones((1, 3), np.uint8)).astype(bool) & R
        grow = max(2, int(round(0.1 * sp)))
        head = head0.astype(bool)
        head |= cv2.dilate(head0, _disk(2 * grow + 1)).astype(bool) & R & ~stem_cols
        kept = np.zeros_like(holes)
        if holes.any():
            wall = max(3, int(round(0.32 * sp)))
            near_h = cv2.dilate(holes.view(np.uint8), _disk(2 * wall + 3))
            hg_n, hg, hg_st, _ = cv2.connectedComponentsWithStats(near_h, connectivity=8)
            per = np.bincount(hg[holes], minlength=hg_n)           # hole px per group of holes
            keep_g = per >= 200
            keep_g[0] = False
            kept = holes & keep_g[hg]
            head |= cv2.dilate(kept.view(np.uint8), _disk(2 * wall + 1)).astype(bool) & R & ~stem_cols
            del hg, near_h
        head &= R                          # a head's own ink only (the filled hole is not ink)
        # a head is at least ~0.9 sp wide and ~0.65 sp tall: a flat's bowl or a dot is not (they fall to `own`)
        hn, hl, hs, _ = cv2.connectedComponentsWithStats(head.view(np.uint8), connectivity=8)
        okh = (hs[:, cv2.CC_STAT_WIDTH] >= 0.9 * sp) & (hs[:, cv2.CC_STAT_HEIGHT] >= 0.65 * sp)
        okh[0] = False
        # ... and ONE head is convex (an ellipse); the joint of two close beams and a stem is not. (A bigger piece
        # is a cluster of touching heads and is not tested.)
        touch = cv2.dilate(kept.view(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        hollow_ids = set(int(v) for v in np.unique(hl[touch]) if v)      # a ring round a real hole: no test needed
        for i in np.nonzero(okh)[0]:
            if hs[i, cv2.CC_STAT_AREA] > CLUSTER_HEADS * 1.2 * sp * sp or int(i) in hollow_ids:
                continue
            x, y, w, h = (int(hs[i, k]) for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT))
            m = (hl[y:y + h, x:x + w] == i).astype(np.uint8)
            cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            hull = sum(cv2.contourArea(cv2.convexHull(c)) for c in cs)
            if hull <= 0 or hs[i, cv2.CC_STAT_AREA] / hull < SOLIDITY_MIN:
                okh[i] = False
        head = okh[hl]
        del hl
        # thick bars (beams, slashes, flag bellies, rest bars): ink an opening by a disk 1.6x a staff line's
        # thickness keeps (a ledger line is as thin as a staff line; a beam is twice that). A beam lying on a
        # staff line is as thick as beam + line: thickness is judged with the staff-line pixels present.
        thick_src = ((R | self.staff_line) & ~head).view(np.uint8)
        bar0 = cv2.morphologyEx(thick_src, cv2.MORPH_OPEN, _disk(_odd(max(0.3 * sp, 1.6 * self.line_thickness))))
        bar = cv2.dilate(bar0, _disk(5)).astype(bool) & R & ~head
        # thin horizontal runs >= 1.5 sp (ledger lines), never through a head or a thick bar
        hopen = cv2.morphologyEx(R8, cv2.MORPH_OPEN, np.ones((1, int(round(1.5 * sp))), np.uint8))
        # (a ledger line stands a whole space from the staff; a strand hugging a staff line is its fringe, not a ledger line)
        near = cv2.dilate(self.staff_line.view(np.uint8), np.ones((int(round(0.9 * sp)) | 1, 1), np.uint8)).astype(bool)
        ledger = hopen.astype(bool) & R & ~head & ~near & ~cv2.dilate(bar.view(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        # pieces of the work ink: which hold a head?
        n2, lab2, st2, _ = cv2.connectedComponentsWithStats(R8, connectivity=8)
        holds_head = np.zeros(n2, bool)
        holds_head[np.unique(lab2[head])] = True
        holds_head[0] = False
        # a lone thin vertical piece (a stem whose head was claimed elsewhere or cut) is a stem piece too
        tall = st2[:, cv2.CC_STAT_HEIGHT] >= 1.5 * sp
        thin = st2[:, cv2.CC_STAT_WIDTH] <= 0.45 * sp
        lone_stem = tall & thin
        lone_stem[0] = False
        in_note = holds_head[lab2]
        stem = stem_cols & ~head & ~bar & ~ledger & (in_note | lone_stem[lab2])
        role = np.zeros(R.shape, np.uint8)
        # the fringe of a staff line: near a line, and in no vertical run of 0.3 sp or more
        v3 = cv2.morphologyEx(R8, cv2.MORPH_OPEN, np.ones((max(3, int(round(0.3 * sp))), 1), np.uint8)).astype(bool)
        cand = R & near & ~v3 & ~head & ~ledger & ~stem & ~bar
        # ... and a fringe: a STRAND along the line of at least 0.9 sp, or a fragment that touches no glyph (a sharp's
        # short crossbar touches its own strokes; a fringe fragment touches only the staff line)
        en, el_, est, _ = cv2.connectedComponentsWithStats(cand.view(np.uint8), connectivity=8)
        glyph = R & ~cand & ~self.staff_line & ~self.bridge
        touches = np.zeros(en, bool)
        touches[np.unique(el_[cv2.dilate(glyph.view(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & cand])] = True
        fringe = (est[:, cv2.CC_STAT_WIDTH] >= 0.9 * sp) | ~touches
        fringe[0] = False
        edge = fringe[el_]
        del el_, cand, glyph
        note_rest = R & ~head & ~ledger & ~stem & ~edge
        role[note_rest & in_note] = ROLE_ID["attached"]
        role[note_rest & ~in_note] = ROLE_ID["own"]
        role[edge] = ROLE_ID["edge"]
        role[stem] = ROLE_ID["stem"]
        role[ledger] = ROLE_ID["ledger"]
        role[head] = ROLE_ID["head"]
        del lab2, in_note
        self._absorb_junctions(role)
        self.role = role
        # connected pieces per role (8-connected), one id space
        self.comp = np.zeros(R.shape, np.int32)
        stats_l: List[np.ndarray] = [np.zeros((1, 5), np.int32)]
        self.comp_role = [0]
        off = 1
        for r in ROLES:
            m = (role == ROLE_ID[r])
            if not m.any():
                continue
            k, lb, st, _ = cv2.connectedComponentsWithStats(m.view(np.uint8), connectivity=8)
            self.comp[m] = lb[m] + (off - 1)
            stats_l.append(st[1:])
            self.comp_role += [ROLE_ID[r]] * (k - 1)
            off += k - 1
        self.stats = np.concatenate(stats_l, 0)
        self.comp_role = np.array(self.comp_role, np.int8)
        # typical head area (page px): the median area of the head pieces that look like ONE head
        ha = self.stats[self.comp_role == ROLE_ID["head"], cv2.CC_STAT_AREA]
        one = ha[(ha > 0.4 * sp * sp) & (ha < 2.2 * sp * sp)]
        self.head_area = float(np.median(one)) if len(one) else 0.9 * sp * sp
        self._cache: Dict[Tuple, CellClaim] = {}

    def _absorb_junctions(self, role: np.ndarray) -> None:
        """A small `attached` piece where a stem crosses a ledger line, or a head meets its stem, is not a
        beam or a flag: it is a joint of the stem / ledger / head beside it. Relabel it (in place) to the
        role it touches most (a head, a stem or a ledger line); an `attached` piece that touches none stays."""
        aid = ROLE_ID["attached"]
        m = (role == aid)
        if not m.any():
            return
        n, lb, st, _ = cv2.connectedComponentsWithStats(m.view(np.uint8), connectivity=8)
        limit = 0.3 * self.sp * self.sp
        for i in np.nonzero(st[1:, cv2.CC_STAT_AREA] < limit)[0] + 1:
            x, y = int(st[i, cv2.CC_STAT_LEFT]), int(st[i, cv2.CC_STAT_TOP])
            w, h = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
            x0, y0, x1, y1 = max(0, x - 2), max(0, y - 2), min(self.w, x + w + 2), min(self.h, y + h + 2)
            mine = (lb[y0:y1, x0:x1] == i)
            ring = cv2.dilate(mine.view(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~mine
            around = role[y0:y1, x0:x1][ring]
            cnt = {r: int((around == ROLE_ID[r]).sum()) for r in ("head", "stem", "ledger")}
            best = max(cnt, key=lambda r: cnt[r])
            if cnt[best] > 0:
                role[y0:y1, x0:x1][mine] = ROLE_ID[best]

    # ------------------------------------------------------------ one claim
    def claim(self, shape: Dict, kind: str) -> CellClaim:
        """The free ink ``kind`` takes inside ``shape`` (see the module docstring)."""
        key = (kind, repr(shape))
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        out = self._claim(shape, kind)
        if len(self._cache) > 20000:
            self._cache.clear()
        self._cache[key] = out
        return out

    def _claim(self, shape: Dict, kind: str) -> CellClaim:
        fx0, fy0, fx1, fy1 = shape_bbox(shape)
        x0, y0 = max(0, int(np.floor(fx0))), max(0, int(np.floor(fy0)))
        x1, y1 = min(self.w, int(np.ceil(fx1)) + 1), min(self.h, int(np.ceil(fy1)) + 1)
        none = CellClaim((x0, y0, x0, y0), np.zeros((0, 0), bool))
        if x1 <= x0 or y1 <= y0:
            return none
        sl = (slice(y0, y1), slice(x0, x1))
        if "poly" in shape:
            pts = np.array([[round(px - x0), round(py - y0)] for px, py in shape["poly"]], np.int32)
            m8 = np.zeros((y1 - y0, x1 - x0), np.uint8)
            cv2.fillPoly(m8, [pts], 1)
            return CellClaim((x0, y0, x1, y1), self.free[sl] & m8.astype(bool), cut=True)
        if kind == "noise":
            return CellClaim((x0, y0, x1, y1), self.free[sl].copy(), cut=False)
        roles = [ROLE_ID[r] for r in KIND_ROLES[kind]]
        sub = self.comp[sl]
        ids, counts = np.unique(sub[sub > 0], return_counts=True)
        if not len(ids):
            return none
        okrole = np.isin(self.comp_role[ids], roles)
        ids, counts = ids[okrole], counts[okrole]
        if not len(ids):
            return none
        area = self.stats[ids, cv2.CC_STAT_AREA]
        keep = counts * 2 >= area
        clip = np.zeros(len(ids), bool)
        if kind == "notehead":
            cluster = area > CLUSTER_HEADS * self.head_area
            clip = cluster & (counts >= 0.3 * self.head_area)     # a box on part of a cluster takes what it holds
            keep &= ~cluster
        elif kind == "staffedge":
            clip = np.ones(len(ids), bool)                        # a fringe strand runs the system: clip at the box
            keep &= False
        whole, clipped = ids[keep], ids[clip]
        if not len(whole) and not len(clipped):
            return none
        rx0, ry0, rx1, ry1 = x0, y0, x1, y1
        if len(whole):
            rx0 = min(rx0, int(self.stats[whole, cv2.CC_STAT_LEFT].min()))
            ry0 = min(ry0, int(self.stats[whole, cv2.CC_STAT_TOP].min()))
            rx1 = max(rx1, int((self.stats[whole, cv2.CC_STAT_LEFT] + self.stats[whole, cv2.CC_STAT_WIDTH]).max()))
            ry1 = max(ry1, int((self.stats[whole, cv2.CC_STAT_TOP] + self.stats[whole, cv2.CC_STAT_HEIGHT]).max()))
        g = int(round(0.15 * self.sp))
        gy0, gy1 = max(0, y0 - g), min(self.h, y1 + g)
        gx0, gx1 = max(0, x0 - g), min(self.w, x1 + g)
        if len(clipped):
            rx0, ry0, rx1, ry1 = min(rx0, gx0), min(ry0, gy0), max(rx1, gx1), max(ry1, gy1)
        reg = (slice(ry0, ry1), slice(rx0, rx1))
        mask = (np.isin(self.comp[reg], whole) & self.free[reg]) if len(whole) else np.zeros((ry1 - ry0, rx1 - rx0), bool)
        if len(clipped):
            cm = np.zeros_like(mask)
            cm[gy0 - ry0:gy1 - ry0, gx0 - rx0:gx1 - rx0] = np.isin(self.comp[gy0:gy1, gx0:gx1], clipped) \
                & self.free[gy0:gy1, gx0:gx1]
            mask |= cm
        if int(mask.sum()) < MIN_PIECE_PX:
            return none
        return CellClaim((rx0, ry0, rx1, ry1), mask, cut=bool(len(clipped)))

    def role_at(self, x: int, y: int) -> Optional[str]:
        r = int(self.role[y, x])
        return ROLES[r - 1] if r else None


def ink_ref(kind: str, c: CellClaim, owned: np.ndarray) -> Dict:
    """The claimed-ink reference stored on a confirmed label: rule, how much, where, a hash of which."""
    x0, y0, x1, y1 = c.bbox
    ys, xs = np.nonzero(owned) if owned.size else (np.array([]), np.array([]))
    bb = [int(x0 + xs.min()), int(y0 + ys.min()), int(x0 + xs.max()) + 1, int(y0 + ys.max()) + 1] if len(xs) else None
    digest = hashlib.sha1(np.packbits(owned).tobytes()).hexdigest()[:16] if owned.size else ""
    ref = {"rule": RULE_VERSION, "roles": list(KIND_ROLES[kind]), "px": int(owned.sum()), "bbox": bb, "sha1": digest}
    if c.cut:
        ref["cut"] = True
    return ref
