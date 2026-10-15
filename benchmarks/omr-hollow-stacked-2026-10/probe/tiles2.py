"""2.132 blind tiles (15): how many noteheads are in the red corners? 0 / 1 / 2 / other. Only a fixed-size red corner bracket is drawn."""
import sys,json,random,os
sys.path.insert(0,'tree')
import fitz
from PIL import Image,ImageDraw
from tools.omr.staged import record_io, readout as RO
OUT=sys.argv[1]
SP="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad"
G=json.load(open('out/hollow_groups.json'))
BRA="/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
LIT="/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
T=json.load(open("tree/data/hand-truth/pages/imslp317803/0.json")); tr={b["id"]:b["rect"] for b in T["boxes"]}
specs=[("bra3","glyph/3/1/11/0","PAIR_kept_brahms"),("bra7","glyph/7/1/2/9","PAIR_kept_brahms"),("bra8","glyph/8/1/0/10","PAIR_kept_brahms"),
 ("bra10","glyph/10/1/0/4","PAIR_kept_brahms"),("bra12","glyph/12/0/2/7","PAIR_kept_brahms_4boxes"),("bra18","glyph/18/1/11/6","PAIR_kept_brahms_3boxes"),
 ("bra10","glyph/10/1/5/3","PAIR_kept_brahms_both_boxes_were_kept_at_one_slot_before"),
 ("lit","glyph/2/1/4/13","PAIR_kept_litolff_doubtful"),("lit","glyph/3/0/1/4","PAIR_kept_litolff_3boxes"),("lit","glyph/3/0/4/6","PAIR_kept_litolff_4boxes"),("lit","glyph/3/1/2/15","PAIR_kept_litolff_clear"),
 ("bra25","glyph/25/1/5/9","REFUSED_stem_does_not_reach_upper_head"),
 ("bra01","glyph/0/0/11/7","NUMERAL_8_of_9over8_expect_0"),("bra18","glyph/18/1/3/7","BASS_CLEF_expect_0"),("truth","q711+q712","CONTROL_one_hollow_head_cut_by_a_line_expect_1")]
runs={}
def run(t):
    if t not in runs:
        p=f"runs/{t}-on.json"; runs[t]=RO.run_from_result(record_io.load_record(p),path=p)
    return runs[t]
items=[]
for tag,g,kind in specs:
    if tag=="truth":
        items.append(dict(kind=kind,glyph=g,page=0,pdf=BRA,boxes=[tr["q711"],tr["q712"]],sp=32.25,dpi=600)); continue
    r=run(tag)
    mem=[k for k in G[f'{tag}|{g}']['members'] if (r.glyphs[k].cls or '').startswith(('noteheadHalf','noteheadWhole'))]
    if g=="glyph/18/1/3/7": mem=["glyph/18/1/3/7/20","glyph/18/1/3/7/26"]
    boxes=[r.glyphs[k].box_page for k in mem]
    hs=None
    for k in mem:
        for s,kd,row in r.rows_at(k):
            if row.get('quantity')=='notehead_is_not_a_notehead' and kd=='verdict' and (row.get('detail') or {}).get('height_spaces'):
                b=r.glyphs[k].box_page; hs=(b[3]-b[1])/row['detail']['height_spaces']; break
        if hs: break
    items.append(dict(kind=kind,glyph=g,page=r.glyphs[mem[0]].page,pdf=BRA if tag.startswith('bra') else LIT,boxes=boxes,sp=hs,dpi=r.dpi))
rnd=random.Random(1320); rnd.shuffle(items)
docs={};cache={}
def pg(pdf,p,dpi):
    if (pdf,p) not in cache:
        d=docs.setdefault(pdf,fitz.open(pdf)); pix=d[p].get_pixmap(dpi=dpi,colorspace=fitz.csRGB); cache[(pdf,p)]=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
    return cache[(pdf,p)]
os.makedirs(OUT+"/_hidden",exist_ok=True)
manifest=[];imgs=[]
for i,o in enumerate(items,1):
    sp=o["sp"]; bs=o["boxes"]
    x0=min(b[0] for b in bs);x1=max(b[2] for b in bs);y0=min(b[1] for b in bs);y1=max(b[3] for b in bs)
    cx=(x0+x1)/2;cy=(y0+y1)/2;half=4.0*sp
    im=pg(o["pdf"],o["page"],o["dpi"]).crop((int(cx-half*1.3),int(cy-half),int(cx+half*1.3),int(cy+half)))
    s=420/im.height; im=im.resize((int(im.width*s),420),Image.LANCZOS); d=ImageDraw.Draw(im)
    hb=1.4*sp*s;ccx=im.width/2;ccy=im.height/2;L=14
    for sx in (-1,1):
        for sy in (-1,1):
            px=ccx+sx*hb;py=ccy+sy*hb
            d.line([(px,py),(px-sx*L,py)],fill=(220,0,0),width=3);d.line([(px,py),(px,py-sy*L)],fill=(220,0,0),width=3)
    t=Image.new("RGB",(im.width,im.height+30),"white");t.paste(im,(0,30))
    ImageDraw.Draw(t).text((6,6),f"{i}   how many noteheads are in the red corners?  0 / 1 / 2 / other",fill=(0,0,0))
    imgs.append(t);manifest.append(dict(tile=i,kind=o["kind"],glyph=o["glyph"],pdf_page=o["page"],pdf=os.path.basename(o["pdf"])))
W=max(t.width for t in imgs)
for part,chunk in enumerate([imgs[:6],imgs[6:12],imgs[12:]]):
    if not chunk: continue
    Hh=max(t.height for t in chunk);sheet=Image.new("RGB",(W*3+20,Hh*2+10),"white")
    for j,t in enumerate(chunk): sheet.paste(t,((j%3)*(W+10),(j//3)*(Hh+10)))
    sheet.save(f"{OUT}/hollow-pairs-review-{part+1}.png")
json.dump(manifest,open(OUT+"/_hidden/manifest.json","w"),indent=1)
print(len(imgs))
