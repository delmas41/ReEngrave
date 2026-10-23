"""2.200 N1: per-box features for every accidental-class box whose accidental_owner verdict is no_candidate (STAGED, ADJUDICATE).
usage: n1_features.py RECORD.json OUT.json [pages comma list]
Everything in the cell's CANONICAL frame (100 units = 1 staff space) unless named page_px. Recomputes the owner's own window test so each
refusal says WHICH bound failed and by how much, plus what a class-agnostic (box-centre) anchor would have done."""
import sys, json, collections
rec_path, out_path = sys.argv[1], sys.argv[2]
d = json.load(open(rec_path)); rec = d.get("record", d)
obs = rec["observations"]; verdicts = rec["verdicts"]
chains = collections.defaultdict(list)
for v in verdicts: chains[(v["subject"], v["quantity"])].append(v)
live = {}
for k, ch in chains.items():
    sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
    live[k] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
boxes = {}; accpos = {}; headpos = {}; space = {}; cellbox = {}
bypage = collections.defaultdict(list); heads_by_cell = collections.defaultdict(list)
for o in obs:
    q = o["quantity"]; s = o["subject"]
    if q == "glyph_box":
        dt = o.get("detail") or {}; b = dt.get("bbox_page_px")
        sp = s.split("/")
        g = dict(key=s, cls=o["value"][0], cv=o["value"][1:5], reader=o["reader"], conf=o.get("score"), pb=b, cat=dt.get("category"),
                 page=int(sp[1]), system=int(sp[2]), staff=int(sp[3]), cell=int(sp[4]))
        boxes[s] = g
        if b: bypage[g["page"]].append(g)
        if g["cat"] == "notehead": heads_by_cell[tuple(sp[1:5])].append(g)
    elif q == "accidental_staff_position": accpos[s] = o
    elif q == "notehead_staff_position":
        if isinstance(o["value"], (int, float)): headpos[s] = float(o["value"])
    elif q == "cell_staff_space":
        try: space[s] = float(o["value"])
        except Exception: pass
    elif q == "cell_box": cellbox[s] = o["value"]
pages = set(int(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 else None
out = []; tot = collections.Counter()
for k, g in boxes.items():
    if g["cat"] != "accidental" or g["cls"].lower().startswith("key") or g["reader"] != "detector": continue
    if pages and g["page"] not in pages: continue
    own = live.get((k, "accidental_owner")); tot[own["reason"] if own and own["outcome"] != "decided" else ("decided" if own else "none")] += 1
    if not own or own["reason"] != "no_candidate": continue
    row = accpos.get(k); dt = (row or {}).get("detail") or {}
    cellk = "cell/" + "/".join(k.split("/")[1:5]); U = space.get(cellk) or 100.0
    ax0, ax1, ay0, ay1 = dt.get("x0"), dt.get("x1"), dt.get("y0"), dt.get("y1")
    apos = float(row["value"]) if row else None; cpos = dt.get("box_centre_position")
    ent = dict(key=k, cls=g["cls"], conf=round(g["conf"] or 0, 3), page=g["page"], system=g["system"], staff=g["staff"], cell=g["cell"], pb=g["pb"],
               w_sp=round((ax1 - ax0) / U, 2) if row else None, h_sp=round((ay1 - ay0) / U, 2) if row else None, apos=apos, cpos=cpos,
               absorbed=bool(dt.get("one_ink_absorbed")), shape=(dt.get("shape") or {}).get("shape"), alteration=dt.get("alteration"),
               own_reason_detail={kk: own["detail"].get(kk) for kk in ("why", "heads_in_cell", "heads_excluded") if kk in own.get("detail", {})})
    cands = []
    ck = tuple(k.split("/")[1:5])
    for h in heads_by_cell.get(ck, []):
        hx, hy, hw, hh = h["cv"]
        npv = live.get((h["key"], "notehead_is_not_a_notehead")); gov = live.get((h["key"], "glyph_owner"))
        status = "live"
        if npv and npv["outcome"] == "decided" and npv["value"] is True: status = "refused:" + str(npv.get("reason"))
        elif npv and npv["outcome"] != "decided": status = "live"
        elif gov and gov["outcome"] == "decided" and isinstance(gov["value"], str) and gov["value"] != "staff/" + "/".join(k.split("/")[1:4]): status = "refused:owned_by_another_staff"
        hp = headpos.get(h["key"])
        if row is None: continue
        reach = hx + hw >= ax1
        dx = max(0.0, hx - ax1) / U
        cands.append(dict(head=h["key"], pb=h["pb"], status=status, reader=h["reader"], hcls=h["cls"], reach=reach, dx=round(dx, 2), hpos=hp,
                          dy=round(abs(hp - apos), 2) if hp is not None else None, dy_c=round(abs(hp - cpos), 2) if (hp is not None and cpos is not None) else None,
                          overlap_x=(min(hx + hw, ax1) - max(hx, ax0)) / U))
    ent["heads"] = cands
    # other-class boxes overlapping the acc box in PAGE px (any cell): fraction of the acc box covered
    ov = []
    if g["pb"]:
        a = g["pb"]; area = max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))
        for o2 in bypage[g["page"]]:
            if o2["key"] == k or o2["cls"] in ("staff", "ledgerLine") or not o2["pb"]: continue
            b = o2["pb"]; ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            if ix * iy / area > 0.15 or (ix * iy / max(1e-6, (b[2] - b[0]) * (b[3] - b[1]))) > 0.5:
                ov.append(dict(cls=o2["cls"], cat=o2["cat"], reader=o2["reader"], frac_of_acc=round(ix * iy / area, 2),
                               frac_of_other=round(ix * iy / max(1e-6, (b[2] - b[0]) * (b[3] - b[1])), 2), conf=round(o2["conf"] or 0, 2)))
    ent["overlaps"] = ov
    out.append(ent)
json.dump(dict(record=rec_path, tree=d.get("tree_sha"), accidental_owner_totals=dict(tot), boxes=out), open(out_path, "w"))
print(len(out), "no_candidate boxes;", dict(tot))
