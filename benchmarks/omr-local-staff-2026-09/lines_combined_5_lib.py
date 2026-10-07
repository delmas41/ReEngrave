"""lane-lines-combined (2026-10-06): diagnostics for ONE far head on the combined tree -- what the reader sees (the lines at the
head, the box it used, every ledger rung found and why it was or was not taken). Read-only."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg

_CAP = {}
_orig = lg.derive_note_first_step


def _spy(img_gray, head_box, edge_y, sign, spacing, rungs_y, **kw):
    out = _orig(img_gray, head_box, edge_y, sign, spacing, rungs_y, **kw)
    _CAP.update(head_box=tuple(head_box), edge_y=edge_y, sign=sign, spacing=spacing, rungs_y=list(rungs_y), out=out)
    return out


lg.derive_note_first_step = _spy


def candidates(cap):
    """Every rung with the test it meets: distance from the box's staff-side edge (spaces, + inside the box) and from the middle."""
    x0, y0, x1, y1 = cap["head_box"]
    sp, sign = cap["spacing"], cap["sign"]
    near_y = y1 if sign < 0 else y0
    mid = (y0 + y1) / 2.0
    rows = []
    for r in cap["rungs_y"]:
        rn = sign * (r - near_y) / sp
        rows.append(dict(y=float(r), from_near_edge_sp=round(rn, 3), from_middle_sp=round((r - mid) / sp, 3),
                         in_near_band=lg.NOTE_LINE_NEAR_BAND_SPACES[0] <= rn <= lg.NOTE_LINE_NEAR_BAND_SPACES[1],
                         in_middle_band=abs(r - mid) <= lg.NOTE_LINE_MIDDLE_BAND_SPACES * sp))
    return rows


def diagnose(fp, subject, box, cls, lines):
    _CAP.clear()
    r = fp.read(subject, box, cls, lines)
    cap = dict(_CAP)
    nf = (r.get("detail") or {}).get("note_first") or {}
    return dict(pos=r["pos"], reason=r["reason"], box_source=r.get("box_source"), box_used=r.get("box_used"),
                detector_box=tuple(float(v) for v in box), lines=r.get("lines_used"), fit=r.get("fit"),
                edge_y=cap.get("edge_y"), spacing=cap.get("spacing"), rungs=candidates(cap) if cap else [],
                note_first=nf)
