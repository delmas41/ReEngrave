"""ROADMAP 2.100 -- the key-signature SLOTS of a header, and what may not stand in them.

Sean, 2026-10-12 (DECISIONS): *"Eighth note rest would never be found before
key signature flats -- in fact -- only clefs appear before key accidentals in a
bar."*

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (CLAUDE.md rule 3,
nobody to ask mid-lane beyond the sentence above): between a system's clef and
its LAST key-signature accidental there is nothing but key accidentals. A box
of a music class (rest, notehead, flag, articulation) whose centre stands in
that stretch, level with the signature, is that signature's own ink -- the
detector boxed a flat a second time under a rest's name (4 of 30 `rest8th`
boxes on Litolff p1-3 are the third flat, boxed identically as `keyFlat`;
ROADMAP 2.99). FALSIFIED by a print with a real rest or note printed between a
clef and a later accidental of the same signature -- none is known; a rest
printed AFTER the signature's last accidental is outside the window by
construction (the positive control in the tests).

⚠️ THE WINDOW IS THE KEY READER'S OWN RUN, NOT A NEW NOTION OF ONE. The run
starts at the first key-shaped box (`keyFlat/Sharp/Natural`, or the detector's
in-bar accidental class on the same shape -- `gather._ACCIDENTAL_SHAPE`) and
ends at the first slot more than `MARKER_RUN_GAP_SPACES` from the last, exactly
as `header._marker_run` ends it, so a lone accidental printed inside bar 1
(a C-major staff with a sharp before its third note) does not open a window
over everything to its left: such a box must also stand within
`MAX_START_AFTER_CLEF_SPACES` of the clef's right edge (the locator's own
bound -- *"a key signature is printed hard against its clef"*), or, with no
clef boxed, be a detector KEY-class box.

⚠️ GEOMETRY ONLY. This decides nothing about WHAT the ink is; it says WHERE it
stands. The consumers (`family_precision`'s rest decision, `notehead_precision`'s
head decision) refuse it as music with a named reason and cite the rows below.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..record import Kind, Q, Scope

#: The detector's key-signature classes, and the in-bar accidental classes
#: that share their shapes (`gather._ACCIDENTAL_SHAPE`, restated by shape only).
KEY_CLASSES = ("keySharp", "keyFlat", "keyNatural")
ACCIDENTAL_SHAPES = {"accidentalFlat": "keyFlat", "accidentalSharp": "keySharp",
                     "accidentalNatural": "keyNatural"}

#: Classes that carry MUSIC to the file. A key accidental boxed under one of
#: these names is refused as that music. (Staff lines, ledger lines, stems,
#: ties, clefs, meter digits are not in question here.)
MUSIC_PREFIXES = ("rest", "notehead", "flag", "artic", "augmentationDot")

#: Classes that are STRUCTURE, not marks: a staff box spans the whole header, a
#: ledger line or stem is a stroke, a barline or brace is a frame. Every other
#: class standing in the key slots -- a flag, an arpeggiato, a tie, a time-
#: signature digit -- is a key accidental the detector named something else
#: (Sean, 2026-10-12, tiles 1 6 7 8 9 11: "All the rest are key accidentals").
STRUCTURAL_PREFIXES = ("staff", "ledgerLine", "stem", "barline", "brace",
                       "bracket", "beam", "clef", "key", "accidental")

#: `header.MARKER_RUN_GAP_SPACES`, `header.MARKER_SLOT_TOLERANCE_SPACES` and
#: `header.MAX_FIFTHS`, restated because `header` imports `clef`, which imports
#: this package's other modules (a cycle waiting to happen). A test asserts the
#: three are equal to the header's.
RUN_GAP_SPACES = 2.0
SLOT_TOLERANCE_SPACES = 0.5
MAX_SLOTS = 7

#: Two slot pitches (a printed flat's left edge to the next one's is ~1.15
#: spaces; measured on Litolff p1-3) plus the slot tolerance: the farthest
#: apart two KEY-class boxes may stand with exactly one slot unboxed between.
BRIDGE_GAP_SPACES = 2.8

#: How exactly a REST-class box must stand on the next slot's x for it to be
#: that slot's accidental, boxed only as a rest (the detector never boxed the
#: last flat as a key class: Litolff p1 s0 staff 10, dx -0.07 spaces). The
#: nearest real rests after a signature on the two count pages stand 0.42 and
#: 1.32 spaces off the next slot, so 0.2 separates them; ASSUMED, NOT
#: CONFIRMED -- blind tile 12 asks Sean.
NEXT_SLOT_TOL_SPACES = 0.2

#: `key_signature_locator.max_start_after_clef_spaces` (2.00).
MAX_START_AFTER_CLEF_SPACES = 2.0

#: How far past the run's last box a centre may stand and still be in its
#: column: a flat is ~1.1 spaces wide and a box edge is a detector's.
EDGE_MARGIN_SPACES = 0.3

#: Level with the signature: a centre within this many spaces of the run's
#: own vertical extent. A neighbour staff's ink padded into the cell stands
#: farther than this from every accidental of the run.
LEVEL_MARGIN_SPACES = 1.0


@dataclass(frozen=True)
class KeyBox:
    row_id: str
    cls: str
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0


@dataclass(frozen=True)
class KeySlotWindow:
    """The stretch between the clef and the key run's last accidental."""
    lo: float
    hi: float
    y_lo: float
    y_hi: float
    members: Tuple[str, ...]          # row ids of the key-shaped boxes
    clef: Optional[str]               # row id of the clef box, if one bounds it
    slots: int
    #: Where the NEXT accidental would stand (its left edge) and the tolerance,
    #: when the run's own slot pitch is measurable (two or more slots); `None`
    #: otherwise. Used only for a rest-class box (`stands_in_the_window`).
    next_x: Optional[float] = None
    next_tol: float = 0.0

    def detail(self) -> Dict[str, Any]:
        return {"key_slot_window": [round(self.lo, 1), round(self.hi, 1)],
                "key_slot_members": list(self.members),
                "key_slot_clef": self.clef, "key_slot_slots": self.slots}


