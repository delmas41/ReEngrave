"""ROADMAP 2.190: 12 fresh blind tiles of the ACCIDENTAL changes between the two arms of a lane_report run (2.186 only vs 2.186 + shape),
drawn with the lane report's own functions. Sean's 2.186b tiles are excluded. Orange box = the note to look at; the key is outside the folder.
usage: tiles_2_190.py REPORT_WORK_DIR OUT_DIR [SEED]"""
import json, pathlib, sys
from tools.omr.staged import lane_report as LR
work, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 190
seen = {k["rg"] for k in json.load(open("out/print/2.186b-accidentals/key.json"))}
ch, same = {}, {}
for p in ("litolff", "brahms"):
    off = json.load(open(work / ("%s.off.symbols.json" % p))); on = json.load(open(work / ("%s.on.symbols.json" % p)))
    d = LR.diff_arms(off, on, tol=0.5 * LR.PLATES[p]["unit"])
    ch[p] = [c for c in d["changes"] if c["kind"] == "accidental" and c.get("rg") not in seen]
    same[p] = [s for s in d["same"] if s["kind"] == "accidental" and s.get("rg") not in seen]
    print(p, "accidental changes", len(ch[p]), "unchanged accidentals", len(same[p]))
items = LR.pick_tiles(ch, same, seed)
out.mkdir(parents=True, exist_ok=True)
print(LR.cut_tiles(items, out))
