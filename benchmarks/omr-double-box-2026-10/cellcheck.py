"""2.185: measure the cross-staff cause: does the OTHER member's cell rectangle contain this box's centre? usage: cellcheck.py RECORD.json ROWS.json
cell_box rows (page px rectangles) are streamed from the record; for every cross-staff production ink the test is run on every pair of members from different staves."""
import ijson, json, sys, collections
rec, rows = sys.argv[1:3]
cb = {}
with open(rec, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        if o.get("quantity") == "cell_box": cb[o["subject"]] = o["value"]
rows = json.load(open(rows))
def cell(s): return "/".join(s.split("/")[:5]).replace("glyph", "cell", 1)
def staff(s): return "/".join(s.split("/")[:4])
n = both = one = none = 0
for x in rows:
    if x["base"] != "cross_staff_crop_overlap": continue
    ms = x["members"]
    for i, a in enumerate(ms):
        for b in ms[i + 1:]:
            if staff(a["subject"]) == staff(b["subject"]): continue
            ca, cbx = cb.get(cell(a["subject"])), cb.get(cell(b["subject"]))
            if not ca or not cbx: continue
            def inside(m, c):
                cx = (m["bbox"][0] + m["bbox"][2]) / 2; cy = (m["bbox"][1] + m["bbox"][3]) / 2
                return c[0] <= cx <= c[2] and c[1] <= cy <= c[3]
            k = inside(a, cbx) + inside(b, ca)
            n += 1; both += k == 2; one += k == 1; none += k == 0
print("cross-staff member pairs", n, "| each box's centre lies inside the OTHER staff's cell rectangle too:", both, "| one way only:", one, "| neither:", none)
