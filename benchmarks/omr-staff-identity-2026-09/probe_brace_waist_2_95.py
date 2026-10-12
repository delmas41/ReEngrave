"""ROADMAP 2.95 -- a cheap raster probe for a PAIR BRACE (measure only, builds nothing).

A brace over staves k,k+1 pinches to a cusp in the gap between them, a little
left of the thick systemic bracket line; a gap between unbraced staves has no
ink there. Per gap: find the left edge of the thick line, take the max windowed
ink in [-1.0, -0.25] staff spaces left of it, call it a waist at >= 0.4.
Checked by eye on Brahms pdf 26 (both systems) and page 1; threshold not tuned.
A brace over THREE staves would put its cusp at the middle staff, not in a gap,
so it is not what this reports (it shows as a horn pair with no gap waist).

    python3 probe_brace_waist_2_95.py brahms 1 2 ... 26   (writes scratch json)
"""
import sys, json
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-add8a563390858360')
import numpy as np
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

PDFS = {
    'brahms': '/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf',
    'litolff': '/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf',
}
S = '/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-rhythm-reading-roadmap-8d6847/517fbc7c-df77-4b16-99dd-52e092de5b8f/scratchpad/'
doc, pages = sys.argv[1], [int(a) for a in sys.argv[2:]]
TAU = 0.4
out = {}
for pg in pages:
    page = render_page(PDFS[doc], pg, dpi=600)
    pws = detect_staves(page)
    ink = page.binary == 0
    by = {}
    for s in sorted(pws.staves, key=lambda s: s.top_y):
        by.setdefault(s.system_index, []).append(s)
    for si, st in sorted(by.items()):
        sp = float(np.median([s.line_spacing_px for s in st]))
        xm = int(np.median([s.x_start for s in st]))
        gaps = []
        detail = []
        for k in range(len(st) - 1):
            ya, yb = int(st[k].bottom_y) + 3, int(st[k + 1].top_y) - 3
            if yb <= ya:
                continue
            lo = int(xm - 1.6 * sp)
            prof = ink[ya:yb, lo:int(xm + sp)].mean(axis=0)
            solid = np.where(prof >= 0.95)[0]
            if len(solid) == 0:
                continue
            L = lo + int(solid[0])                      # left edge of the thick line in this gap
            win = ink[ya:yb, int(L - 1.0 * sp):int(L - 0.25 * sp)].mean(axis=0)
            cusp = float(win.max()) if len(win) else 0.0
            detail.append(round(cusp, 2))
            if cusp >= TAU:
                gaps.append(k)
        out['%d/%d' % (pg, si)] = {'n': len(st), 'gap_cusps': gaps}
        print(pg, si, len(st), 'brace waists in gaps:', gaps, flush=True)
json.dump(out, open(S + 'brace2_%s.json' % doc, 'w'))
