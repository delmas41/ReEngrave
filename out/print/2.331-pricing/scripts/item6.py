"""Item 6: judged tiles scored RIGHT on a box the exporter dropped as `mark_group_duplicate`; what the file writes at that place. Plus item 5's file-side grouping count."""
import sys, json, re, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
from tools.omr.staged import judged as J

base, doc, pages_s = sys.argv[1:4]
pages = {int(p) for p in pages_s.split(",")}
mini = pathlib.Path(base + ".mini-record.json")
P = json.load(open(base + ".probe.json"))
fates = P["fates"]
I = json.load(open(base + ".items.json"))
M = json.loads(mini.read_text())
live = {}
sup = {v.get("supersedes") for v in M["verdicts"] if v.get("supersedes")}
for v in M["verdicts"]:
    if v["id"] not in sup:
        live[(v["subject"], v["quantity"])] = v
box = {o["subject"]: (o.get("detail") or {}).get("bbox_page_px") for o in M["observations"]}
xml = open(base.replace("/litolff", "/litolff.readj").replace("/brahms", "/brahms.readj") + ".musicxml").read()
# events in the file: chord groups, beamed or not, value
ev_of, ev_info = {}, []
for part in re.findall(r"<part id=.*?</part>", xml, re.S):
    cur = None
    for m in re.finditer(r'<note rg="([^"]+)"(.*?)</note>', part, re.S):
        g, body = m.group(1), m.group(2)
        if "<chord/>" not in body or cur is None:
            cur = dict(first=g, beamed=bool(re.search(r"<beam ", body)), type=(re.search(r"<type>(\w+)</type>", body) or [None, None])[1],
                       blue="#1F6FEB" in m.group(0), rest="<rest" in body, members=[])
            ev_info.append(cur)
        cur["members"].append(g)
        ev_of[g] = cur
idx = json.loads(J.INDEX_PATH.read_text())
rep = J.score(idx, mini, doc)
print("judged totals", rep["totals"], "matched", rep["matched"])
mg = I["mark_group"]
rows = []
for t in rep["tiles"]:
    if t["status"] != "right":
        continue
    subs = t["subject"] if isinstance(t["subject"], list) else [t["subject"]]
    subs = [s for s in subs if s]
    dropped = [s for s in subs if fates.get(s) == "mark_group_duplicate"]
    if not dropped:
        continue
    for s in dropped:
        gid = mg.get(s)
        mates = [k for k, g in mg.items() if g == gid and k != s] if gid else []
        won = [k for k in mates if fates.get(k) in ("written", "written_relocated")]
        w = won[0] if won else None
        ev = ev_of.get(w) if w else None
        dv = live.get((w, "duration")) if w else None
        rows.append(dict(item=t["item"], tile=t["tile"], answer=t["answer"], scored_on=s, note=t["note"], group=gid, written_by=w,
                         written_fate=fates.get(w) if w else None, file_type=(ev or {}).get("type"), file_blue=(ev or {}).get("blue"),
                         winner_duration=(dv or {}).get("value"), winner_outcome=(dv or {}).get("outcome"), box=box.get(s), all_subjects=subs,
                         page=int(s.split("/")[1])))
print("right on a dropped twin:", len(rows))
for r_ in rows:
    print(r_["item"], r_["tile"], r_["answer"], r_["scored_on"], "->", r_["written_by"], r_["file_type"], "blue" if r_["file_blue"] else "", r_["winner_outcome"], r_["winner_duration"])
json.dump(dict(totals=rep["totals"], rows=rows), open(base + ".item6.json", "w"), indent=1, default=str)

# item 5 file side: the one beam count against the beam the FILE writes on the event
tot = collections.Counter()
rows5 = []
for (s, q), v in live.items():
    if q != "duration" or not s.startswith("glyph/") or int(s.split("/")[1]) not in pages or fates.get(s) != "written":
        continue
    d = v.get("detail") or {}
    ob = d.get("one_beam_count")
    ev = ev_of.get(s)
    if not isinstance(ob, dict) or ev is None or ob.get("state") != "read":
        continue
    c_, p_ = int(ob.get("certain") or 0), int(ob.get("possible") or 0)
    tot["read"] += 1
    if c_ >= 1 and not ev["beamed"]:
        k = "count_beamed_file_unbeamed"
    elif c_ == 0 and p_ == 0 and ev["beamed"]:
        k = "count_none_file_beamed"
    else:
        continue
    tot[k] += 1
    rows5.append(dict(sub=s, kind=k, certain=c_, A_joined=d.get("beams_by_stem"), flags=d.get("flags_attached"), file_type=ev["type"], file_blue=ev["blue"],
                      box=box.get(s), first=ev["first"]))
# one row per event
seen, ev_rows = set(), []
for r_ in rows5:
    if r_["first"] in seen:
        continue
    seen.add(r_["first"])
    ev_rows.append(r_)
print("item5 file side (notes):", dict(tot), "events:", collections.Counter(r_["kind"] for r_ in ev_rows))
json.dump(dict(totals=dict(tot), events=ev_rows), open(base + ".item5file.json", "w"), indent=1, default=str)
