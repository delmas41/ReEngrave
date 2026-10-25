import json,collections,glob,sys
SC=sys.argv[1]
d=json.load(open(SC+"/run/litolff.off.json"))
pop=[]
for g,v in d["glyphs"].items():
    p=g.split("/")
    if len(p)!=6 or p[4]!="0" or not p[5].isdigit() or int(p[5])>=10000: continue
    if v["rest"] and g not in d["rest_refusals"]: pop.append(g)
rows=[]
byp=collections.defaultdict(list)
for g in pop: byp[int(g.split("/")[1])].append(g)
for pg,gs in sorted(byp.items()):
    box={};cb={};rd={};conf={}
    for l in open(SC+"/slices/litolff/p%02d.observations.jsonl"%pg):
        if '"glyph_box"' in l:
            o=json.loads(l)
            if o["quantity"]=="glyph_box": box[o["subject"]]=(o["value"][0],o["detail"]["bbox_page_px"]); rd[o["subject"]]=o["reader"]; conf[o["subject"]]=o["score"]
        elif '"cell_box"' in l:
            o=json.loads(l)
            if o["quantity"]=="cell_box": cb[o["subject"]]=o["value"]
    for g in gs:
        if g not in box: continue
        p=g.split("/"); cell="cell/"+"/".join(p[1:5]); c=cb[cell]; b=box[g][1]
        x=b[0]-c[0]
        if 60<x<150:
            ownkeys=[box[k][1][0]-c[0] for k in box if k.startswith("glyph/"+"/".join(p[1:5])+"/") and box[k][0].startswith("key")]
            rows.append(dict(g=g,cls=box[g][0],x=round(x),w=round(b[2]-b[0]),h=round(b[3]-b[1]),reader=rd[g],conf=round(conf[g],2),ownkeys=len(ownkeys),box=b))
json.dump(rows,open(SC+"/pop.json","w"))
print(len(rows)); print(collections.Counter((r["cls"],r["reader"]) for r in rows)); print(collections.Counter(r["ownkeys"] for r in rows))
