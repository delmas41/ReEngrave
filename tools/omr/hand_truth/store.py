"""The page-truth store: one JSON file per printed page, every box in page pixels.

``data/hand-truth/pages/<edition>/<pdf_page_index>.json``

WHY PAGE PIXELS. The old labels (``data/user-labeled/v*``) are stored in each
cell's CANONICAL frame — a padded crop resized to a fixed width — and the
manifests do not record the padding the cutter used, so mapping a box back to
the page needs a re-cut and a frame check (``annotate.recut_cells``). Padded
cells also OVERLAP: a mark near a cell edge appears in two crops and was boxed
(or left as background) twice. Here the cell is only a window: it records its
exact page rectangle and canonical size when it is cut, so cell <-> page is an
exact affine map, never a re-derivation, and a box drawn in one cell is already
there when its neighbour opens.

WHAT IS TRUTH. ``boxes`` hold only what a human drew or acted on (``origin``
``drawn`` / ``prefill-confirmed`` / ``prefill-fixed``). A model pre-fill waits
in ``queue`` until Sean acts on it; ``confirm_prefill`` / ``fix_prefill`` move
it across. Nothing else does.

LIFECYCLE (plan C5/C6). ``labeling`` -> ``checked`` (every flag from Claude's
double-check resolved by Sean) -> ``verified`` (every measure marked ``ok`` on
the LilyPond side by side). Forward only, one step at a time. Only a
``verified`` page is truth for scoring; ``checked`` or later may train.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

SCHEMA_VERSION = 1

STATES: Tuple[str, ...] = ("labeling", "checked", "verified")
ORIGINS: Tuple[str, ...] = ("drawn", "prefill-confirmed", "prefill-fixed")
LABELERS: Tuple[str, ...] = ("sean",)
CELL_KINDS: Tuple[str, ...] = ("measure", "margin", "top", "bottom")
#: A cell inspected for EVERY family — the whole-ink pass (Sean 2026-10-08:
#: "start with everything on the page").
ALL_INK = "*"
#: Ink that is not music (specks, bleed-through). Boxed so the ink-coverage
#: control can close; never exported as a training class.
NOISE = "noise"
#: Printed text (instrument names, tempo, plate numbers). Carries ``text``.
TEXT = "text"

Rect = Tuple[float, float, float, float]  # x0, y0, x1, y1 in page pixels

REPO = Path(__file__).resolve().parents[3]
PAGES_DIR = REPO / "data" / "hand-truth" / "pages"


class StoreError(ValueError):
    """A write the store refuses. Raised, never returned as a flag."""


def edition_key(pdf_name: str) -> str:
    """``imslp<digits>`` for an IMSLP file, else the file stem, lower-cased.

    The same key every manifest's ``pdf`` path reduces to, so a page keyed here
    and a cell keyed by its manifest meet.
    """
    name = Path(pdf_name).name
    m = re.search(r"imslp(\d+)", name, flags=re.I)
    if m:
        return f"imslp{m.group(1)}"
    return Path(name).stem.lower()


def _check_rect(rect: Rect, what: str) -> Rect:
    x0, y0, x1, y1 = (float(v) for v in rect)
    if not (x1 > x0 and y1 > y0):
        raise StoreError(f"{what}: empty or inverted rectangle {rect!r}")
    return (x0, y0, x1, y1)


@dataclass
class Box:
    id: str
    cls: str
    rect: Rect
    origin: str
    labeler: str
    text: Optional[str] = None
    #: (system, staff) the notehead belongs to — Sean's, never geometry's.
    owner_staff: Optional[Tuple[int, int]] = None
    #: Staff position in steps from the middle line (0 = middle line).
    staff_position: Optional[int] = None
    cell_id: Optional[str] = None  # the cell it was drawn or confirmed in

    def validate(self) -> None:
        if self.origin not in ORIGINS:
            raise StoreError(f"box {self.id}: origin {self.origin!r} not in {ORIGINS}")
        if self.labeler not in LABELERS:
            raise StoreError(f"box {self.id}: labeler {self.labeler!r} not in {LABELERS}")
        if not self.cls:
            raise StoreError(f"box {self.id}: no class")
        if self.cls == TEXT and not self.text:
            raise StoreError(f"box {self.id}: a text box carries its text")
        self.rect = _check_rect(self.rect, f"box {self.id}")


@dataclass
class Prefill:
    """A machine's proposal. Not truth until a human acts on it."""

    id: str
    cls: str
    rect: Rect
    source: str  # e.g. "sean-v18" (his old label, re-projected), "production", "cv:stems"
    score: Optional[float] = None