def boxes_of(rows: Sequence[Any]) -> List[KeyBox]:
    """`Q.GLYPH_BOX` rows -> boxes. Rows that are not `[class, x, y, w, h]` are
    skipped, never guessed."""
    out: List[KeyBox] = []
    for r in rows:
        v = r.value
        if not isinstance(v, (list, tuple)) or len(v) != 5:
            continue
        try:
            out.append(KeyBox(r.id, str(v[0]), float(v[1]), float(v[2]),
                              float(v[3]), float(v[4])))
        except (TypeError, ValueError):
            continue
    return out


def _shape(cls: str) -> Optional[str]:
    if cls in KEY_CLASSES:
        return cls
    return ACCIDENTAL_SHAPES.get(cls)


def key_slot_window(boxes: Sequence[KeyBox], space: float
                    ) -> Optional[KeySlotWindow]:
    """The key-signature window of ONE header cell, or `None`.

    `None` is the answer wherever there is no scale, no key-shaped box, a first
    accidental farther from the clef than a signature stands, or a run of more
    than seven slots (not a key signature)."""
    if space <= 0:
        return None
    key_kinds = {b.cls for b in boxes if b.cls in KEY_CLASSES}
    shaped = [b for b in boxes if _shape(b.cls) is not None]
    if key_kinds:
        # `[C21]`: one kind per signature. Where the detector's own KEY-class
        # boxes say which kind, an accidental-shaped box of another is the
        # in-bar accidental it said it was (`gather._gather_keysig_markers`).
        shaped = [b for b in shaped if _shape(b.cls) in key_kinds]
    shaped.sort(key=lambda b: b.x)
    if not shaped:
        return None
    first = shaped[0]
    clefs = [b for b in boxes if b.cls.startswith("clef") and b.x < first.x]
    clef = max(clefs, key=lambda b: b.x + b.w) if clefs else None
    if clef is not None:
        if first.x - (clef.x + clef.w) > MAX_START_AFTER_CLEF_SPACES * space:
            return None
    elif first.cls not in KEY_CLASSES:
        return None

    chain = [first]
    bridged = False
    for b in shaped[1:]:
        gap = b.x - chain[-1].x
        if gap > RUN_GAP_SPACES * space:
            # ONE unboxed slot may lie between two printed accidentals: the
            # detector missed the middle flat (Litolff p1 s0 staff 11 boxes
            # slots 1 and 3, 2.6 spaces apart). Bridged only for a box the
            # detector itself called a KEY accidental, never an in-bar
            # accidental, whose gap is two slot pitches; a real rest between
            # a key's last flat and a later accidental must stay outside.
            if (bridged or b.cls not in KEY_CLASSES
                    or not any(c.cls in KEY_CLASSES
                               and abs(c.x - chain[-1].x)
                               <= SLOT_TOLERANCE_SPACES * space
                               for c in chain)
                    or gap > BRIDGE_GAP_SPACES * space):
                break
            bridged = True
        chain.append(b)
    centres = [chain[0].x]
    for b in chain[1:]:
        if b.x - centres[-1] > SLOT_TOLERANCE_SPACES * space:
            centres.append(b.x)
    slots = len(centres) + (1 if bridged else 0)
    if slots > MAX_SLOTS:
        return None
    gaps = sorted(b - a for a, b in zip(centres, centres[1:])
                  if b - a <= 1.6 * space)
    next_x = (centres[-1] + gaps[len(gaps) // 2]) if gaps else None
    lo = (clef.x + clef.w) if clef is not None \
        else first.x - EDGE_MARGIN_SPACES * space
    hi = max(b.x + b.w for b in chain) + EDGE_MARGIN_SPACES * space
    return KeySlotWindow(
        lo=lo, hi=hi,
        y_lo=min(b.y for b in chain) - LEVEL_MARGIN_SPACES * space,
        y_hi=max(b.y + b.h for b in chain) + LEVEL_MARGIN_SPACES * space,
        members=tuple(b.row_id for b in chain),
        clef=None if clef is None else clef.row_id, slots=slots,
        next_x=next_x, next_tol=NEXT_SLOT_TOL_SPACES * space)


#: ROADMAP 2.183: a cancelling run may hold up to this many slots (seven naturals, then up to seven sharps / flats)
MAX_CLAIM_SLOTS = 2 * MAX_SLOTS


def _window_of(chain: Sequence[KeyBox], clef: Optional[KeyBox], space: float, slots: int, next_x: Optional[float] = None
               ) -> KeySlotWindow:
    lo = (clef.x + clef.w) if clef is not None else chain[0].x - EDGE_MARGIN_SPACES * space
    return KeySlotWindow(
        lo=lo, hi=max(b.x + b.w for b in chain) + EDGE_MARGIN_SPACES * space,
        y_lo=min(b.y for b in chain) - LEVEL_MARGIN_SPACES * space,
        y_hi=max(b.y + b.h for b in chain) + LEVEL_MARGIN_SPACES * space,
        members=tuple(b.row_id for b in chain), clef=None if clef is None else clef.row_id, slots=slots,
        next_x=next_x, next_tol=NEXT_SLOT_TOL_SPACES * space)


def window_with_cancels(boxes: Sequence[KeyBox], space: float) -> Optional[KeySlotWindow]:
    """ROADMAP 2.183: the key run when it opens with CANCELLING NATURALS the standard window cannot see (Sean 2026-10-20: "Canceling
    accidentals should be considered key signature"; page-facts §2). `key_slot_window` asks the first accidental to stand within
    `MAX_START_AFTER_CLEF_SPACES` of the clef and keeps one kind of box; a run of naturals pushes the new key's first sharp / flat farther
    out, and a natural boxed as an in-bar accidental is dropped when the detector's KEY boxes are of another kind. Here the run starts at the
    first natural-shaped box within that bound of the clef, chains boxes by `RUN_GAP_SPACES`, takes naturals only BEFORE the first
    sharp / flat (a natural after it is a note's, never the signature's) and one sharp-or-flat kind after them. `None` where there is no
    natural, no sharp / flat after it, or no clef (a natural-only run is `key_slot_window`'s own). CONVENTION ASSUMED (page-facts §2,
    Sean 2026-10-20); WHAT WOULD FALSIFY IT: a print with a note between the cancelling naturals and the new key's accidentals; NOT SEEN on
    the two acceptance plates (neither movement changes key), so this path is covered by constructed tests only."""
    if space <= 0:
        return None
    shaped = sorted((b for b in boxes if _shape(b.cls) is not None), key=lambda b: b.x)
    nat = [b for b in shaped if _shape(b.cls) == "keyNatural"]
    if not nat:
        return None
    first = nat[0]
    clefs = [b for b in boxes if b.cls.startswith("clef") and b.x < first.x]
    if not clefs:
        return None
    clef = max(clefs, key=lambda b: b.x + b.w)
    if first.x - (clef.x + clef.w) > MAX_START_AFTER_CLEF_SPACES * space:
        return None
    chain, kind = [first], None
    for b in shaped:
        if b.x <= first.x or b is first:
            continue
        if b.x - chain[-1].x > RUN_GAP_SPACES * space:
            break
        sh = _shape(b.cls)
        if sh == "keyNatural":
            if kind is not None:
                break
        elif kind is None:
            kind = sh
        elif sh != kind:
            break
        chain.append(b)
    if kind is None:
        return None
    centres = [chain[0].x]
    for b in chain[1:]:
        if b.x - centres[-1] > SLOT_TOLERANCE_SPACES * space:
            centres.append(b.x)
    if len(centres) > MAX_CLAIM_SLOTS:
        return None
    return _window_of(chain, clef, space, len(centres))


def claim_window(boxes: Sequence[KeyBox], space: float) -> Optional[KeySlotWindow]:
    """The window the key-signature CLAIM (ROADMAP 2.183) draws: the standard window, else the one that opens with cancelling naturals."""
    return key_slot_window(boxes, space) or window_with_cancels(boxes, space)


def is_music_class(cls: str) -> bool:
    return cls.startswith(MUSIC_PREFIXES)


def is_refusable_class(cls: str) -> bool:
    """Not structure: any mark a key accidental could be boxed as."""
    return not cls.startswith(STRUCTURAL_PREFIXES)


def stands_in_the_window(window: KeySlotWindow, box: KeyBox) -> bool:
    """Is this box's centre between the clef and the last accidental, level
    with the signature? A key-shaped or clef box never is (it IS the run)."""
    if _shape(box.cls) is not None or box.cls.startswith("clef"):
        return False
    if not window.y_lo <= box.cy <= window.y_hi:
        return False
    if window.lo <= box.cx <= window.hi:
        return True
    return (box.cls.startswith("rest") and window.next_x is not None
            and abs(box.x - window.next_x) <= window.next_tol)


def stand_margin_spaces(window: KeySlotWindow, box: KeyBox, space: float) -> Optional[float]:
    """ROADMAP 2.183: how deep inside the window `stands_in_the_window` puts this box, in staff spaces (the smallest distance of the
    centre from the window's four edges, or, for a rest on the next slot, the tolerance minus its offset); `None` where it does not stand."""
    if not stands_in_the_window(window, box) or space <= 0:
        return None
    inside = min(box.cx - window.lo, window.hi - box.cx, box.cy - window.y_lo, window.y_hi - box.cy)
    if inside >= 0 and window.lo <= box.cx <= window.hi:
        return round(inside / space, 3)
    return round((window.next_tol - abs(box.x - (window.next_x or 0.0))) / space, 3)


def cell_space(ev: Any, cell: Any) -> float:
    for row in ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_DESCENDANTS,
                       subject=cell):
        try:
            value = float(row.value)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0.0


def key_slot_occupant(ev: Any, box_row: Any, space: float = 0.0
                      ) -> Optional[Dict[str, Any]]:
    """If THIS glyph's box stands in its header's key-signature slots, the
    facts that say so (`detail` for the verdict, `used` row ids); else `None`.

    Only CELL 0 of a staff is a header (every bar files one cell; the opening
    cell holds the clef, the signature and the first bar -- `header.
    _cell0_space`). A missing scale or box is `None`, never a refusal.
    """
    cell = ev.subject.at(Kind.CELL)
    if cell is None or cell.cell != 0 or box_row is None:
        return None
    me = boxes_of([box_row])
    if not me or not is_refusable_class(me[0].cls):
        return None
    space = space or cell_space(ev, cell)
    if space <= 0:
        return None
    rows = ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell)
    window = key_slot_window(boxes_of(rows), space)
    if window is None or not stands_in_the_window(window, me[0]):
        return None
    detail = window.detail()
    used = list(window.members) + ([window.clef] if window.clef else [])
    return {"detail": detail, "used": tuple(used)}


