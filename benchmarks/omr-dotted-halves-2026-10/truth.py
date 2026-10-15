import sys,json,glob,collections,statistics; sys.path.insert(0,'.'); sys.path.insert(0,'runs')
from pathlib import Path
from tools.omr.staged import readout as RO
from tools.omr.hand_truth import store as ST
from diag import same, iou
def cls_of(r):
    if r is None: return 'none'
    return r['outcome']
def val(r):
    return r['value'].get('written') if r['outcome']=='decided' and isinstance(r['value'],dict) else None
def judge(r, dotted):
    if r is None: return 'no_verdict'
    if r['outcome']=='abstained': return 'abstained'
    if r['outcome']=='narrowed':
        w=[c.get('written') for c in r['cands']]
        return 'blue_has_right' if (3.0 if dotted else 2.0) in w else 'blue_no_right'
    v=val(r)
    if dotted is None: return 'right' if v in (2.0,3.0) else 'WRONG:%s'%v
    return 'right' if v==(3.0 if dotted else 2.0) else 'WRONG:%s'%v
def brahms(rec,rp):
    run=RO.load_run(rec); d=json.load(open(rp))['durations']
    sp=statistics.median([float(o["value"]) for o in run.observations if o["quantity"]=="staff_spacing"])
    pg=ST.load(Path('data/hand-truth/pages/imslp317803/0.json'))
    dots=[tuple(b.rect) for b in pg.boxes if b.cls=='augmentationDot']
    out=[]
    for b in pg.boxes:
        if not b.cls.startswith('noteheadHalf'): continue
        r=tuple(b.rect); cy=(r[1]+r[3])/2
        # a truth dot: right of the head, within 1.3 sp, level (|dy|<0.8sp) -- stricter than the loose staccato window
        dotted=any(0<x[0]-r[2]<0.9*sp and abs((x[1]+x[3])/2-cy)<0.9*sp for x in dots)
        gs=[g for g in run.glyphs.values() if g.page==0 and (g.cls or '').startswith('notehead') and g.box_page and same(r,g.box_page)]
        gs=[g for g in gs if d.get(g.key) and d[g.key]['reason']!='owned_by_another_staff'] or gs
        j=[(judge(d.get(g.key),dotted),g.key) for g in gs]
        out.append((dotted,j))
    return out
def tally(out):
    c=collections.Counter()
    for dotted,j in out:
        if not j: c['unmatched']+=1; continue
        pri=sorted(j,key=lambda x:(0 if x[0]=='right' else 1))
        c[pri[0][0].split(':')[0]]+=1
    return c
if __name__=='__main__':
    for arm in ('off','on'):
        o=brahms('runs/bra0-base.json',f'runs/rp-bra0-{arm}.json')
        print('brahms p0',arm,len(o),dict(tally(o)))
        if arm=='on':
            for dotted,j in o:
                for x in j:
                    if x[0]!='right': print('   ',dotted,x)

def litolff(rec,rp):
    sys.path.insert(0,'benchmarks/omr-labeling-hollow4-2026-10')
    import importlib.util
    sp_=importlib.util.spec_from_file_location("score_ab","benchmarks/omr-labeling-hollow4-2026-10/score_ab.py"); S=importlib.util.module_from_spec(sp_); sp_.loader.exec_module(S)
    truth,n,cellset=S.litolff_truth()
    leak=json.load(open('benchmarks/omr-head-recentre-2026-10/leak_check.json'))
    lk=set()
    for name in leak['litolff']['key_cells']:
        s,st,m=name.split('/')[1].replace('s','',1).replace('st','').replace('m','').split('-'); lk.add((int(s),int(st),int(m)))
    clean={k for k in cellset if k not in lk}
    run=RO.load_run(rec); d=json.load(open(rp))['durations']
    out=[]
    for k,ts in truth.items():
        if k not in clean: continue
        for t in ts:
            gs=[g for g in run.glyphs.values() if g.page==1 and (g.system,g.staff,g.cell)==k and (g.cls or '').startswith('notehead') and g.box_canon and S.same(t,g.box_canon)]
            gs=[g for g in gs if d.get(g.key) and d[g.key]['reason']!='owned_by_another_staff'] or gs
            out.append((None,[(judge(d.get(g.key),None),g.key) for g in gs]))
    return out