@dataclass
class Cell:
    id: str
    kind: str
    rect: Rect  # the window's exact page rectangle, recorded when it was cut
    canonical_w: int
    canonical_h: int
    inspected: List[str] = field(default_factory=list)  # family names, or ALL_INK
    system: Optional[int] = None
    staff: Optional[int] = None
    measure: Optional[int] = None

    def validate(self) -> None:
        if self.kind not in CELL_KINDS:
            raise StoreError(f"cell {self.id}: kind {self.kind!r} not in {CELL_KINDS}")
        self.rect = _check_rect(self.rect, f"cell {self.id}")
        if self.canonical_w <= 0 or self.canonical_h <= 0:
            raise StoreError(f"cell {self.id}: canonical size must be positive")

    # -- the exact affine map between the cell's canonical frame and the page
    def _scale(self) -> Tuple[float, float]:
        x0, y0, x1, y1 = self.rect
        return (x1 - x0) / self.canonical_w, (y1 - y0) / self.canonical_h

    def to_page(self, r: Rect) -> Rect:
        sx, sy = self._scale()
        x0, y0, _, _ = self.rect
        return (x0 + r[0] * sx, y0 + r[1] * sy, x0 + r[2] * sx, y0 + r[3] * sy)

    def to_cell(self, r: Rect) -> Rect:
        sx, sy = self._scale()
        x0, y0, _, _ = self.rect
        return ((r[0] - x0) / sx, (r[1] - y0) / sy, (r[2] - x0) / sx, (r[3] - y0) / sy)


@dataclass
class StaffCheck:
    """Sean's one-key answer: are the detector's five lines on this staff right?"""

    system: int
    staff: int
    lines_right: Optional[bool] = None  # None = not yet looked at


