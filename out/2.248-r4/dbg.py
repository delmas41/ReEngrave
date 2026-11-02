import json, collections
W = 'out/2.248-r4/lane/work/'
for plate in ("litolff", "brahms"):
    on = json.load(open(W + plate + '.on.symbols.json'))['hosts']
    off = {h['rg']: h for h in json.load(open(W + plate + '.off.symbols.json'))['hosts'] if h.get('rg')}
    ch = [h for h in on if h.get('rg') in off and (h['blue'] != off[h['rg']]['blue'] or h['pitch'] != off[h['rg']]['pitch'])]
    print(plate, len(ch), ch[0] if ch else None)
    r = json.load(open(W + plate + '.on.mini-record.json'))
    r = r.get('record', r)
    print(type(r), list(r.keys())[:6] if isinstance(r, dict) else '')
    vs = r.get('verdicts', [])
    print(collections.Counter(v.get('reason') for v in vs if v.get('quantity') == 'pitch').most_common(8))
