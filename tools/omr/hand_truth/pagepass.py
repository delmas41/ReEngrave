"""The PAGE PASS store (ROADMAP 2.287): hand labels drawn at the grain the reader reads.

``data/hand-truth/pages/<edition>/<pdf_page_index>.pagepass.json`` -- beside the page file
(``<page>.json``, the per-cell labels), never inside it and never replacing it.

WHY. Sean labelled Brahms p0 one cell at a time, so a slur or tie crossing a barline was
drawn as two cut pieces. The reader now reads those marks once on the whole page
(CLAUDE.md section 3, "Claim order"). Truth for them is drawn the same way: pass 1 on the
whole page for the PAGE-WIDE kinds, in claim order (``KINDS``); pass 2 is the existing cell
pass, with pass-1 ink already shown as claimed.

A LABEL CLAIMS INK, NOT A RECTANGLE. The shape (a rectangle, or a polygon for an awkward
piece) only says WHERE; which ink pixels the label owns is decided by ``pageink.InkMap.claim``
per KIND (an arc takes its own thin curve, never the noteheads under its box). The label
carries ``ink_ref`` -- the rule and what it took (pixel count, bbox, a hash of the claimed
mask) -- so a later reader of the file can tell what the label meant and detect drift.

STATES. ``pending`` = a pre-fill (a proposal; drawn dashed; NOT truth); ``confirmed`` =
Sean drew it or acted on a pre-fill (``origin`` says which); ``rejected`` = Sean said the
proposal is not on the page (kept, so it is never proposed again). Only ``confirmed`` is
truth. A pre-fill never becomes truth by itself.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from tools.omr.hand_truth.store import PAGES_DIR, StoreError

SCHEMA_VERSION = 1
PASS_NAME = "page"

#: The page-wide kinds, IN CLAIM ORDER (CLAUDE.md section 3 and Sean 2026-11-10). Earlier kinds
#: win a pixel two labels both reach ("a later reader may mark claimed ink but never take it").
KINDS: Tuple[str, ...] = ("staff", "barline", "bracket", "clef", "key", "meter", "word",
                          "dynamic", "arc", "hairpin", "repeat")
#: What each kind takes from the ink under its shape (see pageink.InkMap).
KIND_MODE: Dict[str, str] = {
    "staff": "lines", "barline": "vertical", "arc": "thin", "hairpin": "thin",
    "bracket": "tall", "clef": "all", "key": "all", "meter": "all", "word": "all",
    "dynamic": "all", "repeat": "all",
}
#: kinds that carry typed text. A METER's text is its whole value ("6/8", "C", "2/2"): one mark, one box
#: (Sean 2026-11-10: "box the meter, 6-8, both numbers at the same time"); its digits stay recoverable in ``parts``.
TEXT_KINDS = ("word", "dynamic", "meter")
#: a WORD box may be a text BLOCK (Sean 2026-11-10: "a big box around all of it and just say title or subtitle")
BLOCK_SUBS = ("title", "subtitle", "composer", "other")
ARC_SUBS = ("tie", "slur")
STATES = ("pending", "confirmed", "rejected")
ORIGINS = ("drawn", "prefill", "prefill-confirmed", "prefill-fixed")

Rect = Tuple[float, float, float, float]


def kind_of_class(cls: str) -> Optional[str]:
    """The page-wide kind a per-cell class belongs to (None = a cell-pass mark)."""
    c = cls.lower()
    if c in ("tie", "slur"):
        return "arc"
    if c.startswith("barline"):
        return "barline"
    if c in ("brace", "bracket") or c.startswith("brace") or c.startswith("bracket"):
        return "bracket"
    if c.startswith("clef"):
        return "clef"
    if c.startswith("key") and not c.startswith("keyboard"):
        return "key"
    if c.startswith("timesig") or c.startswith("meter"):
        return "meter"
    if c == "text":
        return "word"
    if c.startswith("dynamic"):
        return "hairpin" if "hairpin" in c or "crescendo" in c or "diminuendo" in c else "dynamic"
    if c.startswith("repeat"):
        return "repeat"
    if c == "staff":
        return "staff"
    return None


# --------------------------------------------------------------------------- shapes
def rect_shape(r: Sequence[float]) -> Dict:
    x0, y0, x1, y1 = (float(v) for v in r)
    if not (x1 > x0 and y1 > y0):
        raise StoreError(f"empty or inverted rectangle {tuple(r)!r}")
    return {"rect": [x0, y0, x1, y1]}


def poly_shape(pts: Sequence[Sequence[float]]) -> Dict:
    p = [[float(x), float(y)] for x, y in pts]
    if len(p) < 3:
        raise StoreError("a polygon needs at least three points")
    return {"poly": p}


def check_shape(shape: Dict) -> Dict:
    if "rect" in shape:
        return rect_shape(shape["rect"])
    if "poly" in shape:
        return poly_shape(shape["poly"])
    raise StoreError(f"a shape is {{'rect': [...]}} or {{'poly': [...]}}, not {shape!r}")


def shape_bbox(shape: Dict) -> Rect:
    if "rect" in shape:
        return tuple(float(v) for v in shape["rect"])  # type: ignore[return-value]
    xs = [p[0] for p in shape["poly"]]
    ys = [p[1] for p in shape["poly"]]
    return (min(xs), min(ys), max(xs), max(ys))


def shape_area(shape: Dict) -> float:
    if "rect" in shape:
        x0, y0, x1, y1 = shape["rect"]
        return (x1 - x0) * (y1 - y0)
    p = shape["poly"]
    s = 0.0
    for i in range(len(p)):
        x0, y0 = p[i]
        x1, y1 = p[(i + 1) % len(p)]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def shape_contains(shape: Dict, x: float, y: float) -> bool:
    if "rect" in shape:
        x0, y0, x1, y1 = shape["rect"]
        return x0 <= x <= x1 and y0 <= y <= y1
    p = shape["poly"]
    inside = False
    j = len(p) - 1
    for i in range(len(p)):
        xi, yi = p[i]
        xj, yj = p[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def check_sub(kind: str, sub: Optional[str]) -> Optional[str]:
    """The sub-kind a NEW or EDITED label may carry (loading a file is lenient; round 1 wrote free values)."""
    if not sub:
        return None
    ok = ARC_SUBS if kind == "arc" else BLOCK_SUBS if kind == "word" else ()
    if sub not in ok:
        raise StoreError(f"a {kind} label's sub is one of {ok or '(none)'}, not {sub!r}")
    return sub


def normalize_meter(text: Optional[str]) -> Optional[str]:
    """``'6 8'`` / ``'6-8'`` / ``'6:8'`` -> ``'6/8'``; ``'c'`` -> ``'C'``; ``'cut'`` / ``'c|'`` -> ``'C|'``."""
    if text is None:
        return None
    two = str(text).split()
    if len(two) == 2 and all(p.isdigit() for p in two):
        return "/".join(two)                    # "6 8": numerator, space, denominator
    t = "".join(two)
    if not t:
        return None
    low = t.lower()
    if low in ("c", "common"):
        return "C"
    if low in ("c|", "c/", "cut", "alla-breve", "allabreve"):
        return "C|"
    for sep in ("-", ":", "over"):
        low = low.replace(sep, "/")
    return low if "/" in low else t


def meter_split(text: Optional[str]) -> List[str]:
    """The pieces of a meter's value in reading order: ``'6/8'`` -> ``['6', '8']``; ``'C'`` -> ``['C']``."""
    t = normalize_meter(text)
    if not t:
        return []
    return t.split("/") if "/" in t else [t]


