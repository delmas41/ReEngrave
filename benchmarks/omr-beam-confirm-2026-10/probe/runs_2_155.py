"""ROADMAP 2.155 -- PROBE: which `detect_stems` filter refused the stem of each 2.153 tile (4/14/16), on the cell prepared as
the gather prepares it (`pipeline.prepare_pages`). Prints every vertical-run candidate within 1.5 spaces of the head with its
outcome, the cell width and the edge margin. usage: runs_2_155.py"""
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-missing-notes-2026-09/probe")
from l282_stemhyp import pick_cell, to_canon  # noqa: E402
from tools.omr import line_detection as LD  # noqa: E402
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
T = [(4, 2, (2295.8, 3157.6, 2321.8, 3180.8)), (14, 1, (1167.2, 2612.5, 1189.2, 2630.3)),
     (16, 10, (992.8, 2964.6, 1017.7, 2982.6))]
for n, page, hb in T:
    (pws, cells), = prepare_pages(PDF, [page])
    c = pick_cell(cells, (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2)
    sp = LD._staff_line_spacing(c)
    em = max(int(round(sp * 0.8)), 12)
    cb = to_canon(c, *hb)
    cand = []
    LD.detect_stems(c, candidates_out=cand)
    print(f"tile {n}: cell bbox {c.bbox_page_px} width {c.width} canon, space {sp:.1f}, edge margin {em} -> right limit "
          f"{c.width - em}; head canon x {cb[0]:.0f}-{cb[2]:.0f} ({(c.width - cb[2]) / sp:.2f} sp from the right edge)")
    for v in sorted(cand, key=lambda v: v.x):
        if v.x + v.w >= cb[0] - 1.5 * sp and v.x <= cb[2] + 1.5 * sp:
            print(f"   run x {v.x}-{v.x + v.w} y {v.y}-{v.y + v.h} ({v.w / sp:.2f} x {v.h / sp:.2f} sp) -> {v.outcome}")

# ---- arm check (flag off vs on), heads = the record's own notehead boxes of that cell (canonical) ----
if len(sys.argv) > 1:
    import json
    rec = json.load(open(sys.argv[1]))
    for n, page, hb in T:
        (pws, cells), = prepare_pages(PDF, [page])
        c = pick_cell(cells, (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2)
        g = {4: "glyph/2/1/7/12/", 14: "glyph/1/0/8/2/", 16: "glyph/10/1/6/3/"}[n]
        heads = [tuple(o["value"][1:5]) for o in rec["observations"] if o["quantity"] == "glyph_box"
                 and o["subject"].startswith(g) and (o.get("detail") or {}).get("category") == "notehead"]
        for arm in (LD.STEM_FINDER_STAGED_DEFAULT, LD.STEM_FINDER_STAGED_DEFAULT | {"edge_head"}):
            st = LD.detect_lines(c, noteheads=heads, rescue_tall_beams=True, stem_finder=arm)
            print(f"tile {n} {'ON ' if 'edge_head' in arm else 'OFF'} heads {len(heads)} stems "
                  f"{[(s.x_canonical, s.x_canonical + s.width_canonical) for s in st['stems']]} beams "
                  f"{[(b.x_canonical, b.x_canonical + b.width_canonical, b.y_canonical) for b in st['beams']]}")
