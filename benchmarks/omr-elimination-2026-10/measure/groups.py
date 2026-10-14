"""2.120 (d): today's cut-offs as 2-3-way questions, on TRUTH. python3 measure/groups.py"""
import json, collections
R = json.load(open("measure/truth.json"))
def rng(v): return "n=%d %.2f-%.2f" % (len(v), min(v), max(v)) if v else "n=0"
def best_thr(pos, neg):   # pos below threshold is "target"? find threshold minimising errors, either direction
    vals = sorted(set(pos + neg)); best = None
    for t in vals + [vals[-1] + 1]:
        for sign in (1, -1):
            e = sum((sign * (x - t) >= 0) for x in pos) + sum((sign * (x - t) < 0) for x in neg)
            if best is None or e < best[0]: best = (e, t, sign)
    return best
def group(name, target, feat, today=None, today_dir=None, pool=None):
    tgt = [r for r in R if r["sym"] == target]
    co = collections.defaultdict(list)
    for r in R:
        if r["sym"] != target and target in r["all"] and (pool is None or r["sym"] in pool):
            co[r["sym"]].append(feat(r))
    tv = [feat(r) for r in tgt]
    print("\n==", name, "| target", target, rng(tv))
    for s, v in sorted(co.items(), key=lambda kv: -len(kv[1])):
        e, t, sg = best_thr(v, tv)
        line = "  vs %-14s %s  best-thr %.2f errors %d" % (s, rng(v), t, e)
        if today is not None:
            # today's rule: other-class iff feat < today (today_dir='<') or > today
            if today_dir == "<": te = sum(x >= today for x in v) + sum(x < today for x in tv)
            else: te = sum(x <= today for x in v) + sum(x > today for x in tv)
            line += "  | at today's %.2f: errors %d (others kept %d, target lost %d)" % (today, te,
                    te - (sum(x < today for x in tv) if today_dir == "<" else sum(x > today for x in tv)),
                    sum(x < today for x in tv) if today_dir == "<" else sum(x > today for x in tv))
        print(line)
W = lambda r: r["d"]["w"]; H = lambda r: r["d"]["h"]; MX = lambda r: max(r["d"]["w"], r["d"]["h"])
CF = lambda r: r["d"]["cfill"]; F = lambda r: r["d"]["fill"]
group("G1 too_narrow (w < 1.0 sp)", "head_black", W, 1.0, "<")
group("G2 is_a_dot (max side <= 0.75)", "dot", MX, 0.75, ">")
group("G3 head interior (centre 40% fill; proxy, NOT 2.88's reader)", "head_half", CF, None, None, pool={"head_black"})
group("G4 ledger vs flat strokes (height)", "ledger", H)
group("G4b ledger vs flat strokes (fill)", "ledger", F)
group("G5 stem vs barline etc (height)", "stem", H)
print("\nG5 edge: barline edge True %d/%d; stem edge True %d/%d" % (
    sum(r["d"]["edge"] for r in R if r["sym"] == "barline"), sum(r["sym"] == "barline" for r in R),
    sum(r["d"]["edge"] for r in R if r["sym"] == "stem"), sum(r["sym"] == "stem" for r in R)))
ties = [r for r in R if r["sym"] in ("tie", "slur")]
print("\nG6 tie/slur: tie marks whose set contains slur %d/%d; slur marks whose set contains tie %d/%d" % (
    sum("slur" in r["all"] for r in ties if r["sym"] == "tie"), sum(r["sym"] == "tie" for r in ties),
    sum("tie" in r["all"] for r in ties if r["sym"] == "slur"), sum(r["sym"] == "slur" for r in ties)))
hd = [r for r in R if r["d"]["zone"] in ("KEYSLOT", "HEADER")]
print("\nG7 header marks by true class -> survivor sets:")
for k, v in collections.Counter((r["cls"], tuple(r["all"])) for r in hd).most_common(14): print("  ", v, k)
