"""ROADMAP 2.182 -- compare two m1_replay arms: red bars in/out, two-part bars and their fate, rests restored, labelled bars.

usage: c1_compare.py OFF.json ON.json [CENSUS LABELS]"""
import collections
import json
import sys

off, on = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
ro, rn = set(off["red_bars"]), set(on["red_bars"])
K = ("notes", "rests", "notes_in_xml", "two_voice_bars", "bars_red", "bars_add_up")
print("summary off", {k: off["summary"][k] for k in K})
print("summary on ", {k: on["summary"][k] for k in K})
tp = on["two_parts"]
print("two-part decisions", len(tp), dict(collections.Counter(v["reason"] for v in tp.values())))
print("  of them red OFF", sum(b in ro for b in tp), "red ON", sum(b in rn for b in tp),
      "| red->ok", sum(b in ro and b not in rn for b in tp), "ok->red", sum(b not in ro and b in rn for b in tp))
print("all bars: red->ok", len(ro - rn), "ok->red", len(rn - ro))
restored = {g for g in off["rest_refused"] if g not in on["rest_refused"]}
newly = {g for g in on["rest_refused"] if g not in off["rest_refused"]}
print("rests restored", len(restored), dict(collections.Counter(off["rest_refused"][g] for g in restored)), "newly refused", len(newly))
print("two_voice refused off", off["summary"]["two_voice_refused"], "on", on["summary"]["two_voice_refused"])
rb = collections.Counter("/".join(g.split("/")[1:5]) for g in restored)
print("bars with a restored rest", len(rb), "of them red->ok", sum(1 for b in rb if b in ro and b not in rn),
      "ok->red", sum(1 for b in rb if b not in ro and b in rn))
if len(sys.argv) > 4:
    census = json.load(open(sys.argv[3]))
    lab = {}
    for line in open(sys.argv[4]):
        if line.startswith("#") or "|" not in line:
            continue
        i, codes, _t = [x.strip() for x in line.split("|", 2)]
        lab[int(i)] = codes.split()
    seen = {}
    for i, e in enumerate(census):
        seen.setdefault(e["bar"], lab[i])
    for code in ("fv", "d"):
        bars = [b for b, c in seen.items() if code in c]
        print("label", code, len(bars), "| red off", sum(b in ro for b in bars), "red on", sum(b in rn for b in bars),
              "| split on", sum(b in tp for b in bars), "| with a restored rest", sum(b in rb for b in bars))
