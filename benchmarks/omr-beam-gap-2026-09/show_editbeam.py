"""Print editbeam rows (pred vs truth reprs) for one work's ops dump."""
import json
import sys
import collections

f = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 40
d = json.load(open(f))
rows = [r for r in d['rows'] if r['op'] in ('editbeam', 'insbeam', 'delbeam')]
print(len(rows), 'beam rows')
byparts = collections.Counter((r['part_name'], r['measure']) for r in rows)
print('top part/measure:', byparts.most_common(10))
for r in rows[:limit]:
    print(f"-- {r['op']} c{r['cost']} p{r['part_index']:02d} "
          f"{r['part_name'][:16]} m{r['measure']}")
    print('   P:', r['pred_repr'])
    print('   T:', r['truth_repr'])
