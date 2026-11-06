"""BARLINE-CROP TRIAL: the numbers (measure only).

    python3 analyze.py PLATE WORKDIR OUT_PREFIX

Reads WORKDIR/PLATE.pN.json (run_page.py), the 20261104-night slice of the saved record (cell_box, arc_box, glyph_box rows) and the cut test's
inputs (INPUTS_DIR: <plate>.cut.json, <plate>.ledger.json, eb.<plate>.json, taken from branch arc-barline-cut-test ef226deba), and writes
OUT_PREFIX.<plate>.json + prints the summary.

Definitions fixed in VERDICT.md before the numbers existed. A "cut item" is one barline-crossing REAL arc (ledger fate != not_an_arc) whose box is cut at a
PRINTED barline (cut test's own edge test); a right-cut box + a left-cut box across one barline is one item (a "pair": A already boxed both halves).
Arm X "boxes the far half" of item K if some tie/slur box M of X on that page overlaps K in y (>= 0.5 of the shorter), reaches back over >= half of K, and
extends >= 0.75 sp past the barline on the far side. "Whole": M also covers K's far end (and, for a pair, the partner's far end), within 0.5 sp.
"""
import collections
import json
import os
import sys

SLICE = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night/%s/observations.jsonl"
INP = os.environ.get("TRIAL_INPUTS", "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-session-placeholder-setup-6802ad/c91823fb-6cde-4194-b762-519aca0451f9/scratchpad/in/")
ARC = ("tie", "slur")


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix
    return ix / u if u > 0 else 0.0


def inter_frac(a, b):
    """share of a's area inside b"""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    ar = (a[2] - a[0]) * (a[3] - a[1])
    return ix / ar if ar > 0 else 0.0


def y_overlap(a, b):
    o = min(a[3], b[3]) - max(a[1], b[1])
    return o / max(1e-9, min(a[3] - a[1], b[3] - b[1]))


def dedupe(boxes, thr=0.7):
    """boxes: [cls, conf, x0,y0,x1,y1]; keep the highest-conf of overlapping same-class boxes"""
    keep = []
    for b in sorted(boxes, key=lambda z: -z[1]):
        if not any(k[0] == b[0] and iou(k[2:], b[2:]) >= thr for k in keep):
            keep.append(b)
    return keep


def load_slice(plate, pages):
    cells, arcs, glyphs = {}, collections.defaultdict(dict), collections.defaultdict(list)
    for l in open(SLICE % plate):
        if '"quantity": "cell_box"' in l:
            o = json.loads(l)
            p = int(o["subject"].split("/")[1])
            if p in pages:
                cells[o["subject"]] = o["value"]
        elif '"quantity": "arc_box"' in l:
            o = json.loads(l)
            p = int(o["subject"].split("/")[1])
            if p in pages:
                arcs[p][o["subject"]] = [o["value"], o["score"]] + list(o["detail"]["bbox_page_px"])
        elif '"quantity": "glyph_box"' in l:
            o = json.loads(l)
            p = int(o["subject"].split("/")[1])
            b = (o.get("detail") or {}).get("bbox_page_px")
            if p in pages and b:
                v = o["value"]
                glyphs[p].append([str(v[0] if isinstance(v, list) else v), o["score"]] + list(b))
    return cells, arcs, glyphs


