"""ROADMAP 2.217 -- the ADJUDICATE side of `ledger_strokes` (flag `OMR_LEDGERS_FROM_STROKES`, default OFF): turns a cell's `Q.STROKE` rows, its
`Q.STROKE_OWNER` verdict and a head's `Q.GLYPH_BOX` into `ledger_strokes.read_head`'s inputs. No decision lives here; `ownership` and `position`
call it, so both read ONE ledger reading. The caller's decision must declare `Q.STROKE`, `Q.STROKE_OWNER`, `Q.GLYPH_BOX` in `wants`."""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from ..adjudicate import Evidence
from ...annotate import ledger_strokes as LS
from .. import record as R
from ..record import Q, Scope, STROKE_GLYPH_BASE


def enabled() -> bool:
    """Allow-list (CLAUDE section 7): default OFF; a typo leaves it off."""
    return os.environ.get(LS.ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def _parse_staff(key: str) -> Optional[Tuple[int, int, int]]:
    try:
        _k, p, s, st = str(key).split("/")
        return int(p), int(s), int(st)
    except (ValueError, TypeError):
        return None


def head_box(ev: Evidence) -> Optional[Tuple[float, float, float, float]]:
    """The head's box in PAGE px (x0, y0, x1, y1), or None (declined, never defaulted)."""
    rows = ev.rows(Q.GLYPH_BOX)
    if not rows:
        return None
    b = (rows[-1].detail or {}).get("bbox_page_px")
    if isinstance(b, (list, tuple)) and len(b) == 4:
        return tuple(float(v) for v in b)
    return None


def views_for(ev: Evidence, candidate_key: str) -> Optional[List[LS.RungView]]:
    """The candidate staff's cell (this head's measure) as page-frame `RungView`s; None where the cell has no stroke map."""
    ps = _parse_staff(candidate_key)
    sub = ev.subject
    if ps is None or getattr(sub, "cell", None) is None:
        return None
    cell = R.cell(ps[0], ps[1], ps[2], sub.cell)
    rows = ev.rows(Q.STROKE, scope=Scope.SELF_AND_DESCENDANTS, subject=cell)
    if not rows:
        return None
    verdict = ev.verdict(Q.STROKE_OWNER, subject=cell)
    owner: Dict[int, Tuple[str, Optional[str]]] = {}
    if verdict is not None and isinstance(getattr(verdict, "detail", None), dict):
        for o, rec in (verdict.detail.get("strokes") or {}).items():
            try:
                owner[int(o)] = (str(rec[0]), rec[1])
            except (ValueError, TypeError, IndexError):
                continue
    out: List[LS.RungView] = []
    for r in rows:
        g = getattr(r.subject, "glyph", None)
        d = r.detail or {}
        sb, pb, ends, steps = d.get("stroke_box"), d.get("bbox_page_px"), d.get("ends"), d.get("end_steps_from_top")
        if g is None or not (STROKE_GLYPH_BASE <= g < 400_000) or not sb or not pb or not ends or not steps or len(steps) < 2:
            continue
        sw, sh = float(sb[2]), float(sb[3])
        pw, ph = float(pb[2]) - float(pb[0]), float(pb[3]) - float(pb[1])
        scale = (pw / sw) if sw >= sh and sw > 1 else ((ph / sh) if sh > 1 else 0.0)
        if scale <= 0:
            continue
        px = lambda x: float(pb[0]) + (float(x) - float(sb[0])) * scale     # noqa: E731
        py = lambda y: float(pb[1]) + (float(y) - float(sb[1])) * scale     # noqa: E731
        o = g - STROKE_GLYPH_BASE
        st, fam = owner.get(o, ("", None))
        out.append(LS.RungView(
            ordinal=o, row_id=r.id, kind=str(r.value), state=st, family=fam,
            ends=(px(ends[0]), py(ends[1]), px(ends[2]), py(ends[3])), steps=(float(steps[0]), float(steps[1])),
            space_px=float(d.get("staff_space_local_px") or 0.0) * scale, length_sp=float(d.get("length_spaces") or 0.0),
            thickness_sp=float(d.get("thickness_spaces") or 0.0)))
    return out


def reading(ev: Evidence, candidate_key: str, geometry_position) -> LS.Reading:
    """The head's ledger reading toward one candidate staff."""
    return LS.read_head(views_for(ev, candidate_key), head_box(ev), geometry_position)
