"""ROADMAP 2.107 -- read the dynamic letters the detector never boxed.

Sean, 2026-10-13: *"sf should be read as a dynamic - it is letters"* and *"we
added a whole library of text to be checked"*. Case: Litolff Beethoven 5, pdf
page 2, system 1, flute staff, bar 7 (the 2.90 review, tile 9): the printed
`sf` is boxed as a `noteheadBlackOnLine` (the `f`) and two `rest16th` (the `s`),
and nothing is boxed as a dynamic, so `on_a_dynamic_letter` (2.76) never fires
and the `f` becomes a quarter note.

WHAT THE READERS DID BEFORE. `direction_text` (OCR, Surya then Tesseract) looks
in the text bands BETWEEN staves; the dynamic letters the detector boxes
(`dynamicF` ... `dynamicZ`) are joined into words by `adjudicate_dynamic`
against a typed 17-word set; nothing read ink the detector boxed as something
else. Measured on this very `sf` (scratchpad of 2.107, `FINDINGS` §2.107): Surya
returns nothing on four crops of it, Tesseract returns `Ea`/`se`/`om`, and the
production detector's own `dynamicF` fires only when the crop is shown at about
8-12 pixels to the staff space with the staff lines taken out -- at its working
scale (16) with the lines in it says note and rest.

WHAT THIS DOES. A SECOND LOOK, by the same detector, at the ink under a
head/rest box that LOOKS like letters: stemless, letter-sized, no beam.
  1. the staff lines are taken out locally (a vertical run that is no thicker
     than the line, on a long horizontal stroke) -- a stroke that CROSSES a line
     is kept, so an `f`'s stem survives where an opening would cut it;
  2. the ink of the group is shown to the detector at five scales
     (`LOOK_SCALES`), where its letter classes live;
  3. a letter counts only where one class is seen at >= `STRONG_MIN_SCALES`
     scales at >= `STRONG_CONF` (a vote, not a score);
  4. letter-sized ink beside a read letter that no vote explains is an UNREAD
     LETTER: a slot that may be any letter, never a guessed one;
  5. the string the letters (and slots) can spell is looked up in the terms
     library (`musical_terms`, category `dynamics`) and ONLY a string the
     library holds is a dynamic. A slot that completes several library strings
     (`?f` = sf, mf, rf ...) makes the dynamic NARROWED, never a guess.
The result is a handful of letter rows filed as `dynamic*` detections under
their own reader name; everything downstream (twins, ownership, spelling,
anchor, export) is the existing 2.68 machinery, and the refusals of the head
and rest boxes whose ink the letters explain are ADJUDICATE's.

Pure functions only: no log, no cell, no page object. `detect` is any callable
`(image_bgr, imgsz) -> [(class_name, conf, (x0, y0, x1, y1))]`.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

#: Pixels to the staff space the detector is shown, one look each. MEASURED on
#: the 2.90 tile 9 `sf` (Litolff p2): `dynamicF` 0.80-0.88 at every one of these
#: with the lines taken out, and gone at 16 (its working scale on a cell) and
#: above. CONVENTION ASSUMED for other plates / WHAT WOULD FALSIFY IT: a plate
#: whose letters read at 14 and not at 8-12 -- the count of `scales_seen` in the
#: row says it.
LOOK_SCALES: Tuple[float, ...] = (8.0, 9.0, 10.0, 11.0, 12.0)
#: The floor the detector is asked at; everything above it is recorded, only
#: `STRONG_CONF` at `STRONG_MIN_SCALES` looks counts as a reading.
LOOK_CONF_FLOOR = 0.05
#: COST, NOT A DECISION. A group is first shown at these two scales; only one
#: that draws a letter hypothesis of at least `PROBE_CONF` at either gets the
#: full five-scale look under two erasures. Almost every group (Litolff:
#: 1,519 of 1,594; a note, a rest, a tie's end) draws none, and the full look
#: is ten detector calls. Every reading the full look has made on the real
#: pages (Litolff, Dvorak: 9 groups) drew >= 0.68 at one of these two.
PROBE_SCALES: Tuple[float, ...] = (9.0, 11.0)
PROBE_CONF = 0.3
STRONG_CONF = 0.7
STRONG_MIN_SCALES = 4
#: A WEAK hypothesis (an unread letter's best guess) is decisive only at the
#: same bar; below it the slot stays open. The first build used 0.5 on 3 looks
#: and read the broken `s` of the 2.90 tile 9 `sf` as `m` (0.514 on 5 looks):
#: a letter drawn from fragments is not read by a vote that low.
WEAK_DECISIVE_CONF = STRONG_CONF
WEAK_DECISIVE_SCALES = STRONG_MIN_SCALES
WEAK_CONF = 0.15

#: A piece of ink is a LETTER's only within these sizes (staff spaces): an `f`
#: is ~2.9 tall (Sean's 12 hand-labelled: 2.4-2.6), a stem is >= 3.0 and thin,
#: a beam is wider than `LETTER_W_MAX_SPACES`.
LETTER_H_MAX_SPACES = 3.4
LETTER_W_MAX_SPACES = 6.5
LETTER_SPECK_SPACES2 = 0.08
#: A staff-line remnant: flat and long.
LINE_REMNANT_H_SPACES = 0.45
LINE_REMNANT_W_SPACES = 1.2
#: Letters of one word stand this close (the 2.68 neighbour gap is 0.5).
GROUP_GAP_SPACES = 0.6
#: Unread ink must stand this close to a read letter to be a slot of its word.
SLOT_GAP_SPACES = 0.8
#: Below this share of a candidate group's ink inside a DETECTOR dynamic box,
#: the group is not already boxed.
ALREADY_BOXED_SHARE = 0.3
#: A head/rest box whose ink lies this much inside the read letters' boxes is
#: the letters' ink (the refusal ADJUDICATE makes reads this share).
COVER_SHARE = 0.5

LETTER_OF_CLASS = {"dynamicF": "f", "dynamicP": "p", "dynamicM": "m",
                   "dynamicS": "s", "dynamicZ": "z", "dynamicR": "r"}
CLASS_OF_LETTER = {v: k for k, v in LETTER_OF_CLASS.items()}
#: every letter a library dynamic is spelled with
_ALL_LETTERS = tuple(sorted(CLASS_OF_LETTER))
MAX_STRINGS = 64


# ── the terms library is the vocabulary ──────────────────────────────────────


def library_dynamic(text: str) -> Optional[str]:
    """The library term (`Sforzando`) `text` is a printed dynamic of, or None.

    Exact lookup (`musical_terms.lookup` folds case, accents and punctuation);
    only a `dynamics` entry counts, and only a short letter string: this is
    never asked about a word. A string the library does not hold -- `pppp`,
    `ffff` and `sfpp` are not in the 1,760-term export -- is not a dynamic
    HERE, and the reader says so with the string it tried."""
    if not text or len(text) > 5 or not text.isalpha():
        return None
    from .. import musical_terms as _mt
    for m in _mt.lookup(text):
        if m.term.category == "dynamics" and m.via in ("abbreviation", "term"):
            return m.term.term
    return None


# ── ink ──────────────────────────────────────────────────────────────────────


def _runs(col: np.ndarray) -> List[Tuple[int, int]]:
    """(start, end) inclusive of every run of non-zero in a 1-D array."""
    if not col.any():
        return []
    d = np.diff(np.concatenate(([0], (col > 0).astype(np.int8), [0])))
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0] - 1
    return list(zip(starts.tolist(), ends.tolist()))


#: The two erasures a letter must read the same under (`read_group`): the line
#: thickness plus a fifth of a space (the default) and plus ONE pixel. Free
#: ink is the same under both; a letter lying along a line is not, and a class
#: that changes with how the lines were taken out is not a reading.
ERASE_SLACK_TIGHT_PX = 1


def erase_staff_lines(ink: np.ndarray, sp: float,
                      slack_px: Optional[int] = None) -> np.ndarray:
    """`ink` (non-zero = ink) with the staff and ledger lines taken out, 0/1.

    A line is a long horizontal stroke (`>= 3 sp` wide: `MORPH_OPEN`); at each
    column the ink run through it is erased only where the run is NO thicker
    than the line is (+ a fifth of a space). A letter's stroke crossing the
    line is a longer run and survives; a stroke lying ALONG the line is lost,
    which is the price (the 2.107 `s` came back as fragments). An opening with
    a long kernel (what `letter_ink_extent` does) cuts the same `f` in two.
    """
    out = (ink > 0).astype(np.uint8)
    kh = max(5, int(round(3.0 * sp)))
    if out.shape[1] < kh:
        return out
    hl = cv2.morphologyEx(out, cv2.MORPH_OPEN,
                          cv2.getStructuringElement(cv2.MORPH_RECT, (kh, 1)))
    if not hl.any():
        return out
    lens = []
    for x in range(hl.shape[1]):
        for a, b in _runs(hl[:, x]):
            lens.append(b - a + 1)
    if not lens:
        return out
    limit = int(np.median(lens)) + (max(2, int(round(0.2 * sp)))
                                    if slack_px is None else int(slack_px))
    for x in range(out.shape[1]):
        if not hl[:, x].any():
            continue
        for a, b in _runs(out[:, x]):
            if (b - a + 1) <= limit and hl[a:b + 1, x].any():
                out[a:b + 1, x] = 0
    return out


@dataclass
class Comp:
    x0: int
    y0: int
    x1: int          # exclusive
    y1: int
    area: int
    label: int = 0

    @property
    def w(self) -> int:
        return self.x1 - self.x0

    @property
    def h(self) -> int:
        return self.y1 - self.y0

    def box(self) -> Tuple[int, int, int, int]:
        return (self.x0, self.y0, self.x1, self.y1)


def letter_components(clean: np.ndarray, sp: float
                      ) -> Tuple[List[Comp], np.ndarray]:
    """The LETTER-SIZED connected pieces of cleaned ink, and the label image.
    Taller than `LETTER_H_MAX_SPACES` (a stem, a barline, a note with its
    stem), wider than `LETTER_W_MAX_SPACES` (a beam, a tie), a speck, or a
    staff-line remnant is not a letter piece and is left out."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(
        (clean > 0).astype(np.uint8), connectivity=8)
    out: List[Comp] = []
    for i in range(1, n):
        x, y, w, h, a = (int(st[i, k]) for k in range(5))
        if a < LETTER_SPECK_SPACES2 * sp * sp:
            continue
        if h > LETTER_H_MAX_SPACES * sp or w > LETTER_W_MAX_SPACES * sp:
            continue
        if h < LINE_REMNANT_H_SPACES * sp and w > LINE_REMNANT_W_SPACES * sp:
            continue
        out.append(Comp(x, y, x + w, y + h, a, i))
    return out, lab


