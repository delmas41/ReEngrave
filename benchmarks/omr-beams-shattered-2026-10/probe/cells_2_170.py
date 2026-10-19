"""2.170 step 2c: stream one night record's observations+abstentions ONCE and keep, for every CELL holding a narrowed-beam glyph
(extract_2_170 output), the rows the beam readers read. usage: cells_2_170.py DOC EX.json OUT.json"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec as RC  # noqa: E402

PATH = {"litolff": RC.LIB + "beethoven5-litolff-mvt1-whole-20261018-night.record.json",
        "brahms": RC.LIB + "brahms1-breitkopf-mvt1-whole-20261018-night.record.json"}
QS = {"cell_box", "glyph_box", "stem", "beam_stroke", "beam_stroke_ink", "stem_tip_ink", "beam_stem_levels", "beam_stem_join",
      "cell_staff_space", "notehead_class", "staff_lines", "cell_frame"}
doc, exf, out = sys.argv[1:4]
ex = json.load(open(exf))
cells = {"cell/" + "/".join(s.split("/")[1:5]) for s in ex["narrowed"]}
rows = defaultdict(list)
qcount = defaultdict(int)
for kind in ("observations", "abstentions"):
    for o in RC.items(PATH[doc], kind):
        p = o["subject"].split("/")
        if len(p) < 5:
            continue
        ck = "cell/" + "/".join(p[1:5])
        if ck not in cells:
            continue
        qcount[o["quantity"]] += 1
        if o["quantity"] in QS:
            o.pop("basis", None)
            o["_kind"] = kind[:3]
            rows[ck].append(o)
json.dump(dict(rows=rows, qcount=qcount), open(out, "w"))
print("DONE", len(rows), dict(qcount))
