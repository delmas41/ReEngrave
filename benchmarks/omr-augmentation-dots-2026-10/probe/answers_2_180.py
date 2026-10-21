"""ROADMAP 2.180 -- record Sean's answers to the 12 tiles (both his messages verbatim) against the key."""
import json

K = json.load(open("out/print/2.180-review/_key/key.json"))
m1 = "2.180 - 1-4. Dot 4 5. Dot 2 6-8. Dot 4 9. Dot 2 10. 4 11.  Dot 4 12.4"
m2 = "12 is dot 4"
ans = {1: "Dot 4", 2: "Dot 4", 3: "Dot 4", 4: "Dot 4", 5: "Dot 2", 6: "Dot 4", 7: "Dot 4", 8: "Dot 4", 9: "Dot 2",
       10: "4", 11: "Dot 4", 12: "dot 4"}
norm = {"Dot 4": "dotted 4", "dot 4": "dotted 4", "Dot 2": "dotted 2", "4": "4"}
out = {"source": {"sean_2026_10_20_first": m1, "sean_2026_10_20_correction": m2,
                  "note": "tile 12 first read '4' from the first message; Sean corrected it to 'dot 4'. Per-tile answers are "
                          "his words split by tile."},
       "question": "what is the written value of the note in the blue box (e.g. dotted 4, 4, dotted 8)?"}
for k in K:
    i = k["tile"]
    a = ans[i]
    out["tile_%02d" % i] = {"sean": a, "glyph": k["note"], "doc": "brahms", "kind": k["kind"], "off": k["off"],
                            "on": k["on"], "on_right": norm[a] == k["on"], "off_right": norm[a] == k["off"]}
json.dump(out, open("out/print/2.180-review/answers.json", "w"), indent=1)
# the manifest `judged build` joins on (written AFTER Sean answered, so it reveals nothing to him)
json.dump({"label": "brahms", "tiles": [dict(tile=k["tile"], file=k["file"], glyph=k["note"], doc="brahms",
                                             control=k["kind"].startswith("control"), kind=k["kind"]) for k in K]},
          open("out/print/2.180-review/manifest.json", "w"), indent=1)
print([(i, out["tile_%02d" % i]["on_right"], out["tile_%02d" % i]["off_right"]) for i in range(1, 13)])
