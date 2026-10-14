"""ROADMAP 2.115 truth measurement, BEFORE any gather: `gather.recentre_part_boxed` applied to every production notehead box on Sean's two truth pages
(page frame, 600 dpi, the unerased raster = the cell's `binary` up to scale), then the SAME interior reading `gather_notehead_ink` files
(`notehead_ink_under` raw centre, `notehead_ink_off_line` centre) on the box as drawn vs on the standard head box at the re-centred position.
Populations: Brahms 317803 pdf 0 = every production notehead box matching one of Sean's hand-truth heads (black / hollow);
Litolff 984073 idx 1 = the 95 CLEAN test cells (2.112 leak guard result: `leak_check.json`, 9 of 104 cells excluded), box matching Sean's hollow truth
= 'hollow'; every other production notehead box in those cells = 'other' (UNLABELLED: Sean boxed only hollow heads there).
"Reads hollow" = min(raw centre, off-line centre) <= 0.75 (rhythm.HEAD_FILL_HOLLOW_CENTER_MAX); "reads black" = both >= 0.85.
usage: measure_truth.py OUT.json"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "benchmarks/omr-head-recentre-2026-10")
import explore as X
from tools.omr.staged import gather as G

HOLLOW_MAX, BLACK_MIN = 0.75, 0.85

def reads(raw, b, sp):
    r = G.notehead_ink_under(raw, b); o = G.notehead_ink_off_line(raw, b, sp)
    return (None if r is None else r["windows"]["center"], None if o is None else o["windows"]["center"])

def state(rd):
    v = [x for x in rd if x is not None]
    if not v: return "unread"
    if min(v) <= HOLLOW_MAX: return "hollow"
    if min(v) >= BLACK_MIN: return "black"
    return "between"

def apply(raw, h):
    x0, y0, x1, y1 = h["box"]; sp = h["sp"]
    box = (x0, y0, x1 - x0, y1 - y0)
    before = reads(raw, box, sp)
    r = G.recentre_part_boxed(raw, box, sp)
    after = before
    if r and r["accepted"]:
        bx0, bx1, by0, by1 = G._standard_head_box((x0 + x1) / 2, (y0 + y1) / 2 + r["dy_sp"] * sp, sp)
        after = reads(raw, (bx0, by0, bx1 - bx0, by1 - by0), sp)
    return before, after, r

def table(heads, rast, label):
    rows = []
    for h in heads:
        before, after, r = apply(rast[h["page"]], h)
        rows.append(dict(key=h["key"], page=h["page"], label=h["label"], cls=h["cls"], box=h["box"], before=before, after=after,
                         moved=bool(r and r["accepted"]), reason=None if r is None else r["reason"],
                         dy=None if r is None else r.get("dy_sp"), shift_margin=None if r is None else r.get("shift_margin"),
                         size_margin=None if r is None else r.get("size_margin")))
    return rows

if __name__ == "__main__":
    hs, clean, n = X.heads()
    rast = {"brahms": X.raster(X.BRA, 0), "litolff": X.raster(X.LIT, 1)}
    rows = table(hs, rast, "default")
    Path(sys.argv[1]).write_text(json.dumps(rows))
    print("clean Litolff cells", len(clean), "truth hollow", n)
    for pg in ("brahms", "litolff"):
        for lab in ("black", "hollow", "other"):
            v = [r for r in rows if r["page"] == pg and r["label"] == lab]
            if not v: continue
            mv = [r for r in v if r["moved"]]
            sb = [state(r["before"]) for r in v]; sa = [state(r["after"]) for r in v]
            cnt = lambda s, k: sum(1 for x in s if x == k)
            flips = {}
            for a, b in zip(sb, sa):
                if a != b: flips[f"{a}->{b}"] = flips.get(f"{a}->{b}", 0) + 1
            print(f"{pg:8s} {lab:7s} heads {len(v):4d} re-centred {len(mv):3d} | before hollow/between/black {cnt(sb,'hollow')}/{cnt(sb,'between')}/{cnt(sb,'black')} "
                  f"-> after {cnt(sa,'hollow')}/{cnt(sa,'between')}/{cnt(sa,'black')} | changes {flips}")
