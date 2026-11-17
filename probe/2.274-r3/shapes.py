import json
import collections
import sys

r = json.load(open(sys.argv[1]))


def show(q, n=2):
    k = 0
    for o in r['observations']:
        if o['quantity'] == q:
            print(q, o['subject'], o['value'], o.get('reader'), {a: (b if len(str(b)) < 150 else str(b)[:150]) for a, b in (o.get('detail') or {}).items()})
            k += 1
            if k >= n:
                break


for q in ('arc_box', 'arc_ink_shape', 'system_arc', 'page_arc'):
    show(q)
for q in ('arc_is_not_an_arc', 'arc_owner', 'arc_kind', 'tie_pair', 'page_arc_binding'):
    k = 0
    for o in r['verdicts']:
        if o['quantity'] == q:
            print('V', q, o['subject'], o['value'], str(o.get('detail'))[:400])
            k += 1
            if k >= 1:
                break
print(collections.Counter(o['value'] for o in r['observations'] if o['quantity'] == 'page_arc'))
print(collections.Counter(o['value'] for o in r['verdicts'] if o['quantity'] == 'arc_kind'))
print(collections.Counter(o['value'] for o in r['verdicts'] if o['quantity'] == 'arc_is_not_an_arc'))
print(collections.Counter(o['value'] for o in r['verdicts'] if o['quantity'] == 'tie_pair'))
