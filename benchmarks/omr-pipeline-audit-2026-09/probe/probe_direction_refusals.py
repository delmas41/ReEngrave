import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import fixtures, root, chdir_root, SCAN, ENGRAVED, CONTESTS  # fail-loud
chdir_root()
sys.path.insert(0, root())   # so `tools.omr.direction_lexicon` is importable

import json, glob, re
from collections import Counter
from tools.omr.direction_lexicon import TERMS, CONNECTIVE, _normalise, lookup
rej=[]
for f in sorted(fixtures(SCAN, expect_at_least=11)):
    dt=json.load(open(f)).get('direction_text') or {}
    for pg in dt.get('pages',[]): rej += pg.get('rejected',[])
print('refused strings:',len(rej))
buckets=Counter(); examples={}
for s in rej:
    t=s.strip()
    if not re.fullmatch(r"[A-Za-zÀ-ÿ' .,\-]+", t):
        b='charset veto (digit/bracket/symbol)'
    else:
        toks=[x for x in (_normalise(x) for x in t.split()) if x]
        if not toks: b='empty after normalise'
        elif len(toks)>6: b='too many tokens'
        elif any(a==b2 for a,b2 in zip(toks,toks[1:])): b='adjacent repeat veto'
        else:
            m=[x for x in toks if x in TERMS]
            u=[x for x in toks if x not in TERMS and x not in CONNECTIVE]
            if m and u: b=f'PARTIAL: {len(m)} term(s) matched, {len(u)} unknown'
            elif m and not u: b='should have passed?!'
            else: b='no term at all'
    buckets[b]+=1; examples.setdefault(b,[]).append(t)
for k,v in buckets.most_common():
    print(f'  {v:4d}  {k}')
    print('        e.g.', [e for e in examples[k][:6]])
# the partial family in detail
print()
print('PARTIAL refusals in full:')
seen=Counter()
for s in rej:
    t=s.strip()
    if not re.fullmatch(r"[A-Za-zÀ-ÿ' .,\-]+", t): continue
    toks=[x for x in (_normalise(x) for x in t.split()) if x]
    if not toks or len(toks)>6 or any(a==b for a,b in zip(toks,toks[1:])): continue
    m=[x for x in toks if x in TERMS]; u=[x for x in toks if x not in TERMS and x not in CONNECTIVE]
    if m and u: seen[(t, tuple(m), tuple(u))]+=1
for (t,m,u),n in seen.most_common():
    print(f'   x{n}  {t!r}  matched={list(m)}  unknown={list(u)}')
