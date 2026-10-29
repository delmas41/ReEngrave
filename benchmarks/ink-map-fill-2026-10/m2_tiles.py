"""2.220 m2: 12 blind tiles on the file changes (`LR.cut_tiles`, one orange box). Drawn with seed 2220 from the ON file's notes the
consumer marked (`head_ink_guess` on the duration verdict, matched to the ON file's note host by glyph key): every value change
(hollow over an unread black), then half_not_hollow and not_one_head, plus 2 controls (plain notes, unchanged both arms).
usage: m2_tiles.py WORK OUTDIR"""
import json, pathlib, random, sys
from tools.omr.staged import lane_report as LR

W, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
rng = random.Random(2220)
pools = {"head_ink_hollow_over_black": [], "head_ink_half_not_hollow": [], "head_ink_not_one_head": [], "control": []}
for plate in ("litolff", "brahms"):
    on = {h["rg"]: h for h in json.load(open(W / ("%s.on.symbols.json" % plate)))["hosts"] if h["kind"] == "note"}
    off = {h["rg"]: h for h in json.load(open(W / ("%s.off.symbols.json" % plate)))["hosts"] if h["kind"] == "note"}
    mini = json.load(open(W / ("%s.on.mini-record.json" % plate)))
    rule = {}
    for v in mini["verdicts"]:
        if v["quantity"] == "duration":
            g = (v.get("detail") or {}).get("head_ink_guess")
            rule[v["subject"]] = g["rule"] if g else None
    for rg, h in sorted(on.items()):
        o = off.get(rg)
        if o is None:
            continue
        it = dict(plate=plate, page=h["page"], box=h["box"], rg=rg, kind="note", off=o["type"], on=h["type"], blue_off=o["blue"],
                  blue_on=h["blue"])
        r = rule.get(rg)
        if r:
            pools[r].append(dict(it, rule=r, role="case"))
        elif not h["blue"] and not o["blue"] and o["type"] == h["type"]:
            pools["control"].append(dict(it, rule=None, role="control"))
for k, v in pools.items():
    print(k, len(v))
items = list(pools["head_ink_hollow_over_black"])
for k, n in (("head_ink_half_not_hollow", 2), ("head_ink_not_one_head", 2)):
    items += rng.sample(pools[k], n)
items += rng.sample(pools["control"], 12 - 2 - len(items)) if len(items) < 10 else []
items += rng.sample([c for c in pools["control"] if c not in items], 2)
items = items[:12]
rng.shuffle(items)
print(LR.cut_tiles(items, OUT))
