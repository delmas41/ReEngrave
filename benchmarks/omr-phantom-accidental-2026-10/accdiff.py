"""2.192: accidentals gained/lost per note between the lane report's OFF and ON arms. usage: accdiff.py WORKDIR SC.json OUT.json"""
import json, sys
wd, scp, outp = sys.argv[1:4]; sc = json.load(open(scp)); res = []
for p in ("brahms", "litolff"):
    A = {h["rg"]: h for h in json.load(open("%s/%s.off.symbols.json" % (wd, p)))["hosts"]}
    B = {h["rg"]: h for h in json.load(open("%s/%s.on.symbols.json" % (wd, p)))["hosts"]}
    for rg, h in A.items():
        g = B.get(rg)
        if not g: continue
        a, b = h.get("sub", {}).get("accidental"), g.get("sub", {}).get("accidental")
        if a != b:
            cell = "/".join(rg.split("/")[:5])
            c = [(r["acc"], r["cls"], r["why"]) for r in sc if r["plate"] == p and "/".join(r["acc"].split("/")[:5]) == cell]
            res.append(dict(plate=p, head=rg, off=a, on=b, pitch=(h["pitch"], g["pitch"]), page=h["page"], contested=c)); print(p, rg, a, "->", b, c)
json.dump(res, open(outp, "w"))
