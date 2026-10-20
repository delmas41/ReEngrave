"""2.167e probe 20: which of the record-level whole-valued heads are written in a RED bar (from the 2.173 red rows, which carry glyph ids)? And how many of the file's
whole notes does that cover. usage: e20_redwhole.py"""
import json

d = "probe/2.167e/data/"
for pl, nfile in (("lit", 2), ("bra", 54)):
    red = json.load(open(d + "%s_red_rows.json" % pl))
    rw = {}
    for b in red:
        for r in b["rows"]:
            if r["kind"] == "note" and r.get("type") == "whole":
                rw[r["glyph"]] = (b["want_quarters"], b["counted_quarters"], r["status"])
    wh = {r["sub"]: r for r in json.load(open(d + "%s_whole.json" % pl))}
    print(pl, "whole notes in red bars:", len(rw), "of which are among the record's decided wholes:", sum(1 for g in rw if g in wh),
          "| record-level wholes", len(wh), "| whole notes in the file", nfile)
    print("   red-bar wholes not in my list:", [g for g in rw if g not in wh][:10])
    print("   statuses:", {s: sum(1 for v in rw.values() if v[2] == s) for s in ("READ", "GUESSED")})
