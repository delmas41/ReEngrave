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
    lo = (clef.x + clef.w) if clef is not None \
        else first.x - EDGE_MARGIN_SPACES * space
    hi = max(b.x + b.w for b in chain) + EDGE_MARGIN_SPACES * space
    return KeySlotWindow(
        lo=lo, hi=hi,
        y_lo=min(b.y for b in chain) - LEVEL_MARGIN_SPACES * space,
        y_hi=max(b.y + b.h for b in chain) + LEVEL_MARGIN_SPACES * space,
        members=tuple(b.row_id for b in chain),
        clef=None if clef is None else clef.row_id, slots=slots)


def is_music_class(cls: str) -> bool:
    return cls.startswith(MUSIC_PREFIXES)


def stands_in_the_window(window: KeySlotWindow, box: KeyBox) -> bool:
    """Is this box's centre between the clef and the last accidental, level
    with the signature? A key-shaped or clef box never is (it IS the run)."""
    if _shape(box.cls) is not None or box.cls.startswith("clef"):
        return False
    return (window.lo <= box.cx <= window.hi
            and window.y_lo <= box.cy <= window.y_hi)


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


def key_slot_occupant(ev: Any, box_row: Any) -> Optional[Dict[str, Any]]:
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
    if not me or not is_music_class(me[0].cls):
        return None
    space = cell_space(ev, cell)
    if space <= 0:
        return None
    rows = ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell)
    window = key_slot_window(boxes_of(rows), space)
    if window is None or not stands_in_the_window(window, me[0]):
        return None
    detail = window.detail()
    used = list(window.members) + ([window.clef] if window.clef else [])
    return {"detail": detail, "used": tuple(used)}
