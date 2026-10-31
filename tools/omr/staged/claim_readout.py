"""ROADMAP 2.236 -- THE CAPTURE READOUT: per page and per kind, which ink is claimed once, contested, claimed twice, or unclaimed.

    python3 -m tools.omr.staged.claim_readout REC [--pages 0,4] [--truth auto] [--tiles DIR] [--out DIR] [--env NAME=V ...]
    python3 -m tools.omr.staged.claim_readout controls REC --page 0          # the three controls that can fail (module doc, 5)

PATH: STAGED GATHER's claim register and ADJUDICATE's `stroke_owner` verdict, READ -- this module files no row, decides nothing and
names no quantity it writes (registered in `reach.NOT_A_STAGE`, `rule_kinds.INFRA`). Why (Sean, 2026-10-30): "as we're working on the
gather stage, what matters most is that we are capturing the ink and designating it" -- CLAUDE north star: all ink is accounted for
ONE time. Until now each lane built a one-off script ("136/153 arcs", "49/60 words"); this is the one command.

REC is a SLICE DIRECTORY (`observations.jsonl` + `abstentions.jsonl`: `lane_report`'s frozen-sample slices, `PLATE:TAG` such as
`brahms:20261029-night` names them) or a `.record.json` (cut once into `library/_shared-records/claim-readout-slices-*`, streamed, GATHER
rows only). A record over 5 GB is refused: the 19.6 GB Brahms record is never loaded -- use its lane-report slices.

WHAT IS COUNTED. INK is the page's own dark pixels (`pws.page.binary`, the render the cells were cut from); the denominator of every share.
CLAIMS are the pipeline's own, not a second copy: (1) `adjudicate_stroke_owner` is RE-RUN on the GATHER rows (no stage but that one; ~1 s a
page) and its per-stroke candidates are the claims -- detector boxes (`Q.GLYPH_STROKES`), the register's READ areas (clef, key, meter, header
column, barlines, page-wide words and brackets), the arc trace, a found whole rest. A claim whose shape does not fit its stroke (`fit: no`,
the "refused claim") is NOT standing; (2) the CONSUMER boxes the tiers leave out (detector stem / beam / flag boxes, by `Q.GLYPH_STROKES`);
(3) the cv_lines stem / beam readers' own rows, counted ONLY on a stroke nothing else claims (a second witness agreeing is corroboration,
not a claim). A word / dynamic / bracket READ in the page margin outside every cell claims by its area. A GUESSED / NARROWED area claim is
WEAK: reported on its own, never as captured.

HOW THE STROKES ARE DE-DUPLICATED IN PAGE PIXELS. A stroke lives in ONE padded cell on that cell's erased raster, and neighbouring cells
overlap, so the same page ink is a stroke in two cells' maps. The cells are re-cut from the MASTER CELL MAP (`cell_map.load_prepared`, proved
hash-equal), `stroke_map.map_strokes` is re-run on each, and the recomputed strokes are checked box for box against the record's own
`Q.STROKE` rows (a cell that does not match is dropped and counted, never read; the ordinals would be another cell's). Each cell's stroke
label image is then sampled (centre-aligned nearest) onto the cell's PAGE rectangle and OR-ed into ONE page canvas: a page pixel carries the
UNION of the claim kinds (a bitmask) that any cell saw on it, and the COUNT of detector-box claims summed over cells. So the same ink in two
cells is one pixel with one set of kinds; two BOXES (same cell or two cells) on it make it a TWIN claim, two KINDS make it CONTESTED. Shares
are of that one page ink; staff-line ink is the cell's raw ink the eraser took (claimed by the staff), ink in a cell with no stroke is
DEBRIS (under the 0.05 sp^2 stroke floor, or edge), ink outside every cell is claimed only by a READ area (a margin word) else
`outside_cells`.

STATES (ink px): unclaimed | one owner | twin (one kind, two or more boxes) | contested (two or more kinds; `settled` when the stroke owner
chose by tier or shape, `open` when it left the stroke contested). Owner kinds: head, ledger, accidental, dot, rest, arc, hairpin, stem, beam,
flag, word_dynamic, mark, bracket (brace, bracket, header column), barline, clef_key_meter, staff_line.

AGAINST SEAN'S LABELS (`--truth auto`: the aligned hand-truth file of the same master, `tools.omr.hand_truth.align`; a stale or other-master
alignment is refused). Each truth box's ink (staff-line pixels left out) is read off the canvas: RIGHT (the box's coarse kind holds at least half its ink), NOTHING
(at least half unclaimed), WRONG KIND (another kind holds at least half), else SPLIT. Only Sean's labels say what is right; our own claims never
score themselves.

CONTROLS THAT CAN FAIL (`controls`): (a) `OMR_ARC_CLAIM=0` re-adjudicates the same rows and the register's arc claims must DROP; (b) a double
claim planted on real ink must turn up as contested; (c) the readout of an identical copy of the rows must equal the first, byte for byte; and the
stroke-for-stroke match of the re-cut cells against the record is printed for every run.

CONVENTION ASSUMED: the claim states above and the 0.5 / 0.5 truth cut (the register's one cut, `COVER_SHARE_MIN`). WHAT WOULD FALSIFY IT: a
truth box Sean calls right that reads WRONG KIND only because a neighbour's ink sits inside its rectangle (reported, not hidden: the share
columns are printed). NOT CONFIRMED beyond the two plates (Brahms p0 is the only labelled page).
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np

DERIVED_CHECK = False
ROOT = pathlib.Path(__file__).resolve().parents[3]
LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
RECORDS = LIB / "_shared-records"
BIG_RECORD_BYTES = 5 * 1024 ** 3
#: ink of an unclaimed stroke this close (staff spaces) to one of its cell's own staff lines is STAFF-LINE RESIDUE, not a mark
LINE_NEAR_SPACES = 0.2
STROKE_BASE = 375_000                    # record.STROKE_GLYPH_BASE: glyph ordinals from here number a cell's strokes
ORANGE = (255, 140, 0)

# ───────────────────────────── 1. the vocabulary ─────────────────────────────

#: coarse owner kinds, in print order. The bit of a kind in the page canvas is its index here.
KINDS = ("head", "ledger", "accidental", "dot", "rest", "arc", "hairpin", "stem", "beam", "flag", "word_dynamic", "mark",
         "bracket", "barline", "clef_key_meter")
KIND_BIT = {k: 1 << i for i, k in enumerate(KINDS)}
#: stroke_owner family (and the register's owner names) -> coarse kind
FAMILY_KIND = {
    "head": "head", "ledger": "ledger", "accidental": "accidental", "dot": "dot", "rest": "rest", "whole_rest": "rest",
    "arc": "arc", "arc_trace": "arc", "hairpin": "hairpin", "stem": "stem", "beam": "beam", "flag": "flag",
    "dynamic": "word_dynamic", "word": "word_dynamic", "mark": "mark", "text": "mark",
    "bracket": "bracket", "leading_column": "bracket", "barline": "barline",
    "clef": "clef_key_meter", "meter": "clef_key_meter", "key_signature": "clef_key_meter",
}
CONSUMER_FAMILIES = ("stem", "beam", "flag")
STROKE_KINDS = ("vertical", "horizontal", "curve", "blob")

#: Sean's label class -> the coarse kinds that count as RIGHT for it. A bar line at a system's start is the header column's.
TRUTH_KINDS: Dict[str, Tuple[str, ...]] = {
    "stem": ("stem",), "beam": ("beam",), "ledgerLine": ("ledger",), "augmentationDot": ("dot",),
    "tie": ("arc",), "slur": ("arc",), "text": ("word_dynamic",), "tremolo1": ("mark",), "brace": ("bracket",),
    "barlineSingle": ("barline", "bracket"), "barlineDouble": ("barline", "bracket"),
    "keyFlat": ("clef_key_meter", "accidental"), "keySharp": ("clef_key_meter", "accidental"),
    "keyNatural": ("clef_key_meter", "accidental"),
}
for _c in ("noteheadBlackInSpace", "noteheadBlackOnLine", "noteheadHalfInSpace", "noteheadHalfOnLine", "noteheadWholeInSpace",
           "noteheadWholeOnLine", "noteheadDoubleWholeInSpace", "noteheadDoubleWholeOnLine"):
    TRUTH_KINDS[_c] = ("head",)
for _c in ("accidentalSharp", "accidentalFlat", "accidentalNatural", "accidentalDoubleSharp", "accidentalDoubleFlat"):
    TRUTH_KINDS[_c] = ("accidental",)
for _c in ("flag8thDown", "flag8thUp", "flag16thDown", "flag16thUp"):
    TRUTH_KINDS[_c] = ("flag",)
for _c in ("dynamicF", "dynamicP", "dynamicM", "dynamicS", "dynamicZ", "dynamicR"):
    TRUTH_KINDS[_c] = ("word_dynamic",)
for _c in ("restWhole", "restHalf", "restQuarter", "rest8th", "rest16th", "rest32nd"):
    TRUTH_KINDS[_c] = ("rest",)
for _c in ("clefG", "clefF", "clefCAlto", "clefCTenor", "timeSig0", "timeSig1", "timeSig2", "timeSig3", "timeSig4", "timeSig5",
           "timeSig6", "timeSig7", "timeSig8", "timeSig9", "timeSigCommon", "timeSigCutCommon"):
    TRUTH_KINDS[_c] = ("clef_key_meter",)

# unclaimed-stroke codes in the canvas: 1..4 the stroke kind, 5..8 the same where a claim stood but its shape did not fit (refused)
UK_NAMES = {i + 1: "unclaimed:" + k for i, k in enumerate(STROKE_KINDS)}
UK_NAMES.update({i + 5: "refused:" + k for i, k in enumerate(STROKE_KINDS)})


# -- ROADMAP 2.239: ONE MARK, ONE PIECE, OF A PLAUSIBLE SHAPE (Sean 2026-10-30: "I thought we had limits to box sizes") --
#: a truth box is WHOLE when its largest single piece of the right kind holds at least this share of the box's ink (the coordinator's brief)
WHOLE_SHARE = 0.85
#: a piece claimed as one kind must have that kind's shape; the limits are the project's own, never tuned here:
#: head -- `head_ink.MIN_SPACES` (0.6) both ways, `head_ink.MAX_WIDTH_SPACES` (1.75) wide, `head_ink.MAX_HEIGHT_SPACES_V2` (1.6, Sean) tall;
#: ledger -- a line: `stroke_map.CURVE_MAX_THICK_SPACES` (0.5) thick at most and level within `stroke_map.LEDGER_MAX_SLOPE` (2.239);
#: stem -- `stroke_map.STEM_TRUE_WIDTH_MAX_SPACES` (0.7, 2.206d) wide at most and STEM_MIN_TALL_SPACES tall, or touching another stroke.
#: Beams and flags are not shape-tested yet (said in the report, not hidden).
STEM_MIN_TALL_SPACES = 2.5          # the coordinator's brief ("a stem is thin and >= ~2.5 sp tall or attached"); a stem is ~3.5 sp by convention
SHAPE_KINDS = ("head", "ledger", "stem")


def misshapen_why(kind: str, piece: Dict[str, Any]) -> Optional[str]:
    """Why a piece claimed as `kind` is not that kind's shape (None = it is, or the kind is not shape-tested)."""
    import math
    from . import head_ink as HI
    from . import stroke_map as SM
    w, h = piece["w_sp"], piece["h_sp"]
    if kind == "head":
        if w < HI.MIN_SPACES or h < HI.MIN_SPACES:
            return "head_too_small"
        if w > HI.MAX_WIDTH_SPACES:
            return "head_too_wide"
        if h > HI.MAX_HEIGHT_SPACES_V2:
            return "head_too_tall"
    elif kind == "ledger":
        if piece["shape"] not in ("horizontal", "curve") or piece["thick_sp"] > SM.CURVE_MAX_THICK_SPACES:
            return "ledger_not_a_line"
        if abs(math.tan(math.radians(piece["angle"]))) > SM.LEDGER_MAX_SLOPE:
            return "ledger_not_level"
    elif kind == "stem":
        if w > SM.STEM_TRUE_WIDTH_MAX_SPACES:
            return "stem_too_wide"
        if h < STEM_MIN_TALL_SPACES and not piece["touches"]:
            return "stem_short_and_alone"
    return None


