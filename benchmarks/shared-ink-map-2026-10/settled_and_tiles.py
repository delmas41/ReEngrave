"""ROADMAP 2.202 milestone: count `beams_from_strokes.settled` per plate and draw the 12 blind tiles.

usage: settled_and_tiles.py REPORT_OUT_DIR TILES_OUT_DIR

Reads the two arms' mini-records written by `lane_report` (`REPORT_OUT_DIR/work/<plate>.{off,on}.mini-record.json`: every glyph_box row and every
duration verdict). Counts, per plate, the FIRST duration verdicts of the ON arm by `detail.beams_from_strokes.settled` (absent = the stroke map could
not speak) and the box reasons; lists the heads whose live duration differs OFF vs ON. Tiles (docs/measuring.md: blind, one orange box, nothing of ours
drawn): 9 changed heads (>= 3 `box_flag` = hook-as-flag, the rest from the narrowed / candidate / disagreement groups, both plates), + 3 controls (one
unchanged decided beamed head from the ON arm, the re-shown 2.170 tile 2 and 2.153 tile 4). NO TWO TILES ON ONE INK: a tile is skipped when its box,
grown by one staff space, meets the grown box of a tile already chosen on the same page.
"""
import collections
import json
import pathlib
import random
import sys

sys.path.insert(0, ".")
from tools.omr.staged import lane_report as LR

rep, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
PRINT = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.198/out/print")
rng = random.Random(2202)
counts, changed, same_ok = {}, collections.defaultdict(list), collections.defaultdict(list)


def lv(v):
    if v is None:
        return None
    if v.get("outcome") == "decided":
        return ("decided", (v.get("value") or {}).get("beam_levels"))
    return (v.get("outcome"), tuple(sorted((c.get("value") or {}).get("beam_levels", -1) for c in v.get("candidates") or [])))


for plate in ("litolff", "brahms"):
    try:
        off = json.load(open(rep / "work" / ("%s.off.mini-record.json" % plate)))
        on = json.load(open(rep / "work" / ("%s.on.mini-record.json" % plate)))
    except FileNotFoundError:
        continue
    boxes = LR.glyph_boxes(on["observations"])
    live_off, live_on = LR._live(off["verdicts"], ("duration",)), LR._live(on["verdicts"], ("duration",))
    c = collections.Counter()
    reasons = collections.Counter()
    for v in on["verdicts"]:
        if v["quantity"] != "duration" or v.get("supersedes"):
            continue
        d = (v.get("detail") or {}).get("beams_from_strokes")
        key = d["settled"] if d else "(map could not speak or flag path not reached)"
        c[key] += 1
        for bx in (d or {}).get("boxes") or []:
            reasons[bx.get("reason") or bx.get("support")] += 1
    counts[plate] = dict(first_duration_verdicts=sum(c.values()), settled=dict(c), box_reasons=dict(reasons))
    for (sub, q), v in live_on.items():
        d = None
        for x in on["verdicts"]:       # the first verdict of the chain carries the detail
            if x["subject"] == sub and x["quantity"] == "duration" and not x.get("supersedes"):
                d = (x.get("detail") or {}).get("beams_from_strokes")
                break
        b = boxes.get(sub)
        if not b or b["page"] is None:
            continue
        item = dict(plate=plate, page=b["page"], box=b["box"], rg=sub, kind="note", settled=d["settled"] if d else None,
                    off=lv(live_off.get((sub, q))), on=lv(v))
        if d and lv(live_off.get((sub, q))) != lv(v):
            changed[("flag" if "box_flag" in d["settled"] else "other")].append(item)
        elif d and d["settled"] == "agrees" and v.get("outcome") == "decided" and (v.get("value") or {}).get("beam_levels"):
            same_ok[plate].append(item)
    counts[plate]["heads_whose_duration_changed"] = sum(len(x) for x in changed.values() if x and x[0]["plate"] == plate) if False else \
        sum(1 for g in changed.values() for i in g if i["plate"] == plate)

chosen = []


def near(a, b):
    if a["plate"] != b["plate"] or a["page"] != b["page"]:
        return False
    u = LR.PLATES[a["plate"]]["unit"]
    return not (a["box"][2] + u < b["box"][0] - u or b["box"][2] + u < a["box"][0] - u or a["box"][3] + u < b["box"][1] - u or b["box"][3] + u < a["box"][1] - u)


def take(pool, n, role, side):
    pool = list(pool)
    rng.shuffle(pool)
    # alternate plates so both are shown
    pool.sort(key=lambda i: i["plate"])
    pool = [p for p in pool]
    rng.shuffle(pool)
    got = 0
    for it in pool:
        if got >= n:
            break
        if any(near(it, c) for c in chosen):
            continue
        chosen.append(dict(it, role=role, side=side))
        got += 1
    return got


nflag = take(changed["flag"], 4, "case", "hook_as_flag")
nother = take(changed["other"], 9 - len(chosen), "case", "changed")
if len(chosen) < 9:
    take(changed["flag"], 9 - len(chosen), "case", "hook_as_flag")
nctl = take([i for p in same_ok for i in same_ok[p]], 1, "control", "unchanged")


def reshown(tag, n, plate="litolff"):
    """A tile Sean has already answered, drawn again. The 2.170 manifest carries the page box; the 2.153 one does not (its glyph is on a sample page, so
    the box is the ON mini-record's own glyph_box)."""
    m = json.load(open(PRINT / tag / "manifest.json"))
    if isinstance(m["tiles"], list):
        t = [x for x in m["tiles"] if x["n"] == n][0]
        g, box = t.get("subject") or t.get("glyph"), t["page_box"]
    else:
        a = json.load(open(PRINT / tag / "answers.json"))
        g = [x for x in a["tiles"] if x["n"] == n][0]["glyph"]
        on = json.load(open(rep / "work" / ("%s.on.mini-record.json" % plate)))
        box = LR.glyph_boxes(on["observations"])[g]["box"]
    chosen.append(dict(plate=plate, page=int(g.split("/")[1]), box=box, rg=g, kind="note", role="control", side="reshown:%s tile %d" % (tag, n)))


reshown("2.170-review", 2)
reshown("2.153-review", 4)
rng.shuffle(chosen)
res = LR.cut_tiles(chosen, out)
(out / "settled_counts.json").write_text(json.dumps(dict(counts=counts, tiles=res, n_changed=dict((k, len(v)) for k, v in changed.items())), indent=1))
print(json.dumps(dict(counts=counts, tiles=res, n_changed={k: len(v) for k, v in changed.items()}, flag_tiles=nflag), indent=1))
