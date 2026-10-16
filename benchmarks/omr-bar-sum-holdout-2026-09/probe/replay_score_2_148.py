"""ROADMAP 2.148 -- re-decide a SMALL record (STAGED, its own GATHER rows, which carry `interior_white` only when gathered
on a tree with 2.148) with OMR_HEAD_FILL_FIRST off and on; list every head whose ADJUDICATE duration changed, and, on Sean's
hand-truth page (Brahms 317803 pdf 0), score head fill against his boxes in BOTH directions.
usage: replay_score_2_148.py RECORD.json PAGE OUT.json [--truth]"""
import json, os, sys, collections
sys.path.insert(0, ".")
REC, PAGE, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
TRUTH = "--truth" in sys.argv
rec = json.load(open(REC)); rec = rec.get("record", rec)
from tools.omr.staged.record import Q
from tools.omr.staged.review import rerun as RR

boxes, iw = {}, {}
for o in rec["observations"]:
    if not o["subject"].startswith("glyph/%d/" % PAGE): continue
    if o["quantity"] == Q.GLYPH_BOX:
        bb = (o.get("detail") or {}).get("bbox_page_px")
        if bb: boxes[o["subject"]] = bb
    elif o["quantity"] == Q.NOTEHEAD_INK:
        iw[o["subject"]] = (o.get("detail") or {}).get("interior_white")
res = {}
for arm, env in (("off", ""), ("on", "1")):
    os.environ["OMR_HEAD_FILL_FIRST"] = env
    log, _ = RR.rebuild_gather(rec); RR.run_stages(log)
    d = log.to_json(); adj = {}
    for v in d["verdicts"]:
        if v["quantity"] == Q.DURATION and v["subject"].startswith("glyph/%d/" % PAGE) and v.get("decider", "").endswith("adjudicate_duration"):
            val = v["value"]
            w = val.get("written") if isinstance(val, dict) else None
            if v["outcome"] == "narrowed":
                w = "|".join(str(c.get("value", {}).get("written")) for c in (v.get("candidates") or []))
            adj[v["subject"]] = [v["outcome"], w, v["reason"], ((v.get("detail") or {}).get("head_fill_first") or {}).get("settled")]
    res[arm] = adj
rows = []
for g in sorted(set(res["off"]) | set(res["on"])):
    off, on = res["off"].get(g), res["on"].get(g)
    rows.append(dict(glyph=g, bbox=boxes.get(g), off=off, on=on, interior=iw.get(g)))
changed = [r for r in rows if r["off"] != r["on"]]
print("heads", len(rows), "changed", len(changed), collections.Counter((r["off"] and r["off"][1], r["on"] and r["on"][1], r["on"] and r["on"][3]) for r in changed).most_common(8))
if TRUTH:
    HT = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
    th = []
    for b in HT["boxes"]:
        if b["cls"].startswith("notehead"):
            x0, y0, x1, y1 = b["rect"]; th.append((b["cls"], (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))))
    def truth(bb):
        best = None
        for c, r in th:
            ix = min(r[2], bb[2]) - max(r[0], bb[0]); iy = min(r[3], bb[3]) - max(r[1], bb[1])
            if ix > 0 and iy > 0 and (best is None or ix * iy > best[0]): best = (ix * iy, c)
        return None if best is None else ("black" if "Black" in best[1] else "hollow")
    sc = collections.Counter()
    for r in rows:
        if not r["bbox"]: continue
        t = truth(r["bbox"])
        if t is None: continue
        r["truth"] = t
        for arm in ("off", "on"):
            v = r[arm]
            if not v or v[0] != "decided" or not isinstance(v[1], (int, float)): continue
            ours = "hollow" if v[1] >= 2.0 or (v[1] == 3.0) else "black"
            sc[(arm, t, ours)] += 1
    for k in sorted(sc): print("  ", k, sc[k])
    iws = collections.defaultdict(list)
    for r in rows:
        if r.get("truth") and r["interior"]: iws[r["truth"]].append(r["interior"]["rows_share"])
    for k, v in iws.items():
        import numpy as np; v = np.array(v); print("  interior rows_share on the cell raster,", k, len(v), "min/p50/max", v.min(), np.median(v), v.max())
json.dump(rows, open(OUT, "w"), indent=0, default=str)
