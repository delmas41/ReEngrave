import sys,json; sys.path.insert(0,'.')
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
from tools.omr.staged import readout as RO
PDF={'bra':"library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",'lit':"library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
_cache={}
def page(doc,pg):
    k=(doc,pg)
    if k not in _cache:
        g=render_page(Path(PDF[doc]),pg,dpi=600).rgb
        g=g if g.ndim==2 else g[...,:3].mean(axis=2); _cache[k]=np.where(g<128,0,255).astype(np.uint8)
    return _cache[k]
def tile(doc,pg,box,label,sp=100,pad=2.6,out=260):
    im=page(doc,pg); x0,y0,x1,y1=box; cx,cy=(x0+x1)/2,(y0+y1)/2
    # sp in page px: assume 600dpi staff space ~ ? use box height heuristic
    r=int(pad*sp_page)
    crop=im[max(0,int(cy-r)):int(cy+r),max(0,int(cx-r)):int(cx+r)]
    I=Image.fromarray(crop).convert('RGB').resize((out,out)); d=ImageDraw.Draw(I)
    s=out/(2*r); bx0,by0,bx1,by1=[(v-o)*s for v,o in zip(box,(cx-r,cy-r,cx-r,cy-r))]
    L=14
    for (px,py,dx,dy) in((bx0,by0,1,1),(bx1,by0,-1,1),(bx0,by1,1,-1),(bx1,by1,-1,-1)):
        d.line([(px,py),(px+dx*L,py)],fill=(255,0,0),width=2); d.line([(px,py),(px,py+dy*L)],fill=(255,0,0),width=2)
    d.text((3,3),label,fill=(0,0,255)); return I
def sheet(tiles,cols=4):
    w,h=tiles[0].size; rows=(len(tiles)+cols-1)//cols; S=Image.new('RGB',(w*cols,h*rows),'white')
    for i,t in enumerate(tiles): S.paste(t,((i%cols)*w,(i//cols)*h))
    return S
sp_page=27.5
if __name__=='__main__':
    doc,recp,out=sys.argv[1:4]; keys=sys.argv[4:]
    run=RO.load_run(recp); ts=[]
    for i,k in enumerate(keys):
        g=run.glyphs[k]; ts.append(tile(doc,g.page,g.box_page,f"{i+1} {k.replace('glyph/','')}"))
    sheet(ts).save(out)
