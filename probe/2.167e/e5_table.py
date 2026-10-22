"""2.167e probe 5: one line per box on a cell: class conf bbox | head_stem | stem_value | duration (outcome:reason:value). READ-ONLY.
usage: e5_table.py CELLS.json CELLKEY [minconf]"""
import json
import sys

d = json.load(open(sys.argv[1]))[sys.argv[2]]
minc = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
box = {}
for o in d["obs"]:
    if o["quantity"] == "glyph_box":
        box.setdefault(o["subject"], {}).update(cls=o["value"][0], bb=[round(v) for v in o["detail"]["bbox_page_px"]], reader=o["reader"])
    elif o["quantity"] == "glyph_conf":
        box.setdefault(o["subject"], {})["conf"] = round(o["value"], 2)
    elif o["quantity"] in ("notehead_staff_position", "head_stem_reach", "dot_staff_position", "aug_dot", "flag", "rest", "notehead_ink", "head_oval", "rest_ink_contact", "unboxed_rest_shape"):
        v = o["value"]
        if isinstance(v, float):
            v = round(v, 2)
        box.setdefault(o["subject"], {}).setdefault("o", []).append("%s=%s" % (o["quantity"][:14], v))
V = {}
for v in d["verd"]:
    V.setdefault(v["subject"], []).append(v)
for o in d["obs"]:
    if o["subject"].startswith("cell/") and o["quantity"] == "stem":
        print("STEM", o["id"], o["value"], "beam_levels", [x["value"] for x in d["obs"] if x["quantity"] == "beam_stem_levels" and x["detail"].get("stem_row_id") == o["id"]])
for o in d["obs"]:
    if o["subject"].startswith("cell/") and o["quantity"] == "beam_stroke":
        print("BEAM", o["id"], o["value"])
for v in d["verd"]:
    if v["subject"].startswith("cell/") and v["quantity"] in ("event", "voices"):
        print(v["quantity"].upper(), json.dumps(v["value"])[:300], v["reason"])
for sub in sorted(box, key=lambda s: int(s.split("/")[-1])):
    b = box[sub]
    if b.get("conf", 1) < minc or b.get("cls", "").startswith(("ledger", "staff", "arpeg", "accid")):
        continue
    out = []
    for q in ("head_stem", "stem_value", "duration", "dot_role", "rest_is_not_a_rest", "flag_is_not_a_flag", "glyph_owner", "notehead_is_an_eighth_rest", "head_ink_is_a_rest", "unboxed_ink_is_a_rest"):
        for v in V.get(sub, []):
            if v["quantity"] == q:
                out.append("%s %s:%s:%s" % (q[:10], v["outcome"][:4], v.get("reason"), json.dumps(v.get("value"))[:70]))
    print(sub.split("/")[-1], b.get("cls"), b.get("conf"), b.get("bb"), b.get("reader"), " ".join(b.get("o", [])))
    for x in out:
        print("      ", x)
