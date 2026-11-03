import json, sys
tag = sys.argv[1] if len(sys.argv) > 1 else 'r2'
for pl in 'LB':
    try:
        a = json.load(open('out/2.255/%s_off_%s.json' % (pl, tag)))['heads']
        b = json.load(open('out/2.255/%s_on_%s.json' % (pl, tag)))['heads']
    except Exception:
        print(pl, 'pending'); continue
    ref = lambda h: bool(h['got'][0] == 'abs' and h['nb'] and h['nb'][1] is not None)
    print(pl, 'refut off', sum(ref(h) for h in a.values()), 'on', sum(ref(h) for h in b.values()))
    for s in a:
        if a[s]['got'] != b[s]['got']:
            print(' ', s, a[s]['got'][0], '->', b[s]['got'][0], b[s]['got'][1], 'nb_pos', a[s]['nb'] and a[s]['nb'][1],
                  '|', str(b[s]['got'][2])[:80])
