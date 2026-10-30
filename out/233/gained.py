"""2.235: diff the hosts of a lane_report run. usage: gained.py WORKDIR PLATE  -> gained / lost / blue->plain / value change lists (json to stdout)"""
import json, sys, collections
wd, plate = sys.argv[1], sys.argv[2]
off = json.load(open('%s/%s.off.symbols.json' % (wd, plate)))['hosts']
on = json.load(open('%s/%s.on.symbols.json' % (wd, plate)))['hosts']
O = {h['rg']: h for h in off}
N = {h['rg']: h for h in on}
out = collections.defaultdict(list)
for rg, h in N.items():
    o = O.get(rg)
    if o is None:
        out['gained_' + h['kind']].append(h)
    elif o['kind'] == 'note':
        if o['blue'] and not h['blue']:
            out['blue_to_plain'].append(dict(h, was=o['type']))
        if o['type'] != h['type']:
            out['value_changed'].append(dict(h, was=o['type'], was_blue=o['blue']))
        if (not o['blue']) and h['blue']:
            out['plain_to_blue'].append(h)
for rg, h in O.items():
    if rg not in N:
        out['lost_' + h['kind']].append(h)
for k, v in sorted(out.items()):
    print(k, len(v), collections.Counter((x['type'], x['blue']) for x in v).most_common(6))
json.dump(out, open('%s/%s.diff.json' % (wd, plate), 'w'))
for k in ('lost_note', 'lost_rest', 'value_changed'):
    for x in out.get(k, []):
        print(k, x['rg'], x['type'], x.get('was'), x['blue'], x['page'], x['part'], x['measure'])
