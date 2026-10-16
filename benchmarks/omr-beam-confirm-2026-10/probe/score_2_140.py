"""Score the 11 2.140 tiles against Sean's answers using replay2-*.json; writes out/print/2.140-review/answers.json; lists changed cells outside the tiles."""
import json
O = "benchmarks/omr-beam-confirm-2026-10/out/2.140/"
key = json.load(open(O + "tiles-key.json"))["tiles"]
rb = json.load(open(O + "replay2-brah-p18.json"))["changed"]; rl = json.load(open(O + "replay2-lit-p6p4.json"))["changed"]
raw = "1.16 2.16,16,16 3.8. 4.16. 5.8,8,8 6.16,16,16. 7.16,16,16 8.16,16. 9.8,8,8. 10.8,8,8. 11.16,16,16"
sean = {1: ["16"], 2: ["16"] * 3, 3: ["8"], 4: ["16"], 5: ["8"] * 3, 6: ["16"] * 3, 7: ["16"] * 3, 8: ["16"] * 2, 9: ["8"] * 3, 10: ["8"] * 3, 11: ["16"] * 3}
name = {0.5: "8", 0.25: "16", 0.125: "32"}
tiles, tally = [], {"right": 0, "narrowed": 0, "WRONG": 0}
for t in key:
    ch = rb if t["movement"] == "brah" else rl
    now = []
    for g in t["blue"]:
        c = ch.get(g)
        if c:
            now.append(name.get(c["on"][1], "?") if c["on"][0] == "decided" else "narrowed")
        else:
            off = t["info"][g]["off"]
            now.append(name.get(off[1], "?") if off and off[0] == "decided" else "narrowed")
    per = [("right" if n == s else ("narrowed" if n == "narrowed" else "WRONG")) for n, s in zip(now, sean[t["n"]])]
    for p in per: tally[p] += 1
    tiles.append({"n": t["n"], "sean": ",".join(sean[t["n"]]), "role": t["role"], "flag_ON_now": now, "per_note": per, "agrees": all(p != "WRONG" for p in per)})
json.dump({"date": "2026-10-15", "who": "Sean", "raw_answer": raw, "tally_after_cause_fixes": tally,
           "note": "flag_ON_now = replay2 (page-raster rows) after the 2.140 cause fixes; tiles listed in key order; 'narrowed' = blue, never a plain wrong value",
           "tiles": tiles}, open("out/print/2.140-review/answers.json", "w"), indent=1)
print(tally)
for x in tiles: print(x["n"], x["sean"], x["flag_ON_now"], x["agrees"])
tc = {(t["movement"], tuple(t["cell"])) for t in key}
for mov, ch in (("brah", rb), ("lit", rl)):
    for g, c in ch.items():
        cell = tuple(int(x) for x in g.split("/")[1:5])
        if (mov, cell) not in tc and c["on"][0] == "decided": print("OTHER decided change", g, c["off"][:3], c["on"][:3])
