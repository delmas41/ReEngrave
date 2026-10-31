"""ROADMAP 2.245 -- the CV hairpin reader's rows (Q.WEDGE_BOX, reader cv_hairpins) against their own size and the word claims.

Counts, per plate on the frozen sample, the hairpin rows narrower than `MIN_W_SP` staff spaces and the rows whose box lies >= half
inside a READ word claim (Q.CLAIMED_AREA owner word). Usage: python3 benchmarks/wrong-kind-boxes-2026-10/hairpin_letters.py
"""
import json
import collections

S = '/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night'
PAGES = {'litolff': {2, 4, 6, 8, 9, 10, 11, 16}, 'brahms': {0, 4, 5, 8, 12, 14, 19, 25}}
MIN_W_SP = 1.6


def inside(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    area = max(1e-9, (a[2] - a[0]) * (a[3] - a[1]))
    return ix * iy / area


for plate, pages in PAGES.items():
    wedges, words, sp = [], collections.defaultdict(list), {}
    for line in open(f'{S}/{plate}/observations.jsonl'):
        head = line[:300]
        if '"wedge_box"' in head:
            o = json.loads(line)
            if int(o['subject'].split('/')[1]) in pages:
                wedges.append(o)
        elif '"claimed_area"' in head:
            o = json.loads(line)
            d = o.get('detail') or {}
            if d.get('owner') == 'word' and int(o['subject'].split('/')[1]) in pages and isinstance(o.get('value'), list):
                words[int(o['subject'].split('/')[1])].append(o['value'])
        elif '"staff_spacing"' in head:
            o = json.loads(line)
            p = int(o['subject'].split('/')[1])
            if p in pages:
                sp.setdefault(p, []).append(float(o['value']))
    n = narrow = in_word = both = 0
    for o in wedges:
        if o.get('reader') != 'cv_hairpins':
            continue
        p = int(o['subject'].split('/')[1])
        b = (o.get('detail') or {}).get('bbox_page_px')
        if not b or not sp.get(p):
            continue
        n += 1
        u = sorted(sp[p])[len(sp[p]) // 2]
        w = (b[2] - b[0]) / u
        nw = w < MIN_W_SP
        iw = any(inside(b, wb) >= 0.5 for wb in words[p])
        narrow += nw
        in_word += iw
        both += nw and iw
    print('%-8s cv hairpin rows %4d | narrower than %.1f sp %3d | >= half inside a word claim %3d | both %3d'
          % (plate, n, MIN_W_SP, narrow, in_word, both))
