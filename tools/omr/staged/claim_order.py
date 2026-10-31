"""ROADMAP 2.241 -- THE CLAIM-ORDER CHECK, an addition to the capture readout (`claim_readout.py`, 2.236).

    python3 -m tools.omr.staged.claim_order REC [--pages 0,4] [--tiles DIR] [--out DIR] [--env NAME=V ...]
    python3 -m tools.omr.staged.claim_order controls REC --page N [--branch-rows REC2 --branch-page P --tip-key key.json --tip-tile 7]
    python3 -m tools.omr.staged.claim_readout order ...              # the same command

PATH: STAGED GATHER's claim register and ADJUDICATE's `stroke_owner` verdict, READ -- this module files no row, decides nothing, names no
quantity it writes (registered in `reach.NOT_A_STAGE`). TEST TOOLING ONLY: no pipeline behaviour, no flag of its own.

WHY (Sean, 2026-10-30): "Are our tests taking into account the order of when ink is claimed?" Only in pieces: `test_staged_page_claims_2_221`
(words and brackets claim before heads, nothing scanned twice), `test_staged_key_marker_order_2_187b`, `test_staged_evaluate_order`. The 2.236
readout counts ink STATES (one owner / twin / contested / unclaimed) but never asks whether the RIGHT LAYER won. `stroke_owner` only LISTS
candidates by tier; where two families fit and the shape clearly fits the later one, the later one owns the stroke; where both fit, the
stroke stays contested. This module asks the order question of every piece of page ink, end to end.

THE ORDER, ONCE (`LAYERS`; from docs/plan-2026-10-28-page-claim-order.md, not re-invented). Where the plan's sections disagree the later,
Sean-ruled one is followed and said:
  1 staff lines                              §10 pass order, step 1 "structure (staff, barlines, brackets, braces)"; §2 row 1
  2 barlines / brackets / braces             §10 step 1; §2 row 1; §9 (brackets and braces claim page-wide, OMR_CLAIM_BRACKETS_FIRST)
  3 clef / key / meter (the header column)   §10 step 2 "system registers"; §2 row 1
  4 words / dynamics / titles / tempo        §10 step 3-4 "text -> dynamics"; §9 step 1 (claimed page-wide). §2 puts in-staff words (row 4)
                                             AFTER heads: §9/§10 (Sean 2026-10-29, "words ... need to be treated system or page wide") is
                                             later and ranks all words/dynamics first, so that is followed.
  5 arcs / hairpins                          §10 step 5 / §9 (claimed page-wide, before heads). §2 row 5 lists arcs with the per-cell strokes
                                             AFTER heads: superseded by §9 (Sean 2026-10-29 "arcs ... page or system wide").
  6 whole rests                              DECISIONS 2026-10-29 (OMR_WHOLE_REST_HANGS): "a whole rest claims its ink before heads". The
                                             lane's list puts rests after accidentals; the later ruling puts the WHOLE rest here.
  7 heads (and ledger lines)                 §2 row 3; §3 "head -> stem" ; page-facts: the ledger names the owner
  8 stems / beams / flags                    §3 order "head -> stem -> beam/flag"; §2 row 5 (consumers, read what no earlier layer claimed)
  9 accidentals                              §2 row 3 open question 1 (accidentals/rests/dots after heads). NOTE `stroke_owner.TIERS` puts
                                             accidentals BEFORE the stem/beam/flag consumers; this check follows the lane's list and marks
                                             every pair where the code's own tier order differs (`code_agrees` False) so it is not read as a bug.
 10 rests (other than whole)                 §2 row 3 open question 1
 11 dots / articulations                     §2 row 3 open question 1 (`stroke_owner` tier 4 puts them after heads and accidentals)

WHAT IS CHECKED, per piece of de-duplicated page ink (the 2.236 canvas, `claim_readout.PageInk`):
  READ   every layer that read it -- a standing candidate of the stroke owner (a detector box family that covers the stroke, a register area
         or the arc trace that holds it; a candidate whose shape did NOT fit is a refused claim and is not a read), a consumer box (stem / beam /
         flag), a cv_lines stem / beam row, a READ area claim whose rectangle covers the pixel, and the text readers' own accepted rows
         (`direction_word`, `printed_bar_number`: a read that exists whether or not a claim was filed from it).
  OWNER  who has it in the record: the stroke owner's decided family, else a consumer on a stroke no tier claimed, else an area claim for
         ink outside every cell. Several cells see the same ink: the EARLIEST owning layer wins (this hides, never invents, a violation).
  CLASS  ORDER-OK            owner is the earliest READ layer and at least two layers read it (the order held under competition)
         EARLIER-UNREAD      the owner is the only layer that read it (listed by owning layer: an earlier-reader miss, not a violation)
         ORDER-VIOLATION     a LATER layer owns ink an EARLIER layer read, grouped by pair "earlier -> later"
         OPEN                read, owned by nobody (contested, or a read with no claim filed): grouped by the two earliest readers
         SPLIT-ACROSS-CLAIM  a piece of ONE MARK an earlier layer claimed (a clef, a bracket) that the stroke map cut into several strokes: all
                             pieces but the largest, 20 px or more (the clef-tip case, Sean's 2.239 round-2 tile 7)
         NO-READER           no layer read it (the 2.236 "unclaimed")
  Shares are of the page's dark ink with the staff lines left out (the 2.236 columns).

CONTROLS THAT CAN FAIL (`controls`): (a) a head planted over a READ word's ink must show as ORDER-VIOLATION "words -> heads"; (b) with
OMR_CLAIM_WORDS_FIRST=0 on the re-adjudicated rows (the word claim rows are not filed; the word READER's rows stay) the words -> heads
violations must RISE; (c) an identical copy of the rows reads identically; (d) on a gather of land-239-flip-wip (2.239 split ON) the clef tip of
Sean's 2.239 r2 tile 7 must show as SPLIT-ACROSS-CLAIM; (e) this module's canvas equals the 2.236 readout's tally.

CONVENTION ASSUMED: the layer order above and the 20 px piece floor. WHAT WOULD FALSIFY IT: a tile of an ORDER-VIOLATION where the later
layer is right (the ink really is that mark). NOT CONFIRMED by Sean: his tiles under out/print/2.241-tiles are the test.
"""
from __future__ import annotations

import argparse
import collections
import inspect
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

from . import claim_readout as CR

DERIVED_CHECK = False

# ───────────────────────────── 1. the order, once ─────────────────────────────

