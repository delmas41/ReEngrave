"""Which INK a page-pass label claims, and the picture of it (ROADMAP 2.287). Read-only on the page.

THE RULE (``RULE_VERSION``). A label owns INK PIXELS, decided by its KIND from the page's dark pixels
(the page binary the cells are cut from, ``ink = binary < 128``), restricted to the label's shape:

  staff     the staff-line pixels (the lines' own rows, from the cells' measured ``staff_line_ys``)
  barline   long vertical runs (>= 2.5 sp tall) -- plus the staff-line pixels the rule crosses
  arc       THIN CURVE ink only: no staff line, no blob (a head, a beam, a clef curl: ink that
  hairpin   survives an opening of 0.5 sp), no stem-like vertical run (>= 1.5 sp tall). The
            noteheads under an arc's box are NOT its ink
  others    every non-staff ink pixel in the shape (+ staff-line pixels the glyph crosses)
            (bracket clef key meter word dynamic repeat)

A staff-line pixel is a glyph's own (not the staff's) when the kind's ink stands directly above AND
below it -- a clef, a barline or a slur crossing the line. Specks under 30 px are not claimed (unless they touch a staff line: a line cuts every stem and barline into pieces).

CLAIM ORDER decides a pixel two labels both reach: the EARLIER kind (``pagepass.KINDS``) wins
("a later reader may mark claimed ink but never take it"); within a kind the SMALLER shape wins.
That is how a merged piece (Litolff) is split: draw each mark's own shape around its own part
(a polygon where a rectangle cannot), the tighter one owns the overlap. A shattered mark
(Breitkopf) is one label over all its pieces. A pixel no shape reaches stays UNCLAIMED, visibly.

Nothing here writes the page, the cells or the pipeline's stroke map: it reads a binary and the
staff-line positions and returns arrays.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from tools.omr.hand_truth.pagepass import KIND_MODE, KINDS, PLabel, Rect, shape_area, shape_bbox

RULE_VERSION = "pageink-1"

# states drawn in the picture (index into PALETTE)
BG, UNCLAIMED, CLAIMED, PENDING, CELLPASS = 0, 1, 2, 3, 4
#: BGR. Okabe-Ito (colour-blind safe): vermilion = needs claiming, blue = claimed by a confirmed page
#: label, reddish-purple = under a pre-fill still waiting for Sean, bluish-green = claimed in the cell pass.
PALETTE_RGB = {BG: (255, 255, 255), UNCLAIMED: (213, 94, 0), CLAIMED: (0, 114, 178),
               PENDING: (204, 121, 167), CELLPASS: (0, 158, 115)}
STATE_NAMES = {UNCLAIMED: "unclaimed", CLAIMED: "claimed", PENDING: "pending", CELLPASS: "cell pass"}


def _odd(n: float) -> int:
    n = max(3, int(round(n)))
    return n if n % 2 else n + 1


def staff_lines_from_cells(cells) -> List[Tuple[float, float, List[float]]]:
    """(x0, x1, [five line ys]) in PAGE px for every measure cell that measured its staff."""
    out = []
    for c in cells:
        if getattr(c, "kind", None) != "measure" or not c.staff_line_ys:
            continue
        x0, y0, x1, y1 = c.rect
        sy = (y1 - y0) / c.canonical_h
        out.append((float(x0), float(x1), [y0 + float(y) * sy for y in c.staff_line_ys]))
    return out


def measure_sp(lines) -> float:
    d = []
    for _, _, ys in lines:
        d += list(np.diff(sorted(ys)))
    return float(np.median(d)) if d else 0.0


def measure_line_thickness(ink: np.ndarray, lines, sp: float, samples: int = 5) -> float:
    """Median thickness (px) of the staff lines' own ink, measured where the cells say the lines are.

    A 600 dpi scan's lines are 6-9 px (0.2-0.3 sp), not a fixed fraction of a space, so the band is measured.
    """
    h, w = ink.shape
    reach = max(3, int(round(0.4 * sp)))
    runs = []
    for x0, x1, ys in lines:
        for y in ys:
            yc = int(round(y))
            for k in range(samples):
                x = int(x0 + (x1 - x0) * (k + 0.5) / samples)
                if not (0 <= x < w and reach <= yc < h - reach):
                    continue
                col = ink[yc - reach:yc + reach + 1, x]
                idx = np.nonzero(col)[0]
                if not len(idx):
                    continue
                start = int(idx[np.argmin(np.abs(idx - reach))])
                a = b = start
                while a > 0 and col[a - 1]:
                    a -= 1
                while b < len(col) - 1 and col[b + 1]:
                    b += 1
                if abs(start - reach) <= 4 and (b - a + 1) < 0.5 * sp:     # a line, not a glyph sitting on it
                    runs.append(b - a + 1)
    return float(np.median(runs)) if runs else max(2.0, 0.1 * sp)


@dataclass
class Claim:
    bbox: Tuple[int, int, int, int]      # x0, y0, x1, y1 (exclusive) in page px
    mask: np.ndarray                     # bool, bbox-shaped

    @property
    def px(self) -> int:
        return int(self.mask.sum())


@dataclass
class Claims:
    owner: np.ndarray                    # int32 page-shaped: 0 = nobody, i+1 = labels[i]
    labels: List[PLabel]
    px: Dict[str, int]                   # label id -> pixels it owns after precedence
    raw_px: Dict[str, int]               # label id -> pixels in its claim before precedence
    refs: Dict[str, Dict]                # label id -> ink_ref
    ink_px: int
    confirmed_px: int
    pending_px: int
    cellpass_px: int

    def summary(self) -> Dict:
        t = max(1, self.ink_px)
        un = self.ink_px - self.confirmed_px - self.pending_px - self.cellpass_px
        return {"ink_px": self.ink_px, "claimed_px": self.confirmed_px, "pending_px": self.pending_px,
                "cellpass_px": self.cellpass_px, "unclaimed_px": un,
                "claimed_pct": 100.0 * self.confirmed_px / t,
                "pending_pct": 100.0 * self.pending_px / t,
                "cellpass_pct": 100.0 * self.cellpass_px / t,
                "unclaimed_pct": 100.0 * un / t}


class InkMap:
    """The page's ink, split once into the layers the claim rules ask for."""

    MIN_PIECE_PX = 30

    def __init__(self, ink: np.ndarray, sp: float,
                 staff_lines: Sequence[Tuple[float, float, Sequence[float]]]):
        if ink.dtype != bool:
            ink = ink > 0
        self.ink = ink
        self.h, self.w = ink.shape
        self.sp = float(sp) if sp else 32.0
        self.line_thickness = measure_line_thickness(ink, staff_lines, self.sp)
        # the band around a measured line y: half the line's own ink thickness + 2 px for the scan's wander
        self.hb = max(1, min(int(round(0.3 * self.sp)), int(np.ceil(self.line_thickness / 2.0)) + 2))
        line = np.zeros_like(ink)
        for x0, x1, ys in staff_lines:
            for y in ys:
                a, b = max(0, int(round(y)) - self.hb), min(self.h, int(round(y)) + self.hb + 1)
                if b > a:
                    line[a:b, max(0, int(x0)):min(self.w, int(x1))] = True
        # a band pixel is the STAFF LINE's only where the ink runs level for >= 1.5 sp: a glyph's own pixel in
        # the band's edge rows (a stem, a slur's foot) is a short run and stays the glyph's
        hor = cv2.morphologyEx(ink.view(np.uint8), cv2.MORPH_OPEN, np.ones((1, int(round(1.5 * self.sp))), np.uint8))
        self.line = line & ink & hor.astype(bool)
        self.rest = ink & ~self.line
        k = _odd(0.5 * self.sp)
        blob = cv2.morphologyEx(self.rest.view(np.uint8), cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        self.blob = cv2.dilate(blob, np.ones((5, 5), np.uint8)).astype(bool)
        v = cv2.morphologyEx(ink.view(np.uint8), cv2.MORPH_OPEN,
                             np.ones((int(round(1.5 * self.sp)), 1), np.uint8))
        self.vert = cv2.dilate(v, np.ones((1, 3), np.uint8)).astype(bool) & ~self.line
        lv = cv2.morphologyEx(ink.view(np.uint8), cv2.MORPH_OPEN,
                              np.ones((int(round(2.5 * self.sp)), 1), np.uint8))
        self.longvert = cv2.dilate(lv, np.ones((1, 3), np.uint8)).astype(bool) & ~self.line

    # ------------------------------------------------------------ one claim
    def _candidates(self, mode: str, sl: Tuple[slice, slice]) -> np.ndarray:
        if mode == "all":
            return self.rest[sl]
        if mode == "thin":
            return self.rest[sl] & ~self.blob[sl] & ~self.vert[sl]
        if mode == "vertical":
            return self.longvert[sl] & self.rest[sl]
        raise ValueError(mode)

    def claim(self, shape: Dict, kind: str) -> Claim:
        mode = KIND_MODE[kind]
        fx0, fy0, fx1, fy1 = shape_bbox(shape)
        x0, y0 = max(0, int(np.floor(fx0))), max(0, int(np.floor(fy0)))
        x1, y1 = min(self.w, int(np.ceil(fx1)) + 1), min(self.h, int(np.ceil(fy1)) + 1)
        if x1 <= x0 or y1 <= y0:
            return Claim((x0, y0, x0, y0), np.zeros((0, 0), bool))
        sl = (slice(y0, y1), slice(x0, x1))
        inside = np.zeros((y1 - y0, x1 - x0), np.uint8)
        if "rect" in shape:
            inside[:] = 1
        else:
            pts = np.array([[round(px - x0), round(py - y0)] for px, py in shape["poly"]], np.int32)
            cv2.fillPoly(inside, [pts], 1)
        inside = inside.astype(bool)
        if mode == "lines":
            return Claim((x0, y0, x1, y1), self.line[sl] & inside)
        cand = self._candidates(mode, sl) & inside
        cand = self._drop_specks(cand, self.line[sl], min_extent=int(round(0.6 * self.sp)) if mode == "thin" else 0)
        # staff-line pixels the glyph itself crosses (ink of this kind stands above AND below)
        k = 2 * self.hb + 2
        ext = (slice(max(0, y0 - k), min(self.h, y1 + k)), sl[1])
        cext = self._candidates(mode, ext)
        cmask = np.zeros_like(cext)
        oy = y0 - ext[0].start
        cmask[oy:oy + (y1 - y0), :] = cand
        above = cv2.dilate(cmask.view(np.uint8), np.ones((k, 1), np.uint8), anchor=(0, k - 1)).astype(bool)
        below = cv2.dilate(cmask.view(np.uint8), np.ones((k, 1), np.uint8), anchor=(0, 0)).astype(bool)
        cross = (above & below)[oy:oy + (y1 - y0), :] & self.line[sl] & inside
        return Claim((x0, y0, x1, y1), cand | cross)

    def _drop_specks(self, cand: np.ndarray, line: np.ndarray, min_extent: int = 0) -> np.ndarray:
        """Drop pieces under MIN_PIECE_PX -- unless one touches a staff line: a staff line cuts every
        stem and barline into pieces, and the stub left beside it is the glyph's own."""
        if not cand.any():
            return cand
        n, lab, stats, _ = cv2.connectedComponentsWithStats(cand.view(np.uint8), connectivity=8)
        keep = np.zeros(n, bool)
        keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= self.MIN_PIECE_PX
        near = cv2.dilate(line.view(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        keep[np.unique(lab[near & (lab > 0)])] = True
        if min_extent:      # a thin curve is longer than a dot: an augmentation dot under an arc's box is not the arc's
            ext = np.maximum(stats[:, cv2.CC_STAT_WIDTH], stats[:, cv2.CC_STAT_HEIGHT])
            keep &= ext >= min_extent
        keep[0] = False
        return keep[lab]

    # ------------------------------------------------------------ the whole page
    def claims(self, labels: Sequence[PLabel], cellpass: Optional[np.ndarray] = None) -> Claims:
        """Resolve every claiming label (confirmed + pending). Earlier kind wins; then smaller shape."""
        labs = list(labels)
        order = sorted(range(len(labs)), key=lambda i: (KINDS.index(labs[i].kind),
                                                         shape_area(labs[i].shape), labs[i].id))
        owner = np.zeros((self.h, self.w), np.int32)
        px: Dict[str, int] = {}
        raw: Dict[str, int] = {}
        refs: Dict[str, Dict] = {}
        for i in order:
            lab = labs[i]
            c = self.claim(lab.shape, lab.kind)
            x0, y0, x1, y1 = c.bbox
            raw[lab.id] = c.px
            if c.mask.size == 0:
                px[lab.id] = 0
                refs[lab.id] = self._ref(lab, c, c.mask)
                continue
            region = owner[y0:y1, x0:x1]
            take = c.mask & (region == 0)
            region[take] = i + 1
            px[lab.id] = int(take.sum())
            refs[lab.id] = self._ref(lab, c, take)
        conf = np.zeros(len(labs) + 1, bool)
        pend = np.zeros(len(labs) + 1, bool)
        for i, lab in enumerate(labs):
            conf[i + 1] = lab.state == "confirmed"
            pend[i + 1] = lab.state == "pending"
        cp = 0
        if cellpass is not None:
            cp = int((cellpass & self.ink & (owner == 0)).sum())
        return Claims(owner=owner, labels=labs, px=px, raw_px=raw, refs=refs,
                      ink_px=int(self.ink.sum()), confirmed_px=int(conf[owner].sum()),
                      pending_px=int(pend[owner].sum()), cellpass_px=cp)

    def _ref(self, lab: PLabel, c: Claim, mask: np.ndarray) -> Dict:
        """The claimed-ink reference stored on the label: the rule, how much, where, a hash of which."""
        x0, y0, x1, y1 = c.bbox
        ys, xs = np.nonzero(mask) if mask.size else (np.array([]), np.array([]))
        bb = [int(x0 + xs.min()), int(y0 + ys.min()), int(x0 + xs.max()) + 1, int(y0 + ys.max()) + 1] \
            if len(xs) else None
        digest = hashlib.sha1(np.packbits(mask).tobytes()).hexdigest()[:16] if mask.size else ""
        return {"rule": RULE_VERSION, "mode": KIND_MODE[lab.kind], "px": int(mask.sum()),
                "bbox": bb, "sha1": digest}

    def cellpass_mask(self, rects: Iterable[Rect]) -> np.ndarray:
        """Ink under cell-pass boxes (all non-staff ink in each rectangle), as one page mask."""
        out = np.zeros((self.h, self.w), bool)
        for r in rects:
            c = self.claim({"rect": list(r)}, "word")     # 'all' mode
            if c.mask.size:
                x0, y0, x1, y1 = c.bbox
                out[y0:y1, x0:x1] |= c.mask
        return out

    # ------------------------------------------------------------ the picture
    def states(self, claims: Optional[Claims], cellpass: Optional[np.ndarray],
               box: Tuple[int, int, int, int]) -> np.ndarray:
        """uint8 state codes for a page region: BG / UNCLAIMED / CLAIMED / PENDING / CELLPASS."""
        x0, y0, x1, y1 = box
        sl = (slice(y0, y1), slice(x0, x1))
        ink = self.ink[sl]
        code = np.where(ink, UNCLAIMED, BG).astype(np.uint8)
        if cellpass is not None:
            code[ink & cellpass[sl]] = CELLPASS
        if claims is not None:
            lut = np.zeros(len(claims.labels) + 1, np.uint8)
            for i, lab in enumerate(claims.labels):
                lut[i + 1] = CLAIMED if lab.state == "confirmed" else PENDING
            ow = claims.owner[sl]
            m = ow > 0
            code[m & ink] = lut[ow][m & ink]
        return code


def render_states(code: np.ndarray, out_w: int) -> np.ndarray:
    """BGR picture of a state-code region at ``out_w`` px wide (thin ink boosted so it stays visible)."""
    h, w = code.shape
    pal = np.zeros((5, 3), np.uint8)
    for k, (r, g, b) in PALETTE_RGB.items():
        pal[k] = (b, g, r)
    img = pal[code]
    scale = out_w / float(w)
    out_h = max(1, int(round(h * scale)))
    if scale >= 1.0:
        return cv2.resize(img, (out_w, out_h), interpolation=cv2.INTER_NEAREST)
    small = cv2.resize(img, (out_w, out_h), interpolation=cv2.INTER_AREA).astype(np.float32)
    gain = min(6.0, max(1.0, 0.35 / scale))
    return np.clip(255.0 - (255.0 - small) * gain, 0, 255).astype(np.uint8)


def claimed_overlay_rgba(claims: Claims, cellpass: Optional[np.ndarray], ink: np.ndarray,
                         rect: Tuple[float, float, float, float], out_w: int, out_h: int,
                         states: Iterable[int] = (CLAIMED, PENDING)) -> np.ndarray:
    """RGBA overlay for one cell: only claimed ink is tinted (everything else transparent)."""
    x0, y0, x1, y1 = (int(round(v)) for v in rect)
    H, W = claims.owner.shape
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    code = np.zeros((max(0, y1 - y0), max(0, x1 - x0)), np.uint8)
    if code.size == 0:
        return np.zeros((out_h, out_w, 4), np.uint8)
    lut = np.zeros(len(claims.labels) + 1, np.uint8)
    for i, lab in enumerate(claims.labels):
        lut[i + 1] = CLAIMED if lab.state == "confirmed" else PENDING
    ow = claims.owner[y0:y1, x0:x1]
    code = lut[ow]
    code[~ink[y0:y1, x0:x1]] = 0
    rgba = np.zeros((out_h, out_w, 4), np.float32)
    for st in states:
        interp = cv2.INTER_AREA if out_w < code.shape[1] else cv2.INTER_LINEAR
        a = cv2.resize((code == st).astype(np.float32), (out_w, out_h), interpolation=interp)
        a = (a >= 0.4).astype(np.float32) if out_w >= code.shape[1] else np.clip(a * 3.0, 0, 1)  # crisp when enlarged: never fatter than the ink
        r, g, b = PALETTE_RGB[st]
        m = a > 0
        rgba[m, 0], rgba[m, 1], rgba[m, 2] = b, g, r          # BGR
        rgba[..., 3] = np.maximum(rgba[..., 3], a * 255.0)
    return rgba.astype(np.uint8)
