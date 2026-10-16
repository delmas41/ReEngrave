"""ROADMAP 2.150 -- stream (ijson, bounded memory) the rows the rest census needs from a record into a small JSON.
usage: cache_2_150.py RECORD OUT.json   STAGED rows only; decides nothing.
Keeps: every glyph box (class, score, canonical x,y,w,h, bbox_page_px), every Q.STEM row (cell frame), staff
lines/spacing, cell boxes + cell staff space, the Q.REST rows, and the verdicts on rests, heads, flags and stems."""
import ijson, json, sys, resource

P, OUT = sys.argv[1], sys.argv[2]
out = {"boxes": {}, "stems": [], "staff": {}, "cells": {}, "verdicts": {}, "rest_rows": {}}
with open(P, "rb") as f:
    for it in ijson.items(f, "record.observations.item", use_float=True):
        q = it["quantity"]
        s = it["subject"]
        if q == "glyph_box":
            v = it["value"]
            out["boxes"][s] = [v[0], it["score"], v[1:5], (it.get("detail") or {}).get("bbox_page_px")]
        elif q == "stem":
            out["stems"].append([it["id"], s, it["value"]])
        elif q == "staff_lines":
            out["staff"].setdefault(s, {})["lines"] = it["value"]
        elif q == "staff_spacing":
            out["staff"].setdefault(s, {})["space"] = it["value"]
        elif q == "cell_box":
            out["cells"].setdefault(s, {})["box"] = it["value"]
        elif q == "cell_staff_space":
            out["cells"].setdefault(s, {})["space"] = it["value"]
        elif q == "rest":
            out["rest_rows"][s] = it["value"]
    f.seek(0)
    VQ = {"rest_is_not_a_rest", "notehead_is_not_a_notehead", "head_stem", "stem_head_contact",
          "flag_is_not_a_flag", "duration"}
    for it in ijson.items(f, "record.verdicts.item", use_float=True):
        q = it["quantity"]
        if q not in VQ:
            continue
        s = it["subject"]
        if q == "duration" and s not in out["rest_rows"]:
            continue
        val = it.get("value")
        det = it.get("detail") or {}
        if q == "duration" and isinstance(val, dict):
            val = val.get("beats")
        elif q == "stem_head_contact":
            val = [val, det.get("meets")]
        elif q == "head_stem":
            val = [val if isinstance(val, (str, bool, type(None))) else str(val)[:80],
                   {k: det.get(k) for k in ("stem_row", "stem_row_id", "stem", "side") if k in det}]
        out["verdicts"].setdefault(s, {})[q] = [it["outcome"], val, it.get("reason"), it.get("margin")]
print(len(out["boxes"]), len(out["stems"]), len(out["verdicts"]),
      resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1e6, "MB peak")
json.dump(out, open(OUT, "w"))
