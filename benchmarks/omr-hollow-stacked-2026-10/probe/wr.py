import sys,ast,re
def written(p):
    for l in open(p):
        if l.strip().startswith('written: {'):
            return ast.literal_eval(l.split('written: ',1)[1].strip())
def census(p):
    for l in open(p):
        m=re.search(r"'notehead': \{'marks': (\d+), 'detected_more_than_once': (\d+), 'written_once': (\d+)",l)
        if m: return tuple(map(int,m.groups()))
a,b=sys.argv[1],sys.argv[2]
A,B=written(a),written(b)
print({k:(A[k],B.get(k)) for k in A if A[k]!=B.get(k) and isinstance(A[k],(int,float))})
print("notehead census marks/dup/written_once",census(a),census(b))
for key in ("voice_overfull","bars_held","held"):
    pass
for l in open(b):
    if 'held' in l and 'bars' in l: print(l.strip()[:200])
