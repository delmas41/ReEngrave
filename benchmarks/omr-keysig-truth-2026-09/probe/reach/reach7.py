import sys,collections,json; sys.path.insert(0,'.'); sys.path.insert(0,'out/probe')
from load import load
rec=load(sys.argv[1])
n=0
c=collections.Counter()
for v in rec['verdicts']:
    if v['quantity']=='key_signature' and v['subject'].startswith('staff/') and v['reason'] in ('disagrees_with_document','disagrees_with_system'):
        d=v.get('detail') or {}
        key=(v['reason'], d.get('staff_fifths', d.get('reading')), d.get('keysig_run_slots'), d.get('document_fifths'), d.get('system_fifths'))
        c[tuple(str(x) for x in key)]+=1
        if n<3: print(json.dumps(v)[:1200]); n+=1
for k,m in c.most_common(30): print(m,k)
