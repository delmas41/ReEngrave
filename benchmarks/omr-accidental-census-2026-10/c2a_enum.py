"""2.197 C2a: which hand-labelled cells (all label versions) lie on the acceptance plates' pages and hold accidental/key boxes. usage (from repo root): c2a_enum.py OUT.json"""
import sys,json,glob,collections,pathlib
sys.path.insert(0,'.')
from tools.omr.hand_truth.inventory import cell_pages, cell_cut_ids
pg=cell_pages(); cut=cell_cut_ids()
GROUP={59:'flat',60:'flat',170:'flat',61:'natural',62:'natural',171:'natural',63:'sharp',64:'sharp',172:'sharp',65:'dsharp',66:'dflat',173:'dsharp',174:'dflat',67:'keyFlat',68:'keyNat',69:'keySharp'}
R=pathlib.Path('data/user-labeled')
out=collections.defaultdict(collections.Counter)
cells=collections.defaultdict(list)
for v in sorted(R.glob('v*')):
    for f in v.glob('labels/*.txt'):
        e=pg.get(f.stem)
        if not e or e[0] not in('imslp984073','imslp317803'): continue
        n=collections.Counter()
        for l in f.read_text().splitlines():
            p=l.split()
            if len(p)>=5 and int(p[0]) in GROUP: n[GROUP[int(p[0])]]+=1
        out[(v.name[:3],e)].update(n)
        if n: cells[(v.name[:3],e)].append((f.stem,dict(n)))
for k,c in sorted(out.items()): print(k,dict(c))
json.dump({f"{k[0]}|{k[1][0]}|{k[1][1]}":v for k,v in cells.items()},open(sys.argv[1],'w'),indent=1)
