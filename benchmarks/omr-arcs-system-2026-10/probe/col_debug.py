"""ROADMAP 2.166 -- print the composite ink runs of a few page columns (debug). usage: col_debug.py DOC PAGE Y0 Y1 X..."""
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-arcs-system-2026-10/probe")
import arc_debug  # noqa: E402
from tools.omr.staged import arcs_system as AS  # noqa: E402

pws, cells, local, detections = arc_debug.load(sys.argv[1], int(sys.argv[2]))
ink = AS.composite_ink(pws.page.binary, cells)
y0, y1 = int(sys.argv[3]), int(sys.argv[4])
for x in sys.argv[5:]:
    x = int(x)
    print(x, "composite", [(a + y0, b + y0) for a, b in AS._runs(ink[y0:y1, x])],
          "raw", [(a + y0, b + y0) for a, b in AS._runs(pws.page.binary[y0:y1, x] < 128)])
for c in cells:
    if c.bbox_page_px[0] <= int(sys.argv[5]) <= c.bbox_page_px[2] and c.bbox_page_px[1] <= y0 <= c.bbox_page_px[3]:
        print("cell", c.staff_index, c.measure_index, c.bbox_page_px, c.upscale_factor, AS._space_page(c))
for st in pws.staves:
    if abs(st.line_ys[0] - y0) < 200:
        print("staff", st.staff_index, [round(float(v), 1) for v in st.line_ys])
c = [c for c in cells if c.staff_index == 16 and c.measure_index == 4]
if c:
    print("canon lines", c[0].staff_line_ys_canonical, c[0].image.shape, c[0].image_no_staff.shape)
from tools.omr.staged import record as R  # noqa: E402
for c in cells:
    if c.staff_index in (16, 17) and c.measure_index in (2, 3, 4):
        key = local.get(c.staff_index)
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        for gi, d in enumerate(detections.get(sub.to_key(), ())):
            print(c.staff_index, c.measure_index, gi, d.smufl_name, [int(v) for v in AS._page_box(c, d)], round(d.confidence, 2))
