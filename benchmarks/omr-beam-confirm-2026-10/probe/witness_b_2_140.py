"""ROADMAP 2.140 -- witness B (detector stack box taller than one beam), computed with the PRODUCT helper `rhythm.stack_box_excess_beams`
from the streamed GATHER rows, for every decided single-level eighth of a movement. Adds `B` to the count file.
    python3 witness_b_2_140.py ROWS.json COUNT.json OUT.json"""
import json, sys, collections
sys.path.insert(0, ".")
from tools.omr.staged.adjudicators.rhythm import stack_box_excess_beams, BEAM_STACK_BOX_EXCESS_MIN
rows = json.load(open(sys.argv[1])); cnt = json.load(open(sys.argv[2]))
cv, yolo, th, stems, scale = collections.defaultdict(list), collections.defaultdict(list), {}, collections.defaultdict(list), {}
for r in rows:
    q, s = r["quantity"], r["subject"]
    cell = tuple(int(x) for x in s.split("/")[1:5]) if s.split("/")[0] in ("cell", "glyph") else None
    if q == "beam_stroke_ink" and (r["detail"] or {}).get("thickness_px"):
        th[r["detail"]["beam_row_id"]] = r["detail"]["thickness_px"]
    elif q == "glyph_box":
        v, bp = r["value"], (r["detail"] or {}).get("bbox_page_px")
        if bp and v[3] > 0 and cell not in scale:
            sc = (bp[2] - bp[0]) / v[3]; scale[cell] = (sc, bp[0] - v[1] * sc)
for r in rows:
    q, s = r["quantity"], r["subject"]
    if s.split("/")[0] != "cell":
        continue
    cell = tuple(int(x) for x in s.split("/")[1:5])
    if q == "beam_stroke":
        d = r["detail"]; t = (d["x0"], d["x1"], tuple(r["value"]), th.get(r["id"]))
        (cv if r["reader"] == "cv_lines" else yolo)[cell].append((r["id"], t))
    elif q == "stem" and r["reader"] == "cv_lines":
        stems[cell].append(r["value"])
out, c = {}, collections.Counter()
for g, m in cnt.items():
    if "cols" not in m:
        continue
    cell = tuple(int(x) for x in g.split("/")[1:5])
    sc = scale.get(cell)
    if sc is None:
        continue
    # canonical x of this note's stem = the CV stem whose page centre is nearest m['stem_x']
    best = min(stems[cell], key=lambda v: abs(sc[1] + (v[0] + v[2] / 2) * sc[0] - m["stem_x"]), default=None)
    if best is None:
        continue
    x = best[0] + best[2] / 2
    ex, how = stack_box_excess_beams([t for _i, t in cv[cell]], [(a, b, bx) for _i, (a, b, bx, _t) in yolo[cell]], x)
    m["B"] = None if ex is None else round(ex, 3)
    m["B_how"] = how
    nA = max(len(m["cols"]["left"]), len(m["cols"]["right"]))
    m["A_runs"] = nA
    c[("A>=2" if nA >= 2 else "A<2", "B>=min" if (ex is not None and ex >= BEAM_STACK_BOX_EXCESS_MIN) else ("B-none" if ex is None else "B<min"))] += 1
    out[g] = m
json.dump(out, open(sys.argv[3], "w"))
for k, v in sorted(c.items()): print(k, v)
