import json, fitz
from PIL import Image, ImageDraw
R=json.load(open('../2.129/out/refusals_all.json'))
h=json.load(open('tree/benchmarks/omr-stacked-heads-2026-10/out/hollow_scan.json'))
sel=[r['key'] for r in h if r['dy'] is not None and r['dy']>=0.75]
ex=[r for r in R['refusals'] if r['key'] in sel]
doc=fitz.open(R['pdf']); cache={}
tiles=[]
for i,r in enumerate(ex):
    p=r['page']
    if p not in cache:
        pix=doc[p].get_pixmap(dpi=600,colorspace=fitz.csRGB); cache[p]=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
    im=cache[p]
    a,b=r['box_page'],r['keeper_box_page']
    x0=min(a[0],b[0])-110;x1=max(a[2],b[2])+110;y0=min(a[1],b[1])-110;y1=max(a[3],b[3])+110
    c=im.crop((int(x0),int(y0),int(x1),int(y1))).copy();d=ImageDraw.Draw(c)
    d.rectangle([a[0]-x0,a[1]-y0,a[2]-x0,a[3]-y0],outline=(220,0,0),width=2)
    d.rectangle([b[0]-x0,b[1]-y0,b[2]-x0,b[3]-y0],outline=(0,90,255),width=2)
    c=c.resize((300,int(c.height*300/c.width))) if c.width!=300 else c
    d=ImageDraw.Draw(c); d.text((3,3),f"{i} {r['key'][6:]}",fill=(0,0,0)); tiles.append(c)
for s in range(0,len(tiles),9):
    ts=tiles[s:s+9]; H=max(t.height for t in ts)
    sh=Image.new("RGB",(3*310,3*(H+10)),"white")
    for j,t in enumerate(ts): sh.paste(t,((j%3)*310,(j//3)*(H+10)))
    sh.save(f"out/h27_{s//9}.png"); print(sh.size)
json.dump([r['key'] for r in ex],open('out/h27_order.json','w'))
