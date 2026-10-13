"""List every gathered glyph box on a page whose page box overlaps a window.
usage: PYTHONPATH=. python3 near.py RECORD PAGE x0 y0 x1 y1  (ROADMAP 2.105)"""
import sys

from tools.omr.staged.readout import load_run

run = load_run(sys.argv[1])
page = int(sys.argv[2])
w = [float(v) for v in sys.argv[3:7]]
for g in sorted(run.glyphs.values(), key=lambda g: (g.box_page or (0, 0, 0, 0))):
    if g.page != page or g.box_page is None:
        continue
    b = g.box_page
    if b[2] < w[0] or b[0] > w[2] or b[3] < w[1] or b[1] > w[3]:
        continue
    print(g.key, g.cls, [round(v) for v in b], g.score and round(g.score, 2))
