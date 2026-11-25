import sys,json,collections
sys.path.insert(0,".")
from tools.omr.staged import lane_report as L
C="/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/overnight-20261123-night/compare/rank/"
out={}
for plate in ["litolff","brahms"]:
    A=json.load(open(C+plate+".base-all.symbols.json")); B=json.load(open(C+plate+".tag-all.symbols.json"))
    d=L.diff_arms(A,B,tol=0.5*L.PLATES[plate]["unit"])
    print(plate,L.format_counts(d["counts"])[:200])
    out[plate]=d["changes"]
    print(json.dumps(A["hosts"][0])[:600])
json.dump(out,open(sys.argv[1]+"/changes.json","w"))
