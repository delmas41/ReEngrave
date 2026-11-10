"""Which INK a page-pass label claims, and the picture of it (ROADMAP 2.287). Read-only on the page.

THE RULE (``RULE_VERSION`` pageink-2, round 2). A label owns INK PIXELS, decided by its KIND from the
page's dark pixels (the page binary the cells are cut from, ``ink = binary < 128``), inside its shape:

  staff     the staff-line pixels (the lines' own rows, from the cells' measured ``staff_line_ys``)
  barline   long vertical runs (>= 2.5 sp tall) -- plus the staff-line pixels the rule crosses
  arc       THIN CURVE ink only: no staff line, no blob (a head, a beam, a clef curl: ink that
  hairpin   survives an opening of 0.5 sp), no stem-like vertical run (>= 1.5 sp tall). The
            noteheads under an arc's box are NOT its ink
  bracket   (and brace) ONLY its own tall stroke: a connected piece of ink at least half as tall as the
            box (and 4 sp), hooks and curl included -- never a small separate piece that merely falls
            inside the tall box
  others    every connected piece of non-staff ink in the shape (clef key meter word dynamic repeat)

A PIECE IS NOT CUT BY A BOX EDGE (round 2). For the kinds that take whole marks (bracket, clef, key, meter,
word, dynamic, repeat) a RECTANGLE takes a connected piece of ink WHOLE if at least half of it lies inside
the rectangle, and not at all if most of it lies outside. A POLYGON still cuts exactly at its edge: it is
the tool for deliberately splitting a merged piece (Litolff MERGES; Breitkopf SHATTERS: a shattered mark is
one label over all its pieces). A "piece" joins what a staff line cuts apart where a glyph crosses the line
(a clef, a bracket and a barline cross the five lines): ink standing directly above AND below a staff-line
pixel makes that pixel the glyph's own. Specks under 30 px are not claimed (unless they touch a staff line).

WHO OWNS A PIXEL TWO LABELS REACH (round 2; round 1 gave it to the earlier kind, which let a page-long
bracket box take the clefs inside it):
  1. a CONFIRMED label (Sean's statement) outranks a pre-fill (a proposal);
  2. a staff-line pixel belongs to the STAFF label that reaches it;
  3. any other pixel goes to the TIGHTER shape (smaller area) -- the more specific statement;
  4. two shapes of about the same size (within 25%) cannot be told apart: the pixel is CONTESTED, owned by
     neither, drawn in its own colour and counted. Never silently assigned.
A pixel no shape reaches stays UNCLAIMED, visibly.

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

RULE_VERSION = "pageink-2"
#: two shapes whose areas are within this factor cannot be told apart by "the tighter wins": contested
CLOSE_AREA = 1.25
#: a TALL (bracket / brace) stroke is at least this fraction of the box's height, and at least this many spaces
TALL_FRAC, TALL_MIN_SP = 0.5, 4.0

# states drawn in the picture (index into PALETTE)
BG, UNCLAIMED, CLAIMED, PENDING, CELLPASS, CONTESTED = 0, 1, 2, 3, 4, 5
#: RGB. Okabe-Ito (colour-blind safe): vermilion = needs claiming, blue = claimed by a confirmed page
#: label, reddish-purple = under a pre-fill still waiting for Sean, bluish-green = claimed in the cell pass,
#: yellow = CONTESTED (two confirmed labels of about one size reach it; owned by neither until you decide).
PALETTE_RGB = {BG: (255, 255, 255), UNCLAIMED: (213, 94, 0), CLAIMED: (0, 114, 178),
               PENDING: (204, 121, 167), CELLPASS: (0, 158, 115), CONTESTED: (240, 228, 66)}
STATE_NAMES = {UNCLAIMED: "unclaimed", CLAIMED: "claimed", PENDING: "pending", CELLPASS: "cell pass",
               CONTESTED: "contested"}


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
    cut: bool = False                    # a rectangle that sits on ONE merged piece cut it at its edge

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
    contested: Optional[np.ndarray] = None            # bool page-shaped: ink two same-size labels both reach
    contested_px: int = 0
    lost_px: Dict[str, int] = field(default_factory=dict)       # label id -> pixels a TIGHTER label took from it
    lost_to: Dict[str, List[str]] = field(default_factory=dict)  # ... and which labels
    contested_with: Dict[str, List[str]] = field(default_factory=dict)  # label id -> labels it is contested with
    contested_of: Dict[str, int] = field(default_factory=dict)  # label id -> its pixels left contested

    def summary(self) -> Dict:
        t = max(1, self.ink_px)
        un = self.ink_px - self.confirmed_px - self.pending_px - self.cellpass_px - self.contested_px
        return {"ink_px": self.ink_px, "claimed_px": self.confirmed_px, "pending_px": self.pending_px,
                "cellpass_px": self.cellpass_px, "unclaimed_px": un, "contested_px": self.contested_px,
                "claimed_pct": 100.0 * self.confirmed_px / t,
                "pending_pct": 100.0 * self.pending_px / t,
                "cellpass_pct": 100.0 * self.cellpass_px / t,
                "contested_pct": 100.0 * self.contested_px / t,
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
        self._cc = None         # connected pieces, built on first use (see _pieces)
        self._glue = None
        self.staff_lines = [(float(a), float(b), [float(y) for y in ys]) for a, b, ys in staff_lines]

    # ------------------------------------------------------------ one claim
    def _candidates(self, mode: str, sl: Tuple[slice, slice]) -> np.ndarray:
        if mode in ("all", "tall"):
            return self.rest[sl]
        if mode == "thin":
            return self.rest[sl] & ~self.blob[sl] & ~self.vert[sl]
        if mode == "vertical":
            return self.longvert[sl] & self.rest[sl]
        raise ValueError(mode)

    def claim(self, shape: Dict, kind: str, whole: bool = True) -> Claim:
        """The ink ``kind`` takes inside ``shape``. ``whole=False`` clips every kind at the shape's edge (the
        cell pass's boxes: a head box must not take its stem and beam with it)."""
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
        if mode in ("all", "tall") and whole:
            return self._claim_pieces(shape, mode, (x0, y0, x1, y1), inside, fy1 - fy0)
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

    # ------------------------------------------------------------ whole pieces (round 2)
    def _pieces(self):
        """Connected pieces of the page's non-staff ink, a staff line bridged where a glyph crosses it
        (ink directly above AND below the line pixel): a clef, a bracket or a barline is ONE piece."""
        if self._cc is None:
            k = 2 * self.hb + 2
            r8 = self.rest.view(np.uint8)
            above = cv2.dilate(r8, np.ones((k, 1), np.uint8), anchor=(0, k - 1)).astype(bool)
            below = cv2.dilate(r8, np.ones((k, 1), np.uint8), anchor=(0, 0)).astype(bool)
            self._glue = self.rest | (above & below & self.line)
            del above, below
            n, lab, stats, _ = cv2.connectedComponentsWithStats(self._glue.view(np.uint8), connectivity=8)
            self._cc = (n, lab, stats)
        return self._cc

    def _claim_pieces(self, shape: Dict, mode: str, box: Tuple[int, int, int, int], inside: np.ndarray,
                      box_h: float) -> Claim:
        """A RECTANGLE takes a connected piece WHOLE when at least half of it lies inside (and not at all when
        most of it lies outside); a TALL kind (bracket, brace) takes only pieces at least half the box's
        height; a POLYGON cuts exactly at its edge (the tool for splitting a merged piece)."""
        x0, y0, x1, y1 = box
        sl = (slice(y0, y1), slice(x0, x1))
        n, lab, stats = self._pieces()
        if "poly" in shape:
            cand = self._drop_specks(self._glue[sl] & inside, self.line[sl])
            return Claim(box, cand)
        sub = lab[sl]
        ids, counts = np.unique(sub[sub > 0], return_counts=True)
        none = Claim((x0, y0, x0, y0), np.zeros((0, 0), bool))
        if not len(ids):
            return none
        passes = np.ones(len(ids), bool)
        if mode == "tall":
            hh = stats[ids, cv2.CC_STAT_HEIGHT]
            passes = (hh >= TALL_FRAC * max(1.0, box_h)) & (hh >= TALL_MIN_SP * self.sp)
        keep = passes & (counts * 2 >= stats[ids, cv2.CC_STAT_AREA])
        if not passes.any():
            return none
        # The box sits on a MERGED piece (a brace that touches a bracket; a clef that touches a barline) when the
        # pieces it could take whole hold under half of the ink it holds of the pieces that qualify: nothing
        # else could be meant, so it cuts the merged piece at its edge (said on the label: "cut") rather than
        # claim a speck or nothing. A bracket box with its own tall stroke inside is NOT that case: the clef
        # pieces poking into it are small beside the stroke and stay unclaimed by it.
        merged = passes & ~keep
        cut = bool(merged.any() and counts[keep].sum() * 2 < counts[passes].sum())
        if not keep.any() and not cut:
            return none
        whole = ids[keep]
        rx0, ry0, rx1, ry1 = x0, y0, x1, y1
        if len(whole):
            rx0, ry0 = min(rx0, int(stats[whole, cv2.CC_STAT_LEFT].min())), min(ry0, int(stats[whole, cv2.CC_STAT_TOP].min()))
            rx1 = max(rx1, int((stats[whole, cv2.CC_STAT_LEFT] + stats[whole, cv2.CC_STAT_WIDTH]).max()))
            ry1 = max(ry1, int((stats[whole, cv2.CC_STAT_TOP] + stats[whole, cv2.CC_STAT_HEIGHT]).max()))
        reg = (slice(ry0, ry1), slice(rx0, rx1))
        mask = np.isin(lab[reg], whole) if len(whole) else np.zeros((ry1 - ry0, rx1 - rx0), bool)
        if cut:
            m2 = np.zeros_like(mask)
            m2[y0 - ry0:y1 - ry0, x0 - rx0:x1 - rx0] = np.isin(sub, ids[merged])
            mask |= m2
        if not len(whole):          # nothing taken whole: shrink to the box
            mask, reg = mask[y0 - ry0:y1 - ry0, x0 - rx0:x1 - rx0], (slice(y0, y1), slice(x0, x1))
            rx0, ry0, rx1, ry1 = x0, y0, x1, y1
        mask = self._drop_specks(mask, self.line[reg])
        return Claim((rx0, ry0, rx1, ry1), mask, cut=cut)

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
        """Resolve every claiming label (confirmed + pending) by the rule in the module docstring:
        confirmed before pre-fill; a staff label owns the staff-line pixels it reaches; otherwise the
        TIGHTER shape wins; shapes of about one size leave the pixel CONTESTED (owned by neither)."""
        labs = list(labels)
        n = len(labs)
        areas = np.array([shape_area(l.shape) for l in labs] + [0.0])
        is_staff = np.array([l.kind == "staff" for l in labs] + [False])
        order = sorted(range(n), key=lambda i: (labs[i].state != "confirmed", labs[i].kind != "staff",
                                                areas[i], KINDS.index(labs[i].kind), labs[i].id))
        owner = np.zeros((self.h, self.w), np.int32)
        contested = np.zeros((self.h, self.w), bool)
        raw: Dict[str, int] = {}
        claims_: Dict[int, Claim] = {}
        lost: Dict[int, Dict[int, int]] = {}          # label index -> {winner index: px lost}
        cont_pairs: Dict[int, Dict[int, int]] = {}    # label index -> {other index: px contested}
        for i in order:
            lab = labs[i]
            c = self.claim(lab.shape, lab.kind)
            raw[lab.id] = c.px
            claims_[i] = c
            if c.mask.size == 0:
                continue
            x0, y0, x1, y1 = c.bbox
            region, creg = owner[y0:y1, x0:x1], contested[y0:y1, x0:x1]
            free = c.mask & (region == 0) & ~creg
            clash = c.mask & (region > 0)
            if clash.any():
                other = region[clash].astype(np.int64) - 1
                if lab.state == "confirmed":
                    # same-size shapes (neither is the tighter) and not a staff label's line pixels: contested
                    same = (areas[i] <= CLOSE_AREA * areas[other]) & ~is_staff[other] & ~is_staff[i]
                    if same.any():
                        cy, cx = np.nonzero(clash)
                        cy, cx, oo = cy[same], cx[same], other[same]
                        for o, cnt in zip(*np.unique(oo, return_counts=True)):
                            cont_pairs.setdefault(i, {})[int(o)] = cont_pairs.setdefault(i, {}).get(int(o), 0) + int(cnt)
                            cont_pairs.setdefault(int(o), {})[i] = cont_pairs.setdefault(int(o), {}).get(i, 0) + int(cnt)
                        region[cy, cx] = 0
                        creg[cy, cx] = True
                        other = other[~same]
                for o, cnt in zip(*np.unique(other, return_counts=True)):
                    lost.setdefault(i, {})[int(o)] = lost.setdefault(i, {}).get(int(o), 0) + int(cnt)
            region[free] = i + 1
        counts = np.bincount(owner.ravel(), minlength=n + 1)
        px: Dict[str, int] = {}
        refs: Dict[str, Dict] = {}
        for i, lab in enumerate(labs):
            c = claims_[i]
            px[lab.id] = int(counts[i + 1])
            if c.mask.size:
                x0, y0, x1, y1 = c.bbox
                mine = owner[y0:y1, x0:x1] == i + 1
            else:
                mine = c.mask
            refs[lab.id] = self._ref(lab, c, mine)
            if c.cut and int(counts[i + 1]):
                refs[lab.id]["cut"] = True
        conf = np.zeros(n + 1, bool)
        pend = np.zeros(n + 1, bool)
        for i, lab in enumerate(labs):
            conf[i + 1] = lab.state == "confirmed"
            pend[i + 1] = lab.state == "pending"
        cp = 0
        if cellpass is not None:
            cp = int((cellpass & self.ink & (owner == 0) & ~contested).sum())
        ids = [l.id for l in labs]
        for i, d in cont_pairs.items():
            refs[ids[i]]["contested_px"] = int(sum(d.values()))
        return Claims(owner=owner, labels=labs, px=px, raw_px=raw, refs=refs,
                      ink_px=int(self.ink.sum()), confirmed_px=int(conf[owner].sum()),
                      pending_px=int(pend[owner].sum()), cellpass_px=cp,
                      contested=contested, contested_px=int((contested & self.ink).sum()),
                      lost_px={ids[i]: int(sum(d.values())) for i, d in lost.items()},
                      lost_to={ids[i]: [ids[o] for o in sorted(d, key=lambda k: -d[k])] for i, d in lost.items()},
                      contested_with={ids[i]: [ids[o] for o in sorted(d, key=lambda k: -d[k])]
                                      for i, d in cont_pairs.items()},
                      contested_of={ids[i]: int(sum(d.values())) for i, d in cont_pairs.items()})

    def _ref(self, lab: PLabel, c: Claim, mask: np.ndarray) -> Dict:
        """The claimed-ink reference stored on the label: the rule, how much, where, a hash of which."""
        x0, y0, x1, y1 = c.bbox
        ys, xs = np.nonzero(mask) if mask.size else (np.array([]), np.array([]))
        bb = [int(x0 + xs.min()), int(y0 + ys.min()), int(x0 + xs.max()) + 1, int(y0 + ys.max()) + 1] \
            if len(xs) else None
        digest = hashlib.sha1(np.packbits(mask).tobytes()).hexdigest()[:16] if mask.size else ""
        return {"rule": RULE_VERSION, "mode": KIND_MODE[lab.kind], "px": int(mask.sum()),
                "bbox": bb, "sha1": digest}

    def _mid_line_y(self, x: float, y: float) -> Optional[float]:
        best, bd = None, 3.0 * self.sp
        for x0, x1, ys in self.staff_lines:
            if x0 <= x <= x1 and len(ys) >= 3:
                d = abs(sorted(ys)[len(ys) // 2] - y)
                if d <= bd:
                    best, bd = sorted(ys)[len(ys) // 2], d
        return best

    def meter_parts(self, bbox: Tuple[int, int, int, int], mask: np.ndarray, value: Optional[str]) -> List[Dict]:
        """The per-digit ink pieces of ONE meter label, read from the ink it owns, so a detector can later get digit
        boxes from the one label (README: ``parts``). A stacked meter is cut at its staff's middle line (the numeral
        above, the denominator below -- ink is not cut by a staff line, which crosses a 6 or an 8); each row is
        cut into digits at gaps in its columns. A digit gets its character only when the value's row has exactly
        that many digits; otherwise the row stays one piece carrying the row's text (or none)."""
        from tools.omr.hand_truth.pagepass import meter_split

        if mask.size == 0 or not mask.any():
            return []
        x0, y0 = bbox[0], bbox[1]
        rows = meter_split(value)
        ys = np.nonzero(mask.any(axis=1))[0]
        cy = y0 + (ys.min() + ys.max()) / 2.0
        groups: List[Tuple[np.ndarray, Optional[str]]]
        if len(rows) == 2:
            mid = self._mid_line_y(x0 + mask.shape[1] / 2.0, cy)
            cut = int(round((mid if mid is not None else cy) - y0))
            top, bot = mask.copy(), mask.copy()
            top[cut:, :] = False
            bot[:cut, :] = False
            groups = [(top, rows[0]), (bot, rows[1])]
        else:
            groups = [(mask, rows[0] if len(rows) == 1 else None)]
        out: List[Dict] = []
        for g, text in groups:
            if not g.any():
                continue
            cols = g.any(axis=0)
            xs = np.nonzero(cols)[0]
            runs, start = [], xs[0]
            for a, b in zip(xs[:-1], xs[1:]):
                if b - a > 3:
                    runs.append((start, a))
                    start = b
            runs.append((start, xs[-1]))
            texts: List[Optional[str]] = [None] * len(runs)
            if text and len(text) == len(runs) and text.isdigit():
                texts = list(text)
            elif text and len(runs) > 1:
                runs, texts = [(runs[0][0], runs[-1][1])], [text]       # not enough to name each digit: one piece
            elif text:
                texts = [text]
            for (a, b), t in zip(runs, texts):
                sub = g[:, a:b + 1]
                yy = np.nonzero(sub.any(axis=1))[0]
                out.append({"rect": [float(x0 + a), float(y0 + yy.min()), float(x0 + b + 1), float(y0 + yy.max() + 1)],
                            "text": t, "from": "ink"})
        return out

    def owned_mask(self, claims: Claims, label_id: str) -> Tuple[Tuple[int, int, int, int], np.ndarray]:
        """(bbox, mask) of exactly the ink ``label_id`` owns after precedence -- what hovering it highlights."""
        i = next(k for k, l in enumerate(claims.labels) if l.id == label_id)
        ref = claims.refs[label_id].get("bbox")
        if not ref:
            return (0, 0, 0, 0), np.zeros((0, 0), bool)
        x0, y0, x1, y1 = ref
        return (x0, y0, x1, y1), claims.owner[y0:y1, x0:x1] == i + 1

    def cellpass_mask(self, rects: Iterable[Rect]) -> np.ndarray:
        """Ink under cell-pass boxes (all non-staff ink in each rectangle), as one page mask."""
        out = np.zeros((self.h, self.w), bool)
        for r in rects:
            c = self.claim({"rect": list(r)}, "word", whole=False)     # 'all' mode, clipped at the box
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
            if claims.contested is not None:
                code[ink & claims.contested[sl]] = CONTESTED
        return code


def render_states(code: np.ndarray, out_w: int) -> np.ndarray:
    """BGR picture of a state-code region at ``out_w`` px wide (thin ink boosted so it stays visible)."""
    h, w = code.shape
    pal = np.zeros((6, 3), np.uint8)
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


def owned_overlay_rgba(mask: np.ndarray, out_w: int) -> np.ndarray:
    """RGBA picture of ONE label's owned ink (black with a white halo, so it reads on blue, pink or white),
    ``out_w`` px wide; the height follows the mask's shape. Thin ink is widened when shrunk, as render_states does."""
    h, w = mask.shape
    scale = out_w / float(max(1, w))
    out_h = max(1, int(round(h * scale)))
    m = mask.astype(np.float32)
    if scale >= 1.0:
        a = cv2.resize(m, (out_w, out_h), interpolation=cv2.INTER_NEAREST)
        a = a > 0.5
    else:
        a = cv2.resize(m, (out_w, out_h), interpolation=cv2.INTER_AREA)
        a = a * min(6.0, max(1.0, 0.35 / scale)) > 0.25
    halo = cv2.dilate(a.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    rgba = np.zeros((out_h, out_w, 4), np.uint8)
    rgba[halo] = (255, 255, 255, 235)
    rgba[a] = (0, 0, 0, 255)
    return rgba


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
