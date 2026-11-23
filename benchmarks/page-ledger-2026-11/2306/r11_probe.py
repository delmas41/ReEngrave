"""2306 r11 probe: for given glyphs, the page head's own strokes (2.290 claim), their boxes, and every stroke that TOUCHES them (page map `touches`),
with kind / box / contact count; the vertical candidates' x against the head ink's extent. Usage: r11_probe.py REC.json glyph ..."""
import sys, json, collections
rec, gs = sys.argv[1], sys.argv[2:]
pages = {int(g.split("/")[1]) for g in gs}
R = json.load(open(rec))["record"]
st = collections.defaultdict(dict)
claim_of = {}
gbox = {}
for o in R["observations"]:
    q, d = o["quantity"], o.get("detail") or {}
    if not o["subject"].startswith(("page/", "glyph/")) or int(o["subject"].split("/")[1]) not in pages:
        continue
    p = int(o["subject"].split("/")[1])
    if q == "page_stroke":
        st[p][int(d["ordinal"])] = dict(kind=o["value"], box=d["bbox_page_px"], touches=d.get("touches"), comp=d.get("component"), L=d.get("length_spaces"),
                                        sp=d.get("staff_space_local_px"))
    elif q == "claimed_area" and d.get("source") == "page_head_one" and o["value"] != "census":
        for m in d.get("members") or ():
            claim_of[m] = d
    elif q == "glyph_box" and d.get("bbox_page_px"):
        gbox[o["subject"]] = d["bbox_page_px"]
for g in gs:
    p = int(g.split("/")[1])
    d = claim_of.get(g)
    print("==", g, "box", [round(v) for v in gbox.get(g, [])], "claim strokes", d and d["page_strokes"], "oval", d and d.get("oval"), "marked", d and d.get("marked"))
    if not d:
        continue
    hs = d["page_strokes"]
    xs = [st[p][i]["box"] for i in hs if i in st[p]]
    if xs:
        hx0, hx1 = min(b[0] for b in xs), max(b[2] for b in xs)
        hy0, hy1 = min(b[1] for b in xs), max(b[3] for b in xs)
        print("   head ink extent", [round(hx0), round(hy0), round(hx1), round(hy1)])
    for i in hs:
        s = st[p].get(i)
        if not s:
            continue
        print("   own", i, s["kind"], [round(v) for v in s["box"]], "touches", s["touches"])
        for j, c in s["touches"] or ():
            t = st[p].get(int(j))
            if t and int(j) not in hs:
                sp = t["sp"] or 16
                sxc = (t["box"][0] + t["box"][2]) / 2
                print("      touch", j, t["kind"], [round(v) for v in t["box"]], "contact", c, "len", t["L"],
                      "x rel head ink (0=left,1=right): %.2f" % ((sxc - hx0) / max(1, hx1 - hx0)))
