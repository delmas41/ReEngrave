"""ROADMAP 2.146 -- re-decide a SMALL record (STAGED, the record's own GATHER rows) with OMR_STEM_TIP_DECIDES_BEAM off and on,
then score every head of Sean's hand-truth page (Brahms 317803 pdf 0) whose duration CHANGED, plus the whole
beam_discounted_uncertain population, against his boxes: truth kind of the head's stem = beamed (a truth beam box holds
the stem's tip; levels = how many truth beam boxes do), flagged, or bare.
usage: replay_score_2_146.py RECORD.json PAGE_INDEX OUT.json"""
import json, os, sys
sys.path.insert(0, ".")
REC, PAGE, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
HT = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
rec = json.load(open(REC))
rec = rec.get("record", rec)
from tools.omr.staged.record import Q
from tools.omr.staged.review import rerun as RR

def R(b):
    x0, y0, x1, y1 = b["rect"]; return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
T = [dict(cls=b["cls"], r=R(b)) for b in HT["boxes"]]
heads = [t for t in T if t["cls"].startswith("notehead")]
stems = [t["r"] for t in T if t["cls"] == "stem"]
beams = [t["r"] for t in T if t["cls"] == "beam"]
flags = [t["r"] for t in T if t["cls"].startswith("flag")]
SP = 32.0

def ov(a, b, pad=0):
    return min(a[2], b[2]) + pad > max(a[0], b[0]) and min(a[3], b[3]) + pad > max(a[1], b[1])

def truth_for(hr):
    """kind and beam count of the truth stem touching truth head box hr."""
    best = None
    for s in stems:
        if s[0] - 12 <= hr[2] and s[2] + 12 >= hr[0] and s[1] - 12 <= hr[3] and s[3] + 12 >= hr[1]:
            best = s; break
    if best is None: return "no_stem", 0
    xc = (best[0] + best[2]) / 2
    up = abs(best[3] - (hr[1] + hr[3]) / 2) < abs(best[1] - (hr[1] + hr[3]) / 2)  # head at the bottom -> stem up
    ty = best[1] if up else best[3]
    n = sum(1 for b in beams if b[0] - 0.3 * SP <= xc <= b[2] + 0.3 * SP and b[1] - 0.6 * SP <= ty <= b[3] + 0.6 * SP)
    if n: return "beamed", n
    for f in flags:
        if f[0] - 0.5 * SP <= xc <= f[2] + 0.3 * SP and f[1] - 0.5 * SP <= ty <= f[3] + 0.5 * SP: return "flagged", 1
    return "bare", 0

res = {}
boxes = {}
for o in rec["observations"]:
    if o["quantity"] == Q.GLYPH_BOX and o["subject"].startswith("glyph/%d/" % PAGE):
        bb = (o.get("detail") or {}).get("bbox_page_px")
        if bb: boxes[o["subject"]] = bb
for arm, env in (("off", ""), ("on", "1")):
    os.environ["OMR_STEM_TIP_DECIDES_BEAM"] = env
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    d = log.to_json()
    sup = {v["supersedes"] for v in d["verdicts"] if v.get("supersedes")}
    adj = {}
    for v in d["verdicts"]:
        if v["quantity"] == Q.DURATION and v["subject"].startswith("glyph/%d/" % PAGE) and v.get("decider", "").endswith("adjudicate_duration"):
            val = v["value"]
            if isinstance(val, dict): val = val.get("beam_levels")
            adj[v["subject"]] = [v["outcome"], val, v["reason"]]
    res[arm] = adj
    print(arm, len(adj), flush=True)

rows = []
for g in sorted(set(res["off"]) | set(res["on"])):
    off, on = res["off"].get(g), res["on"].get(g)
    if not (off and (off[2] == "beam_discounted_uncertain" or off != on)): continue
    bb = boxes.get(g)
    th = [h for h in heads if bb and ov(h["r"], bb)]
    kind, n = truth_for(th[0]["r"]) if th else ("no_truth_head", 0)
    rows.append(dict(glyph=g, bbox=bb, off=off, on=on, truth=kind, truth_levels=n))
json.dump(rows, open(OUT, "w"), indent=0)
import collections
c = collections.Counter()
for r in rows:
    on = r["on"]
    if on[2] in ("stem_tip_reads_no_beam", "stem_tip_reads_a_beam"):
        said = "beamed" if on[1] else "not beamed"
        right = (said == "beamed") == (r["truth"] == "beamed") if r["truth"] in ("beamed", "bare", "flagged") else None
        c[(on[2], r["truth"], "right" if right else ("WRONG" if right is False else "?"))] += 1
    else:
        c[("still " + on[2], r["truth"], "")] += 1
for k, v in sorted(c.items()): print(v, k)