# --------------------------------------------------------------------------- labels
@dataclass
class PLabel:
    id: str
    kind: str
    shape: Dict
    state: str
    origin: str
    source: str = ""            # where a pre-fill came from ("hand-p0", "arc-key-2.281", "staff-lines")
    text: Optional[str] = None  # a word / dynamic's letters
    sub: Optional[str] = None   # an arc's "tie" | "slur"; a word's BLOCK_SUBS (one box over a block of text)
    note: str = ""              # a pre-fill's assumption, said plainly
    labeler: str = "sean"
    pass_: str = PASS_NAME
    ink_ref: Optional[Dict] = None
    #: a meter's per-digit ink pieces under its ONE label: [{"rect": [...], "text": "6", "from": "hand"|"ink"}, ...]
    #: (round 2; optional, absent in round-1 files). Lets detector training get digit boxes later.
    parts: Optional[List[Dict]] = None

    @property
    def is_block(self) -> bool:
        return self.kind == "word" and self.sub in BLOCK_SUBS

    def validate(self) -> None:
        if self.kind not in KINDS:
            raise StoreError(f"label {self.id}: kind {self.kind!r} not in {KINDS}")
        if self.state not in STATES:
            raise StoreError(f"label {self.id}: state {self.state!r} not in {STATES}")
        if self.origin not in ORIGINS:
            raise StoreError(f"label {self.id}: origin {self.origin!r} not in {ORIGINS}")
        if self.state == "confirmed" and self.origin == "prefill":
            raise StoreError(f"label {self.id}: a confirmed label cannot still be a bare pre-fill")
        if self.state == "pending" and self.origin != "prefill":
            raise StoreError(f"label {self.id}: only a pre-fill is pending")
        self.shape = check_shape(self.shape)

    def to_json(self) -> Dict:
        d = asdict(self)
        d["pass"] = d.pop("pass_")
        if d.get("parts") is None:
            d.pop("parts", None)        # round-2 field: absent unless set, so a round-1 label's JSON is unchanged
        return d

    @classmethod
    def from_json(cls, d: Dict) -> "PLabel":
        d = dict(d)
        d["pass_"] = d.pop("pass", PASS_NAME)
        return cls(**d)


