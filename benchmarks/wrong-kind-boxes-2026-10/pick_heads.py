import json, sys, random
d = json.load(open(sys.argv[1]))
which = sys.argv[2]
n = int(sys.argv[4]) if len(sys.argv) > 4 else 24
picks = []
for plate, rows in d.items():
    for r in rows:
        if not r['cls'].lower().startswith('notehead') or not r['pb']: continue
        kept = r['nh'] and r['nh'][0] == 'decided' and r['nh'][1] is False
        ok = {'wide': r['w'] >= 3.0, 'wide25': 2.5 <= r['w'] < 3.0, 'tall': r['h'] >= 2.0, 'short': r['h'] < 0.65}[which]
        if ok and kept:
            picks.append(dict(plate=plate, page=int(r['g'].split('/')[1]), pb=r['pb'],
                              caption='%s %s %.1fx%.1f %.2f' % (plate[0], r['cls'][8:], r['w'], r['h'], r['conf']), g=r['g']))
random.Random(2245).shuffle(picks)
picks = sorted(picks[:n], key=lambda p: (p['plate'], p['page']))
json.dump(picks, open(sys.argv[3], 'w'))
print(len(picks))