#: (name, the families / register owners that belong to it, the plan line). Index in this list IS the layer number (0-based).
LAYERS: Tuple[Tuple[str, Tuple[str, ...], str], ...] = (
    ("staff_line", (), "plan §10 pass order step 1; §2 row 1"),
    ("barline_bracket", ("barline", "bracket", "leading_column"), "plan §10 step 1; §9 brackets/braces claim page-wide"),
    ("clef_key_meter", ("clef", "key_signature", "meter"), "plan §10 step 2 system registers; §2 row 1"),
    ("word_dynamic", ("word", "dynamic", "text"), "plan §10 steps 3-4; §9 step 1 (page-wide, before heads)"),
    ("arc_hairpin", ("arc", "arc_trace", "hairpin"), "plan §9 / §10 step 5 (page-wide, before heads)"),
    ("whole_rest", ("whole_rest",), "DECISIONS 2026-10-29: a whole rest claims its ink before heads"),
    ("head", ("head", "ledger"), "plan §2 row 3; §3 head first among the per-cell marks"),
    ("stem_beam_flag", ("stem", "beam", "flag"), "plan §3 order head -> stem -> beam/flag; §2 row 5"),
    ("accidental", ("accidental",), "plan §2 row 3 open question 1"),
    ("rest", ("rest",), "plan §2 row 3 open question 1"),
    ("dot_mark", ("dot", "mark"), "plan §2 row 3 open question 1"),
)
LAYER_NAMES = tuple(n for n, _f, _c in LAYERS)
FAMILY_LAYER: Dict[str, int] = {f: i for i, (_n, fams, _c) in enumerate(LAYERS) for f in fams}
L_STAFF, L_WORDS, L_HEAD, L_CONSUMER = 0, LAYER_NAMES.index("word_dynamic"), LAYER_NAMES.index("head"), LAYER_NAMES.index("stem_beam_flag")
NO_OWNER = 255
#: a READ area reads a stroke when this share of the stroke's ink lies inside it (`claims.INSIDE_SHARE_MIN`, the register's one cut)
CR_INSIDE_SHARE = 0.5
#: families whose area is ONE mark by convention (a clef, a bracket): a stroke map that cuts it into several strokes has cut a mark
SINGLE_MARK_OWNERS = ("clef", "bracket")
SPLIT_PIECE_MIN_PX = 20
#: classes in print order
CLASSES = ("ORDER-OK", "EARLIER-UNREAD", "ORDER-VIOLATION", "OPEN", "SPLIT-ACROSS-CLAIM", "NO-READER")
C_OK, C_SOLE, C_VIOL, C_OPEN, C_SPLIT, C_NONE = range(6)
#: text readers whose own accepted rows are a READ of layer "word_dynamic" whether or not a claim was filed from them
TEXT_READER_QUANTITIES = ("direction_word", "printed_bar_number")


def layer_of(family: Optional[str]) -> Optional[int]:
    return FAMILY_LAYER.get(str(family)) if family else None


def code_agrees(early: int, late: int) -> bool:
    """Does `stroke_owner`'s own tier order (TIERS + the consumers last) also put layer `early` before `late`? A pair where it does not is a
    place the code and the plan differ by design, not a bug the pipeline hides."""
    from . import stroke_owner as SO
    tier = {}
    for t, fams in enumerate(SO.TIERS):
        for f in fams:
            tier[f] = t
    for f in SO.CONSUMERS:
        tier[f] = len(SO.TIERS)

    def rank(layer: int) -> Optional[float]:
        # the LATEST tier among the layer's families: a violation comes from a shape decision between BOX families (a dynamic box is tier 5,
        # though the page-wide word claim is tier 0), so the weakest standing of the layer is the one the code ranks it by
        r = [tier[f] for f in LAYERS[layer][1] if f in tier]
        return max(r) if r else None

    a, b = rank(early), rank(late)
    return a is None or b is None or a < b


# ───────────────────────────── 2. one cell's reads and owners (PURE) ─────────────────────────────

@dataclass
class OrderInfo:
    """What read one stroke (layer numbers) and who owns it (`None` = nobody)."""
    read: Set[int] = field(default_factory=set)
    owner: Optional[int] = None
    open: bool = False


def order_for_cell(strokes: Sequence[Any], verdict: Optional[Dict[str, Any]], det: Dict[int, List[str]],
                   cv_reads: Dict[int, List[str]]) -> Dict[int, OrderInfo]:
    """`{label (stroke ordinal + 1): OrderInfo}` for one cell from the stroke owner's verdict detail, the detector consumer boxes and the
    cv_lines reads (the same inputs `claim_readout.claims_for_cell` takes, so the two readings are of one set of claims)."""
    vs = (verdict or {}).get("strokes") or {}
    out: Dict[int, OrderInfo] = {}
    for o in range(len(strokes)):
        info = OrderInfo()
        ent = vs.get(str(o))
        if ent:
            state, fam, cands = ent[0], ent[1], ent[4]
            for cand in cands:
                family, fit = cand[1], cand[3]
                lay = layer_of(family)
                if lay is not None and fit != "no":
                    info.read.add(lay)
            if state in ("decided", "merged"):
                info.owner = layer_of(fam)
            elif state == "contested":
                info.open = True
        cons = [layer_of(f) for f in det.get(o, ())] + [layer_of(f) for f in cv_reads.get(o, ())]
        cons = [c for c in cons if c is not None]
        info.read.update(cons)
        if info.owner is None and not info.open and cons:
            info.owner = min(cons)               # a consumer reads the strokes no tier claimed
        out[o + 1] = info
    return out


def classify(read: int, owner: int, split: bool) -> Tuple[int, Optional[Tuple[int, int]]]:
    """One pixel: (class, pair). `read` a bitmask of layers, `owner` a layer or NO_OWNER, `split` the pixel is a cut piece of a single-mark
    claim. The pair is (earlier, later) for a violation, (first reader, second reader or -1) for OPEN, (owner, -1) for EARLIER-UNREAD / OK."""
    if split:
        return C_SPLIT, (owner if owner != NO_OWNER else -1, -1)
    if read == 0:
        return C_NONE, None
    layers = [i for i in range(len(LAYERS)) if read >> i & 1]
    if owner == NO_OWNER:
        return C_OPEN, (layers[0], layers[1] if len(layers) > 1 else -1)
    e = layers[0]
    if owner > e:
        return C_VIOL, (e, owner)
    if len(layers) >= 2:
        return C_OK, (owner, -1)
    return C_SOLE, (owner, -1)