def _gap(a: Comp, b: Comp) -> Tuple[float, bool]:
    """(horizontal gap in px, vertical ranges overlap)."""
    gx = max(0, max(a.x0, b.x0) - min(a.x1, b.x1))
    voverlap = min(a.y1, b.y1) > max(a.y0, b.y0)
    return float(gx), voverlap


def group_around(comps: Sequence[Comp], seed_boxes: Sequence[Sequence[float]],
                 sp: float) -> List[Comp]:
    """The letter-like pieces touching any seed box, grown through pieces no
    further than `GROUP_GAP_SPACES` apart on a shared line (the letters of one
    word). Empty where no piece lies under a seed."""
    def hits(c: Comp, b) -> bool:
        return (min(c.x1, b[2]) > max(c.x0, b[0])
                and min(c.y1, b[3]) > max(c.y0, b[1]))
    grp = [c for c in comps if any(hits(c, b) for b in seed_boxes)]
    if not grp:
        return []
    gap = GROUP_GAP_SPACES * sp
    grew = True
    while grew:
        grew = False
        for c in comps:
            if c in grp:
                continue
            for g in grp:
                dx, vo = _gap(c, g)
                if vo and dx <= gap:
                    grp.append(c)
                    grew = True
                    break
    return grp


def union_box(comps: Sequence[Comp]) -> Tuple[int, int, int, int]:
    return (min(c.x0 for c in comps), min(c.y0 for c in comps),
            max(c.x1 for c in comps), max(c.y1 for c in comps))