def kind_of(family: str) -> Optional[str]:
    return FAMILY_KIND.get(family)


def mask_kinds(m: int) -> Tuple[str, ...]:
    return tuple(k for k in KINDS if m & KIND_BIT[k])


# ───────────────────────────── 2. one stroke's claims, and the page canvas (PURE) ─────────────────────────────

@dataclass
class StrokeClaims:
    """What claims one stroke of one cell. `kinds` = coarse kinds with a STANDING claim; `register` the subset claimed by an area / trace;
    `n_box` the distinct detector boxes; `shape` the stroke's own kind; `refused` a claim stood but its shape did not fit; `open` the stroke
    owner left it contested."""
    shape: str = "blob"
    kinds: Set[str] = field(default_factory=set)
    register: Set[str] = field(default_factory=set)
    n_box: int = 0
    refused: bool = False
    open: bool = False


def _centre_index(n_dst: int, n_src: int) -> np.ndarray:
    return np.minimum(((np.arange(n_dst) + 0.5) * n_src / float(n_dst)).astype(np.int64), n_src - 1)


def sample_to_rect(arr: np.ndarray, w: int, h: int) -> np.ndarray:
    """`arr` (any frame) sampled centre-aligned nearest onto a w x h page rectangle."""
    return arr[np.ix_(_centre_index(h, arr.shape[0]), _centre_index(w, arr.shape[1]))]


def fill_labels(lab: np.ndarray) -> np.ndarray:
    """One reduced pixel of dilation into unlabelled pixels (the page ink at a stroke's edge lies a fraction of a reduced pixel outside its mask)."""
    import cv2
    f = lab.astype(np.float32)
    d = cv2.dilate(f, np.ones((3, 3), np.uint8))
    return np.where(lab == 0, d, f).astype(lab.dtype)


