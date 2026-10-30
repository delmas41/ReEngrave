"""2.235 census of beam_discounted_uncertain verdicts from a slice: grep beam_discounted_uncertain verdicts.jsonl | python3 bdu_census.py"""
import sys, json, collections
c = collections.Counter()
for l in sys.stdin:
    v = json.loads(l)
    if v['quantity'] != 'duration' or v['reason'] != 'beam_discounted_uncertain':
        continue
    d = v['detail']
    rs = d.get('refused_strokes') or []
    c[('stems', d.get('stems_attached'))] += 1
    c[('tipclean', d.get('bare_stem_tip_window_clean'))] += 1
    c[('atTipStroke', d.get('bare_stem_refused_stroke_at_tip'))] += 1
    c[('whys', tuple(sorted({r['why'] for r in rs})))] += 1
    c[('dots', d.get('dots_attached'))] += 1
for k, n in sorted(c.items(), key=lambda x: (x[0][0], -x[1])):
    print(n, k)
