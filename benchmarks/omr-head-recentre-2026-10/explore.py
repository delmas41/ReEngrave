"""2.115 exploration: for every production notehead box on Sean's truth pages, how big is it vs a standard head, and what does the UNGATED 2.39b
matched-window search (gather.recentre_notehead on the staff-line-erased raster) say. Page frame 600 dpi. usage: explore.py OUT.json"""
import collections, json, statistics, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, ".")
HERE = Path("benchmarks/omr-head-recentre-2026-10")
sys.path.insert(0, str(HERE))
from tools.omr.preprocessing import render_page
from tools.omr.hand_truth import store as ST
from tools.omr.staged import readout as RO
from tools.omr.staged import gather as G
from tools.omr.staged.geometry import STANDARD_HEAD_WIDTH_SPACES as SW, STANDARD_HEAD_HEIGHT_SPACES as SH_
import importlib.util
sp_ = importlib.util.spec_from_file_location("score_ab", "benchmarks/omr-labeling-hollow4-2026-10/score_ab.py"); S = importlib.util.module_from_spec(sp_); sp_.loader.exec_module(S)
LIT = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
BRA = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"

def raster(pdf, pg):
    g = render_page(Path(pdf), pg, dpi=600).rgb
    g = g if g.ndim == 2 else g[..., :3].mean(axis=2)
    return np.where(g < 128, 0, 255).astype(np.uint8)

def erase_lines(img, sp):
    ink = img == 0
    out = ink.copy()
    minrun = int(2.5 * sp)
    for y in range(ink.shape[0]):
        row = ink[y]
        if not row.any(): continue
        d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
        for s, e in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if e - s >= minrun: out[y, s:e] = False
    return np.where(out, 0, 255).astype(np.uint8)

def leaked():
    d = json.loads((HERE / "leak_check.json").read_text()); out = set()
    for name in d["litolff"]["key_cells"]:
        s, st, m = name.split("/")[1].replace("s", "", 1).replace("st", "").replace("m", "").split("-")
        out.add((int(s), int(st), int(m)))
    return out

def sp_of(run):
    return statistics.median([float(o["value"]) for o in run.observations if o["quantity"] == "staff_spacing"])

def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    if i <= 0: return 0.0
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i)

def same_page(t, r):
    if iou(t, r) >= 0.3: return True
    cx, cy = (t[0]+t[2])/2, (t[1]+t[3])/2
    return r[0] <= cx <= r[2] and r[1] <= cy <= r[3]

def heads():
    """dict(page, label, key, box(page x0y0x1y1), sp)"""
    out = []
    # Brahms: production boxes labelled by Sean's hand truth
    img = raster(BRA, 0); run = RO.load_run("runs/2.114/ab/rec-bra-off.json"); sp = sp_of(run)
    page = ST.load(Path("data/hand-truth/pages/imslp317803/0.json"))
    tb = [("hollow" if b.cls.startswith(("noteheadHalf", "noteheadWhole")) else "black", tuple(b.rect)) for b in page.boxes
          if b.cls.startswith(("noteheadHalf", "noteheadWhole", "noteheadBlack"))]
    for g in run.glyphs.values():
        if g.page != 0 or not (g.cls or "").startswith("notehead") or g.box_page is None: continue
        r = tuple(g.box_page); lab = None
        for l, t in tb:
            if same_page(t, r): lab = l; break
        if lab is None: continue
        d = dict(page="brahms", label=lab, key=g.key, cls=g.cls, box=list(r), sp=sp)
        d["truth_box"] = list([t for l, t in tb if l == lab and same_page(t, r)][0])
        out.append(d)
    # Litolff idx1: clean test cells; hollow = production box matched to a truth hollow head; black = production black box matching none
    cellmeta = {(c["system_index"], c["staff_index"], c["measure_index"]): c for c in json.loads(Path("runs/2.114/test-cells/litolff984073_p1/cells.json").read_text())}
    def to_page(k, r):
        c = cellmeta[k]; up = c["w"] / float(c["bbox_page_px"][2] - c["bbox_page_px"][0])
        return (c["bbox_page_px"][0] + r[0] / up, c["bbox_page_px"][1] + r[1] / up, c["bbox_page_px"][0] + r[2] / up, c["bbox_page_px"][1] + r[3] / up)
    lk = leaked(); truth, n, cellset = S.litolff_truth(); clean = {k for k in cellset if k not in lk}
    run = RO.load_run("runs/2.114/ab/rec-lit-off.json"); sp = sp_of(run)
    for g in run.glyphs.values():
        k = (g.system, g.staff, g.cell)
        if g.page != 1 or k not in clean or not (g.cls or "").startswith("notehead") or g.box_canon is None: continue
        tm = [t for t in truth.get(k, []) if S.same(t, g.box_canon)]
        lab = "hollow" if tm else "other"
        d = dict(page="litolff", label=lab, key=g.key, cls=g.cls, box=list(g.box_page), sp=sp)
        if tm: d["truth_box"] = list(to_page(k, tm[0]))
        out.append(d)
    return out, clean, n

if __name__ == "__main__":
    hs, clean, n = heads()
    print("heads", collections.Counter((h["page"], h["label"]) for h in hs), "litolff clean cells", len(clean), "truth hollow", n)
    rast = {"brahms": raster(BRA, 0), "litolff": raster(LIT, 1)}
    erased = {}
    res = []
    for h in hs:
        p = h["page"]; sp = h["sp"]
        if p not in erased: erased[p] = erase_lines(rast[p], sp)
        x0, y0, x1, y1 = h["box"]; cx, cy = (x0+x1)/2, (y0+y1)/2
        wr = (x1-x0) / (SW*sp); hr = (y1-y0) / (SH_*sp)
        r = G.recentre_notehead(erased[p], cx, cy, sp)
        h.update(wr=round(wr, 3), hr=round(hr, 3), search=r)
        res.append(h)
    Path(sys.argv[1]).write_text(json.dumps(res))