def build_items(plate):
    d = json.load(open(INP + plate + ".cut.json"))
    led = json.load(open(INP + plate + ".ledger.json"))["rows"]
    eb = json.load(open(INP + "eb." + plate + ".json"))["edges"]
    fate = {p: r["fate"] for r in led for p in r["pieces"]}
    rows = {r["key"]: r for r in d["rows"] if fate.get(r["key"]) not in (None, "not_an_arc")}

    def is_bar(r, side):
        return eb.get("cell/" + "/".join(r["key"].split("/")[1:5]) + "|" + side)

    items, in_pair = [], set()
    for r in rows.values():
        if r["cut_r"] and is_bar(r, "r"):
            p = rows.get(r["partner_r"]) if r["partner_r"] else None
            if p is not None and p["cut_l"] and is_bar(p, "l"):
                in_pair.add(p["key"])
                items.append(dict(page=r["page"], side="r", sp=r["sp"], K=r["box"], P=p["box"], bar=r["box"][2] + r["r_edge"] * r["sp"], key=r["key"], cls=r["cls"]))
            else:
                items.append(dict(page=r["page"], side="r", sp=r["sp"], K=r["box"], P=None, bar=r["box"][2] + r["r_edge"] * r["sp"], key=r["key"], cls=r["cls"]))
    for r in rows.values():
        if r["cut_l"] and is_bar(r, "l") and r["key"] not in in_pair:
            items.append(dict(page=r["page"], side="l", sp=r["sp"], K=r["box"], P=None, bar=r["box"][0] - r["l_edge"] * r["sp"], key=r["key"], cls=r["cls"]))
    # real arcs NOT cut at a printed barline (the uncut set), from the same rows
    cutkeys = {i["key"] for i in items} | in_pair
    uncut = [r for r in rows.values() if r["key"] not in cutkeys and not (r["cut_l"] and is_bar(r, "l")) and not (r["cut_r"] and is_bar(r, "r"))]
    return items, uncut, rows


def far_cover(it, M):
    """Does arc box M box the far half of cut item it? returns (far, whole)"""
    K, P, bar, sp = it["K"], it["P"], it["bar"], it["sp"]
    if y_overlap(K, M[2:]) < 0.5:
        return False, False
    kw = K[2] - K[0]
    if it["side"] == "r":
        far = M[4] >= bar + 0.75 * sp and M[2] < bar and M[2] <= K[2] - 0.5 * kw
        whole = far and M[2] <= K[0] + 0.5 * sp and (P is None or M[4] >= P[2] - 0.5 * sp)
    else:
        far = M[2] <= bar - 0.75 * sp and M[4] > bar and M[4] >= K[0] + 0.5 * kw
        whole = far and M[4] >= K[2] - 0.5 * sp
    return bool(far), bool(whole)


