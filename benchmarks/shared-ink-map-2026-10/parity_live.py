"""ROADMAP 2.195: re-run the stroke map on the sample pages WITHOUT a gather (it reads the raster alone) and score it against the existing
rows saved from a gathered record. For the parameter sweep: usage parity_live.py PLATE ROWS.json [NAME=VALUE ...] (NAME a stroke_map constant)."""
import json, sys, time
sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/shared-ink-map-2026-10")
from collections import defaultdict
from tools.omr.staged import pipeline, gather as G, stroke_map as S
import stroke_parity as P
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
PAGES = {"litolff": [2, 4, 6, 8, 9, 10, 11, 16], "brahms": [0, 4, 5, 8, 12, 14, 19, 25]}


def live_strokes(plate, pages=None):
    strokes, cpu, n = defaultdict(list), 0.0, 0
    for pg in (pages or PAGES[plate]):
        pws, cells = pipeline.prepare_pages(PDF[plate], [pg], dpi=600)[0]
        loc = G.gather_geometry(G.Log(), pws)
        for c in cells:
            key = loc.get(c.staff_index)
            g = G._cell_grid(c)
            if key is None or not g:
                continue
            t = time.process_time()
            r = S.map_strokes(c.image_no_staff, g[1] * 2, c.staff_line_ys_canonical, c.binary)
            cpu += time.process_time() - t
            if r is None:
                continue
            up, cb = c.upscale_factor, c.bbox_page_px
            ck = (str(pg), str(key[0]), str(key[1]), str(c.measure_index))
            for st in r.strokes:
                x, y, w, h = st.box
                strokes[ck].append(dict(value=st.kind, detail=dict(stroke_box=[x, y, w, h], bbox_page_px=[
                    cb[0] + x / up, cb[1] + y / up, cb[0] + (x + w) / up, cb[1] + (y + h) / up])))
                n += 1
    return strokes, cpu, n


if __name__ == "__main__":
    plate, rows = sys.argv[1], json.load(open(sys.argv[2]))
    for a in sys.argv[3:]:
        k, v = a.split("=")
        setattr(S, k, float(v))
    strokes, cpu, n = live_strokes(plate)
    res = P.parity(rows, strokes)
    import os
    if os.environ.get('PARITY_OUT'):
        json.dump({k: dict(n=v['n'], covered=v['covered'], misses=v['misses'][:600]) for k, v in res.items()}, open(os.environ['PARITY_OUT'], 'w'))
    print(" ".join(("%s=%.1f%%" % (k, 100.0 * v["covered"] / max(1, v["n"]))) if "_miss_is_" not in k else ("%s=n%d" % (k, v["n"])) for k, v in res.items()), "| strokes", n, "cpu %.1fs" % cpu)
