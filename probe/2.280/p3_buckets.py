"""2.280 probe 3: one first cause per head of p2_rerun.py's output (2.167 p2b_causes.py rules, same words, extended).
Order (first match):
  ii  stem FOUND (a Q.STEM row of the cell) beside/above/below the box but the contact test fails
  i   a run beside the head REFUSED by the finder: PAIRED / WIDE / TALL / SHORT / EDGE / AREA / ASPECT
  i   ink run >= 1.5 sp beside the head that was never a candidate  (split: on the ERASED image too / only on the ORIGINAL image = fused to a staff line)
  0   no vertical ink beside the head
Then, INDEPENDENT of the cause: do the PAGE strokes (Q.PAGE_STROKE) / head_stem_reach hold a vertical stroke beside the head that the head never consults?
usage: python3 probe/2.280/p3_buckets.py RERUN.json [OUT.json]"""
import collections
import json
import sys

R = json.load(open(sys.argv[1]))
SHORT = {"PAIRED": "PAIRED", "TOO TALL": "TALL", "TOO WIDE": "WIDE", "TOO SHORT": "SHORT", "CELL EDGE": "EDGE", "AREA": "AREA", "ASPECT": "ASPECT"}


def short(outcome):
    o = outcome.upper()
    for k, v in SHORT.items():
        if k in o:
            return v
    return outcome[:20]


def cause(r):
    if "error" in r:
        return "ERR cell match"
    for n in r["stems_near"]:
        if not n["touches"] and n["dy_sp"] == 0 and n["dx_sp"] <= 0.5:
            return "ii  stem FOUND beside the box; contact fails"
    for n in r["stems_near"]:
        if not n["touches"] and n["dx_sp"] == 0 and n["dy_sp"] <= 0.5:
            return "ii  stem FOUND above/below the box; contact fails"
    for n in r["refused_near"]:
        if n["outcome"] != "accepted" and n["dx_sp"] <= 0.35 and n["dy_sp"] == 0 and n["h_sp"] >= 1.5:
            return "i   run REFUSED: " + short(n["outcome"])
    rr = r["raw_runs"]
    e = max((v["len_sp"] for k, v in rr.items() if k.startswith("erased")), default=0)
    o = max((v["len_sp"] for k, v in rr.items() if k.startswith("original")), default=0)
    if e >= 1.5:
        return "i   ink run never a candidate (erased image)"
    if o >= 1.5:
        return "i   ink run only on the ORIGINAL image (fused to a staff line)"
    return "0   no vertical ink >= 1.5 sp beside the head"


def page_stroke(r):
    """The page strokes beside the head: a vertical stroke >= 1.5 sp whose x is within 0.6 sp of the head and that reaches >= 1 sp beyond it."""
    best = None
    for p in r.get("page_strokes", []):
        ln = p["len_sp"] or 0
        ext = max(p["ext_up_sp"], p["ext_dn_sp"])
        if p["dx_sp"] <= 0.6 and ext >= 1.0:
            if p["kind"] == "vertical" and ln >= 1.5:
                return "page VERTICAL stroke beside the head (len %.1f sp, reaches %.1f sp)" % (ln, ext), p
            if p["kind"] in ("blob", "barline") and best is None:
                best = ("page %s stroke reaching %.1f sp beyond the head" % (p["kind"].upper(), ext), p)
    return best if best else ("no page stroke reaching beyond the head", None)


tot = collections.Counter()
out = {}
for st in ("A", "B"):
    c, cp = collections.Counter(), collections.Counter()
    x = collections.Counter()
    for s, r in sorted(R.items()):
        if r.get("stratum") != st:
            continue
        cs = cause(r)
        ps, pobj = page_stroke(r)
        reach = r.get("reach") or {}
        rch = max(reach.get("up_ext") or 0, reach.get("down_ext") or 0)
        out[s] = dict(stratum=st, cause=cs, page=ps.split(" (")[0], reach_sp=round(rch, 2))
        c[cs] += 1
        cp[ps.split(" (")[0]] += 1
        x[(cs[:3].strip(), "page stroke" if ps.startswith("page VERT") else "-")] += 1
    print("== stratum %s (%s) n=%d" % (st, "narrowed" if st == "A" else "decided with no stem row", sum(c.values())))
    for k, v in sorted(c.items()):
        print("  %3d %s" % (v, k))
    print("  -- page strokes (value computed, never read by the head):")
    for k, v in sorted(cp.items()):
        print("  %3d %s" % (v, k))
    rr = sum(1 for s, o in out.items() if o["stratum"] == st and o["reach_sp"] >= 1.5)
    print("  head_stem_reach >= 1.5 sp (up or down): %d" % rr)
if len(sys.argv) > 2:
    json.dump(out, open(sys.argv[2], "w"), indent=0)
