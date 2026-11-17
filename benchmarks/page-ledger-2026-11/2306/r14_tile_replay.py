"""2.306 r14: replay Sean's r14 tile answers on a facts file (extract.py output): the written note at each tile's place (matched by box), its type and
whether it carries a flag or a beam, against what he read. Usage: r14_tile_replay.py KEY.json PLATE FACTS.json"""
import json
import sys

from tools.omr.staged.judged import boxes_overlap

SEAN = {1: ("eighth", "flag"), 2: ("quarter", "none"), 3: ("eighth", "flag"), 4: ("eighth", "flag"), 5: ("eighth", "flag"), 6: ("eighth", "flag"),
        7: ("eighth", "flag"), 8: ("eighth", "flag"), 12: ("eighth", "flag")}
key = json.load(open(sys.argv[1]))
plate = sys.argv[2]
facts = json.load(open(sys.argv[3]))
w = [h for h in facts["written"] if h["kind"] == "note"]
ok = bad = 0
for t in key["tiles"]:
    if t["plate"] != plate or t["tile"] not in SEAN:
        continue
    m = sorted([h for h in w if h["page"] == t["page"] and boxes_overlap(h["box"], t["box"])[0]], key=lambda h: -boxes_overlap(h["box"], t["box"])[1])
    if not m:
        print(t["tile"], t["rg"], "NOT WRITTEN", "sean", SEAN[t["tile"]])
        bad += 1
        continue
    h = m[0]
    s = h.get("sub") or {}
    mark = "beam" if s.get("beam") else ("flag" if s.get("flag") else "none")
    got = (h["type"], mark)
    good = got == SEAN[t["tile"]]
    ok += good
    bad += not good
    print(t["tile"], h["rg"], "written", got, "sean", SEAN[t["tile"]], "OK" if good else "DIFFERS")
print(plate, "as he read:", ok, "differs:", bad)
