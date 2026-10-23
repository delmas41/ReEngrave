"""2.199 A2 (answers lane 2.200's advice): is the FLAT anchor (0.715) biased, and would re-centring it (instead of the unclassed fallback) keep every decided pair and recover near-misses?
usage: a2_recentre.py VIEW.json"""
import json, sys, statistics, collections
sys.argv += [] ; exec(open(__file__.rsplit("/", 1)[0] + "/a1_options.py").read().split("FR = {")[0].replace("sys.argv[2]", "None"))
FRS = 0.0
def run(shift):
    c = collections.Counter()
    for sub, o in acc.items():
        ov = live.get((sub, "accidental_owner"))
        if not ov or (ov["outcome"], ov["reason"]) not in (("decided", "immediately_right_same_position"), ("abstained", "no_candidate")): continue
        dt = o["detail"]
        if str(dt["detector_class"]).lower() != "accidentalflat": continue
        cell, pool = head_pool(sub, "staff/" + "/".join(sub.split("/")[1:4])); sp = space.get(cell)
        if not sp: continue
        apos = float(o["value"])
        if ov["outcome"] == "decided" and (ov.get("detail") or {}).get("accidental_position") is not None: apos = float(ov["detail"]["accidental_position"])
        r = search(sub, float(dt["x1"]), apos + shift, pool, sp)
        if ov["outcome"] == "decided": c["decided_same" if r[1] == ov["value"] else "decided_CHANGED"] += 1
        else: c["near-miss recovered" if r[0] == "head" else "still none"] += 1
    return dict(c)
off = []
for sub, o in acc.items():
    ov = live.get((sub, "accidental_owner"))
    if ov and ov["outcome"] == "decided" and str(o["detail"]["detector_class"]).lower() == "accidentalflat" and not (ov["detail"] or {}).get("one_ink"):
        hk = ov["value"]
        if hk in hpos: off.append(hpos[hk] - float(ov["detail"]["accidental_position"]))
print("decided flats", len(off), "median (head - anchor) positions", round(statistics.median(off), 2))
for sh in (0.0, -0.42, 0.42, -0.6, -0.8, -1.0):
    print("shift", sh, run(sh))
