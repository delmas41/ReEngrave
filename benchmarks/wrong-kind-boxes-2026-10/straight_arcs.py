import json, sys
S = '/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night'
PAGES = {'litolff': {2, 4, 6, 8, 9, 10, 11, 16}, 'brahms': {0, 4, 5, 8, 12, 14, 19, 25}}
picks = []
for plate, pages in PAGES.items():
    for l in open(f'{S}/{plate}/observations.jsonl'):
        if '"system_arc"' not in l[:200]: continue
        o = json.loads(l)
        if int(o['subject'].split('/')[1]) not in pages: continue
        d = o.get('detail') or {}
        t = d.get('trace') or []; sp = d.get('space_page_px') or 0
        if len(t) < 10 or not sp: continue
        xs = [p[0] for p in t]; cs = [(p[1] + p[2]) / 2 for p in t]
        dev = max(abs(c - (cs[0] + (cs[-1] - cs[0]) * (x - xs[0]) / max(1, xs[-1] - xs[0]))) for x, c in zip(xs, cs)) / sp
        if (xs[-1] - xs[0]) / sp >= 3 and dev < 0.15:
            ys = [p[1] for p in t] + [p[2] for p in t]
            picks.append(dict(plate=plate, page=int(o['subject'].split('/')[1]), pb=[xs[0], min(ys), xs[-1], max(ys)],
                              caption='%s %s bow%.2f' % (plate[0], d.get('piece_classes'), dev), g=o['subject']))
json.dump(picks, open(sys.argv[1], 'w')); print(len(picks))
