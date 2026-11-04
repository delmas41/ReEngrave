"""ROADMAP 2.260a M1 -- THE TILTED BARLINE COLUMN AS A FACT (STAGED GATHER; decides nothing; flag `OMR_BARLINE_COLUMN_FACT`, default ON).

WHY. The shared extractor reads a barline column ONCE per system and, for a tilted scan, fits it as a line through the staves that show the
rule (`measure_extractor._system_barline_columns`, Theil-Sen, 2.221 m2) -- then keeps only the mean x (`Barline.x`). Every later reader cuts at that
x (cells are cut at `bl.x`; the stroke map sees a half barline on either side of it on 78% of Litolff and 83% of Brahms staff-barlines). The
slope the extractor used is thrown away and, with a master cell map (`cell_map`), never even computed: the master holds `Barline.x`. This is
the fact kept: per column, `x = slope * y + intercept` in page px, so M2 can carve the column out of the page raster along its true line.

HOW. A REFIT IN STAGED, from the page-wide barlines and the page raster alone (LEGACY's `measure_extractor` is read, never edited): for
each accepted column (`pws.barlines`, one per system column) and each staff of its system, the rule's x on that staff is the centre of the
widest run of columns near the mean x whose ink fills at least `RULE_FILL_MIN` of the staff's span (staff lines run across every column and
fill only ~0.1, a rule ~1.0). Through those (staff mid y, rule x) points the same estimator as the extractor: slope = the median of the
pairwise slopes, intercept = the median of x - slope * y. Fewer than two staves show the rule: slope 0 at the mean x, said (`staves` holds
what it saw), never a tilt inferred from nothing (rule 8). Nothing reads the rows: the exported file is byte-identical with the flag on.

CONVENTION ASSUMED: a barline is a straight line, tilted as a whole by the scan (one slope per column, all staves). WHAT WOULD FALSIFY IT:
a column whose per-staff x's depart from their line by more than a barline's width (`resid_px` in the row says so per column). NOT CONFIRMED
beyond the two plates.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DERIVED_CHECK = False
ENV = "OMR_BARLINE_COLUMN_FACT"
#: a column belongs to the rule when its ink fills this share of the staff's span (lines alone ~0.1; a rule ~1.0, a scan's broken one ~0.8)
RULE_FILL_MIN = 0.8
#: the search window either side of the mean x, staff spaces (the largest drift measured, 21 px over a system on Litolff p6 = ~0.5 sp per staff)
WINDOW_SPACES = 1.5


def enabled() -> bool:
    """`OMR_BARLINE_COLUMN_FACT` (ROADMAP 2.260a M1), default ON (deny-list, 2.260b landing 2026-11-04: M3 reads it); `OMR_PAGE_CLAIMS` forces it on."""
    from .arc_claim import page_claims_enabled
    return os.environ.get(ENV, "").strip().lower() not in ("0", "false", "no", "off") or page_claims_enabled()


def rule_x_on_staff(ink: np.ndarray, top: int, bottom: int, x_mean: float, sp: float) -> Optional[float]:
    """The x of the barline rule on ONE staff: the centre of the widest run of columns within `WINDOW_SPACES` of `x_mean` whose ink fills at least
    `RULE_FILL_MIN` of rows `top..bottom`; the run nearest `x_mean` on a tie. None where no column does (the staff shows no rule here)."""
    h, w = ink.shape
    top, bottom = max(0, int(top)), min(h, int(bottom) + 1)
    if bottom - top < 3:
        return None
    xa, xb = max(0, int(round(x_mean - WINDOW_SPACES * sp))), min(w, int(round(x_mean + WINDOW_SPACES * sp)) + 1)
    if xb - xa < 1:
        return None
    fill = ink[top:bottom, xa:xb].mean(axis=0)
    good = fill >= RULE_FILL_MIN
    if not good.any():
        return None
    best: Optional[Tuple[int, float, float]] = None       # (width, -distance to x_mean, centre)
    i, n = 0, len(good)
    while i < n:
        if not good[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and good[j + 1]:
            j += 1
        centre = xa + (i + j) / 2.0
        cand = (j - i + 1, -abs(centre - x_mean), centre)
        if best is None or cand[:2] > best[:2]:
            best = cand
        i = j + 1
    return None if best is None else float(best[2])


def theil_sen(pts: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """`(slope, intercept)` of x on y through `pts` = [(y, x), ...], the extractor's estimator (median of pairwise slopes; median intercept).
    Fewer than two points: slope 0 at the one x."""
    pts = sorted(pts)
    if not pts:
        raise ValueError("theil_sen needs at least one point")
    slope = 0.0
    if len(pts) >= 2:
        sl = [(b[1] - a[1]) / (b[0] - a[0]) for i, a in enumerate(pts) for b in pts[i + 1:] if b[0] != a[0]]
        slope = float(np.median(sl)) if sl else 0.0
    icpt = float(np.median([px - slope * py for py, px in pts]))
    return slope, icpt


def fit_columns(pws: Any) -> List[Dict[str, Any]]:
    """One dict per accepted barline column of the page: `system`, `x`, `y0`, `y1`, `slope`, `intercept`, `staves` (staff indices that show the
    rule), `n_staves` (the system's), `tilt_px`, `resid_px`. Reads `pws.barlines`, `pws.staves`, `pws.page.binary`."""
    binary = getattr(getattr(pws, "page", None), "binary", None)
    if binary is None:
        return []
    ink = binary == 0
    by_system: Dict[int, List[Any]] = {}
    for s in pws.staves:
        by_system.setdefault(s.system_index, []).append(s)
    out: List[Dict[str, Any]] = []
    for bl in sorted(pws.barlines, key=lambda b: (b.system_index, b.x)):
        staves = sorted(by_system.get(bl.system_index, ()), key=lambda s: s.top_y)
        if not staves:
            continue
        sp = float(np.median([s.line_spacing_px for s in staves]))
        pts: List[Tuple[float, float]] = []
        seen: List[int] = []
        for s in staves:
            x = rule_x_on_staff(ink, s.top_y, s.bottom_y, float(bl.x), sp)
            if x is not None:
                pts.append(((s.top_y + s.bottom_y) / 2.0, x))
                seen.append(int(s.staff_index))
        y0, y1 = float(bl.y_top), float(bl.y_bottom)
        if len(pts) >= 2:
            slope, icpt = theil_sen(pts)
            resid = max(abs(px - (slope * py + icpt)) for py, px in pts)
        else:
            slope, icpt, resid = 0.0, float(bl.x), 0.0
        out.append(dict(system=int(bl.system_index), x=float(bl.x), y0=y0, y1=y1, slope=round(slope, 6), intercept=round(icpt, 2),
                        staves=seen, n_staves=len(staves), tilt_px=round(slope * (y1 - y0), 2), resid_px=round(float(resid), 2)))
    return out


def x_at(col: Dict[str, Any], y: float) -> float:
    """The column's x at page row `y`."""
    return float(col["slope"]) * float(y) + float(col["intercept"])


def gather_barline_columns(log: Any, pws: Any, *, progress: bool = False) -> List[Dict[str, Any]]:
    """ROADMAP 2.260a M1 (flag `OMR_BARLINE_COLUMN_FACT`, default ON), STAGED GATHER: `Q.BARLINE_COLUMN_FIT`, one row per accepted column, on the
    system's subject. Reads the page raster and the page-wide barlines; files rows only and decides nothing. Returns the fits."""
    if not enabled():
        return []
    from . import record as R
    from .record import Q, READERS
    from .gather import FRAME_PAGE
    p = int(getattr(pws.page, "page_index", 0))
    cols = fit_columns(pws)
    for c in cols:
        log.observe(R.system(p, c["system"]), Q.BARLINE_COLUMN_FIT, [c["slope"], c["intercept"]], reader=READERS.CV_BARLINE_COLUMN, frame=FRAME_PAGE,
                    x=c["x"], y0=c["y0"], y1=c["y1"], staves=c["staves"], n_staves=c["n_staves"], tilt_px=c["tilt_px"], resid_px=c["resid_px"],
                    rule_fill_min=RULE_FILL_MIN)
    if progress:
        print("  gather barline columns p%s: %d columns, max |tilt| %.1f px" % (p, len(cols), max([abs(c["tilt_px"]) for c in cols] or [0.0])))
    return cols
