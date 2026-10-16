"""ROADMAP 2.144 -- candidate CONTROLS: heads that stand in ON arm, in a cell that also holds a head the flag refuses (or a clef box).
usage: controls_2_144.py REPLAY.json ROWS.json"""
import json, sys, collections
r = json.load(open(sys.argv[1])); rows = json.load(open(sys.argv[2])); B = rows["boxes"]
off, on = r["off"], r["on"]
cell = lambda s: "/".join(s.split("/")[:5])
refused_cells = {cell(s) for s in on if on[s].get("notehead_is_not_a_notehead", [0, 0, 0])[2] == "inside_a_clef_box"
                 and off[s]["notehead_is_not_a_notehead"][2] != "inside_a_clef_box"}
by = collections.defaultdict(list)
for s, v in on.items():
    nn = v.get("notehead_is_not_a_notehead")
    if nn and nn[1] is False and cell(s) in refused_cells and s in B and B[s][0].startswith("notehead"):
        by[cell(s)].append((s, B[s][0], round(B[s][1], 2), v.get("duration")))
for c, l in sorted(by.items()):
    print(c); [print("   ", x) for x in l]
