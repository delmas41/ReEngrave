"""ROADMAP 2.140 -- STREAM a saved record (never load it whole) and keep only the GATHER rows a beam-level
measurement needs, as a small JSON. STAGED GATHER rows, read-only.
    python3 stream_rows_2_140.py RECORD OUT.json [page,system,staff,cell ...]   (no cells = every cell)
"""
import json, sys
sys.path.insert(0, ".")
from tools.omr.staged import judged as J
import pathlib
Q = {"glyph_box", "stem", "beam_stroke", "beam_stroke_ink", "staff_lines", "cell_box", "beam_stem_join", "notehead", "head_stem_reach"}
rec, out = pathlib.Path(sys.argv[1]), sys.argv[2]
want = {tuple(int(x) for x in a.split(",")) for a in sys.argv[3:]}
rows, n = [], 0
for o in J.iter_array(rec, "observations"):
    n += 1
    if o.get("quantity") not in Q:
        continue
    p = o["subject"].split("/")
    if want:
        if p[0] in ("glyph", "cell") and len(p) >= 5:
            if tuple(int(x) for x in p[1:5]) not in want:
                continue
        elif p[0] == "staff":
            if not any(tuple(int(x) for x in p[1:4]) == w[:3] for w in want):
                continue
        else:
            continue
    rows.append({k: o.get(k) for k in ("id", "subject", "quantity", "value", "detail", "reader")})
json.dump(rows, open(out, "w"))
print(n, "scanned;", len(rows), "kept ->", out)
