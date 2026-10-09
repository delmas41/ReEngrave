"""Which families are complete on a page — computed, never asserted.

A family is complete on a page only when EVERY cell on it was inspected for
that family. A box that is absent means "not on the page" only for an
inspected family; for any other family it means nothing, and a scorer must
refuse that family rather than score it as zero (rule 8: a fallback never
converts "cannot tell" into an answer).

THE INK-COVERAGE CONTROL (Sean 2026-10-08: "my gut is to cover every bit of
ink"). Every connected ink component on the page — staff lines removed, since
on a scan every head touches them — must lie inside a truth box (a ``noise``
box counts), or it is listed for Sean. It is the control that can fail: an
unboxed mark is found by geometry, not by anyone's memory of having looked.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from tools.omr.score_reading import detector_family
from tools.omr.hand_truth.store import ALL_INK, ALL_INK_PASS, NOISE, TEXT, PageTruth

#: Whole-ink families the reading scorer does not list, so a class never
#: falls through to "unscored" here. Prefix-matched after normalising the
#: class name the way ``detector_family`` does.
_EXTRA_PREFIXES = (
    ("stem", "stem"),
    ("ledger", "ledger_line"),
    ("leger", "ledger_line"),
    ("staff", "staff_line"),
    ("artic", "articulation"),
    ("fermata", "articulation"),
    ("ornament", "ornament"),
    ("tremolo", "tremolo"),
    ("tuplet", "tuplet"),
    ("tuple", "tuplet"),
    ("brace", "brace"),
    ("bracket", "brace"),
    ("repeat", "barline"),
    ("textdynamic", "dynamic_letter"),
    ("grace", "notehead"),
)


def family_of(cls: str) -> str:
    """The family a class is scored and inspected under.

    ``score_reading.detector_family`` first (so the hand truth and the
    engraved reading scorer speak one vocabulary), then the whole-ink
    extras, then ``class:<name>`` — an explicit family of one, never a drop.
    """
    if cls in (NOISE, TEXT):
        return cls
    fam = detector_family(cls)
    if fam:
        return fam
    norm = "".join(ch for ch in cls.lower() if ch.isalnum())
    for prefix, f in _EXTRA_PREFIXES:
        if norm.startswith(prefix):
            return f
    return f"class:{cls}"


#: The OLD pass names (``inspected_passes`` on ``benchmarks/*/verdicts``) and
#: the families each one COMPLETELY covered. Deliberately conservative: a pass
#: over a SUBSET of a family ("hollow noteheads", "grace noteheads") completes
#: no family, because the black heads in the same cell were not swept.
LEGACY_PASS_FAMILIES: Dict[str, frozenset] = {
    "rests+accidentals": frozenset({"rest", "accidental", "key_accidental"}),
    "rests": frozenset({"rest"}),
    "accidentals": frozenset({"accidental", "key_accidental"}),
    "clefs": frozenset({"clef"}),
    "ties+slurs-reconcile": frozenset({"tie", "slur"}),
    "ties+slurs": frozenset({"tie", "slur"}),
    # pass-configs/draw-rich.json (27 classes) and completion-full.json (23).
    "draw-rich": frozenset({"notehead", "accidental", "key_accidental", "slur", "tie", "rest",
                            "augmentation_dot", "dynamic_letter", "hairpin", "clef"}),
    "completion": frozenset({"notehead", "rest", "accidental", "key_accidental",
                             "augmentation_dot", "slur", "tie", "hairpin", "clef"}),
    "hollow noteheads": frozenset(),
    "grace noteheads": frozenset(),
    "rests-reconcile": frozenset(),  # a reconcile of an earlier rests pass, not a sweep
}


def families_covered(passes: Iterable[str]) -> Optional[frozenset]:
    """Families a cell's passes cover; ``None`` means ALL (the whole-ink pass)."""
    out: set = set()
    for p in passes:
        if p in (ALL_INK, ALL_INK_PASS):
            return None
        if p in LEGACY_PASS_FAMILIES:
            out |= LEGACY_PASS_FAMILIES[p]
        else:
            out.add(p)  # a new-style pass names its family directly
    return frozenset(out)


