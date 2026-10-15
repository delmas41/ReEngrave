import sys,json,fitz
sys.path.insert(0,'tree')
from PIL import Image,ImageDraw
from tools.omr.staged import record_io, readout as RO
p="runs/lit-on.json"; run=RO.run_from_result(record_io.load_record(p),path=p)
groups={}
for k,g in run.glyphs.items():
    if not (g.cls or '').startswith('notehead'): continue
    for s,kd,r in run.rows_at(k):
        if r.get('quantity')=='stacked_head_fit' and kd=='observation':
            d=r.get('detail') or {}
            nm=d.get('near_miss') or {}
            if nm.get('hollow_pair')=='both slots hollow':
                groups.setdefault((d.get('stem'),k.rsplit('/',1)[0],nm['hollow_pair'],nm.get('stem_extension_spaces')),[]).append((k,g))
print(len(groups))
pdf=[l for l in open('runs/lit-on.log') if '.pdf' in l][:1]
PDF="tree/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
doc=fitz.open(PDF);cache={}
def pg(i):
    if i not in cache:
        pix=doc[i].get_pixmap(dpi=run.dpi,colorspace=fitz.csRGB);cache[i]=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
    return cache[i]
tiles=[]
for key,mem in sorted(groups.items(),key=lambda x:str(x[0])):
    bs=[g.box_page for k,g in mem]; page=mem[0][1].page
    x0=min(b[0] for b in bs)-90;x1=max(b[2] for b in bs)+90;y0=min(b[1] for b in bs)-90;y1=max(b[3] for b in bs)+90
    im=pg(page).crop((int(x0),int(y0),int(x1),int(y1))).copy();d=ImageDraw.Draw(im)
    for k,g in mem:
        b=g.box_page; d.rectangle([b[0]-x0,b[1]-y0,b[2]-x0,b[3]-y0],outline=(220,0,0),width=2)
    s=300/im.width; im=im.resize((300,int(im.height*s)))
    ImageDraw.Draw(im).text((3,3),f"{mem[0][0][6:]} n{len(mem)} {key[2][:9]} ext{key[3]}",fill=(0,0,0)); tiles.append(im)
for i in range(0,len(tiles),9):
    ts=tiles[i:i+9];H=max(t.height for t in ts);sh=Image.new("RGB",(930,3*(H+8)),"white")
    for j,t in enumerate(ts): sh.paste(t,((j%3)*310,(j//3)*(H+8)))
    sh.save(f"out/lit_{i//9}.png");print(sh.size)