# ─────────────────────────────────────────────────────────────────────────────
# The meter's column. Sean, 2026-10-12, tiles 3 and 13: "Three and thirteen are
# time signatures." A rest8th boxed on the 8 of a 6/8, a restQuarter boxed on a
# whole 2/4 stack: a rest box standing where the printed time signature stands
# is that signature's digit. A meter is printed at one bar on every staff of
# the system (CLAUDE.md §10, Sean 2026-09-30), so WHERE it stands is read off
# the `timeSig*` boxes of the system's OTHER staves, in PAGE pixels (the cell
# frames differ per staff, the page column does not) -- never off the bar.
# ─────────────────────────────────────────────────────────────────────────────

#: A rest's centre may stand this many staff spaces outside the column of the
#: sibling staves' digit boxes and still be that column's ink.
METER_COLUMN_MARGIN_SPACES = 0.3


def _page_box(row: Any) -> Optional[Tuple[float, float, float, float]]:
    bb = (row.detail or {}).get("bbox_page_px")
    if isinstance(bb, (list, tuple)) and len(bb) == 4:
        try:
            return tuple(float(v) for v in bb)  # type: ignore[return-value]
        except (TypeError, ValueError):
            return None
    return None


def meter_column(ev: Any, system: Any, skip_staff: Optional[int]
                 ) -> Optional[Tuple[float, float, List[str]]]:
    """`(left, right, digit row ids)` of the time signature's column on this
    system's header, in page pixels, from the `timeSig*` boxes of every staff
    but `skip_staff` -- excluding those standing in their OWN staff's key slots
    (a flat named a 4 is not the meter). `None` where no sibling printed one."""
    by_staff: Dict[int, List[Any]] = {}
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=system):
        sub = r.subject
        if sub.cell != 0 or sub.staff is None or sub.staff == skip_staff:
            continue
        by_staff.setdefault(sub.staff, []).append(r)
    left, right, ids = None, None, []
    for staff, rows in by_staff.items():
        digits = [r for r in rows if isinstance(r.value, (list, tuple))
                  and str(r.value[0]).startswith("timeSig")]
        if not digits:
            continue
        cell = rows[0].subject.at(Kind.CELL)
        space = cell_space(ev, cell)
        boxes = boxes_of(rows)
        win = key_slot_window(boxes, space) if space > 0 else None
        by_id = {b.row_id: b for b in boxes}
        for r in digits:
            b = by_id.get(r.id)
            if b is None or (win is not None and stands_in_the_window(win, b)):
                continue
            pb = _page_box(r)
            if pb is None:
                continue
            left = pb[0] if left is None else min(left, pb[0])
            right = pb[2] if right is None else max(right, pb[2])
            ids.append(r.id)
    if left is None:
        return None
    return left, right, ids


