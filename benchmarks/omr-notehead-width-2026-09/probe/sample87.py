import json
import random

base = json.load(open('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/2.39-base-arm/out/2.39/base-brahms-p1.json'))['record']
new = json.load(open('out/2.39/new-brahms-p1.json'))['record']


def vidx(rec, q):
    return {v['subject']: v for v in rec['verdicts'] if v['quantity'] == q}


b = vidx(base, 'duration')
n = vidx(new, 'duration')
changed = []
for s in sorted(set(b) | set(n)):
    bv, nv = b.get(s), n.get(s)
    bk = None if bv is None else (bv['outcome'], bv['reason'])
    nk = None if nv is None else (nv['outcome'], nv['reason'])
    if bk != nk:
        changed.append(s)
print(len(changed))
random.seed(2039)
sample = random.sample(changed, 8)
for s in sorted(sample):
    print(s)
with open('/tmp/brahms_87_changed.json', 'w') as f:
    json.dump({"changed": changed, "sample_seed_2039": sorted(sample)}, f)
