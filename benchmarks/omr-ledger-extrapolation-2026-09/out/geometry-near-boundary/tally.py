import json,sys,collections
sys.path.insert(0,"/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab56d1d321c30c4bd")
from tools.omr.pitch_resolver import _pitch_from_position as P
NOT_A_HEAD={"glyph/1/0/3/1/18":"the dynamic f, not a notehead (crop review)"}
def pn(s,cl):
    try: return P(s,cl or "treble") if s is not None else "no answer"
    except Exception: return str(s)
def cat(why):
    w=why or ""
    if "vertical stroke" in w or "no head ink" in w: return "not a separable head (detector box on a barline/stem/text)"
    if "merged" in w: return "head ink merged (stack/beam/neighbour) -- not separable"
    if "no ledger between" in w: return "no ledger between staff and head (missed ledger or not this staff's note)"
    if "staff lines not measured" in w: return "staff lines not measured"
    return w[:60]
out={}
for tag in ("lit3","brk1"):
    rows=json.load(open(f"{tag}-geom2.json"))
    for r in rows:
        if r["subject"] in NOT_A_HEAD:
            r["measured"]={**r["measured"],"step":None,"why":NOT_A_HEAD[r["subject"]]}
    json.dump(rows,open(f"{tag}-final.json","w"),indent=1,default=str)
    for grp in ("near","control","sean"):
        g=[r for r in rows if r["group"]==grp]
        c=collections.Counter(); u=collections.Counter()
        for r in g:
            m=r["measured"]; T=m.get("step")
            if T is None: c["unreadable"]+=1; u[cat(m.get("why"))]+=1; continue
            for k,v in (("geometry",r["geometry"]),("2.44",r["A"]),("ledger_grid",r["B"]),("C",m.get("C"))):
                c[f"{k} {'no answer' if v is None else ('right' if v==T else 'wrong')}"]+=1
            c["readable"]+=1
        if g:
            print(f"== {tag} {grp} n={len(g)}: readable {c['readable']}, unreadable {c['unreadable']}")
            for k in ("geometry","2.44","ledger_grid","C"):
                print(f"   {k:12} right {c[k+' right']:2}  wrong {c[k+' wrong']:2}  no answer {c[k+' no answer']:2}")
            if u: print("   unreadable:",dict(u))
    for r in rows:
        m=r["measured"];T=m.get("step")
        if T is not None and r["geometry"]!=T:
            cl=r["clef"]
            print(f"   GEOMETRY WRONG [{r['group']}] {r['subject']} ({r['staff_pos']}): print {pn(T,cl)} -- {m['words']}; geometry {pn(r['geometry'],cl)}; 2.44 {pn(r['A'],cl)}; ledger_grid {pn(r['B'],cl)}; C {pn(m.get('C'),cl)}")
