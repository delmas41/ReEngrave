"""2.171 probe 9: the per-plate, per-class tables for FINDINGS (markdown), from summary.json. Cells = mean / median / share >= 0.25 of the conf of the best
wanted-family box over the symbol (0 where none). 'phase' = mean over the 9 sampling-phase runs. usage: e9_tables.py > data/tables.md"""
import json

ROOT = __file__.rsplit("/probe/", 1)[0]
S = json.load(open(ROOT + "/probe/2.171/data/summary.json"))
CONDS = [("prod", "prod (production)"), ("phase", "phase null (mean of 9)"), ("sc0.5", "scale x0.5"), ("sc0.7", "scale x0.7"), ("sc1.4", "scale x1.4"), ("sc2.0", "scale x2"),
         ("wide", "wide, same px"), ("wide_rule", "wide, production rule"), ("mirror", "mirror ink"), ("L2white", "bar on white wide canvas"), ("area", "area interp")]
PH = ["phx1", "phx2", "phx3", "phx4", "phx5", "phx6", "phy2", "phy4", "phy6"]
for plate, nm in (("lit", "Litolff (Beethoven 5, merging)"), ("bra", "Brahms (Brahms 1, shattering)")):
    print("\n#### %s\n" % nm)
    for cls in ("dot", "flag", "rest", "blackhead"):
        for g in ("lost", "kept"):
            d = S[plate].get("%s|%s" % (g, cls))
            if not d or d["prod"]["n"] < 3:
                continue
            print("**%s, %s, n=%d**\n" % (cls, "lost (A/B/C)" if g == "lost" else "kept at 0.25+ in the record", d["prod"]["n"]))
            print("| condition | mean | median | share >= 0.25 |\n|---|--:|--:|--:|")
            for c, lab in CONDS:
                if c == "phase":
                    v = [d[x] for x in PH if x in d]
                    if not v:
                        continue
                    print("| %s | %.2f | %.2f | %.2f |" % (lab, sum(x["mean"] for x in v) / len(v), sum(x["median"] for x in v) / len(v), sum(x["share"] for x in v) / len(v)))
                elif c in d:
                    print("| %s | %.2f | %.2f | %.2f |" % (lab, d[c]["mean"], d[c]["median"], d[c]["share"]))
            print()
