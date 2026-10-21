"""ROADMAP 2.180 -- pick the blind tiles: 9 notes the flag lengthens by one dot (spread over pages) + 3 controls (1 plain note,
2 notes dotted by a round dot, both arms equal). usage: pick_2_180.py CHANGED.json OFF.json X1_BRA.json OUT_PICKS.json"""
import json
import random
import sys

ch, offp, x1, out = sys.argv[1:5]
C = json.load(open(ch))
OFF = json.load(open(offp))["dur"]
X = json.load(open(x1))


def name(w, d):
    base = {0.5: "8", 1.0: "4", 2.0: "2", 4.0: "1"}
    for b, n in base.items():
        if abs(w - b * (2 - 0.5 ** d)) < 1e-6:
            return ("dotted " if d == 1 else "double-dotted " if d == 2 else "") + n
    return str(w)


lon = [c for c in C if c["direction"] == "longer" and c["on"][2] == 1 and c["off"][2] == 0 and c["glyph"] in X]
seen, picks = set(), []
random.Random(2180).shuffle(lon)
for c in lon:
    p = c["glyph"].split("/")[1]
    if p in seen:
        continue
    seen.add(p)
    picks.append(dict(plate="bra", note=c["glyph"], kind="changed", off=name(c["off"][1], 0), on=name(c["on"][1], 1)))
    if len(picks) == 9:
        break
pool = [g for g, v in OFF.items() if v[0] == "deci" and v[3] == "adjudicate_duration" and v[4] == "head_and_marks"
        and g in X and str(X[g].get("cls", "")).startswith("noteheadBlack")]
random.Random(7).shuffle(pool)
plain = [g for g in pool if OFF[g][2] == 0 and OFF[g][1] == 1.0][:1]
dotted = [g for g in pool if OFF[g][2] == 1 and OFF[g][1] == 1.5][:2]
for g in plain:
    picks.append(dict(plate="bra", note=g, kind="control_plain", off="4", on="4"))
for g in dotted:
    picks.append(dict(plate="bra", note=g, kind="control_dotted", off="dotted 4", on="dotted 4"))
json.dump(picks, open(out, "w"), indent=1)
print(len(picks), [p["kind"] for p in picks])
