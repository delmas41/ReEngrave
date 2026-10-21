"""2.182a: stream a whole-movement record and keep only what the rest-pair count needs.
usage: extract.py RECORD.json OUT.json   -> verdicts rest_is_not_a_rest (+ their duplicate detail), rest glyph_box rows (class, conf, bbox_page_px)."""
import json, sys, ijson
rec, out = sys.argv[1:3]
verd, boxes, rests = [], {}, {}
with open(rec, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        if v.get("quantity") == "rest_is_not_a_rest":
            verd.append(v)
with open(rec, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        q = o.get("quantity")
        if q == "glyph_box" and isinstance(o.get("value"), list) and str(o["value"][0]).startswith("rest"):
            boxes[o["subject"]] = dict(id=o["id"], value=o["value"], score=o.get("score"), bbox=(o.get("detail") or {}).get("bbox_page_px"))
        elif q == "rest":
            rests[o["subject"]] = o
json.dump(dict(verdicts=verd, boxes=boxes, rests=rests), open(out, "w"))
print(len(verd), len(boxes), len(rests))
