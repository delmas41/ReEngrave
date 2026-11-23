"""2306 r6: for target glyphs whose own reading did not change: every OTHER glyph of the same cell (bar) whose duration / head_stem / stem_direction /
event / voices verdict changed OFF -> ON, and the cell-level verdicts that changed. Usage: bar_cases.py RFPREFIX glyph ..."""
import sys, json, collections
pre, gs = sys.argv[1], sys.argv[2:]
A = json.load(open(pre + ".off.json"))
B = json.load(open(pre + ".on.json"))
LA, LB = collections.defaultdict(dict), collections.defaultdict(dict)
for D, L in ((A, LA), (B, LB)):
    for v in D["verdicts"]:
        L[v["s"]][v["q"]] = v
s = lambda v: v and "%s/%s:%s" % (v["o"], v["r"], json.dumps(v["v"], default=str)[:70])
for g in gs:
    cell = "/".join(g.split("/")[:5])
    ckey = cell.replace("glyph", "cell")
    print("==", g, "| bar red OFF", ckey.replace("cell/", "") in str(A["red"]), "ON", ckey.replace("cell/", "") in str(B["red"]))
    for sub in sorted(set(LA) | set(LB)):
        if not (sub == ckey or sub.startswith(cell + "/") or sub.startswith(ckey + "/")):
            continue
        for q in sorted(set(LA[sub]) | set(LB[sub])):
            if q in ("duration", "head_stem", "stem_direction", "event", "voices", "stem_value", "bar_sum", "measure_duration", "meter") or sub == ckey:
                a, b = LA[sub].get(q), LB[sub].get(q)
                if s(a) != s(b):
                    print("   %-22s %-20s OFF %s\n   %-22s %-20s ON  %s" % (sub, q, s(a), "", "", s(b)))
