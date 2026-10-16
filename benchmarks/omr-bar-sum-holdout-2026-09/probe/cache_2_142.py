"""ROADMAP 2.142 -- stream (ijson, bounded memory: no whole-record load) the rows 2.142 needs from a record into a small JSON.
usage: cache_2_142.py RECORD OUT.json   STAGED rows only; decides nothing."""
import ijson, json, sys, resource
P, OUT = sys.argv[1], sys.argv[2]
VQ = {"notehead_is_not_a_notehead", "notehead_is_a_whole_rest", "notehead_is_an_eighth_rest", "rest_is_not_a_rest",
      "duration", "stem_direction", "head_stem", "notehead_is_a_duplicate_box"}
out = {"boxes": {}, "verdicts": {}, "notes": {}}
with open(P, "rb") as f:
    for it in ijson.items(f, "record.observations.item", use_float=True):
        if it["quantity"] == "glyph_box":
            out["boxes"][it["subject"]] = [it["value"][0], it["score"], it["detail"].get("bbox_page_px")]
    f.seek(0)
    for it in ijson.items(f, "record.verdicts.item", use_float=True):
        if it["quantity"] in VQ:
            val = it.get("value")
            if it["quantity"] == "duration" and isinstance(val, dict):
                val = [val.get("beats"), val.get("beam_levels")]
            elif it["quantity"] == "head_stem":
                val = bool(val)
            out["verdicts"].setdefault(it["subject"], {})[it["quantity"]] = [it["outcome"], val, it.get("reason"), it.get("decider")]
print(len(out["boxes"]), len(out["verdicts"]), resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1e6, "MB peak")
json.dump(out, open(OUT, "w"))
