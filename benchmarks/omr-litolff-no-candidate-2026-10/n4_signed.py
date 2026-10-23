import json,sys,collections,statistics
d=json.load(open(sys.argv[1])); rec=d.get("record",d); obs=rec["observations"]; verdicts=rec["verdicts"]
chains=collections.defaultdict(list)
for v in verdicts: chains[(v["subject"],v["quantity"])].append(v)
live={}
for k,ch in chains.items():
    sup={x.get("supersedes") for x in ch if x.get("supersedes")}; live[k]=([x for x in ch if x["id"] not in sup] or ch)[-1]
accpos={o["subject"]:o for o in obs if o["quantity"]=="accidental_staff_position"}
headpos={o["subject"]:float(o["value"]) for o in obs if o["quantity"]=="notehead_staff_position" and isinstance(o["value"],(int,float))}
cls={o["subject"]:o["value"][0] for o in obs if o["quantity"]=="glyph_box"}
rows=collections.defaultdict(list)
for k,o in accpos.items():
    own=live.get((k,"accidental_owner"))
    if not own or own["outcome"]!="decided": continue
    h=own["value"]; 
    if h not in headpos: continue
    dt=o["detail"]; c=dt["detector_class"]
    rows[c].append((headpos[h]-float(o["value"]), headpos[h]-dt["box_centre_position"], (dt["y1"]-dt["y0"])/100.0))
for c,v in rows.items():
    a=[x[0] for x in v]; b=[x[1] for x in v]
    print(c,len(v),"signed dy (head-anchor): median %.2f sd %.2f | vs centre: median %.2f sd %.2f"%(statistics.median(a),statistics.pstdev(a),statistics.median(b),statistics.pstdev(b)))
