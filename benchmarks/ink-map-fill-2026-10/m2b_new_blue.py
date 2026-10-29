"""2.220 m2b (after Sean's trim, 2026-10-28): EVERY note blue in the ON file and not blue in the OFF file, matched by glyph key (the
same saved gather replayed both arms), each with the rule that marked it (`head_ink_guess` on the ON duration verdict) and a plain-words
reason; then blind tiles (`LR.cut_tiles`, one orange box): all if <= 12, else 12 spread over rules and plates, seed 2220.
usage: m2b_new_blue.py WORK OUTDIR"""
import collections, json, pathlib, random, sys
from tools.omr.staged import lane_report as LR

W, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])


def reason(rule, off, on):
    if rule == "head_ink_hollow_over_black":
        if off != on:
            return ("the detector said black and its fill reader could not read the box, but the head's own trimmed ink has a hole "
                    "and it stands on a stem, so it is written %s in blue (%s the other choice)" % (on, off))
        if on == "half":
            return ("the detector said black and its fill reader could not read the box; OFF already wrote half (the stem's value, a "
                    "later step); now the head's own trimmed ink has a hole, so the half is chosen at the head and written blue "
                    "(quarter the other choice)")
        return ("the detector said black and its fill reader could not read the box; the head's own trimmed ink has a hole but no stem "
                "of its own was found, so the %s is kept and written blue (half the other choice)" % on)
    return "marked blue by %s (not a head-ink rule)" % rule


rows = []
for plate in ("litolff", "brahms"):
    on = {h["rg"]: h for h in json.load(open(W / ("%s.on.symbols.json" % plate)))["hosts"] if h["kind"] == "note"}
    off = {h["rg"]: h for h in json.load(open(W / ("%s.off.symbols.json" % plate)))["hosts"] if h["kind"] == "note"}
    mini = json.load(open(W / ("%s.on.mini-record.json" % plate)))
    rule = {}
    for v in mini["verdicts"]:
        if v["quantity"] == "duration":
            g = (v.get("detail") or {}).get("head_ink_guess")
            if g and g.get("marks_blue", True):
                rule[v["subject"]] = g["rule"]
    for rg, h in sorted(on.items()):
        o = off.get(rg)
        if not h["blue"] or (o is not None and o["blue"]):
            continue
        r = rule.get(rg, "unexplained")
        rows.append(dict(plate=plate, page=h["page"], box=h["box"], rg=rg, kind="note", off=o["type"] if o else None, on=h["type"],
                         blue_off=bool(o and o["blue"]), blue_on=True, rule=r, role="case",
                         reason=reason(r, o["type"] if o else None, h["type"])))
count = collections.Counter((r["rule"], r["plate"]) for r in rows)
print("new blue notes:", len(rows), dict(count))
for r in rows:
    print(r["plate"], r["page"], r["rg"], r["off"], "->", r["on"], r["rule"])
items = list(rows)
if len(items) > 12:
    rng = random.Random(2220)
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["rule"], r["plate"])].append(r)
    for v in by.values():
        rng.shuffle(v)
    items, keys = [], sorted(by)
    while len(items) < 12:
        for k in keys:
            if by[k] and len(items) < 12:
                items.append(by[k].pop())
    rng.shuffle(items)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "all_new_blue.json").write_text(json.dumps({"count_by_rule_plate": {"%s/%s" % k: n for k, n in count.items()}, "rows": rows},
                                                  indent=1))
print(LR.cut_tiles(items, OUT))
