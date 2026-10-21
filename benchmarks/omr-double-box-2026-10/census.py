"""2.185 census engine. usage: census.py EXTRACT.json PAIRS.json THRESH OUT.json
Clusters = connected components of boxes under page-pixel IoU >= THRESH (staff/brace boxes excluded). Each box gets a SOURCE
(reader/detail: production detector, 2.172 small view, 2.179 stem-end head, low-conf rescue, letter look) and a standing ADJUDICATE FATE
(readout.adjudicate_status's own rule, streamed): refused (reason) / given_away / kept / unjudged (no adjudicator claims the class)."""
import json, sys, collections
ex, pr, T, out = sys.argv[1:5]; T = float(T)
d = json.load(open(ex)); P = json.load(open(pr))["pairs"]
bx = [b for b in d["boxes"] if b["bbox"] and b["cls"] not in ("staff", "brace")]
sup = {v["supersedes"] for v in d["verdicts"] if v.get("supersedes")}
stand = collections.defaultdict(dict)       # subject -> quantity -> verdict (last non-superseded)
for v in d["verdicts"]:
    if v["id"] in sup: continue
    stand[v["subject"]][v["quantity"]] = v
def own_staff(s): return "staff/" + "/".join(s.split("/")[1:4])
def fate(b):
    s = b["subject"]; st = stand.get(s, {})
    for q, v in sorted(st.items()):
        if "_is_not_a" in q and v["outcome"] == "decided" and v["value"] is True:
            return "refused", q.replace("_is_not_an_", "").replace("_is_not_a_", "").replace("_is_not_a", "") + ":" + str(v["reason"])
    wr = st.get("notehead_is_a_whole_rest")
    if wr and wr["outcome"] == "decided" and wr["value"] is True: return "refused", "read_as_whole_rest:" + str(wr["reason"])
    ow = st.get("glyph_owner")
    if ow and ow["outcome"] == "decided" and isinstance(ow["value"], str) and ow["value"] not in ("own staff", own_staff(s)):
        return "given_away", "glyph_owner:" + str(ow["reason"])
    if any("_is_not_a" in q for q in st) or "glyph_owner" in st or "duration" in st: return "kept", ""
    return "unjudged", ""
def source(b):
    r = b["reader"]
    if r == "detector": return "prod"
    if r == "yolo_detector_view": return "view_small"
    if r == "yolo_rescue_stem_head": return "stem_end_head"
    if r == "yolo_rescue_lowconf": return "lowconf:" + str(b["witness"])
    return r
FAM = lambda c: ("head" if c.startswith("notehead") else "rest" if c.startswith("rest") else "accidental" if c.startswith("accidental") or c.startswith("key") and c != "keyboardPedalUp" and not c.startswith("keyboard")
    else "flag" if c.startswith("flag") else "dynamic" if c.startswith("dynamic") else "artic" if c.startswith("artic") else "clef" if c.startswith("clef")
    else "fermata" if c.startswith("fermata") else "arc" if c in ("slur", "tie") else "dot" if c in ("augmentationDot", "repeatDot") else "timesig" if c.startswith("timeSig")
    else c)
parent = list(range(len(bx)))
def find(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
edges = [p for p in P if p["iou"] >= T]
for p in edges: parent[find(p["a"])] = find(p["b"])
cl = collections.defaultdict(list)
for i in range(len(bx)): cl[find(i)].append(i)
cl = [sorted(v) for v in cl.values() if len(v) > 1]
def cell(s): return "/".join(s.split("/")[:5])
res = []
for c in cl:
    mem = []
    for i in c:
        b = bx[i]; f, why = fate(b)
        mem.append(dict(i=i, id=b["id"], subject=b["subject"], cls=b["cls"], fam=FAM(b["cls"]), score=b["score"], src=source(b), fate=f, why=why, bbox=b["bbox"]))
    res.append(dict(members=mem, cells=len({cell(m["subject"]) for m in mem}), staffs=len({"/".join(m["subject"].split("/")[:4]) for m in mem})))
json.dump(dict(thresh=T, nbox_scorable=len(bx), nbox_all=len(d["boxes"]), clusters=res, nedges=len(edges)), open(out, "w"))
print("T", T, "boxes", len(d["boxes"]), "scorable", len(bx), "clusters", len(res), "boxes in clusters", sum(len(c["members"]) for c in res))
