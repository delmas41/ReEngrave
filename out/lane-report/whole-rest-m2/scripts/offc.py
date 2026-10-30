import json, collections
for pl in ('litolff', 'brahms'):
    d = 'library/_shared-records/lane-report-slices-wr1029/%s/verdicts.jsonl' % pl
    refused = {}
    dur = {}
    for l in open(d):
        v = json.loads(l)
        if v['quantity'] == 'rest_is_not_a_rest':
            refused[v['subject']] = v
        elif v['quantity'] == 'duration':
            dur[v['subject']] = v
    c = collections.Counter(v['reason'] for v in refused.values() if v['value'] is True)
    print(pl, c.most_common(8))
    offc = [s for s, v in refused.items() if v['reason'] == 'rest_off_center' and v['value'] is True and (v.get('detail') or {}).get('class') == 'restWhole']
    steps = []
    for s in offc:
        det = (dur.get(s) or {}).get('detail') or {}
        steps.append((det.get('staff_step'), det.get('outside_its_own_staff'), s))
    bad = [x for x in steps if x[0] is None or x[1] or not (4.15 <= x[0] <= 6.9)]
    print('  restWhole refused by off_center:', len(offc), ' of those with step outside 4.15-6.9 or outside staff:', len(bad))
    for x in sorted(bad, key=lambda t: str(t))[:12]:
        print('    ', x)
