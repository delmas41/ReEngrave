"""2306 r12: what the record says about given glyphs -- detector box (class, score), every row filed on the glyph (quantity, reader, value), the
page head claim holding it, the page stem reading, every claim on the page strokes under its box (owner, source, standing), the 2.290 head reader's
view (page head census rows naming it), and its verdicts in a replay. Usage: fake_facts.py REC RFPREFIX glyph ..."""
import sys, json, collections
rec, pre, gs = sys.argv[1], sys.argv[2], sys.argv[3:]
R = json.load(open(rec))["record"]
pages = {int(g.split("/")[1]) for g in gs}
gb, rows = {}, collections.defaultdict(list)
strokes = collections.defaultdict(dict)
claims = collections.defaultdict(list)
for o in R["observations"]:
    s, q, d = o["subject"], o["quantity"], (o.get("detail") or {})
    if s in gs:
        rows[s].append((q, o.get("reader"), str(o.get("value"))[:60], {k: v for k, v in d.items() if k in ("how", "category", "family", "owner", "page_stroke", "direction", "via")}))
        if q == "glyph_box":
            gb[s] = d.get("bbox_page_px")
    if s.startswith("page/") and int(s.split("/")[1]) in pages:
        p = int(s.split("/")[1])
        if q == "page_stroke":
            strokes[p][int(d["ordinal"])] = (o["value"], d["bbox_page_px"])
        elif q == "claimed_area" and o["value"] != "census":
            claims[p].append(d)
for a in R["abstentions"]:
    if a["subject"] in gs:
        rows[a["subject"]].append(("ABSTAIN " + a["quantity"], a.get("reader"), a.get("reason"), {k: v for k, v in (a.get("detail") or {}).items() if k in ("how", "note")}))
del R
B = json.load(open(pre + ".on.json"))
for g in gs:
    p = int(g.split("/")[1])
    b = gb.get(g)
    print("==", g, "box", b and [round(v) for v in b])
    for r in rows[g]:
        print("   row", r)
    under = {o for o, (k, sb) in strokes[p].items() if b and sb[0] <= b[2] and sb[2] >= b[0] and sb[1] <= b[3] and sb[3] >= b[1]}
    print("   strokes under its box:", {o: strokes[p][o] for o in sorted(under)})
    for d in claims[p]:
        hit = set(d.get("page_strokes") or ()) & under
        mem = g in (d.get("members") or ())
        if hit or mem:
            print("   claim", d.get("owner"), d.get("source"), d.get("how"), d.get("standing"), "strokes", sorted(hit), "names it" if mem else "")
    for v in B["verdicts"]:
        if v["s"] == g and v["q"] in ("notehead_is_not_a_notehead", "glyph_owner", "head_stem", "duration", "notehead_class", "glyph_kind"):
            print("   verdict", v["q"], v["o"], v["r"], str(v["v"])[:60])
    print("   fate", B["fates"].get(g), [(h.get("pitch"), h.get("type")) for h in B["hosts"] if h.get("rg") == g])
