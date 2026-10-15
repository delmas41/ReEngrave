import json, random, sys, os
import fitz
from PIL import Image, ImageDraw, ImageFont
SP="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129"
OUT=sys.argv[1] if len(sys.argv)>1 else SP+"/tiles"
D=json.load(open(SP+"/out/refusals_all.json")); R={r["key"]:r for r in D["refusals"]}
C=json.load(open(SP+"/out/refusals_cat.json"))
def cat(o):
    if o["dy"]<0.5: return "A"
    if o["dy"]>=0.85 and o["blob"]>=1.8: return "B"
    if o["dy"]>=0.85: return "C"
    return "D"
rnd=random.Random(129)
blk=lambda o:(R[o["key"]]["cls"] or "").startswith("noteheadBlack") and (R[o["key"]]["keeper_cls"] or "").startswith("noteheadBlack")
B=[o for o in C if cat(o)=="B" and blk(o)]; A=[o for o in C if cat(o)=="A"]; Cc=[o for o in C if cat(o)=="C" and o["blob"]<1.0]
# spread B over pages, prefer page 0 truth-verified ones (3), rest random across other pages
b0=[o for o in B if o["page"]==0]; brest=[o for o in B if o["page"]!=0]
rnd.shuffle(brest)
pick=b0[:3]; seen=set()
for o in brest:
    if o["page"] in seen: continue
    seen.add(o["page"]); pick.append(o)
    if len(pick)==13: break
controls=[rnd.choice(A),rnd.choice(Cc)]
for o in controls: o["_ctl"]=True
tiles=pick+controls; rnd.shuffle(tiles)
doc=fitz.open(D["pdf"]); cache={}
def page_img(p):
    if p not in cache:
        pix=doc[p].get_pixmap(dpi=D["dpi"],colorspace=fitz.csRGB); cache[p]=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
    return cache[p]
os.makedirs(OUT+"/_hidden",exist_ok=True)
manifest=[]; imgs=[]
for i,o in enumerate(tiles,1):
    r=R[o["key"]]; b=r["box_page"]; kb=r["keeper_box_page"]
    sp=(b[3]-b[1])/r["height_spaces"]
    x0=min(b[0],kb[0]);x1=max(b[2],kb[2]);y0=min(b[1],kb[1]);y1=max(b[3],kb[3])
    cx=(x0+x1)/2;cy=(y0+y1)/2
    half=4.0*sp
    im=page_img(r["page"]).crop((int(cx-half*1.3),int(cy-half),int(cx+half*1.3),int(cy+half)))
    s=420/im.height; im=im.resize((int(im.width*s),420),Image.LANCZOS)
    d=ImageDraw.Draw(im)
    # fixed-size red corner brackets, 3.2 sp square, centred on the pair
    hb=1.4*sp*s; ccx=im.width/2; ccy=im.height/2; L=14
    for sx in (-1,1):
        for sy in (-1,1):
            px=ccx+sx*hb; py=ccy+sy*hb
            d.line([(px,py),(px-sx*L,py)],fill=(220,0,0),width=3); d.line([(px,py),(px,py-sy*L)],fill=(220,0,0),width=3)
    t=Image.new("RGB",(im.width,im.height+30),"white"); t.paste(im,(0,30)); ImageDraw.Draw(t).text((6,6),f"{i}   how many noteheads are in the red corners?  1 / 2 / other",fill=(0,0,0))
    imgs.append(t)
    manifest.append({"tile":i,"kind":("CONTROL_one_head_boxed_twice" if o.get("_ctl") and cat(o)=="A" else "CONTROL_ghost_box_one_head" if o.get("_ctl") else "PROXY_B_two_heads_expected"),"glyph":o["key"],"pdf_page":r["page"],"dy_sp":o["dy"],"blob_sp":o["blob"]})
cols=3; rows=(len(imgs)+cols-1)//cols
W=max(t.width for t in imgs)
for part,chunk in enumerate([imgs[:6],imgs[6:12],imgs[12:]]):
    if not chunk: continue
    Hh=max(t.height for t in chunk); sheet=Image.new("RGB",(W*3+20,Hh*2+10),"white")
    for j,t in enumerate(chunk): sheet.paste(t,((j%3)*(W+10),(j//3)*(Hh+10)))
    sheet.save(f"{OUT}/stacked-heads-review-{part+1}.png")
json.dump(manifest,open(OUT+"/_hidden/manifest.json","w"),indent=1)
print(len(tiles),"tiles; kinds",[m["kind"][:8] for m in manifest])
