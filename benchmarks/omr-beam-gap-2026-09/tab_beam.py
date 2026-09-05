"""Tabulate wrong flag/beam ops per work from an ops dump directory."""
import collections
import glob
import json
import sys

ops_dir = sys.argv[1] if len(sys.argv) > 1 else \
    'benchmarks/omr-beam-gap-2026-09/ops-baseline'
BEAM_OPS = ('insbeam', 'delbeam', 'editbeam')

tot = collections.Counter()
perwork = {}
for f in sorted(glob.glob(ops_dir + '/*.json')):
    d = json.load(open(f))
    w = f.split('/')[-1][:-5]
    c = {k: v for k, v in d['cost_by_name'].items() if k in BEAM_OPS}
    perwork[w] = (sum(c.values()), c, d['total_cost'])
    for k, v in c.items():
        tot[k] += v
for w, (s, c, tc) in sorted(perwork.items(), key=lambda kv: -kv[1][0]):
    print(f"{w:26s} beam={s:4d} of {tc:4d}  {c}")
print('TOTAL beam', sum(tot.values()), dict(tot),
      ' pooled', sum(v[2] for v in perwork.values()))
