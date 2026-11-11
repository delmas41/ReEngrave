"""The CELL PASS store (ROADMAP 2.287 round 3): pass 2, the labels that are left once the page is labelled.

``data/hand-truth/pages/<edition>/<pdf_page_index>.cellpass.json`` -- a SIBLING of ``<page>.pagepass.json``
(pass 1) and ``<page>.json`` (the old per-cell boxes). Nothing here ever writes either of them: pass 1's
labels are claimed ink and final, the old boxes are only PRE-FILLS (proposals) for this pass.

WHAT PASS 2 LABELS. Pass 1 labelled the page-wide marks (staff, barline, bracket, clef, key, meter, word,
dynamic, arc, hairpin, repeat). What is left is the cell level: noteheads, stems, beams, flags, ledger lines,
augmentation dots, accidentals, rests, articulations, tremolo slashes, tuplet marks, and anything else
(``KINDS``); plus ``staffedge`` (the fringe of a staff line pass 1's band left) and ``noise`` (ink that is not
music). A label carries its ``kind`` (what the INK RULE reads: ``cellink``) and its ``cls`` (the exact class,
``noteheadHalfInSpace``, ``stem``, ... what a detector would train on).

STATES, as in pass 1. ``pending`` = a pre-fill (NOT truth, drawn dashed); ``confirmed`` = Sean drew it or acted
on a pre-fill; ``rejected`` = kept so it is never proposed again. A pre-fill never becomes truth by itself.

PRE-FILLS. ``build`` turns the old per-cell boxes of the page file into pending pre-fills of the CELL-LEVEL
kinds. A box of a page-wide kind (an arc, a barline, a clef ...) is dropped: pass 1 superseded it. The rest of
the pre-fill story -- a pre-fill whose ink pass 1 already claimed is resolved automatically -- is derived by
the service, never written here.

SCHEMA (version 1), one list ``labels``:
  id, kind, cls, shape ({"rect": [x0,y0,x1,y1]} or {"poly": [[x,y],...]}, PAGE px), state, origin (``drawn`` /
  ``prefill`` / ``prefill-confirmed`` / ``prefill-fixed``), source (``hand-p0`` = Sean's old box, ``staff-edge``
  = a fringe strip proposed from the ink), cell_id (the cell it was drawn or proposed in), box_id (the old box's
  id in the page file), note, labeler, pass (``"cell"``), ink_ref (rule ``cellink-1``, roles, px, bbox, sha1).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tools.omr.hand_truth import pagepass as pp
from tools.omr.hand_truth.store import PAGES_DIR, StoreError

SCHEMA_VERSION = 1
PASS_NAME = "cell"
#: the cell-level kinds, in the order the palette shows them (and the order a reader meets them)
KINDS: Tuple[str, ...] = ("notehead", "stem", "beam", "flag", "ledger", "dot", "accidental", "rest",
                          "articulation", "tremolo", "tuplet", "staffedge", "other", "noise")
STATES = pp.STATES
ORIGINS = pp.ORIGINS

_ARTIC_PREFIX = ("artic", "fermata", "ornament", "caesura", "strings", "fingering", "arpeggi", "keyboardpedal")


def cell_kind_of_class(cls: str) -> Optional[str]:
    """The pass-2 kind of a per-cell class; None for a PAGE-WIDE class (pass 1 owns it)."""
    if pp.kind_of_class(cls) is not None:
        return None
    c = cls.lower()
    if c == "noise":
        return "noise"
    if c in ("ledgerline", "legerline"):
        return "ledger"
    if c.startswith("notehead"):
        return "notehead"
    if c == "stem":
        return "stem"
    if c == "beam":
        return "beam"
    if c.startswith("flag"):
        return "flag"
    if c == "augmentationdot":
        return "dot"
    if c.startswith("accidental"):
        return "accidental"
    if c.startswith("rest"):
        return "rest"
    if c.startswith("tremolo"):
        return "tremolo"
    if c.startswith("tuple") or c.startswith("tuplet"):
        return "tuplet"
    if c.startswith(_ARTIC_PREFIX):
        return "articulation"
    return "other"


@dataclass
class CLabel:
    id: str
    kind: str
    cls: str
    shape: Dict
    state: str
    origin: str
    source: str = ""
    cell_id: Optional[str] = None
    box_id: Optional[str] = None
    note: str = ""
    labeler: str = "sean"
    pass_: str = PASS_NAME
    ink_ref: Optional[Dict] = None

    def validate(self) -> None:
        if self.kind not in KINDS:
            raise StoreError(f"label {self.id}: kind {self.kind!r} not in {KINDS}")
        if not self.cls:
            raise StoreError(f"label {self.id}: no class")
        if self.state not in STATES:
            raise StoreError(f"label {self.id}: state {self.state!r} not in {STATES}")
        if self.origin not in ORIGINS:
            raise StoreError(f"label {self.id}: origin {self.origin!r} not in {ORIGINS}")
        if self.state == "confirmed" and self.origin == "prefill":
            raise StoreError(f"label {self.id}: a confirmed label cannot still be a bare pre-fill")
        if self.state == "pending" and self.origin != "prefill":
            raise StoreError(f"label {self.id}: only a pre-fill is pending")
        self.shape = pp.check_shape(self.shape)

    def to_json(self) -> Dict:
        d = asdict(self)
        d["pass"] = d.pop("pass_")
        return d

    @classmethod
    def from_json(cls, d: Dict) -> "CLabel":
        d = dict(d)
        d["pass_"] = d.pop("pass", PASS_NAME)
        return cls(**d)


@dataclass
class CellPass:
    edition: str
    pdf_page_index: int
    dpi: int
    width: int
    height: int
    sp: float = 0.0
    labels: List[CLabel] = field(default_factory=list)
    provenance: Dict = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    # ------------------------------------------------------------ lookup
    def label(self, label_id: str) -> CLabel:
        for lab in self.labels:
            if lab.id == label_id:
                return lab
        raise StoreError(f"no label {label_id!r}")

    def claimers(self) -> List[CLabel]:
        """Labels that claim ink: confirmed ones, and pending pre-fills (shown, not truth)."""
        return [lab for lab in self.labels if lab.state in ("confirmed", "pending")]

    def truth(self) -> List[CLabel]:
        return [lab for lab in self.labels if lab.state == "confirmed"]

    def _next_id(self, prefix: str = "C") -> str:
        used = {lab.id for lab in self.labels}
        n = len(used)
        while f"{prefix}{n}" in used:
            n += 1
        return f"{prefix}{n}"

    # ------------------------------------------------------------ writes
    def add_prefill(self, kind: str, cls: str, shape: Dict, source: str, *, cell_id: Optional[str] = None,
                    box_id: Optional[str] = None, note: str = "") -> CLabel:
        lab = CLabel(id=self._next_id(), kind=kind, cls=cls, shape=shape, state="pending", origin="prefill",
                     source=source, cell_id=cell_id, box_id=box_id, note=note)
        lab.validate()
        self.labels.append(lab)
        return lab

    def draw(self, kind: str, cls: Optional[str], shape: Dict, *, cell_id: Optional[str] = None,
             labeler: str = "sean") -> CLabel:
        lab = CLabel(id=self._next_id(), kind=kind, cls=cls or kind, shape=shape, state="confirmed",
                     origin="drawn", cell_id=cell_id, labeler=labeler)
        lab.validate()
        self.labels.append(lab)
        return lab

    def confirm(self, label_id: str) -> CLabel:
        lab = self.label(label_id)
        if lab.state != "pending":
            raise StoreError(f"label {label_id} is {lab.state}, not a pending pre-fill")
        lab.state, lab.origin = "confirmed", "prefill-confirmed"
        lab.validate()
        return lab

    def reject(self, label_id: str) -> CLabel:
        lab = self.label(label_id)
        if lab.state != "pending":
            raise StoreError(f"label {label_id} is {lab.state}; delete it instead")
        lab.state = "rejected"
        return lab

    def edit(self, label_id: str, *, kind: Optional[str] = None, cls: Optional[str] = None,
             shape: Optional[Dict] = None) -> CLabel:
        """Sean fixed a label. A pre-fill he changes is confirmed AS FIXED (his word, not ours)."""
        lab = self.label(label_id)
        changed = False
        if kind is not None and kind != lab.kind:
            lab.kind, changed = kind, True
            lab.cls = cls or kind
        elif cls is not None and cls != lab.cls:
            lab.cls, changed = cls, True
        if shape is not None:
            lab.shape, changed = pp.check_shape(shape), True
        if changed:
            if lab.state == "pending":
                lab.state, lab.origin = "confirmed", "prefill-fixed"
            elif lab.state == "confirmed" and lab.origin == "prefill-confirmed":
                lab.origin = "prefill-fixed"
        lab.ink_ref = None
        lab.validate()
        return lab

    def bulk_confirm(self, label_ids: List[str]) -> List[CLabel]:
        """Confirm several pending pre-fills as ONE change (one undo). The caller chooses the set (one kind in
        one cell); a label that is not pending is refused -- nothing is confirmed then."""
        labs = [self.label(i) for i in label_ids]
        bad = [lab.id for lab in labs if lab.state != "pending"]
        if bad:
            raise StoreError(f"not pending: {bad[:5]}")
        for lab in labs:
            lab.state, lab.origin = "confirmed", "prefill-confirmed"
            lab.validate()
        return labs

    def delete(self, label_id: str) -> CLabel:
        """Remove a CONFIRMED label (Sean's latest word). A pending one is rejected, not deleted."""
        lab = self.label(label_id)
        if lab.state == "pending":
            return self.reject(label_id)
        self.labels.remove(lab)
        return lab

    # ------------------------------------------------------------ io
    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise StoreError(f"schema {self.schema_version} != {SCHEMA_VERSION}")
        ids = [lab.id for lab in self.labels]
        if len(ids) != len(set(ids)):
            raise StoreError("duplicate label id")
        for lab in self.labels:
            lab.validate()

    def to_json(self) -> Dict:
        self.validate()
        d = asdict(self)
        d["labels"] = [lab.to_json() for lab in self.labels]
        return d

    @classmethod
    def from_json(cls, d: Dict) -> "CellPass":
        cp = cls(edition=d["edition"], pdf_page_index=int(d["pdf_page_index"]), dpi=int(d["dpi"]),
                 width=int(d["width"]), height=int(d["height"]), sp=float(d.get("sp", 0.0)),
                 labels=[CLabel.from_json(x) for x in d.get("labels", [])], provenance=d.get("provenance", {}),
                 schema_version=int(d.get("schema_version", SCHEMA_VERSION)))
        cp.validate()
        return cp

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_json(), indent=1, sort_keys=True) + "\n")
        os.replace(tmp, path)
        return path


