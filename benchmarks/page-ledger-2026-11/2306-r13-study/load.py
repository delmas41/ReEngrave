"""2.306 r13 study, step 1: ONE saved gather per plate (the stems lane's r12 flag-ON gather, slices + its OFF/ON replays `rf12-*`) -> one small
pickle with everything both stem readers saw and said. No pipeline code runs here; nothing is gathered.

  OLD = the cell stem finder's `Q.STEM` rows (reader cv_lines) + the OFF arm's `Q.HEAD_STEM` / `Q.STEM_DIRECTION` verdicts (the cell join).
  NEW = the `Q.PAGE_STEM` rows / abstentions the page reader filed at GATHER, and its `stem` claims.

Usage: load.py SLICES_DIR RF_PREFIX OUT.pkl PAGES   (PAGES comma list: the frozen sample)
"""
import sys, json, pickle, collections

sl, rf, outp = sys.argv[1], sys.argv[2], sys.argv[3]
PAGES = {int(p) for p in sys.argv[4].split(",")}
pg = lambda s: int(s.split("/")[1])
KEEP = {"glyph_box", "notehead_class", "stem", "page_stem", "page_stroke", "claimed_area", "cell_box", "staff_lines", "mark_group", "page_mark",
        "glyph_conf", "page_mark_owner", "cell_staff_space", "head_stem_reach", "stroke"}
D = dict(heads={}, stems={}, pstem={}, pstrokes=collections.defaultdict(dict), claims=collections.defaultdict(list), cellbox={}, staff_lines={},
         pheads=collections.defaultdict(list), cls={}, conf={}, pmark={}, cellsp={}, pages=sorted(PAGES), cstrokes=collections.defaultdict(list), accs={})
for line in open(sl + "/observations.jsonl"):
    q0 = line.find('"quantity": "') + 13
    q = line[q0:line.find('"', q0)]
    if q not in KEEP:
        continue
    o = json.loads(line)
    s = o["subject"]
    if pg(s) not in PAGES:
        continue
    d = o.get("detail") or {}
    v = o.get("value")
    if q == "glyph_box":
        if (d.get("category") == "accidental" or str(v[0]).lower().startswith("accidental")) and d.get("bbox_page_px"):
            D["accs"].setdefault(pg(s), []).append(d["bbox_page_px"])
        if d.get("category") == "notehead" and d.get("bbox_page_px"):
            D["heads"][s] = dict(box=d["bbox_page_px"], can=v[1:5], reader=o.get("reader"), score=o.get("score"), name=v[0], detail={k: d[k] for k in d if k.startswith("ink_") or k in ("source", "witness")})
    elif q == "notehead_class":
        D["cls"][s] = v
    elif q == "stem":
        D["stems"][o["id"]] = dict(cell=s, reader=o.get("reader"), can=[float(t) for t in v[:4]])
    elif q == "page_stem":
        D["pstem"][s] = dict(read=True, value=v, **{k: d.get(k) for k in ("page_stroke", "direction", "side", "tip_y", "stem_box", "head", "how", "candidates", "held", "near", "margin")})
    elif q == "page_stroke":
        b = d.get("bbox_page_px")
        D["pstrokes"][pg(s)][int(d["ordinal"])] = dict(kind=v, box=b, touches=d.get("touches") or [], thick=d.get("thickness_spaces"), sp=d.get("staff_space_local_px"),
                                                      staff=d.get("staff"), length=d.get("length_spaces"), fill=d.get("fill"), comp=d.get("component"),
                                                      joined=d.get("joined_to"), cut=d.get("cut"))
    elif q == "claimed_area":
        row = dict(subject=s, value=v, reader=o.get("reader"), **{k: d.get(k) for k in ("owner", "unit", "standing", "source", "how", "page_strokes", "members", "oval", "scope", "cell", "heads", "direction", "stem_box", "area", "owner_glyph")})
        D["claims"][pg(s)].append(row)
        if o.get("reader") == "cv_page_heads" and d.get("members"):
            D["pheads"][pg(s)].append(dict(members=d["members"], oval=d.get("oval"), strokes=d.get("page_strokes") or [], how=d.get("how"), standing=d.get("standing")))
    elif q == "cell_box":
        D["cellbox"][s] = v
    elif q == "staff_lines":
        D["staff_lines"][s] = v
    elif q == "page_mark":
        if d.get("family") == "head":
            D["pmark"][s] = dict(id=v, members=d.get("members"), ink_px=d.get("ink_px"), why=d.get("why"))
    elif q == "cell_staff_space":
        D["cellsp"][s] = v
    elif q == "stroke":
        D["cstrokes"][s].append(dict(kind=v, box=d.get("stroke_box") or d.get("bbox"), ordinal=d.get("ordinal")))
for line in open(sl + "/abstentions.jsonl"):
    if '"page_stem"' not in line:
        continue
    o = json.loads(line)
    if o["quantity"] != "page_stem" or pg(o["subject"]) not in PAGES:
        continue
    d = o.get("detail") or {}
    D["pstem"][o["subject"]] = dict(read=False, value=None, reason=o.get("reason"), **{k: d.get(k) for k in ("head", "how", "candidates", "held", "near", "margin", "note")})

WANT = {"head_stem", "stem_direction", "notehead_is_not_a_notehead", "glyph_owner", "duration", "stem_value", "event", "unison_voices"}
for arm in ("off", "on"):
    B = json.load(open("%s.%s.json" % (rf, arm)))
    V = collections.defaultdict(dict)
    for v in B["verdicts"]:
        if v["q"] in WANT and v["s"].startswith("glyph/") and pg(v["s"]) in PAGES:
            V[v["s"]][v["q"]] = dict(o=v["o"], r=v.get("r"), v=v.get("v"), d=v.get("d"))
    D["V_" + arm] = dict(V)
    D["written_" + arm] = {h["rg"]: dict(type=h.get("type"), pitch=h.get("pitch"), blue=h.get("blue"), voice=h.get("voice"), chord=h.get("chord"))
                           for h in B["hosts"] if h.get("rg") and h.get("kind") == "note" and h.get("page") in PAGES}
    D["fates_" + arm] = {k: v for k, v in (B.get("fates") or {}).items() if pg(k) in PAGES}
    D["red_" + arm] = B.get("red")
    del B
for k in ("pstrokes", "claims", "pheads", "cstrokes"):
    D[k] = dict(D[k])
pickle.dump(D, open(outp, "wb"))
print(outp, {k: len(v) for k, v in D.items() if hasattr(v, "__len__")})
