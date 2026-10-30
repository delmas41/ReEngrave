import json, sys, collections
rows = {r['sub']: r for r in json.load(open(sys.argv[1]))['rows'] if r['fate'] == 'duration_narrowed'}
c = collections.Counter(); ex = collections.defaultdict(list)
with open(sys.argv[2]) as f:
    for line in f:
        if '"duration"' not in line:
            continue
        v = json.loads(line)
        if v['subject'] not in rows or v['quantity'] != 'duration':
            continue
        d = v.get('detail') or {}
        sb = d.get('beams_from_strokes') or {}
        tip = sb.get('tip') or {}
        lc, lp = d.get('levels_certain'), d.get('levels_possible')
        tl = sb.get('tip_levels')
        clean = (not tip.get('doubt')) and (not tip.get('hooks')) and (not tip.get('stubs')) and (not tip.get('own_head'))
        if v['reason'] in ('beams_ambiguous', 'beam_certain_not_joined') and sb and tl == lc and (lc or 0) >= 1 and clean and tip.get('stem_beamed') and lp and lp > lc:
            k = 'A_tip_exact_beamed(certain=tip>=1, extra only from old readers)'
        elif v['reason'] == 'beam_discounted_uncertain' and sb and tl == 0 and clean:
            k = 'B_bare_stem_clean_tip_by_strokes'
        elif v['reason'] in ('beams_ambiguous', 'beam_discounted_uncertain') and not sb:
            k = 'C_no_stroke_reading(stems %s)' % d.get('stems_attached')
        else:
            k = 'D_other:%s' % v['reason']
        c[k] += 1
        ex[k].append(v['subject'])
for k, n in sorted(c.items()):
    print(n, k)
json.dump({k: v for k, v in ex.items()}, open(sys.argv[3], 'w'))
