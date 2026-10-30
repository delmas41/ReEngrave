import json, sys, collections
d = json.load(open(sys.argv[1]))
rows = [r for r in d['rows'] if r['reason'] == 'beam_discounted_uncertain']
print('still beam_discounted_uncertain:', len(rows), 'with tip note:', sum(1 for r in rows if r.get('thc')))
c = collections.Counter()
for r in rows:
    t = r.get('thc')
    if not t:
        c['no tip note (no own stem / side)'] += 1
        continue
    c[(tuple(t['gather_tip']), t['flag_window'], t['beam_runs_at_tip'], tuple((n['stroke_reading'], tuple(n['claims_ignored'] or ()), n['claims_left']) for n in t['claims']))] += 1
for k, v in c.most_common(25):
    print(v, k)
print('decided/other with note:', collections.Counter((x['reason'], x['outcome']) for x in d['thcs']))