# ───────────────────────────── 3. the page canvas ─────────────────────────────

class OrderCanvas:
    """The order arrays of ONE page, laid over a `claim_readout.PageInk` (same pixels, same cells). `add_cell` is called with the same cell
    rectangle and label image as the PageInk's; `finish` freezes the class image."""

    def __init__(self, base: "CR.PageInk"):
        self.base = base
        h, w = base.shape
        self.rd = np.zeros((h, w), np.uint16)               # bitmask of layers that read the pixel
        self.own = np.full((h, w), NO_OWNER, np.uint8)      # earliest owning layer over the cells that see it
        self.split = np.zeros((h, w), bool)
        self.areas: List[Dict[str, Any]] = []
        self.reader_boxes: List[Tuple[Sequence[float], int]] = []
        self._split_best: Dict[int, Dict[str, Any]] = {}
        self.split_pieces: List[Dict[str, Any]] = []

    # a READ area claim (page px) and the layer it belongs to
    def set_areas(self, areas: Sequence[Dict[str, Any]]) -> None:
        self.areas = [a for a in areas if not a["weak"] and layer_of(a["owner"]) is not None]
        for i, a in enumerate(self.areas):
            a["id"] = i

    def add_cell(self, rect: Sequence[int], labels: np.ndarray, info: Dict[int, OrderInfo]) -> None:
        b = self.base
        x0, y0, x1, y1 = (int(v) for v in rect)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(b.shape[1], x1), min(b.shape[0], y1)
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0:
            return
        n = int(labels.max()) + 1 if labels.size else 1
        rd_t = np.zeros(n, np.uint16)
        own_t = np.full(n, NO_OWNER, np.uint8)
        for i, oi in info.items():
            if i >= n:
                continue
            rd_t[i] = sum(1 << l for l in oi.read)
            if oi.owner is not None:
                own_t[i] = oi.owner
        lab = CR.sample_to_rect(CR.fill_labels(labels), w, h)
        sl = (slice(y0, y1), slice(x0, x1))
        # a READ area (or a text reader's box) reads a STROKE when at least `INSIDE_SHARE_MIN` of the stroke's ink lies inside it (the
        # register's own cut, claims.covering): a word's box is wider than its ink, so a pixel-level test would let it "read" a slur beside it
        total = None
        for rect2, layer in [(a["rect"], layer_of(a["owner"])) for a in self.areas] + self.reader_boxes:
            ax0, ay0, ax1, ay1 = (int(round(v)) for v in rect2)
            ix0, iy0, ix1, iy1 = max(ax0, x0), max(ay0, y0), min(ax1, x1), min(ay1, y1)
            if ix1 <= ix0 or iy1 <= iy0:
                continue
            if total is None:
                total = np.bincount(lab.ravel(), minlength=n)
            inside = np.bincount(lab[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0].ravel(), minlength=n)
            for i in np.nonzero((inside[1:] > 0) & (inside[1:] >= CR_INSIDE_SHARE * np.maximum(total[1:], 1)))[0] + 1:
                if i < n:
                    rd_t[i] |= np.uint16(1 << layer)
        self.rd[sl] |= rd_t[lab]
        self.own[sl] = np.minimum(self.own[sl], own_t[lab])
        for a in self.areas:
            if a["owner"] in SINGLE_MARK_OWNERS:
                self._split_scan(a, (x0, y0, x1, y1), lab)

    def _split_scan(self, a: Dict[str, Any], rect: Tuple[int, int, int, int], lab: np.ndarray) -> None:
        """The strokes of one cell inside one single-mark claim: keep the cell that sees the most of the claim's ink (neighbouring padded cells
        see the same clef; counting both would count it twice)."""
        x0, y0, x1, y1 = rect
        ax0, ay0, ax1, ay1 = (int(round(v)) for v in a["rect"])
        ix0, iy0, ix1, iy1 = max(ax0, x0), max(ay0, y0), min(ax1, x1), min(ay1, y1)
        if ix1 <= ix0 or iy1 <= iy0:
            return
        sub = lab[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0]
        ink = self.base.ink[iy0:iy1, ix0:ix1] & (sub > 0)
        if not ink.any():
            return
        ids, cnt = np.unique(sub[ink], return_counts=True)
        tot = int(cnt.sum())
        prev = self._split_best.get(a["id"])
        if prev is None or tot > prev["tot"]:
            self._split_best[a["id"]] = {"tot": tot, "sub": sub.copy(), "box": (ix0, iy0, ix1, iy1), "ids": ids, "cnt": cnt}

    def add_reader_boxes(self, boxes: Iterable[Sequence[float]], layer: int) -> None:
        """Text readers' accepted boxes: a READ of `layer` for the strokes they hold (set BEFORE the cells are added) and, outside every cell, for
        the ink under them (`finish`)."""
        self.reader_boxes += [(list(r), layer) for r in boxes]

    def finish(self) -> None:
        b = self.base
        for a in self.areas:
            x0, y0, x1, y1 = (int(round(v)) for v in a["rect"])
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(b.shape[1], x1), min(b.shape[0], y1)
            if x1 <= x0 or y1 <= y0:
                continue
            lay = layer_of(a["owner"])
            sl = (slice(y0, y1), slice(x0, x1))
            outside = ~b.incell[sl]                              # inside a cell the strokes were read above (`add_cell`)
            self.rd[sl] |= np.where(outside, np.uint16(1 << lay), np.uint16(0)).astype(np.uint16)
            cur = self.own[sl]
            self.own[sl] = np.where(outside, np.minimum(cur, lay), cur)
        for r, lay in self.reader_boxes:
            x0, y0, x1, y1 = (int(round(v)) for v in r)
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(b.shape[1], x1), min(b.shape[0], y1)
            if x1 > x0 and y1 > y0:
                sl = (slice(y0, y1), slice(x0, x1))
                self.rd[sl] |= np.where(~b.incell[sl], np.uint16(1 << lay), np.uint16(0)).astype(np.uint16)
        # the cut pieces of each single-mark claim: every piece but the largest, 20 px or more
        for aid, best in self._split_best.items():
            ids, cnt = best["ids"], best["cnt"]
            keep = [(int(i), int(c)) for i, c in zip(ids, cnt) if c >= SPLIT_PIECE_MIN_PX]
            if len(keep) < 2:
                continue
            keep.sort(key=lambda t: -t[1])
            ix0, iy0, ix1, iy1 = best["box"]
            sub = best["sub"]
            for i, c in keep[1:]:
                m = (sub == i) & b.ink[iy0:iy1, ix0:ix1]
                if not m.any():
                    continue
                self.split[iy0:iy1, ix0:ix1] |= m
                ys, xs = np.nonzero(m)
                self.split_pieces.append({"area": self.areas[aid]["rect"], "owner": self.areas[aid]["owner"], "ink_px": int(m.sum()),
                                          "box": [int(ix0 + xs.min()), int(iy0 + ys.min()), int(ix0 + xs.max()) + 1, int(iy0 + ys.max()) + 1],
                                          "largest_px": keep[0][1], "n_pieces": len(keep)})
        # per-pixel class and pair
        ink = b.ink & ~(b.staff & ~b.seen)
        self.mask = ink
        cls = np.full(b.shape, C_NONE, np.uint8)
        pair = np.full(b.shape, -1, np.int16)
        ys, xs = np.nonzero(ink)
        rd = self.rd[ys, xs].astype(np.int64)
        own = self.own[ys, xs].astype(np.int64)
        sp = self.split[ys, xs]
        # vectorised classify(): lowest set bit = earliest reader
        lowbit = np.where(rd > 0, np.log2((rd & -rd).clip(1)).astype(np.int64), -1)
        pc = np.zeros(rd.shape, np.int64)
        t = rd.copy()
        for _ in range(len(LAYERS)):
            pc += t & 1
            t >>= 1
        c = np.full(rd.shape, C_NONE, np.uint8)
        p = np.full(rd.shape, -1, np.int64)
        read = rd > 0
        noown = read & (own == NO_OWNER)
        c[noown] = C_OPEN
        has = read & ~noown
        viol = has & (own > lowbit)
        ok = has & ~viol & (pc >= 2)
        sole = has & ~viol & (pc < 2)
        c[viol], c[ok], c[sole] = C_VIOL, C_OK, C_SOLE
        nl = len(LAYERS) + 1
        # a pair is encoded (a + 1) * nl + (b + 1) with -1 -> 0
        second = np.zeros(rd.shape, np.int64)
        rest = rd & (rd - 1)
        second = np.where(rest > 0, np.log2((rest & -rest).clip(1)).astype(np.int64), -1)
        p[viol] = (lowbit[viol] + 1) * nl + (own[viol] + 1)
        p[noown] = (lowbit[noown] + 1) * nl + (second[noown] + 1)
        p[ok | sole] = (own[ok | sole] + 1) * nl + 0
        c[sp] = C_SPLIT
        p[sp] = (np.where(own[sp] == NO_OWNER, -1, own[sp]) + 1) * nl
        cls[ys, xs] = c
        pair[ys, xs] = p
        self.cls, self.pair, self.nl = cls, pair, nl

    def decode(self, p: int) -> Tuple[int, int]:
        return p // self.nl - 1, p % self.nl - 1

    def tally(self) -> Dict[str, Any]:
        sel = self.mask
        total = int(sel.sum())
        counts = np.bincount(self.cls[sel], minlength=len(CLASSES)) if total else np.zeros(len(CLASSES), int)
        out: Dict[str, Any] = {"ink_px": total, "staff_line_px": int(self.base.ink.sum()) - total,
                               "class_px": {CLASSES[i]: int(counts[i]) for i in range(len(CLASSES))}}
        bucket: Dict[str, collections.Counter] = {k: collections.Counter() for k in CLASSES}
        for ci in (C_OK, C_SOLE, C_VIOL, C_OPEN, C_SPLIT):
            m = sel & (self.cls == ci)
            if not m.any():
                continue
            vals, n = np.unique(self.pair[m], return_counts=True)
            for v, k in zip(vals, n):
                a, b_ = self.decode(int(v))
                if ci == C_VIOL:
                    key = "%s->%s" % (LAYER_NAMES[a], LAYER_NAMES[b_])
                elif ci == C_OPEN:
                    key = "%s|%s" % (LAYER_NAMES[a], LAYER_NAMES[b_] if b_ >= 0 else "-")
                else:
                    key = LAYER_NAMES[a] if a >= 0 else "none"
                bucket[CLASSES[ci]][key] += int(k)
        out["by_pair"] = {k: dict(v) for k, v in bucket.items() if v}
        out["split_pieces"] = len(self.split_pieces)
        return out