def meter_column_occupant(ev: Any, box_row: Any) -> Optional[Dict[str, Any]]:
    """If THIS rest-class box stands in the printed time signature's column
    (header cell 0), the facts that say so; else `None`."""
    cell = ev.subject.at(Kind.CELL)
    if cell is None or cell.cell != 0 or box_row is None:
        return None
    v = box_row.value
    if not isinstance(v, (list, tuple)) or len(v) != 5 \
            or not str(v[0]).startswith("rest"):
        return None
    pb = _page_box(box_row)
    space = cell_space(ev, cell)
    if pb is None or space <= 0 or not v[3]:
        return None
    sp_page = space * (pb[2] - pb[0]) / float(v[3])
    col = meter_column(ev, ev.subject.at(Kind.SYSTEM), ev.subject.staff)
    if col is None:
        return None
    left, right, ids = col
    cx = (pb[0] + pb[2]) / 2.0
    margin = METER_COLUMN_MARGIN_SPACES * sp_page
    if not left - margin <= cx <= right + margin:
        return None
    return {"detail": {"meter_column_page_px": [round(left, 1), round(right, 1)],
                       "meter_digit_rows": ids[:6]},
            "used": tuple(ids[:6])}


def _cell0(staff: Any) -> Any:
    from ..record import Subject
    return Subject(Kind.CELL, page=staff.page, system=staff.system,
                   staff=staff.staff, cell=0)


