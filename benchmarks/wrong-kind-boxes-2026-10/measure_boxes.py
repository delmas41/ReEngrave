"""Measure detector head boxes by their own size in staff spaces, on the frozen sample pages (20261029-night slices)."""
import json, sys, collections
S = '/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night'
PAGES = {'litolff': [2, 4, 6, 8, 9, 10, 11, 16], 'brahms': [0, 4, 5, 8, 12, 14, 19, 25]}
out = {}
for plate, pages in PAGES.items():
    pages = set(pages)
    sp = {}; boxes = {}; hairs = []
    for l in open(f'{S}/{plate}/observations.jsonl'):
        if '"cell_staff_space"' in l:
            o = json.loads(l); k = o['subject'].split('/')
            if int(k[1]) in pages: sp[tuple(int(x) for x in k[1:5])] = o['value']
        elif '"quantity": "glyph_box"' in l:
            o = json.loads(l); k = o['subject'].split('/')
            if int(k[1]) not in pages: continue
            boxes[o['subject']] = (o['value'], o['score'], o['detail'].get('bbox_page_px'), o['reader'])
    verd = {}
    for l in open(f'{S}/{plate}/verdicts.jsonl'):
        if '"notehead_is_not_a_notehead"' not in l[:400] and '"arc_kind"' not in l[:400]:
            continue
        o = json.loads(l)
        if o['subject'] in boxes:
            verd[(o['subject'], o['quantity'])] = (o['outcome'], o.get('value'), o.get('reason'))
    rows = []
    for g, (v, sc, pb, rd) in boxes.items():
        k = g.split('/'); cell = tuple(int(x) for x in k[1:5])
        s = sp.get(cell)
        if not s: continue
        rows.append(dict(g=g, cls=v[0], w=v[3] / s, h=v[4] / s, conf=sc, pb=pb, reader=rd,
                         nh=verd.get((g, 'notehead_is_not_a_notehead')), arc=verd.get((g, 'arc_kind'))))
    out[plate] = rows
json.dump(out, open(sys.argv[1], 'w'))
for plate, rows in out.items():
    heads = [r for r in rows if r['cls'].lower().startswith('notehead')]
    print(plate, 'boxes', len(rows), 'head boxes', len(heads))
