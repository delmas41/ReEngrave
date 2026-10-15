import sys, json, statistics, collections
sys.path.insert(0,'.')
from pathlib import Path
from tools.omr.staged import readout as RO
from tools.omr.hand_truth import store as ST
def iou(a,b):
    ix=max(0,min(a[2],b[2])-max(a[0],b[0])); iy=max(0,min(a[3],b[3])-max(a[1],b[1])); i=ix*iy
    return 0 if i<=0 else i/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-i)
def same(t,r):
    if iou(t,r)>=0.3: return True
    cx,cy=(t[0]+t[2])/2,(t[1]+t[3])/2
    return r[0]<=cx<=r[2] and r[1]<=cy<=r[3]
def sp_of(run): return statistics.median([float(o["value"]) for o in run.observations if o["quantity"]=="staff_spacing"])
def final_dur(run,key):
    vs=run.verdicts_at(key,None,'duration')
    return vs[-1] if vs else None
def summarize(run, page, truthpath):
    sp=sp_of(run); pg=ST.load(Path(truthpath))
    tb=[b for b in pg.boxes]
    dots=[tuple(b.rect) for b in tb if b.cls=='augmentationDot']
    stems=[tuple(b.rect) for b in tb if b.cls=='stem']
    out=[]
    for b in tb:
        if not b.cls.startswith(('noteheadHalf','noteheadWhole','noteheadBlack')): continue
        r=tuple(b.rect)
        t_h='half' if b.cls.startswith('noteheadHalf') else ('whole' if b.cls.startswith('noteheadWhole') else 'black')
        cx,cy=(r[0]+r[2])/2,(r[1]+r[3])/2
        dotted=any(0<d[0]-r[2]<1.3*sp and abs((d[1]+d[3])/2-cy)<1.3*sp for d in dots)
        stem=any((s[0]<=r[2]+0.3*sp and s[2]>=r[0]-0.3*sp) and s[1]<=r[3]+0.2*sp and s[3]>=r[1]-0.2*sp for s in stems)
        gs=[g for g in run.glyphs.values() if g.page==page and (g.cls or '').startswith('notehead') and g.box_page and same(r,g.box_page)]
        out.append(dict(truth=t_h,dotted=dotted,stem=stem,rect=r,glyphs=gs,cls=b.cls))
    return out
def rowinfo(run,g):
    d={}
    d['cls']=g.cls
    ink=run.obs_at(g.key,'notehead_ink'); d['ink']=ink[-1]['value'] if ink else None
    vs=run.verdicts_at(g.key,None,'duration')
    d['dur']=[(v['outcome'],v.get('reason'),v.get('value') if v['outcome']=='decided' else [c.get('value',{}).get('written') if isinstance(c,dict) else c for c in (v.get('candidates') or [])][:5]) for v in vs]
    hs=run.verdicts_at(g.key,None,'head_stem'); d['head_stem']=[(v['outcome'],v.get('reason')) for v in hs]
    return d
if __name__=='__main__':
    run=RO.load_run(sys.argv[1]); page=int(sys.argv[2])
    rows=summarize(run,page,sys.argv[3])
    for r in rows:
        if r['truth']=='black': continue
        print(r['truth'],'dotted' if r['dotted'] else '', 'stem' if r['stem'] else 'NOSTEM', [ (g.key,g.cls) for g in r['glyphs']])
        for g in r['glyphs']:
            print('    ',json.dumps(rowinfo(run,g),default=str)[:600])
