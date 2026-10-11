import json,sys,copy
from tools.omr.staged.record_io import load_record
from tools.omr.staged.export import to_musicxml
S=sys.argv[1]; A=json.load(open(f"{S}/arms.json")); out={}
for n in A:
    r=load_record(f"/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/{n}-mvt1-whole-20261010-night.record.json")
    _,rep=to_musicxml(r); base=rep["measure_numbering"]["printed_bar_check"]
    arm=A[n]["surya"]["verdicts"]; k=0
    for v in r["record"]["verdicts"]:
        if v["quantity"]!="printed_bar_number": continue
        o,val,why=arm[v["subject"]]; v["outcome"]=o; v["value"]=val; v["reason"]=why; k+=1
    _,rep=to_musicxml(r); out[n]={"base":base,"arm":rep["measure_numbering"]["printed_bar_check"],"scheme":rep["measure_numbering"].get("scheme"),"swapped":k}
    print(n,"swapped",k,{a:{x:out[n][a][x] for x in ("agree","disagree","abstained")} for a in ("base","arm")},flush=True)
json.dump(out,open(f"{S}/pricecheck.json","w"),default=str)
