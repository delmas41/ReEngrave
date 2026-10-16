"""ROADMAP 2.144 -- stream (ijson, bounded memory) the rows needed to find head boxes standing on clef ink.
usage: cache_2_144.py RECORD OUT.json  [STAGED rows only; decides nothing]
Keeps: every glyph_box (class, score, bbox_page_px), every clef_glyph / clef_located / clef_position row
(small details only), staff_lines, and the notehead_is_not_a_notehead / duration verdicts."""
import ijson, json, sys, resource
P, OUT = sys.argv[1], sys.argv[2]
VQ = {"notehead_is_not_a_notehead", "duration"}
out = {"boxes": {}, "clef_glyph": [], "clef_located": [], "clef_position": [], "verdicts": {}, "stafflines": {}}
with open(P, "rb") as f:
    for it in ijson.items(f, "record.observations.item", use_float=True):
        q = it["quantity"]
        if q == "glyph_box":
            out["boxes"][it["subject"]] = [it["value"][0], it["score"], it["detail"].get("bbox_page_px")]
        elif q in ("clef_glyph", "clef_located", "clef_position"):
            out[q].append({"subject": it["subject"], "value": it["value"], "score": it["score"],
                           "detail": {k: v for k, v in (it.get("detail") or {}).items()
                                      if len(json.dumps(v, default=str)) < 400}})
        elif q == "staff_lines":
            out["stafflines"][it["subject"]] = it["value"]
    f.seek(0)
    for it in ijson.items(f, "record.verdicts.item", use_float=True):
        if it["quantity"] in VQ:
            val = it.get("value")
            if it["quantity"] == "duration" and isinstance(val, dict):
                val = [val.get("beats"), val.get("beam_levels")]
            out["verdicts"].setdefault(it["subject"], {})[it["quantity"]] = [it["outcome"], val, it.get("reason"), it.get("decider")]
print(len(out["boxes"]), len(out["clef_located"]), resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1e6, "MB peak")
json.dump(out, open(OUT, "w"), default=str)
