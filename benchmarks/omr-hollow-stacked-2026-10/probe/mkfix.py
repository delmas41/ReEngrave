import sys,json,numpy as np
sys.path.insert(0,'.')
from tools.omr.preprocessing import render_page
from tools.omr.staged import record_io, readout as RO
p="library/_shared-records/brahms1-breitkopf-mvt1-whole-20261013-night.record.json"
res=record_io.load_record(p); run=RO.run_from_result(res,path=p)
R=json.load(open('../../2.129/out/refusals_all.json'))
cases={"tile9_hollow_pair":["glyph/21/1/3/7/6","glyph/21/1/3/7/10"],
       "numeral_8_of_9over8":["glyph/0/0/11/7/1","glyph/0/0/11/7/0"],
       "bass_clef":["glyph/18/1/3/7/20","glyph/18/1/3/7/26"],
       "line_cut_single_head":["glyph/0/0/5/6/12","glyph/0/0/5/6/13"],
       "pair_12_0_2_6":["glyph/12/0/2/6/4","glyph/12/0/2/6/9"]}
def ob(k,q):
    for s,kd,r in run.rows_at(k):
        if r.get('quantity')==q and kd=='observation': return r
def vd(k,q):
    for s,kd,r in run.rows_at(k):
        if r.get('quantity')==q and kd=='verdict': return r
pages={}
out={}
for name,keys in cases.items():
    ents=[]
    for k in keys:
        g=run.glyphs.get(k)
        if g is None: print(name,'missing',k); continue
        gb=ob(k,'glyph_box'); canon=eval(gb['value'].replace("'",'"')) if isinstance(gb['value'],str) else gb['value']
        ents.append((k,g,gb,canon))
    print(name,[ (k,g.cls,g.box_page,c[1:]) for k,g,gb,c in ents])

import ast
fix={}
for name,keys in cases.items():
    ents=[]
    for k in keys:
        g=run.glyphs[k]; gb=ob(k,'glyph_box')
        canon=ast.literal_eval(gb['value']) if isinstance(gb['value'],str) else gb['value']
        pos=float(ob(k,'notehead_staff_position')['value'])
        hs=vd(k,'head_stem'); sb=(hs.get('detail') or {}).get('stem_box')
        ents.append(dict(key=k,cls=g.cls,page=g.page,bp=g.box_page,canon=canon[1:],pos=pos,stem=sb))
    e0=ents[0]; bp=e0['bp']; c=e0['canon']
    s=(bp[2]-bp[0])/c[2]; sy=(bp[3]-bp[1])/c[3]
    ox=bp[0]-c[0]*s; oy=bp[1]-c[1]*sy
    sp_page=100*s
    # canonical spacing is 100 px/space in these cells (box height / height_spaces)
    half=sp_page/2
    ycen=(bp[1]+bp[3])/2; top_y=ycen-e0['pos']*half
    sb=e0['stem']; stem_page=(ox+sb[0]*s,oy+sb[1]*sy,sb[2]*s,sb[3]*sy)
    if e0['page'] not in pages: pages[e0['page']]=render_page(R['pdf'],e0['page'],dpi=600).binary
    img=pages[e0['page']]
    xs=[e['bp'][0] for e in ents]+[e['bp'][2] for e in ents]
    cx0=int(min(xs)-2.5*sp_page); cx1=int(max(xs)+2.5*sp_page)
    cy0=int(min(stem_page[1],min(e['bp'][1] for e in ents))-0.6*sp_page); cy1=int(max(stem_page[1]+stem_page[3],max(e['bp'][3] for e in ents))+0.6*sp_page)
    crop=img[cy0:cy1,cx0:cx1].copy()
    fix[name]=dict(raster=crop,sp=np.float64(sp_page),top_y=np.float64(top_y-cy0),half=np.float64(half),
                   stem=np.array([stem_page[0]-cx0,stem_page[1]-cy0,stem_page[2],stem_page[3]]),
                   dets=np.array([[ (e['bp'][0]+e['bp'][2])/2-cx0,(e['bp'][1]+e['bp'][3])/2-cy0,e['bp'][2]-e['bp'][0],e['bp'][3]-e['bp'][1]] for e in ents]),
                   cls=np.array([e['cls'] for e in ents]),keys=np.array([e['key'] for e in ents]))
    print(name,crop.shape,'sp',round(sp_page,2),'stem',[round(v,1) for v in fix[name]['stem']],'top_y',round(top_y-cy0,1))
flat={}
for n,d in fix.items():
    for k,v in d.items(): flat[f"{n}__{k}"]=v
np.savez_compressed('../out/hollow_fixtures.npz',**flat)
import os;print(os.path.getsize('../out/hollow_fixtures.npz'))