class PageInk:
    """ONE page's claim canvas. `add_cell` ORs a cell's strokes in page pixels; `tally` counts the ink px by state and kind."""

    def __init__(self, ink: np.ndarray):
        self.ink = ink.astype(bool)
        h, w = self.ink.shape
        self.shape = (h, w)
        self.fam = np.zeros((h, w), np.uint32)          # coarse kinds with a standing claim on the pixel (any cell)
        self.reg = np.zeros((h, w), np.uint32)          # ... of those, the ones claimed by the register (area / trace)
        self.nbox = np.zeros((h, w), np.uint8)          # detector-box claims summed over cells (saturating)
        self.seen = np.zeros((h, w), bool)              # a stroke of some cell stands on it
        self.uk = np.zeros((h, w), np.uint8)            # unclaimed-stroke code (UK_NAMES)
        self.opn = np.zeros((h, w), bool)               # the stroke owner left it contested
        self.incell = np.zeros((h, w), bool)
        self.staff = np.zeros((h, w), bool)             # raw ink the staff-line eraser took
        self.afam = np.zeros((h, w), np.uint32)         # READ area claims (applied outside cells only)
        self.weak = np.zeros((h, w), np.uint32)         # GUESSED / NARROWED area claims
        self.nearline = np.zeros((h, w), bool)         # within LINE_NEAR_SPACES of a staff line at the cell's own lines
        self.sid = np.zeros((h, w), np.int32)            # 2.239: which stroke (page-unique id) holds the pixel (the last cell written)
        self.pieces: Dict[int, Dict[str, Any]] = {}      # 2.239: id -> shape, size in sp, page box, claimed kinds
        self.cells_added = 0
        self.naive_stroke_px = 0                        # stroke ink px summed per cell, NOT de-duplicated (the control's contrast)

    def add_cell(self, rect: Sequence[int], labels: np.ndarray, claims: Dict[int, StrokeClaims],
                 erased_staff: Optional[np.ndarray] = None, lines_page: Sequence[float] = (),
                 meta: Optional[Dict[int, Dict[str, Any]]] = None) -> None:
        """`rect` = the cell's page rectangle (x0, y0, x1, y1); `labels` = its stroke label image in ANY frame (0 none, i = stroke ordinal + 1)
        and `claims[i]` that stroke's claims; `erased_staff` = a bool image (any frame) of the raw ink the eraser took."""
        x0, y0, x1, y1 = (int(v) for v in rect)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.shape[1], x1), min(self.shape[0], y1)
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0:
            return
        n = int(labels.max()) + 1 if labels.size else 1
        fam_t = np.zeros(n, np.uint32)
        reg_t = np.zeros(n, np.uint32)
        nbox_t = np.zeros(n, np.uint8)
        uk_t = np.zeros(n, np.uint8)
        opn_t = np.zeros(n, bool)
        for i, c in claims.items():
            if i >= n:
                continue
            fam_t[i] = sum(KIND_BIT[k] for k in c.kinds)
            reg_t[i] = sum(KIND_BIT[k] for k in c.register)
            nbox_t[i] = min(c.n_box, 255)
            if not c.kinds:
                code = STROKE_KINDS.index(c.shape) + 1 if c.shape in STROKE_KINDS else 4
                uk_t[i] = code + (4 if c.refused else 0)
            opn_t[i] = c.open
        lab = sample_to_rect(fill_labels(labels), w, h)
        sl = (slice(y0, y1), slice(x0, x1))
        self.fam[sl] |= fam_t[lab]
        self.reg[sl] |= reg_t[lab]
        self.nbox[sl] = np.minimum(self.nbox[sl].astype(np.int16) + nbox_t[lab], 255).astype(np.uint8)
        self.seen[sl] |= lab > 0
        self.uk[sl] = np.maximum(self.uk[sl], uk_t[lab])
        self.opn[sl] |= opn_t[lab]
        self.incell[sl] = True
        if meta:
            sid_t = np.zeros(n, np.int32)
            for i, md in meta.items():
                if 0 < i < n:
                    pid = len(self.pieces) + 1
                    c = claims.get(i)
                    self.pieces[pid] = {**md, "kinds": sorted(c.kinds) if c else []}
                    sid_t[i] = pid
            got = sid_t[lab]
            self.sid[sl] = np.where(got > 0, got, self.sid[sl])
        if len(lines_page) >= 2:
            u = (lines_page[-1] - lines_page[0]) / (len(lines_page) - 1)
            for ly in lines_page:
                a, b = max(y0, int(round(ly - LINE_NEAR_SPACES * u))), min(y1, int(round(ly + LINE_NEAR_SPACES * u)) + 1)
                if b > a:
                    self.nearline[a:b, x0:x1] = True
        if erased_staff is not None:
            self.staff[sl] |= sample_to_rect(erased_staff.astype(np.uint8), w, h).astype(bool)
        self.cells_added += 1
        self.naive_stroke_px += int((self.ink[sl] & (lab > 0)).sum())

    def add_area(self, rect: Sequence[float], kind: str, weak: bool = False) -> None:
        """A page-px area claim (`Q.CLAIMED_AREA`, unit area): it claims the ink OUTSIDE every cell (a margin word); inside a cell the stroke
        owner already counted it."""
        x0, y0, x1, y1 = (int(round(v)) for v in rect)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.shape[1], x1), min(self.shape[0], y1)
        if x1 <= x0 or y1 <= y0:
            return
        (self.weak if weak else self.afam)[y0:y1, x0:x1] |= np.uint32(KIND_BIT[kind])

    # ── the states, per ink pixel ──
    def finish(self) -> None:
        """Freeze the per-pixel category: `cat` an int8 image, `CATS` its names."""
        ink = self.ink
        fam = np.where(self.incell, self.fam, self.afam)
        nb = np.where(self.incell, self.nbox, 0)
        pop = np.zeros(fam.shape, np.uint8)
        for i in range(len(KINDS)):
            pop += ((fam >> i) & 1).astype(np.uint8)
        self.fam_eff, self.pop = fam, pop
        cat = np.full(self.shape, -1, np.int16)
        names: List[str] = []
        idx: Dict[str, int] = {}

        def code(name: str) -> int:
            if name not in idx:
                idx[name] = len(names)
                names.append(name)
            return idx[name]

        def put(sel: np.ndarray, name: str) -> None:
            if sel.any():
                cat[sel & (cat < 0)] = code(name)

        claimed = ink & (pop > 0)
        put(claimed & (pop >= 2) & self.opn & self.incell, "contested_open")
        put(claimed & (pop >= 2), "contested_settled")
        put(claimed & (pop == 1) & (nb >= 2), "twin")
        put(claimed & (pop == 1), "one")
        rest = ink & (pop == 0)
        wk = self.weak != 0
        put(rest & wk, "weak_claim")
        for c, name in UK_NAMES.items():
            # only line-shaped strokes (horizontal, curve) can be residue: a stem or a blob crosses a line without being one
            if name.split(":")[1] in ("horizontal", "curve"):
                put(rest & self.incell & self.seen & self.nearline & (self.uk == c), "residue:" + name.split(":")[1])
        for c, name in UK_NAMES.items():
            put(rest & self.incell & self.seen & (self.uk == c), name)
        put(rest & self.incell & self.seen, "unclaimed:blob")
        put(rest & self.incell & ~self.seen & self.staff, "staff_line")
        put(rest & self.incell & ~self.seen, "debris")
        put(rest & ~self.incell, "outside_cells")
        self.cat, self.cat_names = cat, names
        # the staff line, as an owner kind: claimed by the staff geometry that erased it
        # ink with no category cannot exist: every ink pixel is either claimed or in `rest`
        assert not (ink & (cat < 0)).any()

    def tally(self) -> Dict[str, Any]:
        """The page's ink px, by state and by kind (module doc)."""
        ink = self.ink
        total = int(ink.sum())
        out: Dict[str, Any] = {"ink_px": total}
        cat = self.cat[ink]
        counts = np.bincount(cat, minlength=len(self.cat_names)) if cat.size else np.zeros(len(self.cat_names), int)
        by_state = {n: int(counts[i]) for i, n in enumerate(self.cat_names) if counts[i]}
        out["state_px"] = by_state
        fam = self.fam_eff[ink]
        pop = self.pop[ink]
        one = collections.Counter()
        twin = collections.Counter()
        con = collections.Counter()
        for c_name, store in (("one", one), ("twin", twin)):
            if c_name in self.cat_names:
                sel = cat == self.cat_names.index(c_name)
                vals, n = np.unique(fam[sel], return_counts=True)
                for v, k in zip(vals, n):
                    store[mask_kinds(int(v))[0]] += int(k)
        for c_name in ("contested_open", "contested_settled"):
            if c_name in self.cat_names:
                sel = cat == self.cat_names.index(c_name)
                vals, n = np.unique(fam[sel], return_counts=True)
                for v, k in zip(vals, n):
                    con[("+".join(mask_kinds(int(v))), c_name.split("_")[1])] += int(k)
        out["one_by_kind"] = dict(one)
        out["twin_by_kind"] = dict(twin)
        out["contested_by_pair"] = {"%s|%s" % k: v for k, v in con.items()}
        # the register's share: ink claimed by an area or a trace (any kind) among the claimed ink
        reg = self.reg[ink]
        out["register_px_by_kind"] = {k: int(((reg & KIND_BIT[k]) != 0).sum()) for k in KINDS if (reg & KIND_BIT[k]).any()}
        out["claimed_px_by_kind"] = {k: int(((fam & KIND_BIT[k]) != 0).sum()) for k in KINDS if (fam & KIND_BIT[k]).any()}
        out["naive_stroke_px"] = self.naive_stroke_px
        out["stroke_px_deduped"] = int((ink & self.incell & self.seen).sum())
        out["cells"] = self.cells_added
        return out

    # ── Sean's labels ──
    def judge_box(self, rect: Sequence[float], accept: Sequence[str], source: str = "any") -> Dict[str, Any]:
        """RIGHT / NOTHING / WRONG KIND / SPLIT for one truth rectangle (module doc). `source` 'register' reads only area / trace claims."""
        x0, y0, x1, y1 = (int(round(v)) for v in rect)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.shape[1], x1), min(self.shape[0], y1)
        if x1 <= x0 or y1 <= y0:
            return {"verdict": "no_ink", "ink_px": 0}
        sl = (slice(y0, y1), slice(x0, x1))
        sel = self.ink[sl] & ~(self.staff[sl] & ~self.seen[sl])
        n = int(sel.sum())
        if n < 4:
            return {"verdict": "no_ink", "ink_px": n}
        if source == "register":
            fam = np.where(self.incell[sl], self.reg[sl], self.afam[sl])[sel]
        else:
            fam = self.fam_eff[sl][sel]
        want = np.uint32(sum(KIND_BIT[k] for k in accept))
        right = float(((fam & want) != 0).mean())
        none = float((fam == 0).mean())
        wrong = float(((fam != 0) & ((fam & want) == 0)).mean())
        if right >= 0.5:
            v = "right"
        elif none >= 0.5:
            v = "nothing"
        elif wrong >= 0.5:
            v = "wrong_kind"
        else:
            v = "split"
        out = {"verdict": v, "ink_px": n, "right": round(right, 3), "nothing": round(none, 3), "wrong": round(wrong, 3),
               "contested": float(((self.pop[sl][sel]) >= 2).mean())}
        # 2.239: ONE MARK, ONE PIECE -- the largest single piece of the right kind, its share of the box's ink, the piece count, its shape
        ids = self.sid[sl][sel][(fam & want) != 0]
        ids = ids[ids > 0]
        if ids.size:
            vals, cnt = np.unique(ids, return_counts=True)
            k = int(np.argmax(cnt))
            big = int(vals[k])
            out["largest_share"] = round(float(cnt[k]) / n, 3)
            out["n_pieces"] = int((cnt >= 4).sum())
            kind = next((a for a in accept if a in SHAPE_KINDS), None)
            pc = self.pieces.get(big, {})
            out["misshapen"] = misshapen_why(kind, pc) if (kind and pc) else None
            out["piece_box"] = pc.get("page_box")
        else:
            out["largest_share"], out["n_pieces"], out["misshapen"] = 0.0, 0, None
        if v == "right":
            out["strict"] = ("misshapen" if out["misshapen"] else
                             "whole" if out["largest_share"] >= WHOLE_SHARE else "fragmented")
        else:
            out["strict"] = v
        return out

    def misshapen_pieces(self) -> Dict[str, List[Dict[str, Any]]]:
        """2.239: every piece claimed as ONE shape-tested kind (head / ledger / stem) whose shape is not that kind's, with its page box."""
        out: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
        for pid, pc in self.pieces.items():
            ks = [k for k in pc.get("kinds", ()) if k in SHAPE_KINDS]
            if len(pc.get("kinds", ())) != 1 or not ks:
                continue
            why = misshapen_why(ks[0], pc)
            if why:
                out[ks[0]].append({"why": why, "page_box": pc.get("page_box"), "shape": pc.get("shape"),
                                   "w_sp": pc["w_sp"], "h_sp": pc["h_sp"]})
        return dict(out)


