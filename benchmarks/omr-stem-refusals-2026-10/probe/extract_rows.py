"""2.169 step 0: stream one big record ONCE and keep only the rows the stem probes read (cell_box, glyph_box, cv stems, the standing
head_stem verdict per glyph, the notehead_class rows). Writes a small json. usage: extract_rows.py litolff|brahms OUT.json"""
import json
import sys

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec as RC  # noqa: E402

LIB = RC.LIB
PATH = {"litolff": LIB + "beethoven5-litolff-mvt1-whole-20261016-night.record.json",
        "brahms": LIB + "brahms1-breitkopf-mvt1-whole-20261016-night.record.json"}
doc, out = sys.argv[1:3]
cell_box, glyph, stems, nh = {}, {}, {}, set()
with RC.lock():
    for o in RC.items(PATH[doc], "observations"):
        q = o["quantity"]
        if q == "cell_box":
            cell_box[o["subject"]] = o["value"]
        elif q == "glyph_box":
            glyph[o["subject"]] = o["value"]
        elif q == "stem" and o["reader"] == "cv_lines":
            stems.setdefault(o["subject"], []).append(o["value"])
        elif q == "notehead_class":
            nh.add(o["subject"])
    print("obs done", len(cell_box), len(glyph), flush=True)
    hs = {}
    for v in RC.items(PATH[doc], "verdicts"):
        if v["quantity"] == "head_stem":
            hs[v["subject"]] = [v["outcome"], v.get("reason")]
json.dump(dict(cell_box=cell_box, glyph=glyph, stems=stems, notehead=sorted(nh), head_stem=hs), open(out, "w"))
print("DONE", len(hs))