@dataclass
class PagePass:
    edition: str
    pdf_page_index: int
    dpi: int
    width: int
    height: int
    sp: float = 0.0             # staff space in page px (measured from the page file's cells)
    labels: List[PLabel] = field(default_factory=list)
    provenance: Dict = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    # ------------------------------------------------------------ lookup
    def label(self, label_id: str) -> PLabel:
        for lab in self.labels:
            if lab.id == label_id:
                return lab
        raise StoreError(f"no label {label_id!r}")

    def claimers(self) -> List[PLabel]:
        """Labels that claim ink: confirmed ones, and pending pre-fills (shown, not truth)."""
        return [lab for lab in self.labels if lab.state in ("confirmed", "pending")]

    def truth(self) -> List[PLabel]:
        return [lab for lab in self.labels if lab.state == "confirmed"]

    def _next_id(self, prefix: str = "P") -> str:
        used = {lab.id for lab in self.labels}
        n = len(used)
        while f"{prefix}{n}" in used:
            n += 1
        return f"{prefix}{n}"

    # ------------------------------------------------------------ writes
    def add_prefill(self, kind: str, shape: Dict, source: str, *, text: Optional[str] = None,
                    sub: Optional[str] = None, note: str = "", parts: Optional[List[Dict]] = None) -> PLabel:
        lab = PLabel(id=self._next_id(), kind=kind, shape=shape, state="pending", origin="prefill",
                     source=source, text=text, sub=sub, note=note, parts=parts)
        lab.validate()
        self.labels.append(lab)
        return lab

    def draw(self, kind: str, shape: Dict, *, text: Optional[str] = None, sub: Optional[str] = None,
             labeler: str = "sean") -> PLabel:
        sub = check_sub(kind, sub)
        if kind == "meter":
            text = normalize_meter(text)
        lab = PLabel(id=self._next_id(), kind=kind, shape=shape, state="confirmed", origin="drawn",
                     text=text, sub=sub, labeler=labeler)
        lab.validate()
        self.labels.append(lab)
        return lab

    def confirm(self, label_id: str) -> PLabel:
        lab = self.label(label_id)
        if lab.state != "pending":
            raise StoreError(f"label {label_id} is {lab.state}, not a pending pre-fill")
        lab.state, lab.origin = "confirmed", "prefill-confirmed"
        lab.validate()
        return lab

    def reject(self, label_id: str) -> PLabel:
        lab = self.label(label_id)
        if lab.state != "pending":
            raise StoreError(f"label {label_id} is {lab.state}; delete it instead")
        lab.state = "rejected"
        return lab

    def edit(self, label_id: str, *, kind: Optional[str] = None, shape: Optional[Dict] = None,
             text: Optional[str] = None, sub: Optional[str] = None) -> PLabel:
        """Sean fixed a label. A pre-fill he changes is confirmed AS FIXED (his word, not ours)."""
        lab = self.label(label_id)
        changed_geom = False
        if kind is not None and kind != lab.kind:
            lab.kind, changed_geom = kind, True
            if lab.sub and lab.sub not in (ARC_SUBS if kind == "arc" else BLOCK_SUBS if kind == "word" else ()):
                lab.sub = None          # a sub-kind belongs to its kind
            if kind != "meter":
                lab.parts = None
        if shape is not None:
            lab.shape, changed_geom = check_shape(shape), True
        if text is not None:
            lab.text = (normalize_meter(text) if lab.kind == "meter" else text) or None
        if sub is not None:
            lab.sub = check_sub(lab.kind, sub)
        if lab.state == "pending" and changed_geom:
            lab.state, lab.origin = "confirmed", "prefill-fixed"
        elif lab.state == "confirmed" and lab.origin == "prefill-confirmed" and changed_geom:
            lab.origin = "prefill-fixed"
        lab.ink_ref = None
        if lab.parts and (changed_geom or text is not None):
            lab.parts = None            # the digit pieces are re-read from the ink of the new shape / the new value
        lab.validate()
        return lab

    def covered_prefills(self) -> Dict[str, str]:
        """Pending WORD pre-fills lying inside a CONFIRMED text block -> that block's id.

        The block is Sean's one statement about all the words in it, so the fragments need no answer
        (resolved by the block, shown as such; derived here, never written to the file)."""
        out: Dict[str, str] = {}
        blocks = [b for b in self.labels if b.state == "confirmed" and b.is_block]
        if not blocks:
            return out
        for lab in self.labels:
            if lab.state != "pending" or lab.kind != "word":
                continue
            bx0, by0, bx1, by1 = shape_bbox(lab.shape)
            a = max(1e-9, (bx1 - bx0) * (by1 - by0))
            for b in blocks:
                cx0, cy0, cx1, cy1 = shape_bbox(b.shape)
                iw, ih = min(bx1, cx1) - max(bx0, cx0), min(by1, cy1) - max(by0, cy0)
                if iw > 0 and ih > 0 and iw * ih >= 0.8 * a and shape_contains(
                        b.shape, (bx0 + bx1) / 2, (by0 + by1) / 2):
                    out[lab.id] = b.id
                    break
        return out

    def delete(self, label_id: str) -> PLabel:
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
    def from_json(cls, d: Dict) -> "PagePass":
        pp = cls(edition=d["edition"], pdf_page_index=int(d["pdf_page_index"]), dpi=int(d["dpi"]),
                 width=int(d["width"]), height=int(d["height"]), sp=float(d.get("sp", 0.0)),
                 labels=[PLabel.from_json(x) for x in d.get("labels", [])],
                 provenance=d.get("provenance", {}),
                 schema_version=int(d.get("schema_version", SCHEMA_VERSION)))
        pp.validate()
        return pp

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_json(), indent=1, sort_keys=True) + "\n")
        os.replace(tmp, path)
        return path


def pagepass_path(edition: str, page_index: int, root: Path = PAGES_DIR) -> Path:
    return Path(root) / edition / f"{page_index}.pagepass.json"


def load(path: Path) -> PagePass:
    return PagePass.from_json(json.loads(Path(path).read_text()))
