"""DEVELOPMENT ONLY (not the proof): an approximate page stroke map built offline from the cell map's cells (no detector boxes, no arc erase),
pickled as map inputs in the same shape gather_dump.py writes. Usage: approx_map.py plate page"""
import os, pickle, sys, pathlib
sys.path.insert(0, os.getcwd())
from tools.omr.staged import cell_map as CM
from tools.omr.staged import page_strokes as PG
LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
plate, p = sys.argv[1], int(sys.argv[2])
pws, cells = CM.load_prepared(LIB / PDF[plate], [p], root=LIB / "_shared-records" / "cell-maps")[0]
asm = PG.assemble(pws, cells)
from tools.omr.staged import barline_columns as BC
sp = PG.page_spacing(pws)
cols = BC.fit_columns(pws)
PG.carve_columns(asm.canvas, cols, sp)
D = dict(page=p, erased=asm.canvas, sp=float(sp), raw=pws.page.binary, keep_whole=[], touch_boxes=[],
         staves=[dict(top_y=float(s.top_y), bottom_y=float(s.bottom_y), line_spacing_px=float(s.line_spacing_px), line_ys=[float(y) for y in s.line_ys],
                      staff_index=int(s.staff_index), system_index=int(getattr(s, "system_index", 0))) for s in pws.staves], local={}, scale=min(1.0, 16.0 / sp))
os.makedirs("/private/tmp/claude-501/lane-2.306-r25/approx", exist_ok=True)
pickle.dump(D, open(f"/private/tmp/claude-501/lane-2.306-r25/approx/{plate}_map_p{p}.pkl", "wb"), protocol=4)
print(plate, p, asm.canvas.shape, sp)
