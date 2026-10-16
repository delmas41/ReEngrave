"""ROADMAP 2.145 -- stream (ijson, bounded memory) the rows 2.145 needs from a record into a small JSON.
usage: cache_2_145.py RECORD OUT.json   STAGED rows only; decides nothing.
Keeps: glyph boxes (class, score, bbox_page_px), every Q.UNBOXED_REST_SHAPE row (the 2.99 gather files
covered clusters too), Q.STEM observations, and the verdicts the count needs."""
import ijson, json, sys, resource
P, OUT = sys.argv[1], sys.argv[2]
VQ = {"notehead_is_not_a_notehead", "notehead_is_a_whole_rest", "notehead_is_an_eighth_rest", "rest_is_not_a_rest",
      "duration", "head_stem", "unboxed_ink_is_a_rest", "notehead_is_a_duplicate_box"}
out = {"boxes": {}, "shape": [], "stems": [], "verdicts": {}}
with open(P, "rb") as f:
    for it in ijson.items(f, "record.observations.item", use_float=True):
        q = it["quantity"]
        if q == "glyph_box":
            out["boxes"][it["subject"]] = [it["value"][0], it["score"], it["detail"].get("bbox_page_px")]
        elif q == "unboxed_rest_shape" and it.get("state") != "declined":
            d = it.get("detail") or {}
            if "width_spaces" in d:
                out["shape"].append({"subject": it["subject"], **d})
        elif q == "stem":
            d = it.get("detail") or {}
            out["stems"].append({"subject": it["subject"], "value": it.get("value"),
                                 "detail": {k: d.get(k) for k in ("bbox_page_px", "x", "y", "w", "h")}})
    f.seek(0)
    for it in ijson.items(f, "record.verdicts.item", use_float=True):
        if it["quantity"] in VQ:
            val = it.get("value")
            if it["quantity"] == "duration" and isinstance(val, dict):
                val = [val.get("beats"), val.get("beam_levels")]
            elif it["quantity"] == "head_stem":
                val = bool(val)
            out["verdicts"].setdefault(it["subject"], {})[it["quantity"]] = [it["outcome"], val, it.get("reason"), it.get("decider")]
print(len(out["boxes"]), len(out["shape"]), len(out["stems"]), len(out["verdicts"]),
      resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1e6, "MB peak")
json.dump(out, open(OUT, "w"))
