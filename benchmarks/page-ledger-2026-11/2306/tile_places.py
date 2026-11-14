"""2306 r8: the 12 r4 tile places -- what each arm writes now at the tile's glyph (pitch, value, dots, voice), EXPORT's fate, against Sean's answer.
The glyph id is checked against the tile's page box (the record's own glyph box centre must lie inside the tile box). Usage: tile_places.py ANSWERS.json
RFPREFIX_LIT RFPREFIX_BRA REC_LIT REC_BRA"""
import sys, json, re
ans, rl, rb, recl, recb = sys.argv[1:6]
A = json.load(open(ans))["tiles"]
arms = {}
for plate, pre, rec in (("litolff", rl, recl), ("brahms", rb, recb)):
    arms[plate] = {a: json.load(open("%s.%s.json" % (pre, a))) for a in ("off", "on")}
    txt = open(rec, encoding="utf-8").read()
    arms[plate]["boxes"] = {}
    for t in A:
        if t["plate"] != plate:
            continue
        m = re.search(r'"subject":"%s","quantity":"glyph_box".{0,900}?"bbox_page_px":\[([^\]]*)\]' % re.escape(t["glyph"]), txt)
        arms[plate]["boxes"][t["glyph"]] = [float(v) for v in m.group(1).split(",")] if m else None
    del txt


def wrote(D, g):
    return [(h.get("pitch"), h.get("type"), len((h.get("sub") or {}).get("dot") or []), h.get("voice")) for h in D["hosts"] if h.get("rg") == g]


def dur(D, g):
    v = [x for x in D["verdicts"] if x["s"] == g and x["q"] == "duration"]
    return v and "%s/%s" % (v[-1]["o"], v[-1]["r"])


for t in A:
    P = arms[t["plate"]]
    g = t["glyph"]
    b = P["boxes"].get(g)
    tb = t["box_page_px"]
    same = b is not None and tb[0] <= (b[0] + b[2]) / 2 <= tb[2] and tb[1] <= (b[1] + b[3]) / 2 <= tb[3]
    print("tile %2d %-7s %-18s Sean: %-15s | OFF %s %s | ON %s %s fate %s%s" % (
        t["tile"], t["plate"], g, t["sean"], wrote(P["off"], g), dur(P["off"], g), wrote(P["on"], g), dur(P["on"], g),
        P["on"]["fates"].get(g), "" if same else "  [GLYPH ID NOT AT THE TILE'S PLACE: %s]" % b))
