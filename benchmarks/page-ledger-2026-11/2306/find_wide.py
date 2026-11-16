"""2306 r11: written chords of 2+ heads on ONE page stem within one staff, spread >= 3.5 sp (an octave or wider). Usage: find_wide.py REC RFPREFIX SP"""
import sys, json, collections
rec, pre, SP = sys.argv[1], sys.argv[2], float(sys.argv[3])
R = json.load(open(rec))["record"]
gb = {}
grp = collections.defaultdict(lambda: collections.defaultdict(set))
stems = []
for o in R["observations"]:
    d = o.get("detail") or {}
    if o["quantity"] == "glyph_box" and d.get("bbox_page_px"):
        gb[o["subject"]] = d["bbox_page_px"]
    elif o["quantity"] == "page_stem":
        grp[int(o["subject"].split("/")[1])][d.get("head")].add(o["subject"])
    elif o["quantity"] == "claimed_area" and d.get("owner") == "stem" and o["value"] != "census":
        stems.append((int(o["subject"].split("/")[1]), d))
del R
D = json.load(open(pre + ".on.json"))
Wr = {h["rg"]: (h.get("pitch"), h.get("type")) for h in D["hosts"] if h.get("rg") and h.get("kind") == "note"}
out = []
for p, d in stems:
    hs = d.get("heads") or []
    if len(hs) < 2:
        continue
    keys = []
    for h in hs:
        mem = sorted(m for m in grp[p].get(h, ()) if m in gb)
        keys.append((mem, {"/".join(m.split("/")[:4]) for m in mem}))
    staffs = set.intersection(*[s for _, s in keys])
    if not staffs:
        continue
    stf = sorted(staffs)[0]
    mine = [[m for m in mem if m.startswith(stf + "/")][0] for mem, _ in keys]
    cys = [(gb[m][1] + gb[m][3]) / 2 for m in mine]
    spread = (max(cys) - min(cys)) / SP
    if spread >= 3.5 and all(m in Wr for m in mine):
        out.append((round(spread, 1), p, d["direction"], len(d.get("page_strokes") or []), mine, [Wr[m] for m in mine]))
out.sort(reverse=True)
for o in out[:10]:
    print(o)
