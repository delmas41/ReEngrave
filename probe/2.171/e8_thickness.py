"""2.171 probe 8: how thick is a staff line, in staff spaces and in the pixels the detector is shown? (stroke thickness is the other thing that changes when a
crop is shown smaller). Median black vertical run through the 5 line positions of the subject bars' staves, from the page's binary raster.
usage: e8_thickness.py lit|bra"""
import json
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.preprocessing import render_page            # noqa: E402
from tools.omr.staff_detector import detect_staves          # noqa: E402

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
              "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
plate = sys.argv[1]
sample = [tuple(s) for s in json.load(open(str(ROOT) + "/probe/2.167d/data/%s_sample.json" % plate))]
pages = sorted({s[0] for s in sample})[:6]
th = []
sp_all = []
for p in pages:
    pws = detect_staves(render_page(PDF[plate], p, dpi=600))
    B = pws.page.binary
    for st in pws.staves:
        if len(st.line_ys) < 5:
            continue
        sp_all.append(st.line_spacing_px)
        xs = np.linspace(st.x_start + 50, st.x_end - 50, 40).astype(int)
        for y in st.line_ys:
            for x in xs:
                col = B[int(y) - 12:int(y) + 13, x]
                ink = col > 0 if col.max() > 1 else col > 0
                # binary may be 0/255 ink=255 or ink=0: take the minority colour as ink
                if ink.mean() > 0.5:
                    ink = ~ink
                c = len(col) // 2
                if not ink[c]:
                    continue
                a = c
                while a > 0 and ink[a - 1]:
                    a -= 1
                b = c
                while b < len(col) - 1 and ink[b + 1]:
                    b += 1
                th.append((b - a + 1))
sp = statistics.median(sp_all)
print("%s: staff space %.1f page px; staff-line thickness median %.1f page px = %.2f staff spaces (p25 %.1f, p75 %.1f); at the detector's 16 px staff space a line is %.1f px thick" % (
    plate, sp, statistics.median(th), statistics.median(th) / sp, np.percentile(th, 25), np.percentile(th, 75), 16 * statistics.median(th) / sp))
