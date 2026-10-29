"""Fixture: page crops (600 dpi, render_page binary) of Sean's 8 2.220 tiles, with box, foreign boxes of the same cell, page space."""
import json, sys, pathlib
WT = '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a44a05b0ad517dce3'
sys.path.insert(0, WT)
import numpy as np
from tools.omr.staged import head_ink as HI
S = pathlib.Path('/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-agent-manager-workflow-356c39/7e1ea73e-2fd3-4d6c-a450-36868f7e14c0/scratchpad')
key = json.load(open(WT + '/out/print/2.220-plan/key.json'))
ans = {t['tile']: t['seans_answer'] for t in json.load(open(WT + '/out/print/2.220-plan/answers.json'))['tiles']}
SP = {'litolff': 16.0, 'brahms': 27.5}
out = {}
for k in key:
    plate, p, s = k['plate'], k['page'], k['subject']
    d = json.load(open(S / ('lit.json' if plate == 'litolff' else 'bra.json')))
    pg = np.load(S / f'page_{plate}_{p}.npy') if (S / f'page_{plate}_{p}.npy').exists() else None
    if pg is None:
        from tools.omr.preprocessing import render_page
        LIB = pathlib.Path('/Users/seanjohnson/Desktop/ReEngrave/library')
        PDF = {'litolff': 'editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf',
               'brahms': 'editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf'}
        pg = render_page(str(LIB / PDF[plate]), p, dpi=600).binary
    sp = SP[plate]
    b = d['boxes'][s]['page']
    x0, y0 = int(b[0] - 5 * sp), int(b[1] - 4 * sp)
    x1, y1 = int(b[2] + 5 * sp), int(b[3] + 4 * sp)
    crop = pg[y0:y1, x0:x1]
    ck = '/'.join(s.split('/')[:5]) + '/'
    foreign = [[v[0] - x0, v[1] - y0, v[2] - x0, v[3] - y0] for ss, bb in d['boxes'].items()
               if ss.startswith(ck) and HI.is_foreign_class(bb['cls']) and bb['page'] for v in [bb['page']]]
    t = k['tile']
    out[f't{t}_ink'] = np.packbits(crop == 0)
    out[f't{t}_shape'] = np.array(crop.shape)
    out[f't{t}_box'] = np.array([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0])
    out[f't{t}_foreign'] = np.array(foreign, dtype=float).reshape(-1, 4)
    out[f't{t}_sp'] = np.array(sp)
    out[f't{t}_answer'] = np.array(ans[t])
    out[f't{t}_subject'] = np.array(f'{plate} {s}')
np.savez_compressed(WT + '/tools/omr/tests/data_head_ink_2220_tiles.npz', **out)
print('ok', len(out))
