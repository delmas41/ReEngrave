"""ROADMAP 2.158 -- record Sean's 2026-10-17 answers to out/print/2.158-review (answers.json + the manifest naming each
tile's glyph) and score them against the key (out/2.158/tiles-key.json)."""
import json

key = json.load(open("out/2.158/tiles-key.json"))
V1 = ("1-9.2 10.4 11-13.2 14. Box is off on a part of a slur but the measure has a 2 in it. Not sure if that is bad box "
      "placement  or meant to be where it is. 15-21. 2")
V2 = "Sorry 1$ is dotted half"
ans = {n: "2" for n in range(1, 22)}
ans[10] = "4"
ans[14] = ("Box is off on a part of a slur but the measure has a 2 in it. Not sure if that is bad box placement  or meant to "
           "be where it is.")
ans[17] = "dotted half"
val = {"2": 2.0, "4": 1.0, "dotted half": 3.0}
tiles, tally = [], {}
for k in key:
    n, s = k["n"], ans[k["n"]]
    wrote = (k["on"] or {}).get("written")
    if n == 14:
        verdict = "value_fills_bar_box_on_arc_pitch_invented"
    else:
        verdict = "right" if abs(val[s] - wrote) < 1e-6 else "wrong"
    tally["%s/%s" % (k["role"], verdict)] = tally.get("%s/%s" % (k["role"], verdict), 0) + 1
    row = dict(n=n, doc=k["doc"], glyph=k["glyph"], role=k["role"], sean=s, on=k["on"], off=k["off"], verdict=verdict)
    if n == 17:
        row["note"] = "answered '2' first; Sean's correction, verbatim: \"%s\" (the manager reads it as tile 17)" % V2
    if n == 14:
        row["note"] = ("out/print/2.158-tile14/box_vs_head.png: the box is the end of a tie arc on the bottom line; the real "
                       "half-note head (second space) has no detector box")
    tiles.append(row)
json.dump(dict(answered="2026-10-17", verbatim=V1, correction=V2,
               question="What is the written value of the note in the blue box (2, 4, dotted 2 ...)?", tiles=tiles),
          open("out/print/2.158-review/answers.json", "w"), indent=1)
m = json.load(open("out/print/2.158-review/manifest.json"))
m["tiles"] = [dict(n=k["n"], doc=k["doc"], glyph=k["glyph"]) for k in key]
json.dump(m, open("out/print/2.158-review/manifest.json", "w"), indent=1)
print(tally)