# ───────────────────────────── 4. one page, end to end ─────────────────────────────

def reader_boxes(rows: Dict[str, List[dict]]) -> List[List[float]]:
    """The accepted text readers' own page boxes (a READ of the word layer whether or not a claim was filed)."""
    out = []
    for o in rows["observations"]:
        if o.get("quantity") in TEXT_READER_QUANTITIES:
            bb = (o.get("detail") or {}).get("bbox_page_px")
            if isinstance(bb, (list, tuple)) and len(bb) == 4:
                out.append([float(v) for v in bb])
    return out


def apply_flag_arm(rows: Dict[str, List[dict]], env: Optional[Dict[str, str]]) -> Dict[str, List[dict]]:
    """A GATHER flag decides whether a claim row is FILED, so re-adjudicating with the flag off means those rows are absent: the word reader's
    own rows stay (it still read the word), only the `claimed_area` rows it filed go (what a gather with the flag 0 files)."""
    env = env or {}
    drop = set()
    if env.get("OMR_CLAIM_WORDS_FIRST", "1").strip().lower() in ("0", "false", "no", "off"):
        drop.add("word")
    if env.get("OMR_CLAIM_BRACKETS_FIRST", "1").strip().lower() in ("0", "false", "no", "off"):
        drop.add("bracket")
    if not drop:
        return rows
    return {k: [r for r in v if not (r.get("quantity") == "claimed_area" and (r.get("detail") or {}).get("owner") in drop)]
            for k, v in rows.items()}


