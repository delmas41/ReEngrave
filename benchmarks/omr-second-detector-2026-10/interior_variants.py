"""2.114 round 2, Sean's idea (2026-10-14): "move the percentage up to it needing 90% ink inside for a black notehead and anything less is a
hollow head". MEASURED ON TRUTH, wired nowhere. Page-raster frame (600 dpi, threshold 128), per head the interior (centre window, 30% shrink) ink:
  (a) the current 2.88 window: on the box as given (Sean's truth box for a hollow head, Brahms black truth box, a production black box on Litolff)
  (b) the window re-centred on the head's own ink: a standard head box (1.4 x 1.1 sp) placed by `gather.recentre_notehead`'s matched-window
      search (staff-line runs >= 2.5 sp erased first, as `image_no_staff` is), start = the box centre, NO size gate; its centre window read on the RAW raster
  (c) (b)'s box with the local staff-line rows left out (2.73 `notehead_ink_off_line`)
Heads: Brahms 317803 pdf 0 Sean's hand truth (black = noteheadBlack*, hollow = noteheadHalf*/Whole*); Litolff 984073 idx 1: the 95 clean TEST cells'
hand-truth hollow boxes, and as "black" every PRODUCTION (OFF record) black head box in those cells that no truth hollow box matches (a soft label:
Sean boxed only hollow heads there, so an unlabelled hollow head or a tremolo slash would sit in this set; the closest calls are cropped).
usage: interior_variants.py OUT.json"""
import collections, json, statistics, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.hand_truth import store as ST
from tools.omr.staged import readout as RO
from tools.omr.staged import gather as G
HERE = Path("benchmarks/omr-second-detector-2026-10")
sys.path.insert(0, str(HERE))
import importlib.util
sp_ = importlib.util.spec_from_file_location("score_ab", "benchmarks/omr-labeling-hollow4-2026-10/score_ab.py"); S = importlib.util.module_from_spec(sp_); sp_.loader.exec_module(S)
LIT = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
BRA = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
SH = G.NOTEHEAD_INK_CENTER_SHRINK

def raster(pdf, pg):
    g = render_page(Path(pdf), pg, dpi=600).rgb
    g = g if g.ndim == 2 else g[..., :3].mean(axis=2)
    return np.where(g < 128, 0, 255).astype(np.uint8)

def erase_lines(img, sp):
    """staff/ledger lines out: every horizontal ink run >= 2.5 sp long (a head is ~1.4 sp wide)."""
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

