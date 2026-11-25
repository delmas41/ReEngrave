"""Stream-slim a saved record (never loaded whole). usage: slim2.py RECORD OUT.json"""
import sys,json,time
sys.path.insert(0,".")
from tools.omr.staged.judged import iter_array
rec,out=sys.argv[1:3]
t=time.time()
V=[]
for v in iter_array(rec,"verdicts"):
    V.append([v["subject"],v["quantity"],v["outcome"],json.dumps(v.get("value"),sort_keys=True,default=str)[:300],v.get("reason"),v.get("decider"),
              json.dumps(v.get("detail"),sort_keys=True,default=str)[:400],json.dumps(v.get("candidates"),default=str)[:200]])
print("verdicts",len(V),time.time()-t,flush=True)
keep={"glyph_box","page_mark","accidental_staff_position","notehead_class","rest","unboxed_rest_shape","notehead_staff_position","aug_dot","dot_staff_position","staff_spacing","staff_lines","page_mark_owner","far_head_ledger_position","far_head_owner_ledger","ledger_owner_density"}
O=[]
for o in iter_array(rec,"observations"):
    if o["quantity"] in keep:
        O.append([o["subject"],o["quantity"],json.dumps(o.get("value"),default=str)[:200],o.get("reader"),json.dumps(o.get("detail"),default=str)[:500]])
json.dump({"verdicts":V,"obs":O},open(out,"w"))
print("done",len(V),len(O),time.time()-t)