def build_order_page(rows: Dict[str, List[dict]], pdf: pathlib.Path, page: int, cm_root: pathlib.Path,
                     env: Optional[Dict[str, str]] = None, plant_head_on_words: bool = False
                     ) -> Tuple["CR.PageInk", OrderCanvas, Dict[str, int], Any, List[Any]]:
    """The claim canvas AND the order canvas of `page`. The cell loop is `claim_readout.build_page`'s, line for line (the canvas it fills
    must equal that one: control (e)), plus the order arrays. `map_strokes` is given the 2.239 `keep_whole` boxes where the tree has them."""
    from . import cell_map as CM
    from . import gather as G
    from . import stroke_map as SM
    rows = apply_flag_arm(rows, env)
    prows = {k: [r for r in v if CR.page_of_subject(r.get("subject", "")) in (None, page)] for k, v in rows.items()}
    verdicts = CR.owner_verdicts(prows, env)
    det, reads = CR.consumer_rows(prows)
    rec_boxes: Dict[Tuple, Dict[int, list]] = collections.defaultdict(dict)
    keep_whole: Dict[Tuple, list] = {}
    touch: Dict[Tuple, list] = {}
    for o in prows["observations"]:
        if o.get("quantity") == "stroke":
            p = o["subject"].split("/")
            g = int(p[5])
            if g >= CR.STROKE_BASE:
                rec_boxes[CR.cell_key(o["subject"])][g - CR.STROKE_BASE] = (o.get("detail") or {}).get("stroke_box")
        if (o.get("detail") or {}).get("cell_keep_whole"):
            keep_whole[CR.cell_key(o["subject"])] = o["detail"]["cell_keep_whole"]
        if (o.get("detail") or {}).get("cell_touch_boxes"):        # 2.242: the re-cut must cut as the gather cut (2.239 r3 touch cut, the accidental merge)
            touch[CR.cell_key(o["subject"])] = o["detail"]["cell_touch_boxes"]
    takes_keep = "keep_whole" in inspect.signature(SM.map_strokes).parameters
    takes_touch = "touch_boxes" in inspect.signature(SM.map_strokes).parameters
    (pws, cells), = CM.load_prepared(pdf, [page], root=cm_root)
    canvas = CR.PageInk(pws.page.binary == 0)
    oc = OrderCanvas(canvas)
    areas = CR.area_claims(prows)
    oc.set_areas(areas)
    oc.add_reader_boxes(reader_boxes(prows), L_WORDS)
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
        kw = {"keep_whole": keep_whole.get(ck, ())} if takes_keep else {}
        if takes_touch:
            kw["touch_boxes"] = touch.get(ck, ())
        res = SM.map_strokes(img, grid[1] * 2.0, list(getattr(c, "staff_line_ys_canonical", None) or []), getattr(c, "binary", None), **kw)
        mine = {i: list(s.box) for i, s in enumerate(res.strokes)} if res else {}
        theirs = rec_boxes.get(ck, {})
        if mine != {i: list(b) for i, b in theirs.items()}:
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
        cv_cell = CR.cv_read_strokes(res, reads.get(ck, ()))
        claims = CR.claims_for_cell(res.strokes, verdicts.get(ck), det.get(ck, {}), cv_cell)
        info = order_for_cell(res.strokes, verdicts.get(ck), det.get(ck, {}), cv_cell)
        if plant_head_on_words:
            plant_head_over_words(info)
        raw = getattr(c, "binary", None)
        er = ((raw == 0) & (img != 0)) if raw is not None else None
        ys = list(getattr(c, "staff_line_ys_canonical", None) or [])
        canvas.add_cell(c.bbox_page_px, lab, claims, er, [c.bbox_page_px[1] + y / c.upscale_factor for y in ys])
        oc.add_cell(c.bbox_page_px, lab, info)
    for a in areas:
        canvas.add_area(a["rect"], a["kind"], a["weak"])
    canvas.finish()
    oc.finish()
    return canvas, oc, dict(verify), pws, cells


def plant_head_over_words(info: Dict[int, OrderInfo]) -> int:
    """CONTROL (a): a head box planted over a READ word's ink. Every stroke the word layer owns is given to a head (the head read it and took it,
    as a pipeline that let a head box win over a claimed word would): the words -> heads violations must show. Returns the strokes touched."""
    n = 0
    for oi in info.values():
        if oi.owner == L_WORDS:
            oi.read.add(L_HEAD)
            oi.owner = L_HEAD
            n += 1
    return n


# ───────────────────────────── 5. tiles ─────────────────────────────

def violation_components(oc: OrderCanvas, bands: Sequence[Tuple[float, float]], classes: Sequence[int] = (C_VIOL,), limit: int = 60,
                         max_sp: float = 10.0) -> List[Dict[str, Any]]:
    """Connected pieces of ink in `classes`, ONE STAFF AT A TIME (as `claim_readout.problem_components`), each tagged with its pair."""
    import cv2
    if not bands:
        return []
    b = oc.base
    m_all = np.isin(oc.cls, list(classes)) & oc.mask
    if not m_all.any():
        return []
    mids = np.array([(t + bt) / 2.0 for t, bt in bands])
    rows_ = np.arange(b.shape[0])
    owner = np.abs(rows_[:, None] - mids[None, :]).argmin(axis=1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 1))
    out = []
    for bi, (top, bot) in enumerate(bands):
        u = (bot - top) / 4.0
        ys = np.nonzero(owner == bi)[0]
        ys = ys[(ys >= top - 5 * u) & (ys <= bot + 5 * u)]
        if ys.size == 0:
            continue
        y0, y1 = int(ys[0]), int(ys[-1]) + 1
        sub = m_all[y0:y1]
        if not sub.any():
            continue
        joined = cv2.dilate(sub.astype(np.uint8), k)
        n, labim, stats, _c = cv2.connectedComponentsWithStats(joined, connectivity=8)
        for i in range(1, n):
            x, y, w, h, _a = stats[i]
            sl = (slice(y, y + h), slice(x, x + w))
            sel = sub[sl] & (labim[sl] == i)
            px = int(sel.sum())
            if px < 40 or w > max_sp * u or h > max_sp * u:
                continue
            pairs = collections.Counter(int(v) for v in oc.pair[y0:y1][sl][sel])
            cl = collections.Counter(int(v) for v in oc.cls[y0:y1][sl][sel])
            pv, _n = pairs.most_common(1)[0]
            ci = cl.most_common(1)[0][0]
            a, b_ = oc.decode(pv)
            name = ("%s->%s" % (LAYER_NAMES[a], LAYER_NAMES[b_]) if ci == C_VIOL else
                    "split:%s" % (LAYER_NAMES[a] if a >= 0 else "none") if ci == C_SPLIT else
                    "%s|%s" % (LAYER_NAMES[a], LAYER_NAMES[b_] if b_ >= 0 else "-"))
            out.append({"box": [int(x), int(y + y0), int(x + w), int(y + y0 + h)], "ink_px": px, "unit": u, "staff_y": (top, bot),
                        "class": CLASSES[ci], "pair": name, "classes": {CLASSES[c_]: n_ for c_, n_ in cl.items()}})
    out.sort(key=lambda d: -d["ink_px"])
    return out[:limit]