def main():
    plate, work, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    files = sorted(f for f in os.listdir(work) if f.startswith(plate + ".p") and f.endswith(".json"))
    pdata = {int(f.split(".p")[1].split(".")[0]): json.load(open(os.path.join(work, f))) for f in files}
    pages = set(pdata)
    cells_rec, arcs_rec, glyphs_rec = load_slice(plate, pages)
    items, uncut, rows = build_items(plate)
    items = [i for i in items if i["page"] in pages]
    uncut = [r for r in uncut if r["page"] in pages]
    res = dict(plate=plate, pages=sorted(pages), n_items=len(items), n_pairs=sum(1 for i in items if i["P"]), n_uncut=len(uncut))
    armnames = [a for a in ("B", "B2", "C") if all(a in pd["arms"] for pd in pdata.values())]

    # ---- control: arm A re-detect vs record
    ctrl = dict(cells=0, cells_matched=0, rec_arcs=0, rec_arcs_found=0, a_arcs=0, a_arcs_in_rec=0, bad_rec_arcs=0, bad_found=0, bad_cells=0)
    rec_cell_by_bbox = {tuple(round(v) for v in b): k for k, b in cells_rec.items()}
    rec_arc_by_cell = collections.defaultdict(list)
    for p, ad in arcs_rec.items():
        for k, b in ad.items():
            s = k.split("/")
            rec_arc_by_cell["cell/%s/%s/%s/%s" % tuple(s[1:5])].append(b)
    for p, pd in pdata.items():
        for arm, bad in (("A", False), ("A_badimgsz", True)):
            if arm not in pd["arms"]:
                continue
            for it in pd["arms"][arm]["items"]:
                ck = rec_cell_by_bbox.get(tuple(round(v) for v in it["bbox"]))
                mine = [b for b in it["boxes"] if b[0] in ARC]
                if ck is None:
                    if not bad:
                        ctrl["cells"] += 1
                    continue
                rec = rec_arc_by_cell.get(ck, [])
                found = sum(1 for r in rec if any(r[0] == m[0] and iou(r[2:], m[2:]) >= 0.9 for m in mine))
                inrec = sum(1 for m in mine if any(r[0] == m[0] and iou(r[2:], m[2:]) >= 0.9 for r in rec))
                if bad:
                    ctrl["bad_cells"] += 1
                    ctrl["bad_rec_arcs"] += len(rec)
                    ctrl["bad_found"] += found
                else:
                    ctrl["cells"] += 1
                    ctrl["cells_matched"] += 1
                    ctrl["rec_arcs"] += len(rec)
                    ctrl["rec_arcs_found"] += found
                    ctrl["a_arcs"] += len(mine)
                    ctrl["a_arcs_in_rec"] += inrec
    res["control"] = ctrl

    # ---- runtime
    res["runtime_s_per_page"] = {a: round(sum(pd["arms"][a]["t_detect"] for pd in pdata.values() if a in pd["arms"]) / len(pdata), 1)
                                 for a in ["A"] + armnames}
    res["calls_per_page"] = {a: round(sum(pd["arms"][a]["n_calls"] for pd in pdata.values() if a in pd["arms"]) / len(pdata), 1) for a in ["A"] + armnames}
    res["max_boxes_one_call"] = {a: max(pd["arms"][a]["max_calls_boxes"] for pd in pdata.values() if a in pd["arms"]) for a in ["A"] + armnames}
    res["prepare_s_per_page"] = round(sum(pd["t_prepare"] for pd in pdata.values()) / len(pdata), 1)

    # ---- per arm
    arm_boxes = {}
    for a in armnames:
        arm_boxes[a] = {p: dedupe([b for it in pd["arms"][a]["items"] for b in it["boxes"]]) for p, pd in pdata.items()}
    arm_boxes["A"] = {p: dedupe([b for it in pd["arms"]["A"]["items"] for b in it["boxes"]], 0.99) for p, pd in pdata.items()}

    cut = {}
    explained = {a: collections.defaultdict(set) for a in armnames}
    for a in armnames:
        c = dict(n=len(items), far=0, whole=0, together=0, miss=0, pair_far=0, pair_whole=0, lone_far=0, lone_whole=0, lone_n=0, pair_n=0)
        for idx, it in enumerate(items):
            pair = it["P"] is not None
            c["pair_n" if pair else "lone_n"] += 1
            far = whole = False
            best = None
            for mi, M in enumerate(arm_boxes[a][it["page"]]):
                if M[0] not in ARC:
                    continue
                f, w = far_cover(it, M)
                if f:
                    explained[a][it["page"]].add(mi)
                    if best is None or (w, M[4] - M[2]) > (best[1], best[0][4] - best[0][2]):
                        best = (M, w)
                far |= f
                whole |= w
            it.setdefault("cover", {})[a] = dict(box=best[0][2:], cls=best[0][0], conf=best[0][1], whole=best[1]) if best else None
            c["far"] += far
            c["whole"] += whole
            c["pair_far" if pair else "lone_far"] += far
            c["pair_whole" if pair else "lone_whole"] += whole
            ok = pair or far
            c["together"] += ok
            c["miss"] += not ok
        cut[a] = c
    res["cut_items"] = cut
    res["A_alone_far"] = sum(1 for i in items if i["P"])

    # ---- uncut arcs: found by X?
    unc = {}
    for a in armnames:
        found = inwin = foundwin = lenient = 0
        for r in uncut:
            M = [b for b in arm_boxes[a][r["page"]] if b[0] in ARC]
            hit = any(iou(r["box"], m[2:]) >= 0.5 for m in M)
            lenient += any(iou(r["box"], m[2:]) >= 0.5 or (inter_frac(r["box"], m[2:]) >= 0.7 and y_overlap(r["box"], m[2:]) >= 0.5) for m in M)
            found += hit
            if a.startswith("B"):
                wins = [it["bbox"] for it in pdata[r["page"]]["arms"][a]["items"]]
                inside = any(w[0] <= r["box"][0] and r["box"][2] <= w[2] and w[1] <= r["box"][1] and r["box"][3] <= w[3] for w in wins)
                inwin += inside
                foundwin += hit and inside
        unc[a] = dict(n=len(uncut), found_iou50=found, found_lenient=lenient, in_a_window=inwin, found_in_window=foundwin)
    res["uncut"] = unc

    # ---- new arc boxes (not on any A arc box, not a far-half box of a cut item)
    newb = {}
    newlist = {}
    for a in armnames:
        per_page = {}
        lst = []
        for p in sorted(pages):
            A_arcs = [b for b in arms_rec_list(arcs_rec, p)]
            n = 0
            for mi, M in enumerate(arm_boxes[a][p]):
                if M[0] not in ARC:
                    continue
                if any(iou(M[2:], r[2:]) >= 0.3 or inter_frac(M[2:], r[2:]) >= 0.5 or inter_frac(r[2:], M[2:]) >= 0.5 for r in A_arcs):
                    continue
                if mi in explained[a][p]:
                    continue
                # page map: the A (record) glyph box of another class that sits on it
                over = sorted(((inter_frac(M[2:], g[2:]), g[0]) for g in glyphs_rec[p] if g[0] not in ARC), reverse=True)
                top = over[0] if over and over[0][0] >= 0.5 else None
                lst.append(dict(page=p, cls=M[0], conf=M[1], box=M[2:], on_A_glyph=top[1] if top else None))
                n += 1
            per_page[p] = n
        newb[a] = dict(per_page=per_page, mean_per_page=round(sum(per_page.values()) / len(per_page), 2))
        newlist[a] = lst
        newb[a]["on_A_glyph_class"] = dict(collections.Counter(x["on_A_glyph"] or "no A box" for x in lst).most_common(8))
    res["new_arc_boxes"] = newb

    # ---- in passing: every class, X boxes with no same-class A box at IoU >= 0.5 (and A boxes with no X box), C only on the whole page
    passing = {}
    for a in armnames:
        d_new, d_lost = collections.Counter(), collections.Counter()
        for p, pd in pdata.items():
            Ab = arm_boxes["A"][p]
            Xb = arm_boxes[a][p]
            wins = [it["bbox"] for it in pd["arms"][a]["items"]] if a.startswith("B") else None

            def in_win(b):
                cx, cy = (b[2] + b[4]) / 2, (b[3] + b[5]) / 2
                return wins is None or any(w[0] <= cx <= w[2] and w[1] <= cy <= w[3] for w in wins)
            for x in Xb:
                if not any(x[0] == y[0] and iou(x[2:], y[2:]) >= 0.5 for y in Ab):
                    d_new[x[0]] += 1
            for y in Ab:
                if in_win(y) and not any(x[0] == y[0] and iou(x[2:], y[2:]) >= 0.5 for x in Xb):
                    d_lost[y[0]] += 1
        passing[a] = dict(not_in_A=sum(d_new.values()), top_not_in_A=d_new.most_common(8), A_not_in_X=sum(d_lost.values()), top_A_not_in_X=d_lost.most_common(8))
    res["in_passing"] = passing
    json.dump(dict(res=res, items=items, newlist=newlist), open(outp + "." + plate + ".json", "w"))
    print(json.dumps(res, indent=1))


def arms_rec_list(arcs_rec, p):
    return list(arcs_rec[p].values())


if __name__ == "__main__":
    main()
