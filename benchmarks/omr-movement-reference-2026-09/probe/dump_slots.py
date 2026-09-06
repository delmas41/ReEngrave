import json, sys, collections
r = json.load(open(sys.argv[1]))
ctx = r["contextual"]
print("reference:")
for s in ctx.get("reference", []):
    print("  ", json.dumps(s))
print()
for k in ("proposals", "unresolved_labels", "low_confidence_labels", "clef_fills"):
    v = ctx.get(k)
    if v:
        print(k, "=", json.dumps(v)[:2000])
print()
print("staff -> slot map:")
for page in r["pages"]:
    for sy in page.get("systems", []):
        sts = sorted(sy["staves"], key=lambda s: s["staff_geometry"]["line_ys_page"][0])
        row = [(st.get("staff_index"), st.get("slot_index"), st.get("instrument"),
                st.get("instrument_source")) for st in sts]
        print(f"  p{page['page_index']}.s{sy['system_index']}")
        for a in row:
            print("     staff_idx=%s slot=%s inst=%s src=%s" % a)
