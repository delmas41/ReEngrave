"""2.120 round 2 (e): lane 2.119's 69 twin pairs (pairs.csv, from origin/lane-2.119-twins) through the FINAL table.
A pair = one note written + its look-alike that is not. Brahms ids are Sean's truth ids (qNNNN) -> truth boxes + the detector box on them.
Litolff ids are '<cell>#<n>' (n = 2.119's own head counter, not recoverable): matched by CELL where the cell holds exactly one hollow truth head.
Question: does the table (a) give the two twins different sets, (b) catch the detector's wrong class on the missed twin, (c) touch the split?"""
import csv, json, sys, collections
sys.path.insert(0, ".")
import table2 as T2, table as T1
pairs = list(csv.DictReader(open("pairs.csv")))
TR = {r["id"]: r for r in json.load(open("measure2/truth2_rows.json"))}
DT = json.load(open("measure2/detector_rows.json"))
byt = collections.defaultdict(list)
for r in DT:
    if r["tid"] and r["iou"] >= 0.5: byt[r["tid"]].append(r)
LR = json.load(open("measure2/litolff_rows.json")); bycell = collections.defaultdict(list)
for r in LR:
    if not r["leaked"]: bycell[r["cell"]].append(r)
FS = T2.SYMBOLS
out = collections.defaultdict(lambda: collections.Counter())
detail = []
def setof(doc, i):
    if doc == "brahms":
        t = TR.get(i); 
        if not t: return None
        c, _ = T2.candidates(t["d"]); return dict(all=c["all"], sym=t["sym"], det=[(x["cls"], x["status"], x["dsym"], x["dsym"] in T2.candidates(x["d"])[0]["all"]) for x in byt.get(i, [])])
    cell = i.split("#")[0]; L = bycell.get(cell, [])
    if len(L) != 1: return None
    r = L[0]; c, _ = T2.candidates(r["d"]); return dict(all=c["all"], sym=r["sym"], det=[(r["det_cls"], r["det_status"], T1.symbol_of(r["det_cls"]), (T1.symbol_of(r["det_cls"]) in T2.candidates(r["d"])[0]["all"]) if r["det_cls"] else None)] if r["det_iou"] >= 0.5 else [])
for p in pairs:
    g = p["split_group"][:1]; a = setof(p["doc"], p["miss_id"]); b = setof(p["doc"], p["twin_id"])
    o = out[g]; o["pairs"] += 1
    if a is None or b is None: o["unresolved (no truth/descriptor)"] += 1; continue
    o["resolved"] += 1
    o["same candidate set"] += a["all"] == b["all"]
    o["missed twin: true head symbol in set"] += a["sym"] in a["all"]
    o["twin: true head symbol in set"] += b["sym"] in b["all"]
    wrong = [d for d in a["det"] if d[2] and d[2] != a["sym"]]
    o["missed twin has a WRONG detector class"] += bool(wrong)
    o["  ...and the table eliminates that class (caught)"] += any(not d[3] for d in wrong)
    o["missed twin has a detector box (IoU>=.5)"] += bool(a["det"])
    o["missed twin's box is REFUSED"] += any(d[1] == "refused" for d in a["det"])
    detail.append((p["doc"], p["split_group"], p["miss_id"], "/".join(sorted(a["all"] - b["all"])) or "-", "/".join(sorted(b["all"] - a["all"])) or "-"))
print("group | counts")
for g in sorted(out): print(g, dict(out[g]))
print("\nsets that DIFFER between the twins (only-in-missed | only-in-twin):")
for d in detail:
    if d[3] != "-" or d[4] != "-": print(" ", d)
print("\npost-identity splits (A,B,D,G) =", sum(out[g]["pairs"] for g in "ABDG"), "| identity splits (C,E,F) =", sum(out[g]["pairs"] for g in "CEF"))