def choose_tiles(pool: List[Dict[str, Any]], n: int = 12, gap: int = 100, max_split: int = 2) -> List[Dict[str, Any]]:
    """Up to `n` tiles from the biggest pairs: pairs ranked by total ink, then round-robin biggest piece first, no two within `gap` px."""
    by_pair: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for it in pool:
        by_pair[it["pair"]].append(it)
    order = sorted(by_pair, key=lambda k: -sum(i["ink_px"] for i in by_pair[k]))
    for k in order:
        by_pair[k].sort(key=lambda d: -d["ink_px"])
    chosen: List[Dict[str, Any]] = []

    def near(it: Dict[str, Any]) -> bool:
        return any(c["page"] == it["page"] and not (it["box"][2] < c["box"][0] - gap or it["box"][0] > c["box"][2] + gap
                                                    or it["box"][3] < c["box"][1] - gap or it["box"][1] > c["box"][3] + gap) for c in chosen)

    while len(chosen) < n and any(by_pair[k] for k in order):
        for k in order:
            while by_pair[k]:
                it = by_pair[k].pop(0)
                if it.get("class") == "SPLIT-ACROSS-CLAIM" and sum(c.get("class") == "SPLIT-ACROSS-CLAIM" for c in chosen) >= max_split:
                    continue                      # the tiles are for the violation pairs; a clef cut is shown twice, not five times
                if not near(it):
                    chosen.append(it)
                    break
            if len(chosen) >= n:
                break
    return chosen


# ───────────────────────────── 6. the report ─────────────────────────────

def merge(ts: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ink_px": 0, "staff_line_px": 0, "class_px": collections.Counter(), "by_pair": {}, "split_pieces": 0}
    for t in ts:
        out["ink_px"] += t["ink_px"]
        out["staff_line_px"] += t["staff_line_px"]
        out["class_px"].update(t["class_px"])
        out["split_pieces"] += t["split_pieces"]
        for cl, d in t["by_pair"].items():
            out["by_pair"].setdefault(cl, collections.Counter()).update(d)
    return out


def pct2(x: int, tot: int) -> str:
    """Two decimals: the violation pairs are small shares of a page's ink."""
    return "%.2f%%" % (100.0 * x / tot) if tot else "-"


def render(label: str, t: Dict[str, Any], top: int = 8) -> List[str]:
    tot = t["ink_px"]
    cp = t["class_px"]
    lines = ["%s: %d ink px (staff lines %d left out)" % (label, tot, t["staff_line_px"]),
             "  " + "   ".join("%s %s" % (c, pct2(cp.get(c, 0), tot)) for c in CLASSES)]
    for cl in ("ORDER-VIOLATION", "OPEN", "SPLIT-ACROSS-CLAIM", "EARLIER-UNREAD"):
        d = t["by_pair"].get(cl)
        if not d:
            continue
        items = sorted(d.items(), key=lambda kv: -kv[1])[:top]
        lines.append("  %s by %s: " % (cl, "pair" if cl in ("ORDER-VIOLATION", "OPEN") else "owner")
                     + ", ".join("%s %s" % (k, pct2(v, tot)) for k, v in items))
    return lines


def top_violations(t: Dict[str, Any], top: int = 10) -> List[Tuple[str, int, bool]]:
    out = []
    for k, v in sorted((t["by_pair"].get("ORDER-VIOLATION") or {}).items(), key=lambda kv: -kv[1])[:top]:
        a, b = k.split("->")
        out.append((k, v, code_agrees(LAYER_NAMES.index(a), LAYER_NAMES.index(b))))
    return out


def run(rec: str, pages: Optional[Sequence[int]], *, tiles: Optional[pathlib.Path], out: Optional[pathlib.Path],
        env: Optional[Dict[str, str]] = None, cm_root: Optional[pathlib.Path] = None, log=print) -> Dict[str, Any]:
    from . import cell_map as CM
    src = CR.resolve_source(rec)
    pages = list(pages) if pages else CR.slice_pages(src)
    rows_all = CR.read_rows(src, pages)
    ed = CR.edition_info(rows_all)
    pdf = CR.LIB / ed["edition_path"]
    cm_root = cm_root or CM.ROOT_DEFAULT
    man = CM.info(pdf, root=cm_root)
    log("claim_order: %s  pages %s  master %s  env %s" % (src, pages, man["version"], env or {}))
    tallies, per_page, pool, images, verify = [], {}, [], {}, collections.Counter()
    for pg in pages:
        t0 = time.time()
        canvas, oc, v, pws, cells = build_order_page(rows_all, pdf, pg, cm_root, env)
        t = oc.tally()
        tallies.append(t)
        per_page[str(pg)] = t
        verify.update(v)
        if tiles is not None:
            comps = violation_components(oc, CR.staff_bands(cells), (C_VIOL, C_SPLIT))
            if comps:
                from PIL import Image
                images[pg] = Image.fromarray(pws.page.rgb).convert("RGB")
            pool += [{"page": pg, **c_} for c_ in comps]
        log("  page %d: %d ink px, %d cells ok / %d mismatched (%.0fs)" % (pg, t["ink_px"], v.get("cells_ok", 0), v.get("cells_mismatch", 0), time.time() - t0))
        del canvas, oc, pws, cells
    total = merge(tallies)
    lines = ["claim_order %s pages %s master %s" % (os.path.basename(str(src)), pages, man["version"])]
    lines += render("TOTAL", total)
    lines.append("  top ORDER-VIOLATION pairs (share of ink; code_agrees False = the code's own tier order also differs from the plan):")
    for k, v, ag in top_violations(total):
        lines.append("    %-34s %9d px %s  code_agrees=%s" % (k, v, pct2(v, total["ink_px"]), ag))
    for pg in pages:
        lines += render("page %d" % pg, merge([per_page[str(pg)]]))
    lines.append("  cells re-cut and matched stroke-for-stroke to the record: %s" % dict(verify))
    text = "\n".join(lines)
    report = {"record": str(src), "pages": pages, "master": man["version"], "env": env or {}, "total": {
        "ink_px": total["ink_px"], "staff_line_px": total["staff_line_px"], "class_px": dict(total["class_px"]),
        "by_pair": {k: dict(v) for k, v in total["by_pair"].items()}, "split_pieces": total["split_pieces"]},
        "per_page": per_page, "verify": dict(verify), "layers": [[n, list(f), c] for n, f, c in LAYERS]}
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "order.json").write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
        (out / "order.txt").write_text(text + "\n")
    if tiles is not None and pool:
        # the pool and the page rasters are kept beside the report so `merge-tiles` can pick 12 over several plates
        pdir = (tiles.parent if tiles.name == "tiles" else tiles) / "pagecache"
        pdir.mkdir(parents=True, exist_ok=True)
        plate = src.name              # a lane-report slice directory is named for its plate
        for it in pool:
            png = pdir / ("%s-p%d.png" % (plate, it["page"]))
            if not png.exists():
                images[it["page"]].save(png)
            it["png"], it["plate"], it["master"] = str(png), plate, man["version"]
        (pdir.parent / "pool.json").write_text(json.dumps(pool, default=str))
        chosen = choose_tiles(pool, 12)
        CR.cut_tiles(chosen, images, tiles.parent if tiles.name == "tiles" else tiles, 32.0, man["version"])
        text += "\ntiles: %d -> %s (key.json beside the folder)" % (len(chosen), tiles)
    log(text)
    return report


