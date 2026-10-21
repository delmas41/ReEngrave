"""2.184: per-page scan facts: staff-line thickness / staff space, staff space px (600 dpi), for each page of a plate. usage: pagescan.py lit|bra FIRST LAST OUT.json"""
import json, sys, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
plate, a, b, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
res = {}
for p in range(a, b + 1):
    pw = detect_staves(render_page(PDF[plate], p, dpi=600))
    th = [s.median_line_thickness_px / s.line_spacing_px for s in pw.staves if s.median_line_thickness_px]
    sp = [s.line_spacing_px for s in pw.staves]
    res[p] = dict(n_staves=len(pw.staves), thick_over_space=round(st.median(th), 4) if th else None, space_px=round(st.median(sp), 2) if sp else None)
    print(plate, p, res[p], flush=True)
    json.dump(res, open(out, "w"))
