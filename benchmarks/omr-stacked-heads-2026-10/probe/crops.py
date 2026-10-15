import sys, json
sys.path.insert(0,"/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81")
import fitz, numpy as np
from PIL import Image, ImageDraw
from tools.omr.hand_truth import store as ST
SP="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129"
D=json.load(open(SP+"/out/brahms_p0.json")); G=D["glyphs"]
page=ST.load("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81/data/hand-truth/pages/imslp317803/0.json")
doc=fitz.open(D["pdf"]); pix=doc[0].get_pixmap(dpi=600,colorspace=fitz.csRGB)
im=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
cases=[("A twin q116/q119",["glyph/0/0/0/5/10","glyph/0/0/0/5/13"]),("B twin q226/q224",["glyph/0/0/1/3/12","glyph/0/0/1/3/10"]),
("C twin q267/q269",["glyph/0/0/1/6/6","glyph/0/0/1/6/8"]),("D twin q342/q343",["glyph/0/0/2/3/5","glyph/0/0/2/3/6"]),("E twin q741/q750",["glyph/0/0/6/1/7","glyph/0/0/6/1/17"]),
("F true duplicate (one head boxed twice)",["glyph/0/0/0/4/10","glyph/0/0/0/4/15"]),("G k=2 written third (control)",["glyph/0/0/0/1/6","glyph/0/0/0/1/15"])]
tiles=[]
for name,keys in cases:
    bs=[G[k]["box_page"] for k in keys]
    x0=min(b[0] for b in bs)-120;x1=max(b[2] for b in bs)+120;y0=min(b[1] for b in bs)-120;y1=max(b[3] for b in bs)+120
    c=im.crop((int(x0),int(y0),int(x1),int(y1))).copy(); d=ImageDraw.Draw(c)
    for k in keys:
        b=G[k]["box_page"]; refused=any(r["reason"]=="stacked_head_duplicate" for r in G[k]["rows"])
        d.rectangle([b[0]-x0,b[1]-y0,b[2]-x0,b[3]-y0],outline=(220,0,0) if refused else (0,90,255),width=3)
    for h in page.boxes:
        if h.cls.startswith("notehead") and x0<h.rect[0]<x1 and y0<h.rect[1]<y1:
            d.rectangle([h.rect[0]-x0,h.rect[1]-y0,h.rect[2]-x0,h.rect[3]-y0],outline=(0,170,0),width=2)
    c=c.resize((c.width*2//3,c.height*2//3)); d=ImageDraw.Draw(c); d.text((4,4),name,fill=(0,0,0)); tiles.append(c)
W=sum(t.width for t in tiles[:4])+50; 
rows=[tiles[:4],tiles[4:]]
H=sum(max(t.height for t in r) for r in rows)+30
sheet=Image.new("RGB",(max(sum(t.width+10 for t in r) for r in rows),H+40),"white"); y=0
for r in rows:
    x=0
    for t in r: sheet.paste(t,(x,y)); x+=t.width+10
    y+=max(t.height for t in r)+10
ImageDraw.Draw(sheet).text((4,y+5),"LEGEND: green = Sean's truth head boxes; blue = detector box kept; red = detector box refused stacked_head_duplicate",fill=(0,0,0))
sheet.save(SP+"/out/diagnosis_sheet.png"); print(sheet.size)
