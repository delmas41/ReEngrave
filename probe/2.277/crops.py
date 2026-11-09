"""2.277: crops (for OUR look, not Sean's) of boxes by held class.  usage: crops.py PLATE DUMP.json OUTDIR [seed]"""
import collections, json, os, random, sys, pathlib
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from tools.omr.staged import lane_report as LR
from tools.omr.staged import stroke_owner as SO

plate, dump, out = sys.argv[1:4]
seed = int(sys.argv[4]) if len(sys.argv) > 4 else 7
D = json.load(open(dump))
sl = LR.slice_dir(plate, D["tag"])
bp = {}
for line in open(sl / "observations.jsonl"):
    if '"glyph_box"' in line[:200] or '"quantity": "glyph_box"' in line:
        o = json.loads(line)
        if o["quantity"] == "glyph_box":
            bp[o["subject"]] = (o["detail"] or {}).get("bbox_page_px")
EARLY = set(SO.AREA_OWNERS)
buckets = collections.defaultdict(list)
for r in D["rows"]:
    fam = SO.family_of(r["cls"], r.get("cat"))
    if fam not in ("head", "rest"):
        continue
    tot, by = 0.0, collections.Counter()
    for o, sh, cov, ink, kind, own in r["strokes"]:
        if ink is None:
            continue
        tot += ink * sh
        if own and own[0] in ("decided", "merged") and own[1] in EARLY and own[1] != fam:
            by[own[1]] += ink * sh
    if tot <= 0 or not by:
        continue
    f, w = by.most_common(1)[0]
    sh = w / tot
    if f not in ("barline", "arc_trace", "hairpin_trace"):
        continue
    owns = any(own and own[0] in ("decided", "merged") and own[1] == fam and cov for o, _s, cov, _i, _k, own in r["strokes"])
    fate = next(iter(r["fate"].values()), [None, None])
    kept = fate[0] is False
    cls = ("HELD>=.5" if sh >= .5 else "NEAR .25-.5" if sh >= .25 else "low")
    if cls == "low":
        continue
    buckets[(fam, f, cls, "owns" if owns else "noown", "kept" if kept else "refused")].append((r["sub"], round(sh, 2), fate[1]))
rng = random.Random(seed)
items, lab = [], []
for k, v in sorted(buckets.items()):
    print(k, len(v))
    for sub, sh, why in rng.sample(v, min(3, len(v))):
        if not bp.get(sub):
            continue
        p = sub.split("/")
        items.append(dict(plate=plate, page=int(p[1]), box=bp[sub], role="case", subject=sub, bucket=list(k), share=sh, reason=why))
outd = pathlib.Path(out)
outd.mkdir(parents=True, exist_ok=True)
print(LR.cut_tiles(items, outd))
for n, it in enumerate(items, 1):
    print(n, it["bucket"], it["share"], it["reason"])
