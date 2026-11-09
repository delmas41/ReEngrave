import json, sys, collections
plate = sys.argv[1] if len(sys.argv) > 1 else "litolff"
d = '/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night/%s/' % plate
want = collections.Counter()
ex = {}
for kind in ('observations', 'verdicts'):
    for line in open(d + kind + '.jsonl'):
        o = json.loads(line)
        q = o.get('quantity')
        want[(kind, q)] += 1
        if (kind, q) not in ex:
            ex[(kind, q)] = o
for k, v in sorted(want.items(), key=lambda t: -t[1])[:70]:
    print(k, v)
for k in [('verdicts', 'stroke_owner'), ('observations', 'stroke'), ('observations', 'glyph_strokes'), ('observations', 'glyph_box')]:
    o = ex.get(k)
    if o:
        for f in ('considered', 'correlated'):
            o.pop(f, None)
        print(k, json.dumps(o)[:1800])
