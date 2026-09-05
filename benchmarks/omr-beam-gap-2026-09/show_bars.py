"""Show insbar/delbar rows for one ops dump."""
import json
import sys

d = json.load(open(sys.argv[1]))
for r in d['rows']:
    if r['op'] in ('insbar', 'delbar'):
        print(f"{r['op']} c{r['cost']:<3d} p{r['part_index']:02d} "
              f"{r['part_name'][:20]:20s} m{r['measure']} "
              f"P={str(r['pred_repr'])[:80]} T={str(r['truth_repr'])[:80]}")
