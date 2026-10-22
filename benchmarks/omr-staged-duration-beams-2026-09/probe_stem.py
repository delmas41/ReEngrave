"""Why a beam was not associated with its note -- offline, on a saved record.

⚠️ NO BENCHMARK, NO SCORE. It counts, per narrowed duration, whether the
notehead's BOX overlaps a beam it was said to have none of, whether a stem is
attached to that head, and whether that stem meets the beam.

    python3 benchmarks/omr-staged-duration-beams-2026-09/probe_stem.py <staged.json>
"""
import json, sys
from collections import Counter
rec = json.load(open(sys.argv[1]))["record"]
obs = rec["observations"]
gbox = {o["subject"]: o for o in obs if o["quantity"] == "glyph_box"}
dur  = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "duration"}
beams, stems = {}, {}
for o in obs:
    if o["quantity"] == "beam_stroke" and o["reader"] == "cv_lines":
        beams.setdefault(o["subject"], []).append(o["detail"])
    elif o["quantity"] == "stem":
        stems.setdefault(o["subject"], []).append(o["detail"])

def cellof(g): return "cell/" + "/".join(g.split("/")[1:5])

cnt = Counter(); dxs = []
for g, v in dur.items():
    d = v.get("detail") or {}
    if d.get("beam_evidence") != "none_over_this_note": continue
    bx = gbox.get(g)
    if not bx: continue
    val = bx["value"]; x0, w = val[1], val[3]; x1 = x0 + w; xc = x0 + w/2
    bs = beams.get(cellof(g), [])
    if not bs: cnt["no cv beam in cell"] += 1; continue
    # box overlap with any beam
    ov = [b for b in bs if b["x0"] <= x1 and b["x1"] >= x0]
    # stem attached to this notehead (x-range within/adjacent to the head box)
    st = [s for s in stems.get(cellof(g), []) if s["x0"] <= x1 + 2 and s["x1"] >= x0 - 2]
    # stem meeting a beam in x
    stb = [(s, b) for s in st for b in bs if b["x0"] <= s["x1"] and b["x1"] >= s["x0"]]
    key = ("box_ov" if ov else "no_box_ov", "stem" if st else "no_stem",
           "stem_meets_beam" if stb else "-")
    cnt[key] += 1
    if ov:
        b = ov[0]
        dxs.append(round(min(abs(xc - b["x0"]), abs(xc - b["x1"])) / w, 2))
for k, n in cnt.most_common(): print(f"{n:5d}  {k}")
print("\ncentre-past-the-beam-end distance, in notehead widths:",
      Counter(dxs).most_common(10))
