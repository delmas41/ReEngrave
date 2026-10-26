"""2.206b: where does the meter template match in each header cell, OFF vs ON?  usage: meter_x.py PAGE_INDEX [staff...]
Reads OMR_ERASER_FIX from the environment (set it before running)."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr.measure_extractor import detect_barlines
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.staff_header import header_cells_for_page, header_windows_for_page
from tools.omr.time_signature_locator import locate_time_signature
from tools.omr.key_signature_template import claimed_header_edge
import os
from tools.omr.header_ink import staff_metrics
LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
plate, pi = sys.argv[1], int(sys.argv[2])
page = render_page(LIB / PDF[plate], pi, dpi=600)
pws = detect_barlines(detect_staves(page))
cells = header_cells_for_page(pws, windows=header_windows_for_page(pws))
for si in sorted(cells):
    c = cells[si]; tr = {}
    xm = claimed_header_edge(c) if os.environ.get('SLOT')=='1' else None
    r = locate_time_signature(c, trace=tr, x_min_canonical=xm)
    m = staff_metrics(c)
    sp = m[0] if m else None
    top = tr.get("scores", [{}])[:2]
    print(si, "sys", pws.staves[si].system_index if hasattr(pws.staves[si], "system_index") else "?",
          "W", c.image.shape[1], "sp", round(sp or 0, 1),
          "xmin", None if xm is None else round(xm/100,2), "read", (r.raw, round(r.score, 4), r.x_canonical, round(r.x_canonical / sp, 2)) if r else None, "top", top)
