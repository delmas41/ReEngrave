"""2.311 scratch: which of Sean's note-level tile answers fall on the gathered pages, and how each can be placed."""
import collections
import json
import sys

from tools.omr.staged import judged as J

PAGES = {'litolff': {1, 2, 4, 6, 8, 9, 10, 11, 16}, 'brahms': {0, 4, 5, 8, 12, 14, 19, 25}}
KINDS = ('not_a_note', 'duration', 'duration_multi', 'rest', 'yes_no')


def rows():
    d = json.load(open('benchmarks/acceptance/judged-tiles.json'))
    d = J.with_derived_positions(d)
    for r in d['tiles']:
        if r.get('doc') not in PAGES or r['answer_kind'] not in KINDS:
            continue
        pl, bx = J.row_place(r), J.row_box(r)
        sub = r.get('subject') or ''
        pg = int(sub.split('/')[1]) if sub.startswith('glyph/') else (pl[0] if pl else None)
        if pg not in PAGES[r['doc']]:
            continue
        yield r, pl, bx, pg


if __name__ == '__main__':
    c = collections.Counter()
    ex = {}
    for r, pl, bx, pg in rows():
        k = (r['doc'], r['answer_kind'], 'placed' if (pl and bx) else ('subjects' if r.get('subjects') else 'keyonly'))
        c[k] += 1
        ex.setdefault(k, r)
    for k, v in sorted(c.items()):
        print(k, v)
    for k in ex:
        if k[2] != 'placed':
            print(k, json.dumps(ex[k], default=str)[:600])
