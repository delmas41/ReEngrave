import sys, json, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT
from tools.omr.staged.record_io import load_record
from tools.omr.staged.record import Q
CAP={}
orig=EXPORT._place_notes
def place(rec, runs, **kw):
    CAP["rec"]=rec; CAP["fates"]=kw.get("fates"); return orig(rec, runs, **kw)
EXPORT._place_notes=place
d=load_record(sys.argv[1]); EXPORT.to_musicxml(d)
rec,fates=CAP["rec"],CAP["fates"]
subs=[s for s,f in fates.items() if f=="duration_narrowed"]
print(len(subs))
import random; random.seed(278)
for s in random.sample(subs,2):
    v=rec.verdict(Q.DURATION,s)

    print(s, list(v.keys())); print(json.dumps(v,default=str)[:4500])