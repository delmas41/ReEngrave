"""2.167e probe 24: of the whole notes that reach the exported file (all in red bars; glyph ids from the 2.173 red rows), how many have a filled centre (>= 0.6) or stem ink. usage: e24_filewhole.py"""
import json
import collections

d = "probe/2.167e/data/"
for pl in ("lit", "bra"):
    red = json.load(open(d + "%s_red_rows.json" % pl))
    wh = {r["sub"]: r for r in json.load(open(d + "%s_whole.json" % pl))}
    inf = [r["glyph"] for b in red for r in b["rows"] if r["kind"] == "note" and r.get("type") == "whole"]
    inlist = [wh[g] for g in inf if g in wh]
    c = collections.Counter()
    for r in inlist:
        c[("filled" if r["filled"] else "hollow", "stem" if r["stem_ink"] else "nostem")] += 1
    print(pl, "whole notes in file", len(inf), "from the record's 4.0-wholes", len(inlist), dict(c),
          "| filled or stem:", sum(1 for r in inlist if r["filled"] or r["stem_ink"]), "| statuses", collections.Counter(
              r["status"] for b in red for r in b["rows"] if r["kind"] == "note" and r.get("type") == "whole"))
