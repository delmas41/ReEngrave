"""2.167e probe 7: whole-movement compact extract of every glyph's box, the few observations and the STANDING (last in file order)
verdict of each quantity that the four questions need. READ-ONLY. usage: e7_extract.py RECORD OUT.json"""
import ijson
import sys
import json
import time

path, out = sys.argv[1], sys.argv[2]
t0 = time.time()
OBSQ = {"glyph_box", "glyph_conf", "notehead_ink", "notehead_stem_cross_ink", "head_stem_reach", "aug_dot", "flag", "rest",
        "dot_staff_position", "notehead_staff_position", "dot_stroke_ink", "stacked_head_fit", "head_oval", "rest_ink_contact",
        "unboxed_rest_shape", "articulation_mark", "system_arc"}
VERQ = {"duration", "head_stem", "stem_value", "stem_direction", "rest_is_not_a_rest", "dot_role", "notehead_is_not_a_notehead",
        "glyph_owner", "flag_is_not_a_flag", "head_ink_is_a_rest", "unboxed_ink_is_a_rest", "notehead_is_a_whole_rest",
        "notehead_is_an_eighth_rest", "notehead_position", "tie_pair"}
G = {}
n = 0
with open(path, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        sub = o["subject"]
        if not sub.startswith("glyph/") or o["quantity"] not in OBSQ:
            continue
        g = G.setdefault(sub, {})
        q = o["quantity"]
        if q == "glyph_box":
            d = o.get("detail") or {}
            g["cls"] = o["value"][0]
            g["bb"] = [round(v, 1) for v in (d.get("bbox_page_px") or [])]
            g["reader"] = o.get("reader")
        elif q == "glyph_conf":
            g["conf"] = round(o["value"], 3)
        elif q == "notehead_ink":
            g["ink"] = o["value"]
            det = o.get("detail") or {}
            g["ink_net"] = (det.get("ink_net") or {}).get("best")
            g["ink_win"] = (det.get("ink_raw") or {}).get("windows")
        elif q == "notehead_stem_cross_ink":
            g["cross"] = o["value"]
        elif q == "head_stem_reach":
            g["reach"] = o["value"]
        elif q in ("aug_dot", "flag", "rest", "articulation_mark", "system_arc"):
            g[q] = o["value"]
        elif q in ("dot_staff_position", "notehead_staff_position", "dot_stroke_ink", "head_oval", "rest_ink_contact", "unboxed_rest_shape"):
            g[q] = o["value"] if not isinstance(o["value"], float) else round(o["value"], 3)
        elif q == "stacked_head_fit":
            g["stacked"] = o["value"]
        n += 1
t1 = time.time()
with open(path, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        sub = v["subject"]
        if not sub.startswith("glyph/") or v["quantity"] not in VERQ:
            continue
        g = G.setdefault(sub, {})
        val = v.get("value")
        if isinstance(val, (dict, list)):
            val = json.loads(json.dumps(val)) if len(json.dumps(val)) < 200 else str(val)[:120]
        det = v.get("detail") or {}
        keep = {k: det[k] for k in ("duplicate_of", "duplicate_disagrees_with", "head", "owner", "articulation", "mark_tip") if k in det}
        if v["quantity"] == "head_stem" and "stems" in det:
            keep["stems"] = [[s.get("x_frac"), s.get("flush"), s.get("stem_box")] for s in det["stems"].values()]
        if v["quantity"] == "head_stem" and "voices" in det:
            keep["voices"] = det["voices"]
        g.setdefault("V", {})[v["quantity"]] = [v["outcome"][:4], v.get("reason"), val, v.get("decider"), v["id"], keep]
json.dump(G, open(out, "w"), default=float)
print("glyphs", len(G), "obs", n, "pass1", round(t1 - t0), "total", round(time.time() - t0))
