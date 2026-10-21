"""2.186 (Sean 2026-10-21 widening): the CROSS-CELL part, counted from the 20261020-night records' own rows. For every rest / accidental (non-key)
glyph box and its Q.MARK_GROUP: groups whose members stand in >= 2 staves (one ink boxed once per neighbouring staff's cell), what
`glyph_owner` decided for each member, which member WINS TODAY (`mark_group` rep = most confident member), and whether the OWNER cell's
box has a different class from the winner's.
usage: cross_cell.py DOC SLICEDIR GOWN.jsonl OUT.json"""
import collections, glob, json, os, sys
DOC, SD, GOWN, OUT = sys.argv[1:5]
boxes, groups = {}, {}
for p in sorted(glob.glob(os.path.join(SD, DOC, "*.observations.jsonl"))):
    for l in open(p):
        if '"glyph_box"' not in l and '"mark_group"' not in l:
            continue
        o = json.loads(l)
        if o["quantity"] == "glyph_box":
            cat = (o.get("detail") or {}).get("category")
            v = o["value"]
            if cat in ("rest", "accidental") and not str(v[0]).startswith("key"):
                boxes[o["subject"]] = dict(cls=v[0], conf=o.get("score"), reader=o["reader"], cat=cat, v=v, bb=o["detail"].get("bbox_page_px"))
        elif o["quantity"] == "mark_group":
            groups[o["subject"]] = o
owner = {}
for l in open(GOWN):
    v = json.loads(l)
    owner.setdefault(v["subject"], []).append(v)
def live(chain):
    sup = {x.get("supersedes") for x in chain if x.get("supersedes")}
    return ([x for x in chain if x["id"] not in sup] or chain)[-1]
own = {s: live(c) for s, c in owner.items()}
byg = collections.defaultdict(list)
for s, g in groups.items():
    if s in boxes:
        byg[g["value"]].append(s)
staff = lambda s: tuple(s.split("/")[1:4])
res = collections.defaultdict(collections.Counter)
ex = collections.defaultdict(list)
for gid, mem in byg.items():
    cat = boxes[mem[0]]["cat"]
    c = res[cat]
    c["groups"] += 1
    staves = {staff(s) for s in mem}
    if len(staves) < 2:
        c["one_staff_group"] += 1
        continue
    c["cross_staff_groups"] += 1
    rep = groups[mem[0]]["detail"]["rep"]
    rep = rep if rep in boxes else max(mem, key=lambda s: boxes[s]["conf"] or 0)
    owners = {}
    for s in mem:
        v = own.get(s)
        owners[s] = (v["outcome"], v["value"], v["reason"]) if v else None
    decided = {o[1] for o in owners.values() if o and o[0] == "decided"}
    if not any(owners.values()):
        c["no_owner_verdict_on_any_member"] += 1; continue
    if len(decided) != 1:
        c["owner_undecided_or_split"] += 1; ex[cat + ":undecided"].append((gid, owners)); continue
    ostaff = tuple(next(iter(decided)).split("/")[1:4]) if next(iter(decided)).startswith("staff/") else None
    omem = [s for s in mem if staff(s) == ostaff]
    if not omem:
        c["owner_staff_holds_no_box"] += 1; continue
    c["owner_decided"] += 1
    obest = max(omem, key=lambda s: boxes[s]["conf"] or 0)
    if staff(rep) == ostaff:
        c["winner_is_in_owner_cell"] += 1
    else:
        c["winner_in_other_cell(ink changes hands)"] += 1
    if boxes[obest]["cls"] != boxes[rep]["cls"]:
        c["owner_class_differs_from_winner_class"] += 1
        ex[cat + ":differs"].append((gid, rep, boxes[rep]["cls"], boxes[rep]["conf"], obest, boxes[obest]["cls"], boxes[obest]["conf"], staff(rep) == ostaff))
json.dump(dict(counts={k: dict(v) for k, v in res.items()}, examples={k: v[:40] for k, v in ex.items()}), open(OUT, "w"), indent=1, default=str)
for k, v in res.items():
    print(DOC, k, dict(v))