def family_status(page: PageTruth, families: Optional[Sequence[str]] = None) -> Dict[str, Dict]:
    """Per family: complete?, and which cells were not inspected for it.

    ``families`` defaults to every family a box on the page carries plus every
    family any cell names, so nothing that was labeled is left unreported.
    """
    if families is None:
        fams = {family_of(b.cls) for b in page.boxes}
        for c in page.cells:
            cov = families_covered(c.inspected)
            if cov:
                fams |= set(cov)
        families = sorted(fams)
    out: Dict[str, Dict] = {}
    for fam in families:
        missing = []
        for c in page.cells:
            cov = families_covered(c.inspected)
            if cov is not None and fam not in cov:
                missing.append(c.id)
        out[fam] = {
            "complete": bool(page.cells) and not missing,
            "cells_total": len(page.cells),
            "cells_missing": missing,
        }
    return out


@dataclass
class InkReport:
    components: int
    covered: int
    uncovered: List[Dict]  # {"rect": (x0,y0,x1,y1), "area": px, "covered_frac": f}
    specks_below_min_area: int

    @property
    def clean(self) -> bool:
        return not self.uncovered


def ink_coverage(page: PageTruth, ink: np.ndarray, staff_mask: Optional[np.ndarray] = None,
                 *, min_area: int = 4, cover_frac: float = 0.5) -> InkReport:
    """Every ink component must sit inside a truth box, or it is listed.

    ``ink``: boolean page raster at the page's DPI (True = ink). ``staff_mask``:
    the staff-line pixels to remove first (the CV erasure the CV consumers
    already use) — without it a scanned staff joins every head into one
    component. Components smaller than ``min_area`` are COUNTED, not dropped.
    """
    import cv2  # the repo's connected-component reader (8-connectivity), as in clef_locator

    if ink.shape != (page.height, page.width):
        raise ValueError(f"ink raster {ink.shape} is not the page's {(page.height, page.width)}")
    work = ink.astype(bool)
    if staff_mask is not None:
        work = work & ~staff_mask.astype(bool)
    boxed = np.zeros_like(work)
    for b in page.boxes:
        x0, y0, x1, y1 = b.rect
        boxed[max(0, int(np.floor(y0))):int(np.ceil(y1)), max(0, int(np.floor(x0))):int(np.ceil(x1))] = True
    n, labels, stats, _ = cv2.connectedComponentsWithStats(work.astype(np.uint8), connectivity=8)
    covered = specks = 0
    uncovered: List[Dict] = []
    for i in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[i])
        if area < min_area:
            specks += 1
            continue
        comp = labels[y:y + h, x:x + w] == i
        frac = float((comp & boxed[y:y + h, x:x + w]).sum()) / float(area)
        if frac >= cover_frac:
            covered += 1
        else:
            uncovered.append({"rect": (x, y, x + w, y + h), "area": area, "covered_frac": round(frac, 3)})
    return InkReport(components=n - 1, covered=covered, uncovered=uncovered,
                     specks_below_min_area=specks)


def page_complete(page: PageTruth, ink_report: Optional[InkReport] = None) -> Dict:
    """The whole-ink verdict: every cell ALL_INK, every staff's lines confirmed,
    and the ink-coverage control clean. Without an ink report it is NOT complete
    — the control was not run, which is not the same as passing it."""
    cells_ok = bool(page.cells) and all(families_covered(c.inspected) is None for c in page.cells)
    staves_ok = bool(page.staves) and all(s.lines_right is True for s in page.staves)
    ink_ok = ink_report is not None and ink_report.clean
    return {
        "complete": cells_ok and staves_ok and ink_ok,
        "cells_all_ink": cells_ok,
        "staff_lines_confirmed": staves_ok,
        "ink_coverage": None if ink_report is None else ink_report.clean,
    }
