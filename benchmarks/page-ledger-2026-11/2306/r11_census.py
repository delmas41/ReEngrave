"""2306 r11: the page-stem census over a gather (summed page census rows) and the contact readings (page heads, not glyph copies) by how the column
reached the head -- through bare stem / a stem piece ('stem') or only a touching chord mate ('chord_mate'). Usage: r11_census.py REC.json"""
import sys, json, collections
R = json.load(open(sys.argv[1]))["record"]
tot = collections.Counter()
via = collections.Counter()
seen = set()
for o in R["observations"]:
    d = o.get("detail") or {}
    if o["quantity"] == "claimed_area" and o.get("reader") == "cv_page_stems" and o["value"] == "census":
        for k, v in d.items():
            if isinstance(v, int) and not isinstance(v, bool):
                tot[k] += v
    elif o["quantity"] == "page_stem" and d.get("how") == "contact_with_head_ink":
        key = (o["subject"].split("/")[1], d.get("head"))
        if key in seen:
            continue
        seen.add(key)
        c = next((c for c in d.get("candidates") or () if c.get("why") == "contact" and c.get("stroke") == d.get("page_stroke")), {})
        via[c.get("via", "?")] += 1
for a in R["abstentions"]:
    pass
print({k: tot[k] for k in sorted(tot) if not k.startswith("run_") and k not in ("seconds",)})
print("contact readings (page heads filed on their own staff) by via:", dict(via))
