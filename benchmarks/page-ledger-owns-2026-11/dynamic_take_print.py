"""Print the per-claim table of a dynamic_take_probe JSON (plain text)."""
import json
import sys

d = json.load(open(sys.argv[1]))
for pg, v in d["pages"].items():
    print("PAGE", pg)
    for r in v["claims"]:
        print([round(x) for x in r["box"]], r["source"], r["text"], r["letter"], "wh_sp", r["box_w_sp"], r["box_h_sp"], "inside", r["inside_px"], "owned",
              r["owned_px"], "own", r["own_px"], "TAKEN", r["taken_px"], r["taken_by_kind"], "strokes", r["owned_strokes"], "contested", r["contested_strokes"],
              "marks_left_out", len(r["left_out"] or []), r["id"])
        for c in r["comps"]:
            print("      ", c)
    pl = v.get("plant")
    if pl:
        res = pl.get("result") or {}
        print("PLANT", {k: pl[k] for k in pl if k != "result"}, {k: res.get(k) for k in ("taken_px", "taken_by_kind", "taken_unboxed", "taken_boxed", "owned_px", "inside_px", "comps")})
