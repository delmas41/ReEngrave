import json
import collections
B = json.load(open("/private/tmp/claude-501/s/count-base.json"))
T = json.load(open("/private/tmp/claude-501/s/count-tag.json"))
for n, D in (("BASE", B), ("TAG", T)):
    r = D["refusals"]
    amb = [a for a in D["fit_abstentions"] if a["reason"] == "ambiguous"]
    tie = [x for x in r if x["this"] is not None and x["other"] is not None and abs(x["this"] - x["other"]) < 0.02]
    hol = [x for x in r if x["cls"] and not x["cls"].startswith("noteheadBlack")]
    print(n, "refusals", len(r), "| near-tie ink (<0.02)", len(tie), "| hollow-class refused", len(hol),
          "| fit abstentions", len(D["fit_abstentions"]), "ambiguous", len(amb))
    pg = collections.Counter(x["subject"].split("/")[1] for x in r)
    print("   refusals per page", dict(sorted(pg.items(), key=lambda kv: int(kv[0]))))
bs = {x["subject"] for x in B["refusals"]}
ts = {x["subject"] for x in T["refusals"]}
bamb = {a["subject"] for a in B["fit_abstentions"] if a["reason"] == "ambiguous"}
print("TAG refusals whose same key was ambiguous-abstained in BASE:", len(ts & bamb), "; same key refused in both:", len(ts & bs),
      "; TAG-only key:", len(ts - bs - bamb))
