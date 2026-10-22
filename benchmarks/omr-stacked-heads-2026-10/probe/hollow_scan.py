import sys,json; sys.path.insert(0,".")
from tools.omr.staged import record_io, readout as RO
from tools.omr.staged.adjudicators import rhythm
run=RO.run_from_result(record_io.load_record("library/_shared-records/brahms1-breitkopf-mvt1-whole-20261013-night.record.json"),path="x")
box_of={}
for o in run.observations:
    if o["quantity"]=="stacked_head_fit": box_of[o["id"]]=o["subject"]
out=[]
for k,g in run.glyphs.items():
    if not (g.cls or "").startswith(("noteheadHalf","noteheadWhole")): continue
    for s,kd,r in run.rows_at(k):
        if r.get("reason")=="stacked_head_duplicate":
            d=r.get("detail") or {}; kp=box_of.get(d.get("duplicate_of")); kg=run.glyphs.get(kp)
            def hol(key):
                for rr in run.obs_at(key,"notehead_ink"): return rhythm._ink_reads_decisively_hollow(rr.get("detail") or {}), ((rr.get("detail") or {}).get("ink_raw") or {}).get("windows")
                return None,None
            h1=hol(k); h2=hol(kp) if kp else (None,None)
            b=g.box_page; kb=kg.box_page if kg else None
            sp=(b[3]-b[1])/d["height_spaces"] if b and d.get("height_spaces") else None
            dy=abs((b[1]+b[3])/2-(kb[1]+kb[3])/2)/sp if kb and sp else None
            out.append({"key":k,"keeper":kp,"cls":g.cls,"kcls":kg.cls if kg else None,"dy":dy,"hol":h1[0],"khol":h2[0],"w":h1[1],"kw":h2[1],"page":g.page})
json.dump(out,open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129/out/hollow_scan.json","w"))
print(len(out))
