"""ROADMAP 2.206 (read-only): the detector's glyph boxes on the frozen-sample pages, pulled from an existing gathered OFF record
(the detector reads the UNERASED cell, so its boxes do not depend on the eraser). usage: extract_boxes.py RECORD.json OUT.json PAGE..."""
import json, sys
import ijson
rec, out = sys.argv[1], sys.argv[2]
pages = {int(a) for a in sys.argv[3:]}
res = {}
with open(rec, "rb") as f:
    for r in ijson.items(f, "record.observations.item"):
        if r.get("quantity") != "glyph_box" or r.get("reader") != "detector":
            continue
        parts = r["subject"].split("/")          # glyph/page/system/staff/cell/ordinal
        if int(parts[1]) not in pages:
            continue
        cls, x, y, w, h = r["value"][:5]
        res.setdefault("/".join(parts[1:5]), []).append([cls, float(x), float(y), float(w), float(h), float(r.get("score") or 0)])
json.dump(res, open(out, "w"))
print(len(res), sum(len(v) for v in res.values()))
