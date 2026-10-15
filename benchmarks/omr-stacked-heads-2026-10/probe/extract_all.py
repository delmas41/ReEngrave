import sys, json, time
sys.path.insert(0, ".")
from tools.omr.staged import record_io, readout as RO
from tools.omr.staged.record import Q
rec_path, out = sys.argv[1], sys.argv[2]
t0=time.time()
result=record_io.load_record(rec_path); run=RO.run_from_result(result,path=rec_path)
print("indexed",round(time.time()-t0),flush=True)
# row id -> glyph key for GLYPH_BOX observations
box_of={}
for k,g in run.glyphs.items(): pass
for o in run.observations:
    if o["quantity"] in (Q.GLYPH_BOX, Q.STACKED_HEAD_FIT): box_of[o["id"]]=o["subject"]
res=[]
for k,g in run.glyphs.items():
    for stage,kind,r in run.rows_at(k):
        if r.get("reason")=="stacked_head_duplicate":
            d=r.get("detail") or {}
            kp=d.get("duplicate_of")
            keeper=box_of.get(kp)
            kg=run.glyphs.get(keeper)
            res.append({"key":k,"page":g.page,"cls":g.cls,"box_page":g.box_page,"box_canon":g.box_canon,
                        "height_spaces":d.get("height_spaces"),"width_spaces":d.get("width_spaces"),
                        "signal":d.get("stacked_head_signal"),"this_ink":d.get("stacked_head_this_ink"),"other_ink":d.get("stacked_head_other_ink"),
                        "keeper":keeper,"keeper_box_page":kg.box_page if kg else None,"keeper_box_canon":kg.box_canon if kg else None,"keeper_cls":kg.cls if kg else None})
json.dump({"dpi":run.dpi,"pdf":run.pdf,"refusals":res},open(out,"w"),default=str)
print("wrote",len(res),round(time.time()-t0),flush=True)