def read(img, noline, box, sp):
    """box (x0,y0,x1,y1) page px -> (a, b, c) interior fractions + the (b) box."""
    x0, y0, x1, y1 = box
    a = G.notehead_ink_under(img, (x0, y0, x1 - x0, y1 - y0))
    a = None if a is None else a["windows"]["center"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # recentre on a window of the erased raster (a local crop keeps the search cheap)
    r = G.recentre_notehead(noline, cx, cy, sp)
    if r is None or r["fill"] <= 0:
        return a, None, None, None
    ncx, ncy = cx + r["dx_sp"] * sp, cy + r["dy_sp"] * sp
    bx0, bx1, by0, by1 = G._standard_head_box(ncx, ncy, sp)
    bb = (bx0, by0, bx1 - bx0, by1 - by0)
    b = G.notehead_ink_under(img, bb)
    c = G.notehead_ink_off_line(img, bb, sp)
    return a, (None if b is None else b["windows"]["center"]), (None if c is None else c["windows"]["center"]), bb

def collect():
    items = []     # dict(page, label, key, box, a, b, c)
    # ---- Brahms
    img = raster(BRA, 0)
    run = RO.load_run("runs/2.114/ab/rec-bra-off.json")
    sp = statistics.median([float(o["value"]) for o in run.observations if o["quantity"] == "staff_spacing"])
    noline = erase_lines(img, sp)
    page = ST.load(Path("data/hand-truth/pages/imslp317803/0.json"))
    for b in page.boxes:
        lab = "hollow" if b.cls.startswith(("noteheadHalf", "noteheadWhole")) else "black" if b.cls.startswith("noteheadBlack") else None
        if lab is None: continue
        a, bb, cc, box = read(img, noline, tuple(b.rect), sp)
        items.append(dict(page="brahms", label=lab, key=f"{b.cls}@{[round(v) for v in b.rect]}", box=list(b.rect), a=a, b=bb, c=cc, bbox=box))
    # ---- Litolff clean 95
    import score_second as SS
    leak = SS.leaked_cells()
    truth, n, cellset = S.litolff_truth()
    clean = {k for k in cellset if k not in leak}
    cells = {(c["system_index"], c["staff_index"], c["measure_index"]): c for c in json.loads(Path("runs/2.114/test-cells/litolff984073_p1/cells.json").read_text())}
    img = raster(LIT, 1)
    run = RO.load_run("runs/2.114/ab/rec-lit-off.json")
    sp = statistics.median([float(o["value"]) for o in run.observations if o["quantity"] == "staff_spacing"])
    noline = erase_lines(img, sp)
    # scale check against production glyphs: canonical -> page must reproduce a glyph's own page box
    bad = 0
    byc = collections.defaultdict(list)
    for g in run.glyphs.values():
        if g.page == 1 and g.box_page and g.box_canon: byc[(g.system, g.staff, g.cell)].append(g)
    def to_page(k, r):
        c = cells[k]; up = c["w"] / float(c["bbox_page_px"][2] - c["bbox_page_px"][0])
        return (c["bbox_page_px"][0] + r[0] / up, c["bbox_page_px"][1] + r[1] / up, c["bbox_page_px"][0] + r[2] / up, c["bbox_page_px"][1] + r[3] / up)
    chk = []
    for k in list(clean)[:30]:
        for g in byc.get(k, [])[:2]:
            p = to_page(k, g.box_canon); chk.append(max(abs(p[i] - g.box_page[i]) for i in range(4)))
    print("canonical->page max abs error over", len(chk), "glyph boxes: median %.1f px, max %.1f px" % (statistics.median(chk), max(chk)))
    for k in sorted(clean):
        for t in truth.get(k, []):
            box = to_page(k, t)
            a, bb, cc, bx = read(img, noline, box, sp)
            items.append(dict(page="litolff", label="hollow", key=f"truth{k}@{[round(v) for v in box]}", box=list(box), a=a, b=bb, c=cc, bbox=bx))
        for g in byc.get(k, []):
            if (g.cls or "").startswith("noteheadBlack") and not any(S.same(t, g.box_canon) for t in truth.get(k, [])):
                a, bb, cc, bx = read(img, noline, g.box_page, sp)
                items.append(dict(page="litolff", label="black", key=g.key, box=list(g.box_page), a=a, b=bb, c=cc, bbox=bx))
    return items

def stats(v):
    v = np.array(v, float)
    if not len(v): return None
    return dict(n=len(v), min=round(float(v.min()), 2), p5=round(float(np.percentile(v, 5)), 2), median=round(float(np.median(v)), 2),
                p95=round(float(np.percentile(v, 95)), 2), max=round(float(v.max()), 2))

def best_cut(bl, ho):
    """cut c: black if v >= c, hollow if v < c. Minimise errors; ties -> widest gap."""
    cand = sorted(set(round(x, 3) for x in bl + ho))
    cuts = [(a + b) / 2 for a, b in zip(cand, cand[1:])] + [0.9]
    best = None
    for c in cuts:
        err = sum(1 for x in bl if x < c) + sum(1 for x in ho if x >= c)
        below = [x for x in ho if x < c]; above = [x for x in bl if x >= c]
        gap = (min(above) if above else 1.0) - (max(below) if below else 0.0)
        key = (err, -gap)
        if best is None or key < best[0]: best = (key, c, err, gap)
    return dict(cut=round(best[1], 3), errors=best[2], gap=round(best[3], 3))

if __name__ == "__main__":
    items = collect()
    res = {"items": items, "summary": {}}
    for pg in ("brahms", "litolff", "both"):
        for var in ("a", "b", "c"):
            sub = [i for i in items if (pg == "both" or i["page"] == pg) and i[var] is not None]
            bl = [i[var] for i in sub if i["label"] == "black"]; ho = [i[var] for i in sub if i["label"] == "hollow"]
            miss = sum(1 for i in items if (pg == "both" or i["page"] == pg) and i[var] is None)
            res["summary"][f"{pg}/{var}"] = dict(black=stats(bl), hollow=stats(ho), unread=miss,
                black_flip_at_090=sum(1 for x in bl if x < 0.9), black_n=len(bl),
                hollow_stay_black_at_090=sum(1 for x in ho if x >= 0.9), hollow_n=len(ho),
                best=best_cut(bl, ho) if bl and ho else None)
    Path(sys.argv[1]).write_text(json.dumps(res, indent=1))
    for k, v in res["summary"].items():
        print(k, json.dumps(v))