def cellpass_path(edition: str, page_index: int, root: Path = PAGES_DIR) -> Path:
    return Path(root) / edition / f"{page_index}.cellpass.json"


def load(path: Path) -> CellPass:
    return CellPass.from_json(json.loads(Path(path).read_text()))


# --------------------------------------------------------------------------- pre-fills from the old boxes
def build(truth, staff_edge: bool = True) -> Tuple[CellPass, Dict]:
    """A new cell-pass file: every OLD box of the page file (``truth``, a ``store.PageTruth``) of a cell-level
    class becomes a PENDING pre-fill; a box of a page-wide class is dropped (pass 1 superseded it). Plus one
    pending ``staffedge`` strip per measure cell (the staff's lines +- 0.5 sp), the fringe pre-fill.

    Returns (the page, the counts: imported / dropped_page_wide / by_kind / staff_edge)."""
    sp = 0.0
    try:
        from tools.omr.hand_truth.pageink import measure_sp, staff_lines_from_cells
        sp = measure_sp(staff_lines_from_cells(truth.cells))
    except Exception:  # noqa: BLE001
        pass
    cp = CellPass(edition=truth.edition, pdf_page_index=truth.pdf_page_index, dpi=truth.dpi, width=truth.width,
                  height=truth.height, sp=sp or 32.0,
                  provenance={"built_from": f"{truth.edition}/{truth.pdf_page_index}.json (never edited)"})
    counts: Dict = {"imported": 0, "dropped_page_wide": 0, "by_kind": {}, "staff_edge": 0}
    for b in truth.boxes:
        k = cell_kind_of_class(b.cls)
        if k is None:
            counts["dropped_page_wide"] += 1
            continue
        cp.add_prefill(k, b.cls, pp.rect_shape(b.rect), "hand-p0", cell_id=b.cell_id, box_id=b.id)
        counts["imported"] += 1
        counts["by_kind"][k] = counts["by_kind"].get(k, 0) + 1
    if staff_edge:
        for c in truth.cells:
            if c.kind != "measure" or not c.staff_line_ys:
                continue
            x0, y0, x1, y1 = c.rect
            sy = (y1 - y0) / c.canonical_h
            ys = [y0 + float(y) * sy for y in c.staff_line_ys]
            h = 0.5 * cp.sp
            cp.add_prefill("staffedge", "staffedge", pp.rect_shape([x0, min(ys) - h, x1, max(ys) + h]),
                           "staff-edge", cell_id=c.id,
                           note="the fringe of this staff's lines, which pass 1's band left")
            counts["staff_edge"] += 1
    return cp, counts
