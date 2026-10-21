"""ROADMAP 2.182 -- every bar an arm split as two parts: reason, red OFF/ON, the parts' glyphs, the guessed notes, red words.

usage: c2_split_bars.py OFF.json ON.json"""
import json
import sys

off, on = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
ro, rn = set(off["red_bars"]), set(on["red_bars"])
rr = {"/".join(str(r[k]) for k in ("page", "system", "staff", "cell")): r for r in on["red_rows"]}
for b, v in sorted(on["two_parts"].items()):
    r = rr.get(b) or {}
    print(b, v["reason"][10:], "red off/on", b in ro, b in rn, v["voices"], v["guessed"], r.get("words"), r.get("two_voice"))
