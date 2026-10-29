import json, sys, pathlib
WT = '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a44a05b0ad517dce3'
sys.path.insert(0, WT)
import numpy as np, cv2
from tools.omr.staged.gather import head_interior_white
S = pathlib.Path('/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-agent-manager-workflow-356c39/7e1ea73e-2fd3-4d6c-a450-36868f7e14c0/scratchpad')
from tools.omr.preprocessing import render_page
LIB = pathlib.Path('/Users/seanjohnson/Desktop/ReEngrave/library')
PDF = {'litolff': 'editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf',
       'brahms': 'editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf'}
tiles = []
for plate, pages in (('litolff', (4, 6)), ('brahms', (5, 14))):
    d = json.load(open(S / ('lit.json' if plate == 'litolff' else 'bra.json')))
    rows = [r for r in json.load(open(S / f'm_{plate}.json')) if r['p'] in pages and r['written'] == 2.0]
    base = 0
    for p in pages:
        f = S / f'page_{plate}_{p}.npy'
        if not f.exists():
            np.save(f, render_page(str(LIB / PDF[plate]), p, dpi=600).binary)
        pg = np.load(f)
        for r in [r for r in rows if r['p'] == p]:
            b = d['boxes'][r['s']]['page']
            iw = head_interior_white(pg, (b[0], b[1], b[2] - b[0], b[3] - b[1]))
            r['box_slit'] = iw['rows_share'] if iw else None
            base += (r['box_slit'] or 0) >= 0.18
            if (r['slit'] or 0) < 0.18:
                x0, y0 = int(b[0]) - 40, int(b[1]) - 40
                c = cv2.cvtColor(pg[y0:y0 + 100, x0:x0 + 110].copy(), cv2.COLOR_GRAY2BGR)
                cv2.rectangle(c, (int(b[0]) - x0, int(b[1]) - y0), (int(b[2]) - x0, int(b[3]) - y0), (0, 140, 255), 1)
                tiles.append(cv2.resize(c, (220, 200), interpolation=cv2.INTER_NEAREST))
                print(plate, r['s'], 'trim slit', r['slit'], 'box slit', r['box_slit'], r['noh'], r['ext'], r['box_sp'])
    print(plate, 'halves', len(rows), 'box slit >= 0.18 (page raster, detector box):', base)
while len(tiles) % 4:
    tiles.append(np.full_like(tiles[0], 255))
grid = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)])
cv2.imwrite(str(S / 'misses.png'), grid)
