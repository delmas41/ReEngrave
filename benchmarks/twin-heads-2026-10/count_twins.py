"""ROADMAP 2.212 (read-only): count the detector's twin boxes on a lane_report's saved records.

usage: python3 benchmarks/twin-heads-2026-10/count_twins.py WORKDIR PLATE ARM

WORKDIR is a lane_report `work/` dir holding `<plate>.<arm>.gathered.record.json` (the position / class / stacked-fit rows)
and `<plate>.<arm>.mini-record.json` (the boxes and ADJUDICATE's verdicts). A twin pair is a box ADJUDICATE refused as
`stacked_head_duplicate` (2.42) or `notehead_is_a_duplicate_box` (2.30), with the box it kept. Counted by |dy| between the two
box centres in staff spaces: under 0.5 sp is one head boxed twice, over is mostly two heads (or a head and a head+stem box).
Prints, per refusal rule and dy band: pairs, how many give a different WRITTEN POSITION (rounded half-steps) and how many a
different class family (black vs hollow)."""
import collections
import json
import sys


def hollow(c):
    return c.startswith("noteheadHalf") or c.startswith("noteheadWhole")


def main(work, plate, arm):
    mini = json.load(open("%s/%s.%s.mini-record.json" % (work, plate, arm)))
    g = json.load(open("%s/%s.%s.gathered.record.json" % (work, plate, arm)))
    g = g["record"] if "observations" not in g else g
    want = {"notehead_staff_position", "stacked_head_fit", "cell_staff_space"}
    keep = [o for o in g["observations"] if o["quantity"] in want]
    del g
    pos = {o["subject"]: o["value"] for o in keep if o["quantity"] == "notehead_staff_position"}
    space = {o["subject"]: o["value"] for o in keep if o["quantity"] == "cell_staff_space"}
    owner = {o["id"]: o["subject"] for o in keep}
    owner.update({o["id"]: o["subject"] for o in mini["observations"]})
    box = {o["subject"]: o["value"] for o in mini["observations"] if o["quantity"] == "glyph_box"}
    table = collections.Counter()
    for v in mini["verdicts"]:
        if v["quantity"] != "notehead_is_not_a_notehead" or v["reason"] not in (
                "stacked_head_duplicate", "notehead_is_a_duplicate_box"):
            continue
        dup = (v.get("detail") or {}).get("duplicate_of")
        keeper = owner.get(dup, dup)
        s = v["subject"]
        sp = space.get("cell/" + "/".join(s.split("/")[1:5]))
        if keeper not in box or not sp:
            continue
        dy = abs((box[s][2] + box[s][4] / 2.0) - (box[keeper][2] + box[keeper][4] / 2.0)) / sp
        band = "dy<0.5sp" if dy < 0.5 else ("0.5-1.0sp" if dy < 1.0 else ">=1.0sp")
        k = (v["reason"][:8], band)
        table[k, "pairs"] += 1
        table[k, "pitch differs"] += round(pos[s]) != round(pos[keeper])
        table[k, "class differs"] += hollow(box[s][0]) != hollow(box[keeper][0])
    for (k, what), n in sorted(table.items()):
        print(plate, arm, k[0], k[1], what, n)


if __name__ == "__main__":
    main(*sys.argv[1:4])