def merge_tiles(pool_files: Sequence[str], out_dir: pathlib.Path, n: int = 12, log=print) -> List[Dict[str, Any]]:
    """12 tiles over several plates' pools (`pool.json` of each `run --tiles`): the biggest pairs first, round-robin, one staff, one thin
    orange box, nothing else drawn; `key.json` goes OUTSIDE the tile folder (`out_dir`)."""
    from PIL import Image, ImageDraw
    pool: List[Dict[str, Any]] = []
    for f in pool_files:
        pool += json.loads(pathlib.Path(f).read_text())
    for it in pool:
        it["page"] = "%s:%s" % (it["plate"], it["page"])       # so two plates' page 0 are not "the same page" to the spacing test
    chosen = choose_tiles(pool, n)
    tdir = out_dir / "tiles"
    tdir.mkdir(parents=True, exist_ok=True)
    for f in tdir.glob("*"):
        f.unlink()
    key, cache = [], {}
    W = 520
    for k, it in enumerate(chosen, 1):
        im = cache.setdefault(it["png"], Image.open(it["png"]).convert("RGB"))
        bb = [it["box"][0] - 4, it["box"][1] - 4, it["box"][2] + 4, it["box"][3] + 4]
        cx, cy = (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0
        u = it["unit"]
        top, bot = it["staff_y"]
        x0, x1 = max(0, int(cx - 6 * u)), int(cx + 6 * u)
        y0, y1 = max(0, int(min(top - 4 * u, bb[1] - u))), int(max(bot + 4 * u, bb[3] + u))
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([round(bb[0] - x0), round(bb[1] - y0), round(bb[2] - x0), round(bb[3] - y0)],
                                       outline=CR.ORANGE, width=max(2, int(u / 10)))
        crop = crop.resize((W, max(1, int(W * crop.height / crop.width))))
        crop.save(tdir / ("tile_%02d.png" % k))
        key.append({"tile": k, "plate": it["plate"], "page": int(str(it["page"]).split(":")[1]), "box": it["box"], "pair": it["pair"],
                    "class": it["class"], "ink_px": it["ink_px"], "unit": u, "crop_origin": [x0, y0], "cell_map": it["master"]})
    (tdir / "README.md").write_text(
        "# Claim-order tiles\n\nEach picture is a piece of a scanned score page with ONE orange box on it and nothing else drawn. "
        "The box only says where to look.\n\n**Question, for every tile:** what is this ink (a note, a stem, a beam, a rest, a flag, "
        "an accidental, a dot, a tie or slur, a hairpin, a word or dynamic, a clef, a bracket, a barline, or something else)?\n\nAnswer by tile number.\n")
    (out_dir / "key.json").write_text(json.dumps(key, indent=1, default=str))
    log("merge-tiles: %d tiles -> %s (key.json beside the folder)" % (len(chosen), tdir))
    return key


# ───────────────────────────── 7. the controls ─────────────────────────────

def _cls(t: Dict[str, Any], cl: str, key: str) -> int:
    return int((t["by_pair"].get(cl) or {}).get(key, 0))


def word_unowned(t: Dict[str, Any]) -> int:
    """Ink the word layer read and does not own: ORDER-VIOLATION pairs `word_dynamic->X` plus OPEN pairs `word_dynamic|X`."""
    v = sum(n for k, n in (t["by_pair"].get("ORDER-VIOLATION") or {}).items() if k.startswith(LAYER_NAMES[L_WORDS] + "->"))
    o = sum(n for k, n in (t["by_pair"].get("OPEN") or {}).items() if k.startswith(LAYER_NAMES[L_WORDS] + "|"))
    return int(v + o)


def controls(rec: str, page: int, cm_root: Optional[pathlib.Path] = None, branch: Optional[Dict[str, Any]] = None, log=print) -> int:
    """Controls (a), (b), (c), (e) on `page` of `rec`; (d) when `branch` names {rec, page, key, tile}. Exit 1 if any does not behave."""
    from . import cell_map as CM
    src = CR.resolve_source(rec)
    rows = CR.read_rows(src, [page])
    ed = CR.edition_info(rows)
    pdf = CR.LIB / ed["edition_path"]
    cm_root = cm_root or CM.ROOT_DEFAULT
    ok = True
    canvas, oc, _v, *_ = build_order_page(rows, pdf, page, cm_root)
    base = oc.tally()
    key = "word_dynamic->head"
    # (a)
    _c2, oc_a, *_ = build_order_page(rows, pdf, page, cm_root, plant_head_on_words=True)
    a = oc_a.tally()
    log("(a) head planted over READ words' ink: %s ink px %d -> %d (must rise from the unplanted page)" % (key, _cls(base, "ORDER-VIOLATION", key), _cls(a, "ORDER-VIOLATION", key)))
    ok &= _cls(a, "ORDER-VIOLATION", key) > _cls(base, "ORDER-VIOLATION", key)
    # (b)
    _c3, oc_b, *_ = build_order_page(rows, pdf, page, cm_root, env={"OMR_CLAIM_WORDS_FIRST": "0"})
    b = oc_b.tally()
    # The word claim rows are not filed, the word reader's rows stay. Whether a HEAD box then takes the ink (words -> heads) needs a head box
    # standing on a letter, and the stroke owner refuses a head on a letter's shape, so the ink is usually left OPEN instead: the control
    # counts every word-read ink the word layer does not own and prints the head pair beside it.
    nb, nbase = word_unowned(b), word_unowned(base)
    log("(b) OMR_CLAIM_WORDS_FIRST=0 (word claim rows not filed, the word reader's rows kept): word-read ink the word layer does not own "
        "(words->later violations + words-first OPEN) %d -> %d px (must rise); of it words->heads %d -> %d"
        % (nbase, nb, _cls(base, "ORDER-VIOLATION", key), _cls(b, "ORDER-VIOLATION", key)))
    ok &= nb > nbase
    # (c)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="claim-order-copy-"))
    try:
        for k in ("observations", "abstentions"):
            shutil.copy(src / ("%s.jsonl" % k), tmp / ("%s.jsonl" % k))
        rows2 = CR.read_rows(tmp, [page])
        _c4, oc_c, *_ = build_order_page(rows2, pdf, page, cm_root)
        same = json.dumps(oc_c.tally(), sort_keys=True) == json.dumps(base, sort_keys=True)
        log("(c) identical copy of the rows: %s" % ("identical" if same else "DIFFERENT"))
        ok &= same
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # (e)
    ref = CR.PageInk.tally(canvas)
    ink = int(canvas.ink.sum())
    ok_e = base["ink_px"] + base["staff_line_px"] == ink and ref["ink_px"] == ink
    log("(e) the order canvas lies on the 2.236 canvas: ink px %d = %d + %d staff-line px: %s" % (ink, base["ink_px"], base["staff_line_px"], "yes" if ok_e else "NO"))
    ok &= ok_e
    # (d)
    if branch:
        ok &= control_tip(branch["rec"], branch["page"], branch["key"], branch["tile"], cm_root, log)
    else:
        log("(d) not run here: it needs the code of land-239-flip-wip and a gather made with it (`claim_order tip`, run from that tree)")
    log("controls: %s" % ("ALL BEHAVE" if ok else "A CONTROL DID NOT DO WHAT IT MUST"))
    return 0 if ok else 1


def control_tip(rec: str, page: int, key_path: str, tile_no: int, cm_root: Optional[pathlib.Path] = None, log=print) -> bool:
    """CONTROL (d): the clef tip of Sean's 2.239 round-2 tile `tile_no` (`key_path`), read from a gather made with the 2.239 split ON, must show
    as SPLIT-ACROSS-CLAIM. Run it from the tree that made the gather: the stroke map must cut the cells the way the record's strokes were cut
    (a cell that does not match stroke for stroke is dropped, and the tip would then 'pass' as nothing)."""
    from . import cell_map as CM
    cm_root = cm_root or CM.ROOT_DEFAULT
    brow = CR.read_rows(CR.resolve_source(rec), [page])
    bpdf = CR.LIB / CR.edition_info(brow)["edition_path"]
    _c, oc, v, *_ = build_order_page(brow, bpdf, page, cm_root)
    tile = next(t for t in json.loads(pathlib.Path(key_path).read_text()) if t["tile"] == tile_no)
    x0, y0, x1, y1 = tile["box"]
    box = (slice(y0, y1), slice(x0, x1))
    ink = int(oc.mask[box].sum())
    sp = int((oc.split[box] & oc.mask[box]).sum())
    cl = collections.Counter(CLASSES[int(c)] for c in oc.cls[box][oc.mask[box]])
    log("(d) 2.239 split ON, tile %d (%s) box %s: %d of %d ink px are SPLIT-ACROSS-CLAIM (must be > 0); classes there %s; cells %s; split pieces on the page %d"
        % (tile_no, tile.get("kind"), tile["box"], sp, ink, dict(cl), v, len(oc.split_pieces)))
    return sp > 0 and not v.get("cells_mismatch")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="claim_order", description=__doc__.split("\n")[0])
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "tip":
        ap.add_argument("cmd")
        ap.add_argument("rec")
        ap.add_argument("--page", type=int, required=True)
        ap.add_argument("--tip-key", required=True)
        ap.add_argument("--tip-tile", type=int, default=7)
        ap.add_argument("--cell-map", default=None)
        a = ap.parse_args(argv)
        return 0 if control_tip(a.rec, a.page, a.tip_key, a.tip_tile, pathlib.Path(a.cell_map) if a.cell_map else None) else 1
    if argv and argv[0] == "merge-tiles":
        ap.add_argument("cmd")
        ap.add_argument("out")
        ap.add_argument("pools", nargs="+")
        a = ap.parse_args(argv)
        merge_tiles(a.pools, pathlib.Path(a.out))
        return 0
    if argv and argv[0] == "controls":
        ap.add_argument("cmd")
        ap.add_argument("rec")
        ap.add_argument("--page", type=int, default=0)
        ap.add_argument("--cell-map", default=None)
        ap.add_argument("--branch-rows", default=None)
        ap.add_argument("--branch-page", type=int, default=None)
        ap.add_argument("--tip-key", default=None)
        ap.add_argument("--tip-tile", type=int, default=7)
        a = ap.parse_args(argv)
        br = ({"rec": a.branch_rows, "page": a.branch_page, "key": a.tip_key, "tile": a.tip_tile}
              if a.branch_rows and a.branch_page is not None and a.tip_key else None)
        return controls(a.rec, a.page, pathlib.Path(a.cell_map) if a.cell_map else None, br)
    ap.add_argument("rec", help="slice directory, PLATE:TAG (lane_report slices) or a .record.json under 5 GB")
    ap.add_argument("--pages", default=None)
    ap.add_argument("--tiles", default=None, help="write 12 tiles of the biggest violation pairs to DIR/tiles (key.json beside the folder)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("--cell-map", default=None)
    a = ap.parse_args(argv)
    pages = None
    if a.pages:
        pages = []
        for part in a.pages.split(","):
            lo, _, hi = part.partition("-")
            pages += list(range(int(lo), int(hi or lo) + 1))
    t = pathlib.Path(a.tiles) if a.tiles else None
    run(a.rec, pages, tiles=(t / "tiles" if t else None), out=pathlib.Path(a.out) if a.out else (t if t else None),
        env=CR.parse_env(a.env), cm_root=pathlib.Path(a.cell_map) if a.cell_map else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
