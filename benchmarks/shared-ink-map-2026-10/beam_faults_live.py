"""ROADMAP 2.202b (read-only, NO gather): re-run the stroke map on the sample pages in two readings of a horizontal stroke's thickness and file them: OLD (erased raster only = the 2.202 reading) and A (the ink the eraser took out
of the stroke's own columns put back; stroke_map.THICKNESS_FROM_UNERASED). usage: beam_faults_live.py PLATE OUT.json [PAGE ...]   (rows keyed like the record: page/system/staff/cell, ordinal)."""
import json, sys, time
sys.path.insert(0, ".")
from tools.omr.staged import pipeline, gather as G, stroke_map as S
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
PAGES = {"litolff": [2, 4, 6, 8, 9, 10, 11, 16], "brahms": [0, 4, 5, 8, 12, 14, 19, 25]}
plate, out = sys.argv[1], sys.argv[2]
pages = [int(a) for a in sys.argv[3:]] or PAGES[plate]
res = {}
for pg in pages:
    pws, cells = pipeline.prepare_pages(PDF[plate], [pg], dpi=600)[0]
    loc = G.gather_geometry(G.Log(), pws)
    for c in cells:
        key = loc.get(c.staff_index)
        g = G._cell_grid(c)
        if key is None or not g:
            continue
        arms = {}
        for name, a in dict(old=False, A=True).items():
            S.THICKNESS_FROM_UNERASED = a
            arms[name] = S.map_strokes(c.image_no_staff, g[1] * 2, c.staff_line_ys_canonical, c.binary)
        if arms["old"] is None:
            continue
        ck = "%d/%s/%s/%s" % (pg, key[0], key[1], c.measure_index)
        rows = []
        for i, s0 in enumerate(arms["old"].strokes):
            if s0.kind not in ("horizontal", "curve"):
                continue
            nv = sum(1 for j, _c in s0.touches if arms["old"].strokes[j].kind == "vertical" and arms["old"].strokes[j].length_sp <= 8.0)
            rows.append(dict(i=i, kind=s0.kind, nv=nv, len=s0.length_sp, box=s0.box, mid=(s0.end_steps[0] + s0.end_steps[1]) / 2.0,
                             old=s0.thickness_sp, A=arms["A"].strokes[i].thickness_sp))
        if rows:
            res[ck] = rows
    print(pg, len(res), time.strftime("%H:%M:%S"), flush=True)
    json.dump(res, open(out, "w"))
S.THICKNESS_FROM_UNERASED = True