# ───────────────────────────── 3. reading rows ─────────────────────────────

def page_of_subject(sub: str) -> Optional[int]:
    p = (sub or "").split("/")
    if len(p) >= 2 and p[0] in ("glyph", "cell", "staff", "system", "mark", "page", "mg", "measure") and p[1].lstrip("-").isdigit():
        return int(p[1])
    return None


def cell_key(sub: str) -> Optional[Tuple[int, int, int, int]]:
    p = sub.split("/")
    if p[0] in ("glyph", "cell") and len(p) >= 5:
        try:
            return int(p[1]), int(p[2]), int(p[3]), int(p[4])
        except ValueError:
            return None
    return None


def read_rows(src: pathlib.Path, pages: Sequence[int]) -> Dict[str, List[dict]]:
    """The slice's GATHER rows of `pages` plus every document-level row (jsonl, filtered by a cheap subject sniff before parsing)."""
    keep = set(pages)
    out: Dict[str, List[dict]] = {"observations": [], "abstentions": [], "verdicts": []}
    for kind in ("observations", "abstentions"):
        with open(src / ("%s.jsonl" % kind)) as fh:
            for line in fh:
                i = line.find('"subject": "')
                sub = line[i + 12:i + 70].split('"')[0] if i >= 0 else ""
                pg = page_of_subject(sub)
                if pg is None or pg in keep:
                    out[kind].append(json.loads(line))
    return out


def edition_info(rows: Dict[str, List[dict]]) -> Dict[str, Any]:
    for o in rows["observations"]:
        if o.get("quantity") == "document_identity":
            d = o.get("detail") or {}
            return {"edition_path": d.get("edition_path"), "imslp_id": d.get("imslp_id"), "work_id": d.get("work_id")}
    return {}


