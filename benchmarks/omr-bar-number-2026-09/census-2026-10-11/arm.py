import json,sys
from types import SimpleNamespace
from tools.omr.preprocessing import render_page
from tools.omr.staged import gather as G, adjudicate, adjudicators  # noqa
from tools.omr.staged.record import Log, Q
S=sys.argv[1]
L="/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDF={"brahms1-breitkopf":L+"brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
     "beethoven5-litolff":L+"beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
def rows(log):
    out=[]
    for r in log.all_rows():
        if getattr(r,"quantity",None)!=Q.PRINTED_BAR_NUMBER: continue
        out.append({"subject":r.subject.to_key(),"reader":str(r.reader),"value":getattr(r,"value",None),
                    "reason":str(getattr(r,"reason","")) or None,"bbox":(r.detail or {}).get("bbox_page_px")})
    return out
def verdicts(log, subs):
    log.freeze(); adjudicate.run(log)
    out={}
    for s in subs:
        v=log.verdict(Q.PRINTED_BAR_NUMBER, s)
        out[s.to_key()]=(str(v.outcome.value), v.value, v.reason)
    return out
res={}
for n,pdf in PDF.items():
    st=json.load(open(f"{S}/{n}_staves.json"))
    pages=sorted({int(k.split("/")[1]) for k in st})
    arms={"tess":Log(),"surya":Log()}
    for p in pages:
        img=render_page(pdf,p,600)
        staves=[]
        for k,v in st.items():
            _,pp,sy,o=k.split("/")
            if int(pp)!=p or "staff_lines" not in v or "staff_extent" not in v: continue
            staves.append(SimpleNamespace(system_index=int(sy),staff_index=int(o),line_ys=v["staff_lines"],
                x_start=v["staff_extent"][0],x_end=v["staff_extent"][1],top_y=v["staff_lines"][0]))
        pws=SimpleNamespace(page=SimpleNamespace(page_index=p,rgb=img.rgb),staves=staves)
        G.gather_printed_bar_numbers(arms["tess"],pws,surya=False)
        G.gather_printed_bar_numbers(arms["surya"],pws,surya=True)
        print(n,p,flush=True)
    res[n]={}
    for a,log in arms.items():
        rr=rows(log)
        from tools.omr.staged import record as R
        subs=sorted({tuple(map(int,x["subject"].split("/")[1:])) for x in rr})
        res[n][a]={"rows":rr,"verdicts":verdicts(log,[R.system(*s) for s in subs])}
json.dump(res,open(f"{S}/arms.json","w"),default=str)