# ── the second look ──────────────────────────────────────────────────────────


@dataclass
class Hypothesis:
    cls: str
    conf: float
    box: Tuple[float, float, float, float]      # window pixels
    scale: float


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


CANVAS_MARGIN_PX = 40


def look(group_ink: np.ndarray, box: Tuple[int, int, int, int], sp: float,
         detect: Callable[[np.ndarray, int], list],
         scales: Sequence[float] = LOOK_SCALES) -> List[Hypothesis]:
    """Show the group's ink (0/1, window pixels; everything not in the group
    already zeroed) to `detect` at each scale; every box it returns, mapped
    back to window pixels. The crop is the group's box plus 1.5 spaces."""
    x0, y0, x1, y1 = box
    pad = int(round(1.5 * sp))
    cx0, cy0 = max(0, x0 - pad), max(0, y0 - pad)
    cx1, cy1 = min(group_ink.shape[1], x1 + pad), min(group_ink.shape[0], y1 + pad)
    crop = (255 - 255 * (group_ink[cy0:cy1, cx0:cx1] > 0)).astype(np.uint8)
    out: List[Hypothesis] = []
    for target in scales:
        f = target / sp
        im = cv2.resize(crop, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        side = max(im.shape[:2]) + 2 * CANVAS_MARGIN_PX
        canvas = np.full((side, side), 255, np.uint8)
        canvas[CANVAS_MARGIN_PX:CANVAS_MARGIN_PX + im.shape[0],
               CANVAS_MARGIN_PX:CANVAS_MARGIN_PX + im.shape[1]] = im
        canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
        imgsz = max(128, int(math.ceil(side / 32.0) * 32))
        for name, conf, (bx0, by0, bx1, by1) in detect(canvas, imgsz):
            out.append(Hypothesis(
                name, float(conf),
                ((bx0 - CANVAS_MARGIN_PX) / f + cx0,
                 (by0 - CANVAS_MARGIN_PX) / f + cy0,
                 (bx1 - CANVAS_MARGIN_PX) / f + cx0,
                 (by1 - CANVAS_MARGIN_PX) / f + cy0), float(target)))
    return out


@dataclass
class Region:
    """One letter-sized place on the group's ink, with the letters it may be."""
    box: Tuple[float, float, float, float]
    #: the letters still possible (one = read; several = open)
    letters: Tuple[str, ...]
    #: `read` (a vote) or `unread` (ink no vote explains)
    how: str
    conf: float = 0.0
    scales_seen: int = 0
    weak: Dict[str, Tuple[float, int]] = field(default_factory=dict)
    #: letters the default erasure read strongly and the tight one did not
    #: confirm: evidence that SOMETHING letter-shaped is here, never a name
    unstable: Tuple[str, ...] = ()


def regions_from(hyps: Sequence[Hypothesis]) -> List[Region]:
    """Vote the letter hypotheses of all looks into regions. A region is a
    cluster of boxes (IoU >= 0.4); each class in it carries its best confidence
    and the number of looks that saw it. A class at >= `STRONG_CONF` on >=
    `STRONG_MIN_SCALES` looks is READ; two such classes on one ink are both
    kept (twins: `f`/`p`, left to the 2.68 identity-by-ink rule)."""
    letters = [h for h in hyps if h.cls in LETTER_OF_CLASS]
    letters.sort(key=lambda h: -h.conf)
    clusters: List[List[Hypothesis]] = []
    for h in letters:
        for c in clusters:
            if _iou(h.box, c[0].box) >= 0.4:
                c.append(h)
                break
        else:
            clusters.append([h])
    out: List[Region] = []
    for c in clusters:
        stats: Dict[str, Tuple[float, set]] = {}
        for h in c:
            best, seen = stats.get(h.cls, (0.0, set()))
            stats[h.cls] = (max(best, h.conf), seen | {h.scale})
        strong = sorted(
            (cls for cls, (best, seen) in stats.items()
             if best >= STRONG_CONF and len(seen) >= STRONG_MIN_SCALES))
        top = c[0]
        weak = {LETTER_OF_CLASS[k]: (round(b, 3), len(s))
                for k, (b, s) in stats.items()}
        if strong:
            key = max(strong, key=lambda k: stats[k][0])
            boxes = [h.box for h in c if h.cls == key]
            box = tuple(float(np.median([b[i] for b in boxes])) for i in range(4))
            out.append(Region(box=box,  # type: ignore[arg-type]
                              letters=tuple(LETTER_OF_CLASS[k] for k in strong),
                              how="read", conf=round(stats[key][0], 3),
                              scales_seen=len(stats[key][1]), weak=weak))
        else:
            out.append(Region(box=top.box, letters=(), how="weak",
                              conf=round(top.conf, 3),
                              scales_seen=len(stats[top.cls][1]), weak=weak))
    out.sort(key=lambda r: r.box[0])
    return out


def _covered(c: Comp, boxes: Sequence[Sequence[float]]) -> float:
    area = max(1, c.w * c.h)
    best = 0.0
    for b in boxes:
        ix = max(0.0, min(c.x1, b[2]) - max(c.x0, b[0]))
        iy = max(0.0, min(c.y1, b[3]) - max(c.y0, b[1]))
        best = max(best, ix * iy / area)
    return best


#: Ink beside a read letter, off its core piece, must hold at least this much
#: (square staff spaces) to be a letter of its own and not a fleck.
SLOT_MIN_AREA_SPACES2 = 0.3
#: ... and a weak letter hypothesis must stand over it on at least this many
#: looks, so that a fragment of the read letter itself (a crossbar cut by a
#: line) is not an unread letter.
SLOT_WEAK_LOOKS = 2


def slots_for(strong: Sequence[Region], weak: Sequence[Region],
              comps: Sequence[Comp], sp: float) -> List[Region]:
    """UNREAD LETTERS: ink of the group that is not the core piece of a read
    letter, that a WEAK letter hypothesis stands over, and that is beside a read
    letter. The read letter's BOX may cover such ink (the 2.90 `sf`: the
    detector's `f` box spans the `s` fragments to its left), so coverage by a
    box is NOT the test; connectedness is -- a read letter's own ink is its
    core piece (the biggest piece centred in its box) and whatever is joined
    to it.

    A weak hypothesis that is decisive (`WEAK_DECISIVE_CONF` on
    `WEAK_DECISIVE_SCALES` looks) names the slot's letter; otherwise the slot
    is open (`letters=()`: the caller spells it with every letter the library
    can complete). No weak hypothesis over the ink, no slot: leftover ink with
    no letter-shaped evidence is read as a part of the letter beside it."""
    if not strong:
        return []
    cores: List[Comp] = []
    for r in strong:
        inside = [c for c in comps
                  if r.box[0] <= (c.x0 + c.x1) / 2.0 <= r.box[2]
                  and r.box[1] <= (c.y0 + c.y1) / 2.0 <= r.box[3]]
        if inside:
            cores.append(max(inside, key=lambda c: c.area))
    left = [c for c in comps if c not in cores
            and c.area >= 0.05 * sp * sp]
    if not left:
        return []
    gap = SLOT_GAP_SPACES * sp
    slots: List[List[Comp]] = []
    for c in sorted(left, key=lambda c: c.x0):
        for sl in slots:
            if any(_gap(c, m)[0] <= GROUP_GAP_SPACES * sp and _gap(c, m)[1]
                   for m in sl):
                sl.append(c)
                break
        else:
            slots.append([c])
    out: List[Region] = []
    for sl in slots:
        if sum(c.area for c in sl) < SLOT_MIN_AREA_SPACES2 * sp * sp:
            continue
        ux0, uy0, ux1, uy1 = union_box(sl)
        near = min(max(0.0, max(ux0, r.box[0]) - min(ux1, r.box[2]))
                   for r in strong)
        if near > gap:
            continue            # stray ink, not a letter of this word
        wk: Dict[str, Tuple[float, int]] = {}
        shaky: set = set()
        for w in weak:
            if _iou((ux0, uy0, ux1, uy1), w.box) < 0.3:
                continue
            shaky |= set(w.unstable)
            for letter, (conf, n) in w.weak.items():
                if n >= SLOT_WEAK_LOOKS and conf >= WEAK_CONF:
                    if letter not in wk or conf > wk[letter][0]:
                        wk[letter] = (conf, n)
        if not wk:
            continue
        # a letter the two erasures disagreed on is evidence of a letter, not
        # its name (Litolff p10's `s` was `m` at 0.739 under one erasure)
        decisive = tuple(sorted(
            k for k, (conf, n) in wk.items()
            if conf >= WEAK_DECISIVE_CONF and n >= WEAK_DECISIVE_SCALES
            and k not in shaky))
        out.append(Region(box=(float(ux0), float(uy0), float(ux1), float(uy1)),
                          letters=decisive, how="unread", conf=0.0,
                          scales_seen=0, weak=wk))
    return out


# ── spelling, against the library ────────────────────────────────────────────


@dataclass
class Spelling:
    status: str                       # "spelled" | "narrowed" | "rejected"
    reason: str
    text: Optional[str] = None        # the one string (spelled)
    candidates: Tuple[str, ...] = ()  # library strings (narrowed)
    tried: Tuple[str, ...] = ()
    term: Optional[str] = None
    regions: List[Region] = field(default_factory=list)   # left to right,
    #: with an open region's `letters` filled with the letters each library
    #: string puts in it


def spell(regions: Sequence[Region]) -> Spelling:
    """Left-to-right, the strings the regions can spell, each looked up in the
    library. An unread slot with no decisive letter may be any letter; a
    string only counts where the library holds it. One valid string = spelled;
    several = narrowed (the dynamic exists, its letters are not all read);
    none = rejected, with what was tried."""
    ordered = sorted(regions, key=lambda r: r.box[0])
    if not ordered or not any(r.how == "read" for r in ordered):
        return Spelling("rejected", "no_letter_read")
    slots = [r.letters if r.letters else _ALL_LETTERS for r in ordered]
    n = 1
    for s in slots:
        n *= len(s)
    if n > MAX_STRINGS:
        return Spelling("rejected", "too_many_readings", tried=())
    combos = ["".join(c) for c in itertools.product(*slots)]
    valid = [c for c in combos if library_dynamic(c)]
    if not valid:
        return Spelling("rejected", "not_in_library",
                        tried=tuple(combos[:8]) if n > 8 else tuple(combos))
    valid = sorted(set(valid))
    resolved: List[Region] = []
    for i, r in enumerate(ordered):
        letters = tuple(sorted({v[i] for v in valid}))
        resolved.append(Region(r.box, letters, r.how, r.conf, r.scales_seen,
                               r.weak, r.unstable))
    if len(valid) == 1:
        return Spelling("spelled", "library", text=valid[0],
                        term=library_dynamic(valid[0]), tried=tuple(combos[:8]),
                        regions=resolved)
    return Spelling("narrowed", "several_library_strings",
                    candidates=tuple(valid), tried=tuple(combos[:8]),
                    regions=resolved)


# ── one candidate group, end to end ──────────────────────────────────────────


@dataclass
class GroupReading:
    status: str                  # "read" | "narrowed" | "rejected" | "skipped"
    reason: str
    box: Tuple[int, int, int, int]
    spelling: Optional[Spelling] = None
    #: per seed box, the share of its ink inside the read letters' boxes
    cover: List[float] = field(default_factory=list)
    rival: Optional[Tuple[str, float]] = None    # best note/rest class, any look
    n_hypotheses: int = 0
    #: how close a refusal came (CLAUDE.md "A refusal says how close it came"):
    #: the best (letter, confidence, looks seen) over all looks, strongest first
    near: List[Tuple[str, float, int]] = field(default_factory=list)
    #: the member ids `cover` is in the order of (set by `read_page_group`)
    seed_ids: List[Any] = field(default_factory=list)
    #: True where only the two-scale probe was run (no letter drawn at it)
    probe_only: bool = False
    #: letters seen strongly under the default erasure that the tight erasure
    #: did not confirm: `(letters, conf)` each -- the reading they would have
    #: been, recorded so the near misses can be shown
    unstable: List[Tuple[Tuple[str, ...], float]] = field(default_factory=list)


def _near(hyps: Sequence[Hypothesis]) -> List[Tuple[str, float, int]]:
    stats: Dict[str, Tuple[float, set]] = {}
    for h in hyps:
        if h.cls in LETTER_OF_CLASS:
            best, seen = stats.get(h.cls, (0.0, set()))
            stats[h.cls] = (max(best, h.conf), seen | {h.scale})
    return sorted(((LETTER_OF_CLASS[k], round(b, 3), len(sn))
                   for k, (b, sn) in stats.items()), key=lambda t: -t[1])[:3]


def _rival(hyps: Sequence[Hypothesis]) -> Optional[Tuple[str, float]]:
    best: Optional[Tuple[str, float]] = None
    for h in hyps:
        low = h.cls.lower()
        if h.cls in LETTER_OF_CLASS:
            continue
        if low.startswith("notehead") or low.startswith("rest"):
            if best is None or h.conf > best[1]:
                best = (h.cls, round(h.conf, 3))
    return best


def _confirm_under_the_tight_erasure(
        strong: List[Region], regions_b: Sequence[Region]
) -> Tuple[List[Region], List[Region], List[Tuple[Tuple[str, ...], float]]]:
    """`(still strong, demoted to weak, unstable)`: a strong region keeps the
    letters the TIGHT erasure also read strongly on the same ink (box IoU >=
    0.4); with none left it is demoted to a weak region carrying its stats."""
    kept: List[Region] = []
    demoted: List[Region] = []
    unstable: List[Tuple[Tuple[str, ...], float]] = []
    for r in strong:
        agree = set()
        for b in regions_b:
            if b.how == "read" and _iou(r.box, b.box) >= 0.4:
                agree |= set(b.letters)
        letters = tuple(l for l in r.letters if l in agree)
        if letters:
            kept.append(Region(r.box, letters, "read", r.conf, r.scales_seen,
                               r.weak))
        else:
            unstable.append((r.letters, r.conf))
            demoted.append(Region(r.box, (), "weak", r.conf, r.scales_seen,
                                  r.weak, unstable=tuple(r.letters)))
    return kept, demoted, unstable


def read_group(window_clean: np.ndarray, comps: Sequence[Comp],
               seed_boxes: Sequence[Sequence[float]], sp: float,
               detect: Callable[[np.ndarray, int], list],
               dynamic_boxes: Sequence[Sequence[float]] = (),
               window_alt: Optional[np.ndarray] = None) -> GroupReading:
    """Read ONE group of letter-like pieces (`group_around`'s result).

    `window_clean` is the cleaned ink of the window (0/1), `comps` the group's
    pieces, `seed_boxes` the head/rest boxes that put the group here, all in
    window pixels. Returns the reading and, per seed box, how much of its ink
    the read letters hold (`cover`)."""
    box = union_box(comps)
    # a group the detector already boxed as a dynamic is not ours to read
    already = 0
    total = 0
    for c in comps:
        total += c.area
        if dynamic_boxes and _covered(c, dynamic_boxes) >= 0.5:
            already += c.area
    if total and already / total >= ALREADY_BOXED_SHARE:
        return GroupReading("skipped", "already_boxed_as_a_dynamic", box)
    mask = np.zeros_like(window_clean)
    for c in comps:
        sub = window_clean[c.y0:c.y1, c.x0:c.x1]
        mask[c.y0:c.y1, c.x0:c.x1] |= sub
    probe = look(mask, box, sp, detect, scales=PROBE_SCALES)
    if not any(h.cls in LETTER_OF_CLASS and h.conf >= PROBE_CONF for h in probe):
        return GroupReading("rejected", "no_letter_read", box,
                            rival=_rival(probe), n_hypotheses=len(probe),
                            near=_near(probe), probe_only=True)
    hyps = look(mask, box, sp, detect)
    rival = _rival(hyps)
    near = _near(hyps)
    regions = regions_from(hyps)
    strong = [r for r in regions if r.how == "read"]
    unstable: List[Tuple[Tuple[str, ...], float]] = []
    if window_alt is not None and strong:
        # ⚠️ A LETTER IS READ ONLY IF IT READS THE SAME WHEN THE STAFF LINES
        # ARE TAKEN OUT ANOTHER WAY. Litolff p10 prints an `sf` whose `s` lies
        # on a line; the detector called its fragments `m` at 0.739 on four
        # looks (-> `mf`) and, with the lines taken out one pixel tighter,
        # something else. Free ink reads the same either way.
        mask_b = np.zeros_like(window_alt)
        for c in comps:
            y0, y1 = max(0, c.y0 - 1), min(window_alt.shape[0], c.y1 + 1)
            x0, x1 = max(0, c.x0 - 1), min(window_alt.shape[1], c.x1 + 1)
            mask_b[y0:y1, x0:x1] |= window_alt[y0:y1, x0:x1]
        regions_b = regions_from(look(mask_b, box, sp, detect))
        strong, demoted, unstable = _confirm_under_the_tight_erasure(
            strong, regions_b)
        regions = sorted([r for r in regions if r.how != "read"] + demoted
                         + strong, key=lambda r: r.box[0])
    if not strong:
        return GroupReading("rejected", "no_letter_read", box, rival=rival,
                            n_hypotheses=len(hyps), near=near,
                            unstable=unstable)
    # ⚠️ NOT DOUBLED: a read letter lying on a letter the detector DID box is
    # the detector's (Litolff p2 `sf` between the staves: the detector held
    # `dynamicS` and `dynamicF`, the look read the same two again). The group
    # was mostly note ink, so the group-level share above could not see it.
    for r in strong:
        for d in dynamic_boxes:
            ix = max(0.0, min(r.box[2], d[2]) - max(r.box[0], d[0]))
            iy = max(0.0, min(r.box[3], d[3]) - max(r.box[1], d[1]))
            small = max(1.0, min((r.box[2] - r.box[0]) * (r.box[3] - r.box[1]),
                                 (d[2] - d[0]) * (d[3] - d[1])))
            if ix * iy / small >= 0.5:
                return GroupReading("skipped", "already_boxed_as_a_dynamic", box,
                                    rival=rival, n_hypotheses=len(hyps),
                                    near=near)
    weak = [r for r in regions if r.how == "weak"]
    slots = slots_for(strong, weak, comps, sp)
    sp_ = spell(list(strong) + slots)
    if sp_.status == "rejected":
        return GroupReading("rejected", sp_.reason, box, spelling=sp_,
                            rival=rival, n_hypotheses=len(hyps), near=near)
    letter_boxes = [r.box for r in sp_.regions]
    cover: List[float] = []
    for b in seed_boxes:
        bx0, by0, bx1, by1 = (int(round(v)) for v in b)
        sub = mask[max(0, by0):max(0, by1), max(0, bx0):max(0, bx1)]
        ink = int((sub > 0).sum())
        if ink == 0:
            cover.append(0.0)
            continue
        inside = 0
        ys, xs = np.nonzero(sub)
        for yy, xx in zip(ys.tolist(), xs.tolist()):
            px, py = bx0 + xx, by0 + yy
            if any(lb[0] <= px < lb[2] and lb[1] <= py < lb[3] for lb in letter_boxes):
                inside += 1
        cover.append(round(inside / ink, 3))
    return GroupReading("read" if sp_.status == "spelled" else "narrowed",
                        sp_.reason, box, spelling=sp_, cover=cover,
                        rival=rival, n_hypotheses=len(hyps), near=near,
                        unstable=unstable)


# ── the page-level entry points GATHER and the reach tool share ──────────────

#: A head/rest box is a SEED (the ink under it might be letters) unless it is a
#: whole/half/breve head or a long rest: those are hollow or rectangular and no
#: letter is either.
SEED_SKIP_HEADS = ("whole", "double")
SEED_SKIP_RESTS = ("restWhole", "restHalf", "restDoubleWhole", "restHBar",
                   "restLonga", "restMaxima")
#: where, around a seed, to look for the pieces of its group (staff spaces)
WINDOW_PAD_X_SPACES = 8.0
WINDOW_PAD_Y_SPACES = 6.0
#: a group must be this big to be a letter group at all (staff spaces)
GROUP_MIN_H_SPACES = 0.8
GROUP_MIN_W_SPACES = 0.5


def is_seed_class(name: str) -> bool:
    """Is a detector class one whose box can hold a dynamic letter's ink: a
    black or short head, a short rest?"""
    low = str(name).lower()
    if low.startswith("notehead"):
        return not any(k in low for k in SEED_SKIP_HEADS)
    if low.startswith("rest"):
        return str(name) not in SEED_SKIP_RESTS
    return False


@dataclass
class PageGroup:
    comps: List[Comp]                       # PAGE pixel coordinates
    seeds: List[Any]                        # the member ids that put it here

    def box(self) -> Tuple[int, int, int, int]:
        return union_box(self.comps)


def find_groups(clean: np.ndarray, members: Sequence[Tuple[Any, Sequence[float]]],
                sp: float) -> List[PageGroup]:
    """The candidate letter groups of one staff band: for each seed member
    `(id, page box)`, the letter-like pieces under it grown through
    `GROUP_GAP_SPACES` gaps, deduplicated on their union box, each carrying every
    seed it touches. `clean` is the page's cleaned ink (0/1; non-staff-band rows
    may be zero). Groups outside `GROUP_MIN_*`/`LETTER_*_MAX` size are dropped:
    they are marks too small to be letters or tall as a note."""
    H, W = clean.shape[:2]
    found: Dict[Tuple[int, int, int, int], PageGroup] = {}
    for mid, bx in members:
        wx0 = int(max(0, bx[0] - WINDOW_PAD_X_SPACES * sp))
        wy0 = int(max(0, bx[1] - WINDOW_PAD_Y_SPACES * sp))
        wx1 = int(min(W, bx[2] + WINDOW_PAD_X_SPACES * sp))
        wy1 = int(min(H, bx[3] + WINDOW_PAD_Y_SPACES * sp))
        win = clean[wy0:wy1, wx0:wx1]
        if win.size == 0:
            continue
        comps, _lab = letter_components(win, sp)
        seed = [(bx[0] - wx0, bx[1] - wy0, bx[2] - wx0, bx[3] - wy0)]
        grp = group_around(comps, seed, sp)
        if not grp:
            continue
        ub = union_box(grp)
        h, w = (ub[3] - ub[1]) / sp, (ub[2] - ub[0]) / sp
        if h < GROUP_MIN_H_SPACES or w < GROUP_MIN_W_SPACES:
            continue
        page_comps = [Comp(c.x0 + wx0, c.y0 + wy0, c.x1 + wx0, c.y1 + wy0,
                           c.area) for c in grp]
        key = (round((ub[0] + wx0) / 4), round((ub[1] + wy0) / 4),
               round((ub[2] + wx0) / 4), round((ub[3] + wy0) / 4))
        if key in found:
            found[key].seeds.append(mid)
        else:
            found[key] = PageGroup(page_comps, [mid])
    return list(found.values())


def read_page_group(clean: np.ndarray, group: PageGroup,
                    seed_boxes: Dict[Any, Sequence[float]], sp: float,
                    detect: Callable[[np.ndarray, int], list],
                    dynamic_boxes: Sequence[Sequence[float]] = (),
                    clean_alt: Optional[np.ndarray] = None
                    ) -> GroupReading:
    """`read_group` on a window cut around the group, everything in and out in
    PAGE pixels. `seed_boxes` maps every member id the group touches (not only
    its first seed) to its page box; `cover` comes back in the order of
    `group.seeds`'s extension: the ids that overlap the group, sorted."""
    ub = group.box()
    pad = int(round(3.0 * sp))
    H, W = clean.shape[:2]
    wx0, wy0 = max(0, ub[0] - pad), max(0, ub[1] - pad)
    wx1, wy1 = min(W, ub[2] + pad), min(H, ub[3] + pad)
    win = clean[wy0:wy1, wx0:wx1]
    comps = [Comp(c.x0 - wx0, c.y0 - wy0, c.x1 - wx0, c.y1 - wy0, c.area)
             for c in group.comps]
    touching = sorted(
        (i for i, b in seed_boxes.items()
         if min(ub[2], b[2]) > max(ub[0], b[0])
         and min(ub[3], b[3]) > max(ub[1], b[1])), key=str)
    local_seeds = [(seed_boxes[i][0] - wx0, seed_boxes[i][1] - wy0,
                    seed_boxes[i][2] - wx0, seed_boxes[i][3] - wy0)
                   for i in touching]
    dyn = [(d[0] - wx0, d[1] - wy0, d[2] - wx0, d[3] - wy0)
           for d in dynamic_boxes]
    win_alt = (clean_alt[wy0:wy1, wx0:wx1] if clean_alt is not None else None)
    gr = read_group(win, comps, local_seeds, sp, detect, dyn, win_alt)

    def back(b):
        return (b[0] + wx0, b[1] + wy0, b[2] + wx0, b[3] + wy0)
    gr.box = tuple(int(v) for v in back(gr.box))      # type: ignore[assignment]
    if gr.spelling is not None:
        for r in gr.spelling.regions:
            r.box = back(r.box)       # type: ignore[assignment]
    gr.seed_ids = touching
    return gr
