"""2.4b reverse graft: per-class glyph (detector box) counts per record, whole Litolff p1 and Brahms p0.
  python3 class_counts.py label=lit.json:bra.json ...   [--out counts.json]   (classes canonical-folded: trailing OnLine/InSpace etc kept as is)"""
import argparse, collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from tools.omr.staged import readout as RO

def counts(path, page):
    run = RO.load_run(path)
    c = collections.Counter()
    for g in run.glyphs.values():
        if g.page == page and (g.cls or ""):
            c[g.cls] += 1
    return c

ap = argparse.ArgumentParser(); ap.add_argument("arms", nargs="+"); ap.add_argument("--out", type=Path)
ap.add_argument("--base", default="production"); a = ap.parse_args()
res = {}
for s in a.arms:
    lab, p = s.split("=", 1); lit, bra = p.split(":")
    res[lab] = {"lit": counts(lit, 1), "bra": counts(bra, 0)}
base = res[a.base]
allc = sorted({k for r in res.values() for pg in r.values() for k in pg})
if a.out: a.out.write_text(json.dumps({l: {pg: dict(c) for pg, c in r.items()} for l, r in res.items()}, indent=0))
for pg in ("lit", "bra"):
    print(f"--- {pg}"); labs = list(res)
    print("%-28s" % "class" + "".join("%12s" % l[:11] for l in labs))
    for k in allc:
        b = base[pg][k]
        if b < 5 and max(res[l][pg][k] for l in labs) < 5: continue
        print("%-28s" % k + "".join("%12s" % (res[l][pg][k] if l == a.base else f"{res[l][pg][k]} ({100*(res[l][pg][k]-b)/max(b,1):+.0f}%)") for l in labs))
