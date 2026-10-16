"""2.146 probe 2: read every truth stem FROM ITS TIP. Does a thick stroke leave the tip, how far, how many levels?
Truth class per stem from Sean's boxes: beamed (a beam box holds the tip), flagged (a flag box at the tip), bare."""
import json, sys
import numpy as np
exec(open(__file__.replace("tip_probe.py", "beam_probe_lib.py")).read())

flags = [R(b) for b in boxes if b["cls"].startswith("flag")]
beams = [R(b) for b in boxes if b["cls"] == "beam"]

def truth_kind(tx, ty, sp):
    for b in beams:
        if b[0] - 0.3 * sp <= tx <= b[2] + 0.3 * sp and b[1] - 0.3 * sp <= ty <= b[3] + 0.3 * sp: return "beamed"
    for f in flags:
        if f[0] - 0.5 * sp <= tx <= f[2] + 0.3 * sp and f[1] - 0.5 * sp <= ty <= f[3] + 0.5 * sp: return "flagged"
    return "bare"

def walk(tx, ty, head_below, sp, T, side):
    """follow a run at least T px thick from the stem column outward; return extent (sp) and levels at start."""
    sgn = 1 if side == "right" else -1
    lo, hi = (ty - 0.4 * sp, ty + 0.9 * sp) if head_below else (ty - 0.9 * sp, ty + 0.4 * sp)
    x = int(tx + sgn * 0.3 * sp)
    col = ink[int(lo):int(hi), x] if 0 <= x < ink.shape[1] else np.zeros(0, bool)
    cands = [(s + int(lo), e + int(lo)) for s, e in runs(col) if e - s >= T]
    if not cands: return 0.0, 0
    # nearest to the tip
    s, e = min(cands, key=lambda r: abs((r[0] + r[1]) / 2 - ty))
    c = (s + e) / 2; start = x; miss = 0; last = x
    while 0 <= x < ink.shape[1] and abs(x - tx) < 12 * sp:
        x += sgn * 2
        if not (0 <= x < ink.shape[1]): break
        y0, y1 = int(c - 0.6 * sp), int(c + 0.6 * sp)
        rr = [(a + y0, b + y0) for a, b in runs(ink[y0:y1, x]) if b - a >= T and a + y0 <= c <= b + y0]
        if rr:
            a, b = rr[0]
            if b - a < 2.5 * sp:      # not a stem/barline column: re-centre
                c = 0.7 * c + 0.3 * ((a + b) / 2)
            last = x; miss = 0
        else:
            miss += 2
            if miss > 0.25 * sp: break
    # levels: thick runs in the start column window
    levels = len(cands)
    return abs(last - start) / sp, levels

res = []
for s in stems:
    t = stem_tip(s)
    if not t: continue
    tx, ty = t
    sp, line = local_staff(tx, ty)
    if not sp: continue
    head_below = ty < (s[1] + s[3]) / 2 + 0 and ty == s[1]
    kind = truth_kind(tx, ty, sp)
    row = dict(kind=kind, sp=sp, line=line)
    for name, T in (("sp036", 0.36 * sp), ("sp040", 0.40 * sp), ("line175", 1.75 * line)):
        er, lr = walk(tx, ty, head_below, sp, T, "right")
        el, ll = walk(tx, ty, head_below, sp, T, "left")
        row[name] = dict(right=round(er, 2), left=round(el, 2), levels=max(lr, ll))
    res.append(row)
json.dump(res, open(sys.argv[1], "w"))
import collections
print("truth kinds", collections.Counter(r["kind"] for r in res))
for name in ("sp036", "sp040", "line175"):
    print("==", name)
    for k in ("beamed", "flagged", "bare"):
        rows = [r[name] for r in res if r["kind"] == k]
        ext = np.array([max(r["left"], r["right"]) for r in rows])
        print(f"  {k:8s} n={len(rows):3d} longest run from tip (sp): 0:{(ext==0).sum():3d} <1:{((ext>0)&(ext<1)).sum():3d} 1-1.5:{((ext>=1)&(ext<1.5)).sum():3d} >=1.5:{(ext>=1.5).sum():3d}  median {np.median(ext):.2f}")
