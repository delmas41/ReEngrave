import sys, json
sys.path.insert(0,'.'); sys.path.insert(0,'benchmarks/omr-head-recentre-2026-10')
import measure_truth as M, explore as X
from tools.omr.staged import gather as G
hs, clean, n = X.heads()
rast = {"brahms": X.raster(X.BRA, 0), "litolff": X.raster(X.LIT, 1)}
def run(wins, main, spread):
    G.RECENTRE_PART_WINDOWS=wins; G.RECENTRE_PART_HALF_WINDOW_SPACES=main; G.RECENTRE_PART_MAX_SPREAD_SPACES=spread
    rows=M.table(hs,rast,"x"); out=[]
    for pg in ("brahms","litolff"):
        for lab in ("black","hollow","other"):
            v=[r for r in rows if r["page"]==pg and r["label"]==lab]
            if not v: continue
            sb=[M.state(r["before"]) for r in v]; sa=[M.state(r["after"]) for r in v]
            fl={}
            for a,b in zip(sb,sa):
                if a!=b: fl[f"{a}>{b}"]=fl.get(f"{a}>{b}",0)+1
            out.append(f"{pg[:3]}-{lab}: mv {sum(r['moved'] for r in v)} {fl}")
    t13=[r for r in rows if r['key']=='glyph/1/0/9/11/1']
    print(wins,main,spread,'|',' ; '.join(out),'| t13 moved',[ (r['moved'],r['reason'],r['dy']) for r in t13],flush=True)
for wins,main in [((0.6,0.65,0.7,0.75),0.7),((0.75,0.8,0.9,1.0),0.8),((0.7,0.75,0.8,0.9),0.8),((0.75,0.8,0.85,0.9),0.8),((0.8,0.9,1.0),0.9)]:
    for sp in (0.1,0.15):
        run(wins,main,sp)
