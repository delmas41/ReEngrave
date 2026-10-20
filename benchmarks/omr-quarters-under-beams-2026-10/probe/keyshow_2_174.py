"""2.174: show Sean's 2.165 tile answers against the key and the census features. usage: keyshow_2_174.py"""
import json

J = json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
print("2.165-review rows in the judged index:", sum(1 for t in J if t["item"] == "2.165-review"))
K = json.load(open("out/2.165/tiles-key.json"))
A = json.load(open("out/print/2.165-review/answers.json"))["answers"]
cen = {}
for d in ("litolff", "brahms"):
    for r in json.load(open("scratch/census_%s.json" % d))["rows"]:
        cen[(d, r["subject"])] = r
for k in K:
    kept = k["kept"]
    r = cen.get((k["doc"], k["glyph"]))
    print(k["n"], k["doc"], k["glyph"], k["role"], "kept", (kept.get("written") if isinstance(kept, dict) else kept), "alt", k.get("alternative"),
          "SEAN", A[str(k["n"])], "| census:", None if r is None else {x: r[x] for x in ("reason", "cv", "yolo", "far", "arc", "ink", "ledger", "by_stem", "stems", "side", "has_stem")})
