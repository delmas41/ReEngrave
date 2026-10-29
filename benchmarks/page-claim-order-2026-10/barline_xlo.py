"""x_start and spacing of a system's staves: barline_xlo.py PDF page system."""
import sys
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
pws = detect_staves(render_page(sys.argv[1], int(sys.argv[2]), dpi=600))
for s in pws.staves:
    if s.system_index == int(sys.argv[3]):
        print(s.staff_index, s.x_start, s.x_end, round(s.line_spacing_px, 1))
