"""usage: extract_boxes.py RECORD.json OUT.json -- every notehead glyph_box (class, page-px bbox) and every notehead_is_not_a_notehead
verdict (outcome/reason/value) of one gathered record, for choosing probe cases."""
import json, sys
import ijson
boxes, verd = {}, {}
with open(sys.argv[1], "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        if o["quantity"] == "glyph_box" and str(o["value"][0]).lower().startswith("notehead"):
            boxes[o["subject"]] = [o["value"][0], o["detail"]["bbox_page_px"]]
with open(sys.argv[1], "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        if v["quantity"] == "notehead_is_not_a_notehead":
            verd[v["subject"]] = [v.get("outcome"), v.get("reason"), v.get("value")]
json.dump({"boxes": boxes, "verdicts": verd}, open(sys.argv[2], "w"))
print(len(boxes), len(verd))
