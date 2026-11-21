"""2306 r12 step 1: for given glyphs, what the r9-reader gather and the r11-reader gather of the SAME pages write (ON), with the page stem reading
of each and the duration / fate. Usage: same_gather.py R9_REC R9_RFPRE R11_REC R11_RFPRE glyph ..."""
import sys, json, re
r9rec, r9pre, r11rec, r11pre = sys.argv[1:5]
gs = sys.argv[5:]


def stems(rec):
    txt = open(rec, encoding="utf-8").read()
    out = {}
    for g in gs:
        m = re.search(r'"subject":"%s","quantity":"page_stem",("value":"(obs:[0-9]+)"|"reader").{0,500}?"how":"([a-z_]+)"' % re.escape(g), txt)
        out[g] = m and (m.group(2), m.group(3))
    return out


def arm(pre):
    D = json.load(open(pre + ".on.json"))
    v = {}
    for x in D["verdicts"]:
        if x["s"] in gs and x["q"] in ("duration", "head_stem", "stem_direction"):
            v.setdefault(x["s"], {})[x["q"]] = "%s/%s:%s" % (x["o"], x["r"], str(x["v"])[:40])
    w = {g: [(h.get("pitch"), h.get("type")) for h in D["hosts"] if h.get("rg") == g] for g in gs}
    return v, w, D["fates"]


S9, S11 = stems(r9rec), stems(r11rec)
V9, W9, F9 = arm(r9pre)
V11, W11, F11 = arm(r11pre)
for g in gs:
    print("==", g)
    print("   r9 : page stem %s | wrote %s | fate %s | %s" % (S9[g], W9[g], F9.get(g), V9.get(g)))
    print("   r11: page stem %s | wrote %s | fate %s | %s" % (S11[g], W11[g], F11.get(g), V11.get(g)))
