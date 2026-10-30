import json, sys
wd, plate, part, meas = sys.argv[1:5]
for arm in ('off', 'on'):
    hs = json.load(open('%s/%s.%s.symbols.json' % (wd, plate, arm)))['hosts']
    print(arm, [(h['rg'].replace('glyph/', ''), h['kind'], h['type'], h['pitch'] if 'pitch' in h else '', h['blue'], h.get('onset'), h.get('voice'))
                for h in hs if h['part'] == part and h['measure'] == meas])
