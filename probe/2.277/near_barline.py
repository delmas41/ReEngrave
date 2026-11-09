"""2.277: kept head boxes at barline share 0.3-0.5 (Sean's look 24/25/26 false, 27 real): how many, how many reach the file, and a seeded sample of 12 as tiles.
usage: near_barline.py PLATE DUMP.json SYMBOLS.json OUTDIR [seed] [lo hi]"""
import json, os, pathlib, random, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from tools.omr.staged import lane_report as LR
from tools.omr.staged import stroke_owner as SO

plate, dump, symf, out = sys.argv[1:5]
seed = int(sys.argv[5]) if len(sys.argv) > 5 else 2277
lo, hi = (float(sys.argv[6]), float(sys.argv[7])) if len(sys.argv) > 7 else (0.3, 0.5)
D = json.load(open(dump))
S = json.load(open(symf))
written = {h.get("rg") for h in S["hosts"] if h.get("rg")}
hosts_by_page = {}
for h in S["hosts"]:
    hosts_by_page.setdefault(h["page"], []).append(h)
bp = {}
for line in open(LR.slice_dir(plate, D["tag"]) / "observations.jsonl"):
    if '"glyph_box"' in line[:300]:
        o = json.loads(line)
        if o["quantity"] == "glyph_box":
            bp[o["subject"]] = o["detail"]["bbox_page_px"]
cand = []
for r in D["rows"]:
    if SO.family_of(r["cls"], r.get("cat")) != "head":
        continue
    tot = held = 0.0
    for o, sh, cov, ink, k, own in r["strokes"]:
        if not ink:
            continue
        tot += ink * sh
        if own and own[0] in ("decided", "merged") and own[1] == "barline":
            held += ink * sh
    if not tot or not (lo <= held / tot < hi):
        continue
    f = next(iter(r["fate"].values()), [None, None])
    if f[0] is not False:
        continue
    b = bp.get(r["sub"])
    reach = r["sub"] in written
    if not reach and b:   # a chord host names one glyph: a host whose box overlaps this box's centre also counts
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        reach = any(h["box"][0] - 3 <= cx <= h["box"][2] + 3 and h["box"][1] - 3 <= cy <= h["box"][3] + 3 for h in hosts_by_page.get(int(r["sub"].split("/")[1]), []) if h.get("box"))
    cand.append((r["sub"], round(held / tot, 2), reach, b))
print("kept head boxes at barline share %.2f-%.2f: %d; reach the file: %d" % (lo, hi, len(cand), sum(1 for c in cand if c[2])))
items = []
for sub, sh, reach, b in random.Random(seed).sample(cand, min(12, len(cand))):
    if b:
        items.append(dict(plate=plate, page=int(sub.split("/")[1]), box=b, role="case", subject=sub, share=sh, reaches_file=reach))
if items:
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    print(LR.cut_tiles(items, pathlib.Path(out)))
