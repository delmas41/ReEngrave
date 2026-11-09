import json, collections, sys
R = [json.loads(l) for l in open(sys.argv[1])]
c = [r for r in R if r['fate'] == 'chord_value_undecided']
for r in c[:8]:
    print(r['sub'], r.get('reason'), r['cands'], r.get('head_stem'), r.get('stem_value'),
          {k: r['d'].get(k) for k in ('levels_certain', 'levels_possible', 'stems_attached', 'beams_by_stem', 'flag_levels')})
print(collections.Counter(str((r.get('stem_value') or ['-', '-'])[:2]) for r in c).most_common(10))