@dataclass
class PageTruth:
    edition: str
    pdf_page_index: int
    dpi: int
    width: int
    height: int
    state: str = "labeling"
    boxes: List[Box] = field(default_factory=list)
    queue: List[Prefill] = field(default_factory=list)
    cells: List[Cell] = field(default_factory=list)
    staves: List[StaffCheck] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION

    # ------------------------------------------------------------ lookup
    def cell(self, cell_id: str) -> Cell:
        for c in self.cells:
            if c.id == cell_id:
                return c
        raise StoreError(f"no cell {cell_id!r} on {self.edition} page {self.pdf_page_index}")

    def _next_id(self, prefix: str) -> str:
        used = {b.id for b in self.boxes} | {p.id for p in self.queue}
        n = len(used)
        while f"{prefix}{n}" in used:
            n += 1
        return f"{prefix}{n}"

    # ------------------------------------------------------------ cells
    def add_cell(self, cell: Cell) -> Cell:
        cell.validate()
        if any(c.id == cell.id for c in self.cells):
            raise StoreError(f"cell {cell.id!r} already on this page")
        self.cells.append(cell)
        return cell

    def mark_inspected(self, cell_id: str, families: Iterable[str]) -> None:
        c = self.cell(cell_id)
        for f in families:
            if f not in c.inspected:
                c.inspected.append(f)

    # ------------------------------------------------------------ boxes
    def draw(self, cell_id: str, cls: str, cell_rect: Rect, *, labeler: str = "sean",
             text: Optional[str] = None, owner_staff: Optional[Tuple[int, int]] = None,
             staff_position: Optional[int] = None) -> Box:
        """A box Sean drew in a cell's canonical frame, stored in page pixels."""
        c = self.cell(cell_id)
        box = Box(id=self._next_id("b"), cls=cls, rect=c.to_page(cell_rect), origin="drawn",
                  labeler=labeler, text=text, owner_staff=owner_staff,
                  staff_position=staff_position, cell_id=cell_id)
        box.validate()
        self.boxes.append(box)
        return box

    def propose(self, cls: str, page_rect: Rect, source: str, score: Optional[float] = None) -> Prefill:
        p = Prefill(id=self._next_id("q"), cls=cls, rect=_check_rect(page_rect, "prefill"),
                    source=source, score=score)
        self.queue.append(p)
        return p

    def _take(self, prefill_id: str) -> Prefill:
        for i, p in enumerate(self.queue):
            if p.id == prefill_id:
                return self.queue.pop(i)
        raise StoreError(f"no pre-fill {prefill_id!r} in the queue")

    def confirm_prefill(self, prefill_id: str, cell_id: str, *, labeler: str = "sean", **attrs) -> Box:
        self.cell(cell_id)
        p = self._take(prefill_id)
        box = Box(id=p.id, cls=p.cls, rect=p.rect, origin="prefill-confirmed", labeler=labeler,
                  cell_id=cell_id, **attrs)
        box.validate()
        self.boxes.append(box)
        return box

    def fix_prefill(self, prefill_id: str, cell_id: str, *, cls: Optional[str] = None,
                    cell_rect: Optional[Rect] = None, labeler: str = "sean", **attrs) -> Box:
        c = self.cell(cell_id)
        p = self._take(prefill_id)
        rect = c.to_page(cell_rect) if cell_rect is not None else p.rect
        box = Box(id=p.id, cls=cls or p.cls, rect=rect, origin="prefill-fixed", labeler=labeler,
                  cell_id=cell_id, **attrs)
        box.validate()
        self.boxes.append(box)
        return box

    def reject_prefill(self, prefill_id: str) -> None:
        """Sean says the proposal is not on the page. It simply leaves the queue."""
        self._take(prefill_id)

    def boxes_in_cell(self, cell_id: str) -> List[Tuple[Box, Rect, bool]]:
        """Every truth box that touches the cell, in the cell's canonical frame.

        Returns ``(box, cell_rect, clipped)``. A box drawn in a neighbouring cell
        shows here too — that is the point of storing one page.
        """
        c = self.cell(cell_id)
        out: List[Tuple[Box, Rect, bool]] = []
        cx0, cy0, cx1, cy1 = c.rect
        for b in self.boxes:
            x0, y0, x1, y1 = b.rect
            if x1 <= cx0 or x0 >= cx1 or y1 <= cy0 or y0 >= cy1:
                continue
            clipped = x0 < cx0 or y0 < cy0 or x1 > cx1 or y1 > cy1
            ix = (max(x0, cx0), max(y0, cy0), min(x1, cx1), min(y1, cy1))
            out.append((b, c.to_cell(ix), clipped))
        return out

    # ------------------------------------------------------------ lifecycle
    def advance(self, to: str) -> None:
        if to not in STATES:
            raise StoreError(f"state {to!r} not in {STATES}")
        cur, nxt = STATES.index(self.state), STATES.index(to)
        if nxt != cur + 1:
            raise StoreError(f"{self.state} -> {to}: states advance one step at a time")
        self.state = to

    # ------------------------------------------------------------ io
    def validate(self) -> None:
        if self.state not in STATES:
            raise StoreError(f"state {self.state!r} not in {STATES}")
        if self.schema_version != SCHEMA_VERSION:
            raise StoreError(f"schema {self.schema_version} != {SCHEMA_VERSION}")
        for c in self.cells:
            c.validate()
        ids = [b.id for b in self.boxes] + [p.id for p in self.queue]
        if len(ids) != len(set(ids)):
            raise StoreError("duplicate box/pre-fill id")
        for b in self.boxes:
            b.validate()

    def to_json(self) -> Dict:
        self.validate()
        return asdict(self)

    @classmethod
    def from_json(cls, d: Dict) -> "PageTruth":
        def rect(v) -> Rect:
            return tuple(float(x) for x in v)  # type: ignore[return-value]

        page = cls(
            edition=d["edition"], pdf_page_index=int(d["pdf_page_index"]), dpi=int(d["dpi"]),
            width=int(d["width"]), height=int(d["height"]), state=d.get("state", "labeling"),
            schema_version=int(d.get("schema_version", SCHEMA_VERSION)),
            boxes=[Box(**{**b, "rect": rect(b["rect"]),
                          "owner_staff": tuple(b["owner_staff"]) if b.get("owner_staff") else None})
                   for b in d.get("boxes", [])],
            queue=[Prefill(**{**p, "rect": rect(p["rect"])}) for p in d.get("queue", [])],
            cells=[Cell(**{**c, "rect": rect(c["rect"])}) for c in d.get("cells", [])],
            staves=[StaffCheck(**s) for s in d.get("staves", [])],
        )
        page.validate()
        return page

    def path(self, root: Path = PAGES_DIR) -> Path:
        return root / self.edition / f"{self.pdf_page_index}.json"

    def save(self, root: Path = PAGES_DIR) -> Path:
        p = self.path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_json(), indent=1, sort_keys=True) + "\n")
        return p


def load(path: Path) -> PageTruth:
    return PageTruth.from_json(json.loads(Path(path).read_text()))


def load_all(root: Path = PAGES_DIR) -> List[PageTruth]:
    if not root.exists():
        return []
    return [load(p) for p in sorted(root.glob("*/*.json"))]
