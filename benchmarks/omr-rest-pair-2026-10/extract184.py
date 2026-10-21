"""2.184: stream a whole-movement record; keep every rest glyph_box observation IN FULL (reader, frame, detail), every rest_is_not_a_rest
verdict, and the cell frame of each. usage: extract184.py RECORD.json OUT.json"""
import json, sys, ijson
rec, out = sys.argv[1:3]
verd, boxes = [], []
with open(rec, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        if v.get("quantity") == "rest_is_not_a_rest":
            verd.append(v)
with open(rec, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        if o.get("quantity") == "glyph_box" and isinstance(o.get("value"), list) and str(o["value"][0]).startswith("rest"):
            boxes.append(o)
json.dump(dict(verdicts=verd, boxes=boxes), open(out, "w"))
print(len(verd), len(boxes))
