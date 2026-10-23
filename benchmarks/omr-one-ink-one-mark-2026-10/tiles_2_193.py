"""ROADMAP 2.193: 12 blind tiles of the ACCIDENTAL changes between the two arms of the lane report (OMR_NATURAL_CANDIDATE off vs on), drawn with the
lane report's own functions (proportional to the changes, 9 changed + 3 unchanged controls, one note per tile, orange box on the note, key outside the
folder). Sean's earlier accidental tiles (2.186b, 2.190) are excluded. Also prints the 4 earlier tiles that were a natural the detector never offered.
usage: tiles_2_193.py REPORT_WORK_DIR OUT_DIR KEYS_JSON_DIR [SEED]   KEYS_JSON_DIR holds 2.186b.key.json and 2.190.key.json"""
import json, pathlib, sys
from tools.omr.staged import lane_report as LR
work, out, keys = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]); seed = int(sys.argv[4]) if len(sys.argv) > 4 else 193
earlier = json.load(open(keys / "2.186b.key.json")) + json.load(open(keys / "2.190.key.json"))
seen = {k["rg"] for k in earlier}
ch, same = {}, {}
H = {}
for p in ("litolff", "brahms"):
    off = json.load(open(work / ("%s.off.symbols.json" % p))); on = json.load(open(work / ("%s.on.symbols.json" % p)))
    H[p] = ({h["rg"]: h for h in off["hosts"]}, {h["rg"]: h for h in on["hosts"]})
    d = LR.diff_arms(off, on, tol=0.5 * LR.PLATES[p]["unit"])
    ch[p] = [c for c in d["changes"] if c["kind"] == "accidental" and c.get("rg") not in seen]
    same[p] = [s for s in d["same"] if s["kind"] == "accidental" and s.get("rg") not in seen]
    print(p, "accidental changes (not seen before)", len(ch[p]), "unchanged accidentals", len(same[p]))
for t in earlier:
    if t["plate"] == "brahms" and t["rg"] in ("glyph/25/1/1/8/1", "glyph/4/1/11/6/3", "glyph/19/1/10/1/3", "glyph/12/0/13/0/17"):
        o, n = H["brahms"][0].get(t["rg"]), H["brahms"][1].get(t["rg"])
        f = lambda h: None if h is None else (h["pitch"], (h.get("sub") or {}).get("accidental"), "blue" if h["blue"] else "plain")
        print("earlier tile", t["rg"], "before(2.190 ON)", f(o), "after(+2.193)", f(n))
items = LR.pick_tiles(ch, same, seed)
out.mkdir(parents=True, exist_ok=True)
print(LR.cut_tiles(items, out))
