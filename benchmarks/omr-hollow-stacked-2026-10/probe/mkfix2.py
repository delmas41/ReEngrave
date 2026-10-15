import sys,json,ast,numpy as np
sys.path.insert(0,'.')
from tools.omr.preprocessing import render_page
from tools.omr.staged import record_io, readout as RO
p="../runs/lit-on.json"; run=RO.run_from_result(record_io.load_record(p),path=p)
PDF="library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
def ob(k,q):
    for s,kd,r in run.rows_at(k):
        if r.get('quantity')==q and kd=='observation': return r
cases={"litolff_pair_two_stems":["glyph/3/0/1/5/7","glyph/3/0/1/5/10"],"litolff_pair_kept":["glyph/3/1/2/15/0","glyph/3/1/2/15/2"]}
z=dict(np.load('tools/omr/tests/fixtures/stacked_hollow_2_132.npz'))
pages={}
for name,keys in cases.items():
    ents=[]
    for k in keys:
        g=run.glyphs[k]; gb=ob(k,'glyph_box'); canon=ast.literal_eval(gb['value']) if isinstance(gb['value'],str) else gb['value']
        ents.append(dict(key=k,cls=g.cls,page=g.page,bp=g.box_page,canon=canon[1:],pos=float(ob(k,'notehead_staff_position')['value'])))
    e0=ents[0];bp=e0['bp'];c=e0['canon']
    s=(bp[2]-bp[0])/c[2]; sy=(bp[3]-bp[1])/c[3]; ox=bp[0]-c[0]*s; oy=bp[1]-c[1]*sy
    # canonical staff space: box h / height_spaces -> use stem-free estimate from detection: standard head ~1.1 sp
    stems=[]
    cellkey="cell/"+keys[0][6:].rsplit('/',1)[0]
    for stage,kind,r in run.by_subject.get(cellkey,[]):
        if r.get('quantity')=='stem': stems.append(r['value'])
    # spacing: take from refusal height_spaces of a refused box
    hs=None
    for k in keys:
        for stg,kd,r in run.rows_at(k):
            if r.get('quantity')=='notehead_is_not_a_notehead' and kd=='verdict':
                d=r.get('detail') or {}
                if d.get('height_spaces'): hs=(k,d['height_spaces'])
    g0=run.glyphs[hs[0]]; sp_page=(g0.box_page[3]-g0.box_page[1])/hs[1]
    half=sp_page/2; ycen=(bp[1]+bp[3])/2; top_y=ycen-e0['pos']*half
    stems_page=[(ox+a*s,oy+b*sy,w*s,h*sy) for a,b,w,h in stems]
    if e0['page'] not in pages: pages[e0['page']]=render_page(PDF,e0['page'],dpi=600).binary
    img=pages[e0['page']]
    xs=[e['bp'][0] for e in ents]+[e['bp'][2] for e in ents]
    cx0=int(min(xs)-2.5*sp_page);cx1=int(max(xs)+2.5*sp_page)
    cy0=int(min(min(st[1] for st in stems_page),min(e['bp'][1] for e in ents))-0.6*sp_page); cy1=int(max(max(st[1]+st[3] for st in stems_page),max(e['bp'][3] for e in ents))+0.6*sp_page)
    cy0=max(cy0,0)
    z[name+"__raster"]=img[cy0:cy1,cx0:cx1].copy(); z[name+"__sp"]=np.float64(sp_page); z[name+"__top_y"]=np.float64(top_y-cy0); z[name+"__half"]=np.float64(half)
    z[name+"__stems"]=np.array([[a-cx0,b-cy0,w,h] for a,b,w,h in stems_page]); z[name+"__stem"]=z[name+"__stems"][0]
    z[name+"__dets"]=np.array([[(e['bp'][0]+e['bp'][2])/2-cx0,(e['bp'][1]+e['bp'][3])/2-cy0,e['bp'][2]-e['bp'][0],e['bp'][3]-e['bp'][1]] for e in ents])
    z[name+"__cls"]=np.array([e['cls'] for e in ents]); z[name+"__keys"]=np.array([e['key'] for e in ents])
    print(name,z[name+"__raster"].shape,round(sp_page,1),z[name+"__stems"].round(0).tolist(),hs)
np.savez_compressed('tools/omr/tests/fixtures/stacked_hollow_2_132.npz',**z); np.savez_compressed('../out/hollow_fixtures.npz',**z)
