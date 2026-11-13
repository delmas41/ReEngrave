"""Print `results/t2_score.json` as short tables (measure only)."""
import json
import sys

FAMS = ['head_filled', 'head_hollow', 'head_whole', 'rest', 'accidental', 'flag', 'dot', 'clef']
d = json.load(open(sys.argv[1]))
print('TIMING (s): prepare / cells / row / band ; most boxes in one call')
for k, v in d['timing'].items():
    print('  %-11s' % k, v['prepare'], v['cells'], v['row'], v['band'], v['most_boxes_in_a_call'])
print('BRAHMS p0 vs SEAN (found / missed / not his)')
for fam in FAMS:
    L = d['labels_p0']
    print('  %-12s labels %3d   ' % (fam, L['cells'][fam]['labels'])
          + '   '.join('%s %d/%d/%d' % (w, L[w][fam]['found'], L[w][fam]['missed'], L[w][fam]['not_his']) for w in ('cells', 'row', 'band')))
print('VS CELLS by place (in both / only cells / only this way)')
for p, ws in d['vs_cells'].items():
    for w, t in ws.items():
        print('  %s %s: ' % (p, w) + ' | '.join('%s %d/%d/%d' % (fam, t.get(fam + ':both', 0), t.get(fam + ':only_cells', 0),
                                                                 t.get(fam + ':only_this_way', 0)) for fam in FAMS))
print('JUDGED tiles', d['judged_n'], d.get('judged_error', ''))
for w, c in d['judged'].items():
    print('  ', w, c)
