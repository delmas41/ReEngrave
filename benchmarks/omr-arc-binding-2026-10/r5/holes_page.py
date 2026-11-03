"""Read a head box's holes on the PAGE raster with the LOCAL staff lines (diagnosis only).
args: plate page x0,y0,x1,y1 [reach_sp]"""
import sys
import numpy as np
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf")
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf/out/2.252r5")
import local as LC
from tools.omr.staged import box_kind as K
from tools.omr.staged import head_ink


def staff_of(lines, y):
    # the 5 lines nearest y forming a staff (consecutive gaps similar)
    best = None
    for i in range(len(lines) - 4):
        five = lines[i:i + 5]
        gaps = np.diff(five)
        if gaps.max() - gaps.min() > 4:
            continue
        d = min(abs(y - five[0]), abs(y - five[-1])) if not (five[0] <= y <= five[-1]) else 0
        if best is None or d < best[0]:
            best = (d, five)
    return best[1] if best else None


def run(plate, pg, box, reach=0.25, top_hint=None):
    left, right = LC.measure(plate, pg, box)
    cy = (box[1] + box[3]) / 2
    ref = cy if top_hint is None else top_hint
    sl, sr = staff_of(left, ref), staff_of(right, ref)
    five = sr or sl
    if sl and sr and abs(sl[0] - sr[0]) >= 5:
        five = min((sl, sr), key=lambda f: abs(f[0] - ref) if top_hint is not None else 0)
    if sl and sr and abs(sl[0] - sr[0]) < 5:
        five = [(a + b) / 2 for a, b in zip(sl, sr)]
    sp = float(np.mean(np.diff(five)))
    a = LC.page(plate, pg)
    g = a.mean(axis=2) if a.ndim == 3 else a
    ink = g < 128
    r = reach * sp
    grown = (box[0], box[1] - r, box[2], box[3] + r)
    holes = K.head_holes(ink, grown, sp, five[0], five)
    t = head_ink.trim_head(np.where(ink, 0, 255).astype(np.uint8), box, sp)
    tr = t.get("trimmed") if t else None
    inkpos = ((tr[1] + tr[3]) / 2 - five[0]) / (sp / 2) if tr is not None else None
    return dict(lines=[round(v, 1) for v in five], sp=round(sp, 2), box_pos=round((cy - five[0]) / (sp / 2), 2),
                holes=[(h["step"], h["pieces"], h["cy"], h["span_sp"], h["cut_dx_sp"], h["cut_off_sp"]) for h in holes], ink_pos=None if inkpos is None else round(inkpos, 2),
                ink=t and {k: t.get(k) for k in ("extent_sp", "not_one_head", "trimmed")})


if __name__ == "__main__":
    print(run(sys.argv[1], int(sys.argv[2]), [float(v) for v in sys.argv[3].split(",")], 0.25, *(float(v) for v in sys.argv[4:])))
