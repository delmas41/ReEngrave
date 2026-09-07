"""VERIFIER: independently recompute the 436 class-disagreement figure and both
agents' class breakdowns from the OMR_CONTEST_DUMP artefacts."""
import json, glob, collections
files = sorted(glob.glob('benchmarks/omr-additive-vs-gated-2026-09/out/contests/*.contests.json'))
rows = []
for f in files:
    d = json.load(open(f))
    for p in d['pages']:
        for c in p.get('contests', []):
            c = dict(c); c['row_id'] = d['row_id']; rows.append(c)
print('files', len(files), 'total contests', len(rows))
disagree = [c for c in rows if c['class_i'] != c['class_j']]
print('class disagreements', len(disagree), '=', round(len(disagree)/len(rows), 4))
print('decided_by over disagreements', collections.Counter(c['decided_by'] for c in disagree))
print('decided_by over all', collections.Counter(c['decided_by'] for c in rows))
print('category over disagreements', collections.Counter(c['category'] for c in disagree))
pairs = collections.Counter(tuple(sorted((c['class_i'], c['class_j']))) for c in disagree)
print('\ntop unordered class pairs:')
for k, v in pairs.most_common(20):
    print(' %-58s %d' % (' / '.join(k), v))

# Agent I's named buckets
def has(c, a, b):
    s = {c['class_i'], c['class_j']}
    return a in s and b in s
named = {
 'beam/tie': sum(1 for c in disagree if has(c,'beam','tie')),
 'slur/tie': sum(1 for c in disagree if has(c,'slur','tie')),
 'beam/slur': sum(1 for c in disagree if has(c,'beam','slur')),
 'dynamicF/dynamicP': sum(1 for c in disagree if has(c,'dynamicF','dynamicP')),
 'accidentalFlat/accidentalNatural': sum(1 for c in disagree if has(c,'accidentalFlat','accidentalNatural')),
}
print('\nAgent I named pairs:', named, 'sum of arc three =', named['beam/tie']+named['slur/tie']+named['beam/slur'])

# Agent II's family buckets (by category of the contest)
ARC = {'beam','tie','slur'}
def fam(c):
    s = {c['class_i'], c['class_j']}
    if s <= ARC: return 'arc'
    return None
print('\nboth-classes-in-{beam,tie,slur}:', sum(1 for c in disagree if fam(c)=='arc'))
print('either-class-in-arc:', sum(1 for c in disagree if ({c['class_i'],c['class_j']} & ARC)))
for tag, pred in [('accidental*', lambda s: any(x.startswith('accidental') for x in s)),
                  ('both accidental*', lambda s: all(x.startswith('accidental') for x in s)),
                  ('dynamic*', lambda s: any(x.startswith('dynamic') for x in s)),
                  ('both dynamic*', lambda s: all(x.startswith('dynamic') for x in s)),
                  ('flag*', lambda s: any(x.startswith('flag') for x in s)),
                  ('both flag*', lambda s: all(x.startswith('flag') for x in s))]:
    print('%-20s %d' % (tag, sum(1 for c in disagree if pred({c['class_i'],c['class_j']}))))
print('\ncategory of ALL contests:', collections.Counter(c['category'] for c in rows))
