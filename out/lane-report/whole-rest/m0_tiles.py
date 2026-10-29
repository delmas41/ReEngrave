"""whole-rest m0: cut 12 BLIND tiles (LR.cut_tiles, one neutral orange box, nothing of ours drawn). The box is a staff-height window 10
staff spaces wide, centred on where the file's mark was (or on the bar's middle where there was none), so it gives away nothing about
what is there. The key (outside the tile folder) says the case of each tile.
usage: m0_tiles.py OUTDIR"""
import json, pickle, random, sys, pathlib, collections
import numpy as np
from tools.omr.staged import lane_report as LR
from tools.omr.preprocessing import render_page
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
W = pathlib.Path("out/lane-report/whole-rest")
D = {}
for pl, pk in (("litolff", "lit"), ("brahms", "brah")):
    d = pickle.load(open(W / (pk + ".pkl"), "rb"))
    F = json.load(open(W / ("fates.%s.json" % pl)))
    obs = collections.defaultdict(dict)
    for o in d["observations"]:
        obs[o["quantity"]][o["subject"]] = o
    ver = collections.defaultdict(dict)
    for v in d["verdicts"]:
        ver[v["quantity"]][v["subject"]] = v
    D[pl] = dict(obs=obs, ver=ver, F=F)
random.seed(229)

def staff_of(key):
    p = key.split("/")
    return "staff/%s/%s/%s" % (p[0], p[1], p[2])

def mk(pl, key, centre, case, role="case", extra=None):
    """centre = page-px (cx, cy) or None -> the cell's middle."""
    d = D[pl]; u = LR.PLATES[pl]["unit"]
    cell = d["obs"]["cell_box"]["cell/" + key]["value"]
    lines = d["obs"]["staff_lines"][staff_of(key)]["value"]
    cx = centre[0] if centre else (cell[0] + cell[2]) / 2
    box = [cx - 5 * u, min(lines) - 0.6 * u, cx + 5 * u, max(lines) + 0.6 * u]
    return dict(plate=pl, page=int(key.split("/")[0]), box=box, role=role, case=case, bar=key, **(extra or {}))

items = []
def bars(pl, kind):
    return [b for b in D[pl]["F"]["bars"] if b["kind"] == kind]
def found(pl, key):
    o = D[pl]["obs"]["empty_bar_rest_search"].get("cell/" + key)
    return o
# case 1: no box, the search FOUND a rest (decided, unwritten)
for pl, n in (("litolff", 2), ("brahms", 2)):
    c = [b for b in bars(pl, "no_head_or_rest_glyph") if (found(pl, b["key"]) or {}).get("value") is True]
    for b in random.sample(c, n):
        bb = found(pl, b["key"])["detail"]["bbox_page_px"]
        items.append(mk(pl, b["key"], ((bb[0] + bb[2]) / 2, 0), "1_no_box_search_found_a_rest"))
# case 1b: no box, the search found nothing
c = [b for b in bars("litolff", "no_head_or_rest_glyph") if (found("litolff", b["key"]) or {}).get("value") is False]
b = random.choice(c); items.append(mk("litolff", b["key"], None, "1b_no_box_search_found_nothing"))
# case 2: restWhole refused
def refused(pl, reason):
    r = []
    for b in bars(pl, "all_glyphs_judged_not_symbols"):
        gs = [g for g in b["glyphs"] if g[1] == "restWhole" and g[2] == "not_a_rest:" + reason]
        if gs:
            r.append((b, gs[0]))
    return r
def glyph_centre(pl, key, idx):
    sub = "glyph/%s/%s" % (key, idx)
    bb = D[pl]["obs"]["glyph_box"][sub]["detail"]["bbox_page_px"]
    return ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
for pl, reason, n in (("litolff", "rest_touches_two_staff_lines", 1), ("brahms", "rest_touches_two_staff_lines", 1),
                      ("litolff", "rest_off_center", 1), ("brahms", "rest_off_center", 1)):
    b, g = random.choice(refused(pl, reason))
    items.append(mk(pl, b["key"], glyph_centre(pl, b["key"], g[0]), "2_restWhole_refused:" + reason))
# case 3: read as a black head, refused at export as ink_is_a_whole_rest
b = random.choice(bars("litolff", "whole_rest_ink_refused"))
g = [g for g in b["glyphs"] if g[2] == "ink_is_a_whole_rest"][0]
items.append(mk("litolff", b["key"], glyph_centre("litolff", b["key"], g[0]), "3_head_refused_ink_is_a_whole_rest"))
# control A: a bar the file WRITES as a whole rest (a kept restWhole, bar not unread)
unread = {"cell/" + b["key"] for b in D["litolff"]["F"]["bars"]}
kept = [s for s, v in D["litolff"]["ver"]["rest_is_not_a_rest"].items() if v["value"] is False
        and D["litolff"]["obs"]["glyph_box"][s]["value"][0] == "restWhole" and ("cell/" + "/".join(s.split("/")[1:5])) not in unread]
s = random.choice(kept); key = "/".join(s.split("/")[1:5])
bb = D["litolff"]["obs"]["glyph_box"][s]["detail"]["bbox_page_px"]
items.append(mk("litolff", key, ((bb[0] + bb[2]) / 2, 0), "control_written_whole_rest", role="control"))
# control B: a bar with NO ink between the staff lines: not-found, no-glyph bars, least ink in the middle third (staff lines masked)
cand = []
cache = {}
for pl in ("litolff",):
    for b in bars(pl, "no_head_or_rest_glyph"):
        o = found(pl, b["key"])
        if (o or {}).get("value") is not False:
            continue
        cand.append((pl, b["key"]))
random.shuffle(cand)
best = None
for pl, key in cand[:60]:
    pg = int(key.split("/")[0]); u = LR.PLATES[pl]["unit"]
    if pg not in cache:
        cache.clear(); cache[pg] = np.asarray(render_page(str(LR.LIB / LR.PLATES[pl]["pdf"]), pg, dpi=600).rgb).mean(axis=2) < 140
    dk = cache[pg]
    cell = D[pl]["obs"]["cell_box"]["cell/" + key]["value"]; lines = D[pl]["obs"]["staff_lines"][staff_of(key)]["value"]
    x0 = int(cell[0] + 0.8 * u); x1 = int(cell[2] - 0.8 * u)
    reg = dk[int(min(lines) - 0.5 * u):int(max(lines) + 0.5 * u), x0:x1].copy()
    for ly in lines:
        reg[int(ly - min(lines) + 0.5 * u - 0.3 * u):int(ly - min(lines) + 0.5 * u + 0.3 * u), :] = False
    if reg.size == 0:
        continue
    frac = float(reg.mean())
    if best is None or frac < best[0]:
        best = (frac, pl, key)
print("emptiest no-glyph bar: ink fraction %.4f %s" % (best[0], best[2]))
items.append(mk(best[1], best[2], None, "control_bar_with_no_ink(ink_frac=%.4f)" % best[0], role="control"))
random.shuffle(items)
print(len(items), collections.Counter(i["case"].split(":")[0] for i in items))
res = LR.cut_tiles(items, out)
print(res)
