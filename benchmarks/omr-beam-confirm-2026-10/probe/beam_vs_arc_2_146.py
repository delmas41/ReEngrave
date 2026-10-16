"""2.146 probe: on Sean's hand-truth Brahms 317803 pdf 0, measure beams vs slurs vs ties.
(a) stroke thickness in staff spaces AND in staff-line thicknesses (local);
(b) stem-tip contact: how many truth stems' TIPS touch the stroke's ink.
Truth = Sean's boxes; raster = the PDF page at 600 dpi, ink < 180."""
import json, sys
import numpy as np
import fitz

ROOT = "/Users/seanjohnson/Desktop/ReEngrave"
PDF = ROOT + "/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
HT = json.load(open(ROOT + "/data/hand-truth/pages/imslp317803/0.json"))

doc = fitz.open(PDF)
pix = doc[0].get_pixmap(dpi=600, alpha=False, colorspace=fitz.csGRAY)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
ink = img < 180
print("raster", ink.shape, "truth", HT["height"], file=sys.stderr)

boxes = HT["boxes"]
def R(b):
    x0, y0, x1, y1 = b["rect"]; return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

def runs(col):
    d = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
    s = np.where(d == 1)[0]; e = np.where(d == -1)[0]
    return list(zip(s, e))

def local_staff(xc, yc, half=150):
    """staff space and line thickness from vertical run lengths in a window around (xc, yc)."""
    x0, x1 = int(max(0, xc - half)), int(min(ink.shape[1], xc + half))
    y0, y1 = int(max(0, yc - 400)), int(min(ink.shape[0], yc + 400))
    blk, wht = [], []
    for x in range(x0, x1, 3):
        col = ink[y0:y1, x]
        rs = runs(col)
        for (s, e) in rs: blk.append(e - s)
        for (a, b) in zip(rs, rs[1:]): wht.append(b[0] - a[1])
    blk = np.array([v for v in blk if 2 <= v <= 30]); wht = np.array([v for v in wht if 20 <= v <= 120])
    if not len(blk) or not len(wht): return None, None
    line = np.bincount(blk).argmax(); gap = np.bincount(wht).argmax()
    return float(gap + line), float(line)   # staff space = line pitch

heads = [R(b) for b in boxes if b["cls"].startswith("notehead")]
stems = [R(b) for b in boxes if b["cls"] == "stem"]

def stem_tip(s):
    x0, y0, x1, y1 = s; xc = (x0 + x1) / 2
    def near(y):
        return any(h[0] - 15 <= xc <= h[2] + 15 and h[1] - 25 <= y <= h[3] + 25 for h in heads)
    top_head, bot_head = near(y0), near(y1)
    if bot_head and not top_head: return xc, y0
    if top_head and not bot_head: return xc, y1
    return None

tips = [t for t in (stem_tip(s) for s in stems) if t]
print("stems", len(stems), "with a tip", len(tips), file=sys.stderr)

def measure(b):
    x0, y0, x1, y1 = R(b)
    sp, line = local_staff((x0 + x1) / 2, (y0 + y1) / 2)
    if not sp: return None
    xs = range(int(x0 + 0.2 * (x1 - x0)), int(x1 - 0.2 * (x1 - x0)) + 1)
    th = []
    for x in xs:
        col = ink[int(y0):int(y1) + 1, x]
        rs = [e - s for s, e in runs(col)]
        if rs: th.append(max(rs))
    if not th: return None
    t = float(np.median(th))
    # stem tips touching the stroke: tip inside the box's x span, and stroke ink within 0.25 sp of the tip
    # in the columns just beside the stem (stem x +/- 0.3..0.5 sp)
    touch = 0; near_tip = 0
    for (tx, ty) in tips:
        if not (x0 - 0.3 * sp <= tx <= x1 + 0.3 * sp and y0 - sp <= ty <= y1 + sp): continue
        near_tip += 1
        hit = False
        for dx in (-0.45 * sp, 0.45 * sp):
            x = int(tx + dx)
            if not (0 <= x < ink.shape[1]): continue
            ya, yb = int(ty - 0.3 * sp), int(ty + 0.3 * sp)
            if ink[ya:yb, x].any() and x0 - 2 <= x <= x1 + 2: hit = True
        touch += hit
    return dict(cls=b["cls"], id=b["id"], sp=sp, line=line, thick_px=t, thick_sp=t / sp, thick_lines=t / line,
                width_sp=(x1 - x0) / sp, tips_in_box=near_tip, tips_touching=touch)

out = []
for b in boxes:
    if b["cls"] in ("beam", "slur", "tie"):
        m = measure(b)
        if m: out.append(m)
json.dump(out, open(sys.argv[1], "w"), indent=0)
import collections
for c in ("beam", "slur", "tie"):
    rows = [r for r in out if r["cls"] == c]
    if not rows: continue
    ts = np.array([r["thick_sp"] for r in rows]); tl = np.array([r["thick_lines"] for r in rows])
    tt = np.array([r["tips_touching"] for r in rows])
    print(f"{c:5s} n={len(rows):3d}  thick_sp p10/50/90 {np.percentile(ts,10):.2f}/{np.median(ts):.2f}/{np.percentile(ts,90):.2f}"
          f"  thick_lines p10/50/90 {np.percentile(tl,10):.2f}/{np.median(tl):.2f}/{np.percentile(tl,90):.2f}"
          f"  stem tips touching: 0:{(tt==0).sum()} 1:{(tt==1).sum()} >=2:{(tt>=2).sum()}")
sps = [r["sp"] for r in out]; lines = [r["line"] for r in out]
print("staff space px p10/50/90", np.percentile(sps, [10, 50, 90]), " line px", np.percentile(lines, [10, 50, 90]))