def owner_verdicts(rows: Dict[str, List[dict]], env: Optional[Dict[str, str]] = None) -> Dict[Tuple[int, int, int, int], Dict[str, Any]]:
    """Re-run ONLY `adjudicate_stroke_owner` over the GATHER rows: `{cell key: verdict detail}` (flags read at call time, so `env` is the OFF arm)."""
    from . import adjudicate as A
    from .record import Q
    from .review import rerun as RR
    saved = {k: os.environ.get(k) for k in (env or {})}
    try:
        for k, v in (env or {}).items():
            os.environ[k] = v
        log, _ = RR.rebuild_gather({"observations": rows["observations"], "abstentions": rows["abstentions"], "verdicts": []})
        A._ensure_decisions()
        spec = A.REGISTRY[Q.STROKE_OWNER]
        log.freeze()
        out = {}
        for sub in A.subjects_for(log, spec):
            v = A.adjudicate_one(log, spec, sub)
            if isinstance(v.detail, dict):
                out[(sub.page, sub.system, sub.staff, sub.cell)] = v.detail
        return out
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def consumer_rows(rows: Dict[str, List[dict]]) -> Tuple[Dict[Tuple, Dict[int, List[str]]], Dict[Tuple, List[Tuple[str, List[float]]]]]:
    """(detector consumer boxes: `{cell: {stroke ordinal: [stem|beam|flag ...]}}`, cv_lines reads: `{cell: [(kind, [x, y, w, h])]}`)."""
    from .stroke_owner import family_of
    boxes: Dict[str, Tuple[str, dict]] = {}
    strokes: Dict[str, List[int]] = {}
    reads: Dict[Tuple, List[Tuple[str, List[float]]]] = collections.defaultdict(list)
    for o in rows["observations"]:
        q = o.get("quantity")
        if q == "glyph_box":
            v = o.get("value")
            if isinstance(v, list) and v and not str(o.get("reader") or "").startswith("yolo_rescue"):
                fam = family_of(str(v[0]), (o.get("detail") or {}).get("category"))
                if fam in CONSUMER_FAMILIES:
                    boxes[o["subject"]] = (fam, o)
        elif q == "glyph_strokes" and isinstance(o.get("value"), list):
            strokes[o["subject"]] = o["value"]
        elif q in ("stem", "beam_stroke") and isinstance(o.get("value"), list) and len(o["value"]) == 4:
            ck = cell_key(o["subject"])
            if ck:
                reads[ck].append(("stem" if q == "stem" else "beam", [float(t) for t in o["value"]]))
    det: Dict[Tuple, Dict[int, List[str]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for key, (fam, _o) in boxes.items():
        ck = cell_key(key)
        for ordinal in strokes.get(key, ()):
            det[ck][int(ordinal)].append(fam)
    return det, reads


def area_claims(rows: Dict[str, List[dict]]) -> List[Dict[str, Any]]:
    out = []
    for o in rows["observations"]:
        if o.get("quantity") != "claimed_area":
            continue
        d = o.get("detail") or {}
        v = o.get("value")
        if d.get("unit") != "area" or not (isinstance(v, list) and len(v) == 4) or d.get("owner") not in FAMILY_KIND:
            continue
        out.append({"rect": [float(t) for t in v], "kind": FAMILY_KIND[d["owner"]], "owner": d["owner"],
                    "weak": d.get("standing", "READ") != "READ"})
    return out


def claims_for_cell(strokes: Sequence[Any], verdict: Optional[Dict[str, Any]], det: Dict[int, List[str]],
                    cv_reads: Dict[int, List[str]]) -> Dict[int, StrokeClaims]:
    """`{label (ordinal + 1): StrokeClaims}` for one cell from the stroke owner's verdict detail, the consumer boxes and the cv_lines reads."""
    vs = (verdict or {}).get("strokes") or {}
    out: Dict[int, StrokeClaims] = {}
    for o, st in enumerate(strokes):
        c = StrokeClaims(shape=st.kind if hasattr(st, "kind") else str(st))
        ent = vs.get(str(o))
        if ent:
            state, _fam, _owners, _by, cands = ent[0], ent[1], ent[2], ent[3], ent[4]
            c.open = state == "contested"
            keys = set()
            for cand in cands:
                key, family, _cls, fit, _why, how = cand[:6]
                k = kind_of(family)
                if k is None:
                    continue
                if fit == "no":
                    c.refused = True
                    continue
                c.kinds.add(k)
                if how == "area":
                    c.register.add(k)
                elif key not in keys:
                    keys.add(key)
                    c.n_box += 1
        for fam in det.get(o, ()):
            c.kinds.add(fam)
            c.n_box += 1
        if not c.kinds:
            for k in cv_reads.get(o, ()):
                c.kinds.add(k)
        if c.kinds:
            c.refused = False
        out[o + 1] = c
    return out


def cv_read_strokes(res: Any, reads: Sequence[Tuple[str, List[float]]]) -> Dict[int, List[str]]:
    """The strokes a cv_lines stem / beam row covers (at least `COVER_SHARE_MIN` of the stroke's ink inside its box)."""
    from . import stroke_map as SM
    out: Dict[int, List[str]] = collections.defaultdict(list)
    for kind, (x, y, w, h) in reads:
        for o, share in SM.strokes_in_box(res, (x, y, x + w, y + h)):
            if share >= SM.COVER_SHARE_MIN and kind not in out[o]:
                out[o].append(kind)
    return out


def plant_double_claim(claims: Dict[int, StrokeClaims], kind_from: str = "head", kind_to: str = "rest", limit: int = 5) -> List[int]:
    """CONTROL: put a second kind on up to `limit` strokes a `kind_from` claim stands on; returns the labels it touched."""
    done = []
    for lab, c in sorted(claims.items()):
        if kind_from in c.kinds and kind_to not in c.kinds and len(done) < limit:
            c.kinds.add(kind_to)
            done.append(lab)
    return done


# ───────────────────────────── 4. one page, end to end ─────────────────────────────

@dataclass
class PageResult:
    page: int
    tally: Dict[str, Any]
    verify: Dict[str, int]
    truth: Optional[Dict[str, Any]] = None
    canvas: Optional[PageInk] = None
    tiles: List[Dict[str, Any]] = field(default_factory=list)


def _plant_cut_head(lab: np.ndarray, res: Any, claims: Dict[int, StrokeClaims], meta: Dict[int, Dict[str, Any]], limit: int = 40) -> None:
    """CONTROL (2.239): cut up to `limit` head-claimed strokes of a cell in half across their middle row -- the lower half becomes a new label
    with the same claims and half the height. The truth boxes on them must turn FRAGMENTED, the halves MISSHAPEN (too small)."""
    nxt = int(lab.max()) + 1
    done = 0
    for i in sorted(claims):
        c = claims[i]
        if "head" not in c.kinds or done >= limit or i not in meta:
            continue
        ys, _xs = np.nonzero(lab == i)
        if ys.size < 8:
            continue
        mid = int(np.median(ys))
        low = (lab == i) & (np.arange(lab.shape[0])[:, None] > mid)
        if not low.any():
            continue
        lab[low] = nxt
        claims[nxt] = StrokeClaims(shape=c.shape, kinds=set(c.kinds), register=set(c.register), n_box=c.n_box)
        half = dict(meta[i])
        half["h_sp"] = round(meta[i]["h_sp"] / 2.0, 2)
        meta[i] = dict(half)
        meta[nxt] = dict(half)
        nxt += 1
        done += 1


def build_page(rows: Dict[str, List[dict]], pdf: pathlib.Path, page: int, cm_root: pathlib.Path,
               env: Optional[Dict[str, str]] = None, plant: Optional[Tuple[str, str]] = None, want_rgb: bool = False
               ) -> Tuple[PageInk, Dict[str, int], Any, List[Any]]:
    """The page canvas of `page` (module doc). Returns (canvas, verify counts, the loaded page with staves, its cells)."""
    from . import cell_map as CM
    from . import gather as G
    from . import stroke_map as SM
    prows = {k: [r for r in v if page_of_subject(r.get("subject", "")) in (None, page)] for k, v in rows.items()}
    verdicts = owner_verdicts(prows, env)
    det, reads = consumer_rows(prows)
    rec_boxes: Dict[Tuple, Dict[int, list]] = collections.defaultdict(dict)
    keep_whole: Dict[Tuple, list] = {}
    touch: Dict[Tuple, list] = {}
    for o in prows["observations"]:
        if o.get("quantity") == "stroke":
            p = o["subject"].split("/")
            g = int(p[5])
            if g >= STROKE_BASE:
                rec_boxes[cell_key(o["subject"])][g - STROKE_BASE] = (o.get("detail") or {}).get("stroke_box")
                if (o.get("detail") or {}).get("cell_keep_whole"):     # ROADMAP 2.239: the boxes the split left whole, as the gather saw them
                    keep_whole[cell_key(o["subject"])] = o["detail"]["cell_keep_whole"]
                if (o.get("detail") or {}).get("cell_touch_boxes"):    # 2.239 r3: the boxes a touching accidental was cut against
                    touch[cell_key(o["subject"])] = o["detail"]["cell_touch_boxes"]
    (pws, cells), = CM.load_prepared(pdf, [page], root=cm_root)
    canvas = PageInk(pws.page.binary == 0)
    local = G._system_local(pws.staves)
    verify = collections.Counter()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        ck = (c.page_index, key[0], key[1], c.measure_index)
        grid = G._cell_grid(c)
        img = getattr(c, "image_no_staff", None)
        if grid is None or img is None:
            verify["cell_no_grid"] += 1
            continue
        res = SM.map_strokes(img, grid[1] * 2.0, list(getattr(c, "staff_line_ys_canonical", None) or []), getattr(c, "binary", None),
                             keep_whole=keep_whole.get(ck, ()), touch_boxes=touch.get(ck, ()))
        mine = {i: list(s.box) for i, s in enumerate(res.strokes)} if res else {}
        theirs = rec_boxes.get(ck, {})
        if mine != {i: list(b) for i, b in theirs.items()}:
            # the ordinals of this cell are not the record's: drop it, say so (a mismatched cell would give another stroke's claims)
            verify["cells_mismatch"] += 1
            verify["strokes_in_mismatch"] += len(mine)
            continue
        verify["cells_ok"] += 1
        verify["strokes_ok"] += len(mine)
        if not mine:
            canvas.add_cell(c.bbox_page_px, np.zeros((1, 1), np.int16), {}, None)
            continue
        s = res.scale
        hr, wr = int(round(img.shape[0] * s)), int(round(img.shape[1] * s))
        lab = np.zeros((hr, wr), np.int16)
        for i, (m, x0, y0) in enumerate(res.masks):
            mh, mw = m.shape
            y1, x1 = min(hr, y0 + mh), min(wr, x0 + mw)
            if y1 > y0 and x1 > x0:
                sub = lab[y0:y1, x0:x1]
                sub[m[:y1 - y0, :x1 - x0]] = i + 1
        claims = claims_for_cell(res.strokes, verdicts.get(ck), det.get(ck, {}), cv_read_strokes(res, reads.get(ck, ())))
        if plant and plant != ("cut", "head"):
            plant_double_claim(claims, plant[0], plant[1])
        raw = getattr(c, "binary", None)
        er = ((raw == 0) & (img != 0)) if raw is not None else None
        ys = list(getattr(c, "staff_line_ys_canonical", None) or [])
        up = float(c.upscale_factor)
        spc = float(res.sp_canonical)
        meta = {}
        for i, st in enumerate(res.strokes):
            x, y, w_, h_ = st.box
            meta[i + 1] = {"shape": st.kind, "w_sp": round(w_ / spc, 2), "h_sp": round(h_ / spc, 2), "thick_sp": st.thickness_sp,
                           "angle": st.angle_deg, "touches": bool(st.touches),
                           "page_box": [round(c.bbox_page_px[0] + x / up), round(c.bbox_page_px[1] + y / up),
                                        round(c.bbox_page_px[0] + (x + w_) / up), round(c.bbox_page_px[1] + (y + h_) / up)]}
        if plant == ("cut", "head"):
            _plant_cut_head(lab, res, claims, meta)
        canvas.add_cell(c.bbox_page_px, lab, claims, er, [c.bbox_page_px[1] + y / c.upscale_factor for y in ys], meta)
    for a in area_claims(prows):
        canvas.add_area(a["rect"], a["kind"], a["weak"])
    canvas.finish()
    return canvas, dict(verify), pws, cells


# ───────────────────────────── 5. Sean's labels ─────────────────────────────

def load_truth(edition: str, page: int, master_version: str) -> Optional[Dict[str, Any]]:
    """The aligned hand-truth of `page` (None = no labelled page). Refused when it describes another master or other labels."""
    from tools.omr.hand_truth import align as AL
    al = AL.Alignment.load(edition, page)
    if al is None:
        return None
    if al.version != master_version:
        raise SystemExit("hand truth %s p%d is aligned to master %s, this run reads %s: re-run hand_truth.align" % (edition, page, al.version, master_version))
    pp = AL.PAGES_DIR / edition / ("%d.json" % page)
    stale = al.stale_against(pp)
    if stale:
        raise SystemExit("hand truth %s p%d: %s" % (edition, page, stale))
    return {"page": json.loads(pp.read_text()), "alignment": al}


def score_truth(canvas: PageInk, truth: Dict[str, Any], source: str = "any") -> Dict[str, Any]:
    """Per label class: right / nothing / wrong_kind / split / no_ink / unmapped, plus the box lists of the misses."""
    al = truth["alignment"]
    per: Dict[str, Dict[str, int]] = collections.defaultdict(lambda: collections.Counter())
    strict: Dict[str, Dict[str, int]] = collections.defaultdict(lambda: collections.Counter())
    strict_misses: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    misses: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for b in truth["page"]["boxes"]:
        cls = b["cls"]
        accept = TRUTH_KINDS.get(cls)
        if accept is None:
            per[cls]["unmapped"] += 1
            continue
        j = canvas.judge_box(b["rect"], accept, source)
        per[cls][j["verdict"]] += 1
        strict[cls][j.get("strict", j["verdict"])] += 1
        if j.get("strict") in ("fragmented", "misshapen") and len(strict_misses[cls]) < 60:
            strict_misses[cls].append({"id": b["id"], "rect": [round(v, 1) for v in b["rect"]], "strict": j["strict"],
                                       "largest_share": j.get("largest_share"), "n_pieces": j.get("n_pieces"), "why": j.get("misshapen"),
                                       "piece_box": j.get("piece_box")})
        if j["verdict"] in ("nothing", "wrong_kind", "split") and len(misses[cls]) < 40:
            misses[cls].append({"id": b["id"], "rect": [round(v, 1) for v in b["rect"]], "cell": al.cell_of(b["id"]), **j})
    return {"by_class": {c: dict(v) for c, v in sorted(per.items())}, "misses": dict(misses), "master": al.version,
            "n_boxes": len(truth["page"]["boxes"]), "strict_by_class": {c: dict(v) for c, v in sorted(strict.items())},
            "strict_misses": dict(strict_misses)}


# ───────────────────────────── 6. tiles ─────────────────────────────

def staff_bands(cells: Sequence[Any]) -> List[Tuple[float, float]]:
    """Each staff's (top line y, bottom line y) in page px, once per staff (from its cells)."""
    seen: Dict[int, Tuple[float, float]] = {}
    for c in cells:
        ys = list(c.staff_line_ys_canonical or [])
        if len(ys) >= 5 and c.staff_index not in seen:
            y0 = c.bbox_page_px[1]
            seen[c.staff_index] = (y0 + ys[0] / c.upscale_factor, y0 + ys[-1] / c.upscale_factor)
    return sorted(seen.values())


def problem_components(canvas: PageInk, bands: Sequence[Tuple[float, float]], limit: int = 40, join_px: int = 1) -> List[Dict[str, Any]]:
    """The biggest connected pieces of unclaimed / contested ink, ONE STAFF AT A TIME (each page row goes to the staff whose middle line is
    nearest, so a system barline or bracket is cut into one piece per staff, never a tile of the whole system), biggest first."""
    import cv2
    names = canvas.cat_names
    bad = [i for i, n in enumerate(names) if n.startswith(("unclaimed", "refused", "contested", "weak", "outside"))]   # residue is not a tile: it is the staff's
    if not bad or not bands:
        return []
    m = np.isin(canvas.cat, bad) & canvas.ink
    mids = np.array([(t + b) / 2.0 for t, b in bands])
    rows = np.arange(canvas.shape[0])
    owner = np.abs(rows[:, None] - mids[None, :]).argmin(axis=1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (join_px, join_px))
    out = []
    for bi, (top, bot) in enumerate(bands):
        u = (bot - top) / 4.0
        ys = np.nonzero(owner == bi)[0]
        ys = ys[(ys >= top - 5 * u) & (ys <= bot + 5 * u)]
        if ys.size == 0:
            continue
        y0, y1 = int(ys[0]), int(ys[-1]) + 1
        sub = m[y0:y1]
        if not sub.any():
            continue
        joined = cv2.dilate(sub.astype(np.uint8), k)
        n, lab, stats, _c = cv2.connectedComponentsWithStats(joined, connectivity=8)
        for i in range(1, n):
            x, y, w, h, _a = stats[i]
            sl = (slice(y, y + h), slice(x, x + w))
            sel = sub[sl] & (lab[sl] == i)
            px = int(sel.sum())
            if px < 40 or w > 10 * u or h > 10 * u:   # a piece longer than ten spaces is a run along the staff or a system rule, not a mark
                continue
            cats = collections.Counter(names[c] for c in canvas.cat[y0:y1][sl][sel])
            out.append({"box": [int(x), int(y + y0), int(x + w), int(y + y0 + h)], "ink_px": px, "states": dict(cats.most_common(4)),
                        "unit": u, "staff_y": (top, bot)})
    out.sort(key=lambda d: -d["ink_px"])
    return out[:limit]


def cut_tiles(items: List[Dict[str, Any]], pages: Dict[int, Any], out_dir: pathlib.Path, unit: float, cm_version: str) -> None:
    """One tile per item: the piece's staff, one thin orange box sized to the ink, nothing else drawn. The key goes OUTSIDE the tile folder."""
    from PIL import Image, ImageDraw
    tdir = out_dir / "tiles"
    tdir.mkdir(parents=True, exist_ok=True)
    for f in tdir.glob("*"):
        f.unlink()
    key = []
    W = 520
    for n, it in enumerate(items, 1):
        im = pages[it["page"]]
        bb = [it["box"][0] - 4, it["box"][1] - 4, it["box"][2] + 4, it["box"][3] + 4]
        cx, cy = (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0
        u = it.get("unit") or unit
        top, bot = it.get("staff_y") or (cy - 2 * u, cy + 2 * u)
        x0, x1 = max(0, int(cx - 6 * u)), int(cx + 6 * u)
        y0, y1 = max(0, int(min(top - 4 * u, bb[1] - u))), int(max(bot + 4 * u, bb[3] + u))
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([round(bb[0] - x0), round(bb[1] - y0), round(bb[2] - x0), round(bb[3] - y0)],
                                       outline=ORANGE, width=max(2, int(u / 10)))
        crop = crop.resize((W, max(1, int(W * crop.height / crop.width))))
        crop.save(tdir / ("tile_%02d.png" % n))
        key.append({**{k: v for k, v in it.items() if k != "staff_y"}, "tile": n, "crop_origin": [x0, y0], "cell_map": cm_version})
    (tdir / "README.md").write_text(
        "# Capture tiles\n\nEach picture is a piece of a scanned score page with ONE orange box on it and nothing else drawn. "
        "The box only says where to look.\n\n**Question, for every tile:** what is this ink (a note, a stem, a beam, a rest, a flag, "
        "an accidental, a dot, a tie or slur, a hairpin, a word or dynamic, a bracket, a barline, or something else)?\n\nAnswer by tile number.\n")
    (out_dir / "key.json").write_text(json.dumps(key, indent=1, default=str))


# ───────────────────────────── 7. the source ─────────────────────────────

def resolve_source(rec: str) -> pathlib.Path:
    """REC -> a slice directory (module doc)."""
    if ":" in rec and not os.path.exists(rec):
        from . import lane_report as LR
        plate, tag = rec.split(":", 1)
        return LR.slice_dir(plate, tag)
    p = pathlib.Path(rec)
    if p.is_dir():
        if not (p / "observations.jsonl").exists():
            raise SystemExit("%s holds no observations.jsonl (a slice directory)" % p)
        return p
    if not p.exists():
        raise SystemExit("no such record: %s" % rec)
    if p.stat().st_size > BIG_RECORD_BYTES:
        raise SystemExit("%s is %.1f GB: never loaded whole. Use its lane-report slices (`brahms:TAG`)." % (p.name, p.stat().st_size / 1e9))
    return cut_record(p)


def cut_record(path: pathlib.Path) -> pathlib.Path:
    """A `.record.json` cut ONCE to its GATHER rows (observations + abstentions), streamed, under the shared one-big-reader lock."""
    from .judged import iter_array
    from .lane_report import record_lock
    st = path.stat()
    d = RECORDS / ("claim-readout-slices-%s" % path.name.replace(".record.json", ""))
    stamp = {"size": st.st_size, "mtime": int(st.st_mtime)}
    if (d / "stamp.json").exists() and json.loads((d / "stamp.json").read_text()) == stamp:
        return d
    d.mkdir(parents=True, exist_ok=True)
    with record_lock():
        for kind in ("observations", "abstentions", "verdicts"):
            with open(d / ("%s.jsonl" % kind), "w") as fh:
                for it in iter_array(path, kind):
                    if kind == "verdicts" and it.get("quantity") != "stroke_owner":
                        continue          # only the stroke owner's own verdicts: the parity control reads them
                    fh.write(json.dumps(it, default=str) + "\n")
    (d / "stamp.json").write_text(json.dumps(stamp))
    return d


def slice_pages(src: pathlib.Path) -> List[int]:
    st = src / "stamp.json"
    if st.exists():
        pg = json.loads(st.read_text()).get("pages")
        if pg:
            return sorted(pg)
    pages = set()
    with open(src / "observations.jsonl") as fh:
        for line in fh:
            if '"quantity": "staff_lines"' in line[:200]:
                i = line.find('"subject": "')
                p = page_of_subject(line[i + 12:i + 60].split('"')[0])
                if p is not None:
                    pages.add(p)
    return sorted(pages)


# ───────────────────────────── 8. the report ─────────────────────────────

def pct(x: int, tot: int) -> str:
    return "%5.1f%%" % (100.0 * x / tot) if tot else "   -  "


def merge_tallies(ts: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ink_px": 0, "state_px": collections.Counter(), "one_by_kind": collections.Counter(),
                           "twin_by_kind": collections.Counter(), "contested_by_pair": collections.Counter(),
                           "register_px_by_kind": collections.Counter(), "claimed_px_by_kind": collections.Counter(),
                           "naive_stroke_px": 0, "stroke_px_deduped": 0, "cells": 0}
    for t in ts:
        out["ink_px"] += t["ink_px"]
        for k in ("state_px", "one_by_kind", "twin_by_kind", "contested_by_pair", "register_px_by_kind", "claimed_px_by_kind"):
            out[k].update(t[k])
        for k in ("naive_stroke_px", "stroke_px_deduped", "cells"):
            out[k] += t[k]
        for k, v in (t.get("misshapen_pieces") or {}).items():     # 2.239
            out.setdefault("misshapen_pieces", {}).setdefault(k, []).extend(v)
    return out


def todo_list(t: Dict[str, Any], top: int = 10) -> List[Tuple[str, int]]:
    """GATHER's to-do list: the unclaimed / contested ink kinds, ranked by share of the page ink."""
    rows = []
    for name, px in t["state_px"].items():
        if name.startswith(("unclaimed", "refused", "residue", "weak_claim", "debris", "outside_cells")):
            rows.append((name, px))
    for pair, px in t["contested_by_pair"].items():
        kinds, how = pair.split("|")
        rows.append(("contested(%s):%s" % (how, kinds), px))
    for k, px in t["twin_by_kind"].items():
        rows.append(("twin:" + k, px))
    rows.sort(key=lambda r: -r[1])
    return rows[:top]


def render_tally(label: str, t: Dict[str, Any]) -> List[str]:
    tot = t["ink_px"]
    sp = t["state_px"]
    one = sum(t["one_by_kind"].values())
    lines = ["%s: %d ink px, %d cells" % (label, tot, t["cells"])]
    con = sum(v for k, v in sp.items() if k.startswith("contested"))
    twin = sp.get("twin", 0)
    unc = sum(v for k, v in sp.items() if k.startswith(("unclaimed", "refused", "residue", "weak_claim", "debris", "outside_cells")))
    staff = sp.get("staff_line", 0)
    lines.append("  one owner %s   twin %s   contested %s (open %s)   unclaimed %s   staff line (erased, the staff's) %s" % (
        pct(sp.get("one", 0), tot), pct(twin, tot), pct(con, tot), pct(sp.get("contested_open", 0), tot), pct(unc, tot), pct(staff, tot)))
    lines.append("  one owner by kind: " + ", ".join("%s %s" % (k, pct(v, tot)) for k, v in sorted(t["one_by_kind"].items(), key=lambda kv: -kv[1])))
    lines.append("  claimed by the register (area / trace), any state: " + (", ".join("%s %s" % (k, pct(v, tot)) for k, v in sorted(t["register_px_by_kind"].items(), key=lambda kv: -kv[1])) or "-"))
    lines.append("  unclaimed: " + (", ".join("%s %s" % (k, pct(v, tot)) for k, v in sorted(sp.items(), key=lambda kv: -kv[1])
                                           if k.startswith(("unclaimed", "refused", "residue", "weak_claim", "debris", "outside_cells")) and v) or "-"))
    lines.append("  de-dup: stroke ink px summed per cell %d -> in page pixels %d (%.1f%% of the sum was the same ink seen twice)" % (
        t["naive_stroke_px"], t["stroke_px_deduped"], 100.0 * (1 - t["stroke_px_deduped"] / t["naive_stroke_px"]) if t["naive_stroke_px"] else 0.0))
    mis = t.get("misshapen_pieces") or {}
    if mis:                                       # 2.239: pieces claimed as one shape-tested kind but outside its limits (never right)
        lines.append("  misshapen pieces (claimed by one kind, outside its size/shape limits): " + ", ".join(
            "%s %d (%s)" % (k, len(v), ", ".join("%s %d" % kv for kv in collections.Counter(p_["why"] for p_ in v).most_common()))
            for k, v in sorted(mis.items())))
    return lines


def render_truth(tr: Dict[str, Any], tr_reg: Optional[Dict[str, Any]] = None) -> List[str]:
    lines = ["truth (Sean's labels, master %s): %d boxes" % (tr["master"], tr["n_boxes"]),
             "  %-24s %5s %6s %7s %6s %6s %6s %6s   right via register" % ("class", "boxes", "right", "nothing", "wrong", "split", "noink", "unmap")]
    tot = collections.Counter()
    for c, v in tr["by_class"].items():
        n = sum(v.values())
        reg = (tr_reg or {}).get("by_class", {}).get(c, {}).get("right", 0)
        lines.append("  %-24s %5d %6d %7d %6d %6d %6d %6d   %d" % (c, n, v.get("right", 0), v.get("nothing", 0), v.get("wrong_kind", 0),
                                                              v.get("split", 0), v.get("no_ink", 0), v.get("unmapped", 0), reg))
        tot.update(v)
        tot["_reg"] += reg
    n = sum(v for k, v in tot.items() if k != "_reg")
    lines.append("  %-24s %5d %6d %7d %6d %6d %6d %6d   %d" % ("ALL", n, tot["right"], tot["nothing"], tot["wrong_kind"], tot["split"], tot["no_ink"], tot["unmapped"], tot["_reg"]))
    if tr.get("strict_by_class"):
        lines.append("  STRICT (2.239: right AND one piece >= %.2f of the box's ink AND that piece in its kind's size/shape limits)" % WHOLE_SHARE)
        lines.append("  %-24s %5s %6s %10s %9s" % ("class", "boxes", "whole", "fragmented", "misshapen"))
        st = collections.Counter()
        for c, v in tr["strict_by_class"].items():
            lines.append("  %-24s %5d %6d %10d %9d" % (c, sum(v.values()), v.get("whole", 0), v.get("fragmented", 0), v.get("misshapen", 0)))
            st.update(v)
        lines.append("  %-24s %5d %6d %10d %9d" % ("ALL", sum(st.values()), st["whole"], st["fragmented"], st["misshapen"]))
    return lines


# ───────────────────────────── 9. the command ─────────────────────────────

def parse_env(specs: Sequence[str]) -> Dict[str, str]:
    out = {}
    for s in specs or ():
        k, _, v = s.partition("=")
        out[k.strip()] = v
    return out


def run(rec: str, pages: Optional[Sequence[int]], *, truth: Optional[str], tiles: Optional[pathlib.Path], out: Optional[pathlib.Path],
        env: Optional[Dict[str, str]] = None, cm_root: Optional[pathlib.Path] = None, seed_tiles: int = 12, log=print) -> Dict[str, Any]:
    from . import cell_map as CM
    src = resolve_source(rec)
    pages = list(pages) if pages else slice_pages(src)
    rows_all = read_rows(src, pages)
    ed = edition_info(rows_all)
    pdf = LIB / ed["edition_path"]
    cm_root = cm_root or CM.ROOT_DEFAULT
    man = CM.info(pdf, root=cm_root)
    log("claim_readout: %s  pages %s  master %s" % (src, pages, man["version"]))
    results: List[PageResult] = []
    tile_pool: List[Dict[str, Any]] = []
    images: Dict[int, Any] = {}
    for pg in pages:
        t0 = time.time()
        canvas, verify, pws, cells = build_page(rows_all, pdf, pg, cm_root, env)
        tally = canvas.tally()
        tally["misshapen_pieces"] = canvas.misshapen_pieces()          # 2.239: per shape-tested kind, every piece outside its limits
        res = PageResult(pg, tally, verify)
        if truth == "auto":
            tr = load_truth("imslp%s" % ed.get("imslp_id"), pg, man["version"])
            if tr is not None:
                res.truth = {"any": score_truth(canvas, tr, "any"), "register": score_truth(canvas, tr, "register")}
        if tiles is not None:
            from PIL import Image
            comps = problem_components(canvas, staff_bands(cells))
            if comps:
                images[pg] = Image.fromarray(pws.page.rgb).convert("RGB")
            for cmp_ in comps:
                tile_pool.append({"page": pg, **cmp_})
        results.append(res)
        log("  page %d: %d ink px, %d cells ok / %d mismatched (%.0fs)" % (pg, tally["ink_px"], verify.get("cells_ok", 0), verify.get("cells_mismatch", 0), time.time() - t0))
        del canvas, pws, cells
    total = merge_tallies([r.tally for r in results])
    report: Dict[str, Any] = {"record": str(src), "pages": pages, "master": man["version"], "env": env or {},
                              "total": {k: (dict(v) if isinstance(v, collections.Counter) else v) for k, v in total.items()},
                              "todo": todo_list(total), "per_page": {}, "verify": {}}
    for r in results:
        report["per_page"][str(r.page)] = {"tally": r.tally, "truth": r.truth}
        for k, v in r.verify.items():
            report["verify"][k] = report["verify"].get(k, 0) + v
    lines = ["claim_readout %s pages %s master %s" % (os.path.basename(str(src)), pages, man["version"])]
    lines += render_tally("TOTAL", total)
    lines.append("  cells re-cut and matched stroke-for-stroke to the record: %s" % report["verify"])
    for r in results:
        lines += render_tally("page %d" % r.page, r.tally)
        if r.truth:
            lines += render_truth(r.truth["any"], r.truth["register"])
    lines.append("TO-DO (top 10 unclaimed / contested ink, share of the plate's ink):")
    for i, (k, px) in enumerate(report["todo"], 1):
        lines.append("  %2d. %-40s %9d px  %s" % (i, k, px, pct(px, total["ink_px"])))
    text = "\n".join(lines)
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "readout.json").write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
        (out / "report.txt").write_text(text + "\n")
    if tiles is not None and tile_pool:
        tile_pool.sort(key=lambda d: -d["ink_px"])
        chosen: List[Dict[str, Any]] = []
        for it in tile_pool:
            if any(c["page"] == it["page"] and not (it["box"][2] < c["box"][0] - 100 or it["box"][0] > c["box"][2] + 100
                                                       or it["box"][3] < c["box"][1] - 100 or it["box"][1] > c["box"][3] + 100) for c in chosen):
                continue
            chosen.append(it)
            if len(chosen) >= seed_tiles:
                break
        cut_tiles(chosen, images, tiles.parent if tiles.name == "tiles" else tiles, 32.0, man["version"])
        text += "\ntiles: %d -> %s (key.json beside the folder)" % (len(chosen), tiles)
    log(text)
    return report


def verdict_parity(src: pathlib.Path, rows: Dict[str, List[dict]], page: int) -> Optional[Dict[str, int]]:
    """CONTROL: the record's own saved `Q.STROKE_OWNER` verdicts of `page` against the ones this module re-runs (state and family of every
    stroke; row ids differ between a slice and a record, so they are not compared). None = none saved."""
    vf = src / "verdicts.jsonl"
    if not vf.exists():
        return None
    saved: Dict[Tuple, Dict[str, Any]] = {}
    with open(vf) as fh:
        for line in fh:
            if '"stroke_owner"' not in line[:400]:
                continue
            v = json.loads(line)
            ck = cell_key(v["subject"])
            if ck and ck[0] == page and isinstance(v.get("detail"), dict):
                saved[ck] = v["detail"]
    if not saved:
        return None
    mine = owner_verdicts({k: [r for r in v if page_of_subject(r.get("subject", "")) in (None, page)] for k, v in rows.items()})
    diff = 0
    for ck, d in saved.items():
        a = {o: (e[0], e[1]) for o, e in (d.get("strokes") or {}).items()}
        b = {o: (e[0], e[1]) for o, e in ((mine.get(ck) or {}).get("strokes") or {}).items()}
        diff += a != b
    return {"compared": len(saved), "differ": diff, "cells_not_rerun": sum(1 for ck in saved if ck not in mine)}


def controls(rec: str, page: int, cm_root: Optional[pathlib.Path] = None, log=print) -> int:
    """The three controls that can fail (module doc). Exit 1 if any does not do what it must."""
    from . import cell_map as CM
    src = resolve_source(rec)
    rows = read_rows(src, [page])
    ed = edition_info(rows)
    pdf = LIB / ed["edition_path"]
    cm_root = cm_root or CM.ROOT_DEFAULT
    man = CM.info(pdf, root=cm_root)
    ok = True
    truth = load_truth("imslp%s" % ed.get("imslp_id"), page, man["version"])
    # (a) the arc register: on, then OMR_ARC_CLAIM=0 on the same rows
    c_on, v_on, *_ = build_page(rows, pdf, page, cm_root)
    c_off, _v, *_ = build_page(rows, pdf, page, cm_root, env={"OMR_ARC_CLAIM": "0"})
    t_on, t_off = c_on.tally(), c_off.tally()
    a_on, a_off = t_on["register_px_by_kind"].get("arc", 0), t_off["register_px_by_kind"].get("arc", 0)
    log("(a) OMR_ARC_CLAIM: register-claimed arc ink px %d -> %d with the flag 0 (must drop)" % (a_on, a_off))
    ok &= a_off < a_on
    if truth is not None:
        r_on = score_truth(c_on, truth, "register")["by_class"]
        r_off = score_truth(c_off, truth, "register")["by_class"]
        on = sum(r_on.get(k, {}).get("right", 0) for k in ("tie", "slur"))
        off = sum(r_off.get(k, {}).get("right", 0) for k in ("tie", "slur"))
        n = sum(sum(r_on.get(k, {}).values()) for k in ("tie", "slur"))
        log("    Sean's arcs (tie+slur) right via the register: %d of %d -> %d with the flag 0 (must drop)" % (on, n, off))
        ok &= off < on
    # (b) a planted double claim must show as contested
    c_pl, *_ = build_page(rows, pdf, page, cm_root, plant=("head", "rest"))
    p_on, p_pl = t_on["state_px"], c_pl.tally()["state_px"]
    cont = lambda s: sum(v for k, v in s.items() if k.startswith("contested"))
    log("(b) planted head+rest double claim: contested ink px %d -> %d (must rise)" % (cont(p_on), cont(p_pl)))
    ok &= cont(p_pl) > cont(p_on)
    # (c) two identical copies of the rows read identically
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="claim-readout-copy-"))
    try:
        for k in ("observations", "abstentions"):
            shutil.copy(src / ("%s.jsonl" % k), tmp / ("%s.jsonl" % k))
        rows2 = read_rows(tmp, [page])
        c2, *_ = build_page(rows2, pdf, page, cm_root)
        same = json.dumps(c2.tally(), sort_keys=True) == json.dumps(t_on, sort_keys=True)
        log("(c) readout of an identical copy of the rows: %s" % ("identical" if same else "DIFFERENT"))
        ok &= same
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # (f) 2.239: heads planted cut in half must read FRAGMENTED or MISSHAPEN, never whole
    if truth is not None:
        c_cut, *_ = build_page(rows, pdf, page, cm_root, plant=("cut", "head"))
        s_on = score_truth(c_on, truth)["strict_by_class"]
        s_cut = score_truth(c_cut, truth)["strict_by_class"]
        hk = ("noteheadBlackInSpace", "noteheadBlackOnLine")
        whole_on = sum(s_on.get(k, {}).get("whole", 0) for k in hk)
        whole_cut = sum(s_cut.get(k, {}).get("whole", 0) for k in hk)
        bad_cut = sum(s_cut.get(k, {}).get(x, 0) for k in hk for x in ("fragmented", "misshapen"))
        log("(f) heads planted cut in half: black heads WHOLE %d -> %d, fragmented+misshapen -> %d (whole must drop)" % (whole_on, whole_cut, bad_cut))
        ok &= whole_cut < whole_on
    par = verdict_parity(src, rows, page)
    if par is not None:
        log("(e) the stroke owner re-run on the GATHER rows vs the record's own saved verdicts: %s" % par)
        ok &= par["differ"] == 0 and par["compared"] > 0
    else:
        log("(e) no saved stroke_owner verdicts beside these rows (a `.record.json` cut by this command keeps them): parity not checked")
    log("(d) stroke-for-stroke match of the re-cut cells with the record: %s" % v_on)
    ok &= v_on.get("cells_mismatch", 0) == 0
    log("controls: %s" % ("ALL BEHAVE" if ok else "A CONTROL DID NOT DO WHAT IT MUST"))
    return 0 if ok else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="claim_readout", description=__doc__.split("\n")[0])
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "order":                  # ROADMAP 2.241: the claim-order check (claim_order.py), same command family
        from . import claim_order as CO
        return CO.main(argv[1:])
    if argv and argv[0] == "controls":
        ap.add_argument("cmd")
        ap.add_argument("rec")
        ap.add_argument("--page", type=int, default=0)
        ap.add_argument("--cell-map", default=None)
        a = ap.parse_args(argv)
        return controls(a.rec, a.page, pathlib.Path(a.cell_map) if a.cell_map else None)
    ap.add_argument("rec", help="slice directory, PLATE:TAG (lane_report slices) or a .record.json under 5 GB")
    ap.add_argument("--pages", default=None, help="comma list / ranges (default: every page of the slice)")
    ap.add_argument("--truth", default=None, choices=["auto"])
    ap.add_argument("--tiles", default=None, help="write 12 unclaimed / contested tiles to DIR/tiles (key.json in DIR)")
    ap.add_argument("--out", default=None, help="write readout.json and report.txt here")
    ap.add_argument("--env", action="append", default=[], help="NAME=V set while the stroke owner is re-run (a control arm)")
    ap.add_argument("--cell-map", default=None)
    a = ap.parse_args(argv)
    pages = None
    if a.pages:
        pages = []
        for part in a.pages.split(","):
            lo, _, hi = part.partition("-")
            pages += list(range(int(lo), int(hi or lo) + 1))
    t = pathlib.Path(a.tiles) if a.tiles else None
    run(a.rec, pages, truth=a.truth, tiles=(t / "tiles" if t else None), out=pathlib.Path(a.out) if a.out else (t if t else None),
        env=parse_env(a.env), cm_root=pathlib.Path(a.cell_map) if a.cell_map else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
