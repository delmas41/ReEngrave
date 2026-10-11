"""ROADMAP 2.86 reach census: per system, every staff's tail-cell GLYPH_BOX classes,
the arm's `_staff_tail_is_key_shaped` vote, and the saved Q.SYSTEM_KEY verdict.
Usage: tail_census_2_86.py REC OUT.json [TREE]. Streams with ijson."""
import sys, json, collections
TREE=sys.argv[3] if len(sys.argv)>3 else "."
sys.path.insert(0, TREE)
import ijson
from tools.omr.staged.record import Kind, Q, Subject
from tools.omr.staged.adjudicators import structure as S
rec=sys.argv[1]; out=sys.argv[2]
n_cells={}
with open(rec,"rb") as fh:
    for it in ijson.items(fh,"record.observations.item",use_float=True):
        if it["quantity"]==Q.BARLINE_COLUMN:
            n_cells[it["subject"]]=int(it["value"])
tail={}
for k,n in n_cells.items():
    s=Subject.from_key(k); tail.setdefault((s.page,s.system),set()).add(n-1)
glyph=collections.defaultdict(list)  # (page,system,staff,cell) -> rows
with open(rec,"rb") as fh:
    for it in ijson.items(fh,"record.observations.item",use_float=True):
        if it["quantity"]!=Q.GLYPH_BOX: continue
        s=Subject.from_key(it["subject"])
        if s.cell is None or s.cell not in tail.get((s.page,s.system),()): continue
        glyph[(s.page,s.system,s.staff,s.cell)].append(it)
keys={}
with open(rec,"rb") as fh:
    for it in ijson.items(fh,"record.verdicts.item",use_float=True):
        if it["quantity"]==Q.SYSTEM_KEY:
            keys[it["subject"]]={k:it.get(k) for k in ("id","outcome","value","reason","supersedes")}
class R:  # minimal row shim
    def __init__(s,it): s.value=it["value"]
res={"systems":{}}
for (p,sy),cells in sorted(tail.items()):
    staves=[]
    for k,n in n_cells.items():
        s=Subject.from_key(k)
        if (s.page,s.system)!=(p,sy): continue
        rows=sorted(glyph.get((p,sy,s.staff,n-1),[]), key=lambda it: it["value"][1])
        vote=S._staff_tail_is_key_shaped([R(r) for r in rows]) if rows else None
        staves.append({"staff":s.staff,"n_cells":n,"classes":[r["value"][0] for r in rows],"vote":vote})
    res["systems"][f"{p}/{sy}"]={"staves":sorted(staves,key=lambda d:d["staff"]),
        "n_yes":sum(1 for d in staves if d["vote"] is True),
        "n_voting":sum(1 for d in staves if d["vote"] is not None),
        "system_key":keys.get(f"system/{p}/{sy}")}
json.dump(res,open(out,"w"),indent=1,default=str)