def meter_rows_outside_key_slots(ev: Any, rows: Sequence[Any],
                                 spaces: Optional[Dict[str, float]] = None,
                                 glyph_rows: Optional[Sequence[Any]] = None
                                 ) -> Tuple[List[Any], int]:
    """`Q.METER_GLYPH` rows minus those whose box stands in their staff's key
    slots (header cell 0 only), and how many were dropped. A meter glyph row is
    filed on the STAFF with the detection's class, `x` and `cell`; its box is
    the cell-0 `Q.GLYPH_BOX` of the same class and left x."""
    kept: List[Any] = []
    dropped = 0
    windows: Dict[Any, Tuple[Optional[KeySlotWindow], List[KeyBox]]] = {}
    by_cell: Dict[str, List[Any]] = {}
    for g in glyph_rows or ():
        if g.subject.cell == 0:
            by_cell.setdefault(g.subject.at(Kind.CELL).to_key(), []).append(g)
    for r in rows:
        d = r.detail or {}
        if r.frame != "cell:0":
            kept.append(r)
            continue
        staff = r.subject.at(Kind.STAFF)
        key = staff.to_key()
        if key not in windows:
            cell = _cell0(staff)
            space = (spaces or {}).get(cell.to_key()) or cell_space(ev, cell)
            boxes = boxes_of(by_cell.get(cell.to_key(), []) if glyph_rows is not None
                             else ev.rows(Q.GLYPH_BOX,
                                          scope=Scope.SELF_AND_DESCENDANTS,
                                          subject=cell))
            windows[key] = (key_slot_window(boxes, space), boxes)
        win, boxes = windows[key]
        hit = None
        if win is not None:
            for b in boxes:
                if b.cls == str(r.value) \
                        and abs(b.x - float(d.get("x") or -1e9)) < 1.5:
                    hit = b
                    break
        if hit is not None and stands_in_the_window(win, hit):
            dropped += 1
        else:
            kept.append(r)
    return kept, dropped
