"""GATED strip arm (measure only):  python3 gate.py PLATE WORKDIR OUTDIR

Arm C boxes (run_page.py --arms C) kept ONLY where they continue an existing cell-cut arc box across a barline: the cut box K is ANY saved-record arc
box cut at an interior cell edge that is a printed barline (real or not, the gate cannot know), the strip box M is on K's page and y-band, reaches back
over >= half of K, and extends >= 0.75 sp past K's barline (analyze.far_cover). GUARD: M is dropped if it contains two or more separate saved cell arc
boxes (>= 80% of a box inside M, same y band); boxes that touch across a cell edge (gap <= 1 sp, y overlap) count as ONE arc.
Reports far-half coverage of the REAL cut items, false boxes (kept boxes that far-cover no real cut item) per page, kept boxes spanning > 1 arc.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as AN  # noqa: E402

ARC = AN.ARC


def groups_inside(M, recs, sp):
    ins = [r for r in recs if AN.inter_frac(r[2:], M[2:]) >= 0.8 and AN.y_overlap(r[2:], M[2:]) >= 0.3]
    ins.sort(key=lambda r: r[2])
    g = 0
    cur_end, cur = None, None
    for r in ins:
        if cur_end is not None and r[2] - cur_end <= sp and AN.y_overlap(r[2:], cur) >= 0.5:
            cur_end = max(cur_end, r[4])
            cur = r[2:]
            continue
        g += 1
        cur_end, cur = r[4], r[2:]
    return g


def main():
    plate, work, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    files = sorted(f for f in os.listdir(work) if f.startswith(plate + ".p") and f.endswith(".json"))
    pdata = {int(f.split(".p")[1].split(".")[0]): json.load(open(os.path.join(work, f))) for f in files}
    pages = set(pdata)
    _, arcs_rec, _ = AN.load_slice(plate, pages)
    items, uncut, rows = AN.build_items(plate)
    items = [i for i in items if i["page"] in pages]
    # all cut boxes (real or not) for the gate
    d = json.load(open(AN.INP + plate + ".cut.json"))
    eb = json.load(open(AN.INP + "eb." + plate + ".json"))["edges"]
    allcut = []
    for r in d["rows"]:
        if r["page"] not in pages:
            continue
        ck = "cell/" + "/".join(r["key"].split("/")[1:5])
        if r["cut_r"] and eb.get(ck + "|r"):
            allcut.append(dict(page=r["page"], side="r", sp=r["sp"], K=r["box"], P=None, bar=r["box"][2] + r["r_edge"] * r["sp"]))
        if r["cut_l"] and eb.get(ck + "|l"):
            allcut.append(dict(page=r["page"], side="l", sp=r["sp"], K=r["box"], P=None, bar=r["box"][0] - r["l_edge"] * r["sp"]))
    res = dict(plate=plate, pages=sorted(pages), n_items=len(items))
    kept_all, kept_after = [], []
    per_page = {}
    sp_of = {p: 16.0 for p in pages}
    for p in sorted(pages):
        recs = list(arcs_rec[p].values())
        Cb = AN.dedupe([b for it in pdata[p]["arms"]["C"]["items"] for b in it["boxes"]])
        Cb = [b for b in Cb if b[0] in ARC]
        cuts = [c for c in allcut if c["page"] == p]
        n_c = len(Cb)
        kept = [M for M in Cb if any(AN.far_cover(c, M)[0] for c in cuts)]
        multi_before = [M for M in kept if groups_inside(M, recs, sp_of[p]) >= 2]
        after = [M for M in kept if groups_inside(M, recs, sp_of[p]) < 2]
        per_page[p] = dict(c_arc_boxes=n_c, kept=len(kept), guard_removed=len(multi_before), kept_after_guard=len(after))
        for M in kept:
            kept_all.append((p, M))
        for M in after:
            kept_after.append((p, M))
    res["per_page"] = per_page
    n = len(items)

    def covered(sel):
        by_page = collections.defaultdict(list)
        for p, M in sel:
            by_page[p].append(M)
        far = whole = 0
        used = collections.defaultdict(set)
        for it in items:
            f = w = False
            for mi, M in enumerate(by_page[it["page"]]):
                a, b = AN.far_cover(it, M)
                if a:
                    used[it["page"]].add(mi)
                f |= a
                w |= b
            far += f
            whole += w
        nfalse = sum(len(by_page[p]) - len(used[p]) for p in pages)
        return far, whole, nfalse

    for name, sel in (("gate", kept_all), ("gate+guard", kept_after)):
        far, whole, nfalse = covered(sel)
        res[name] = dict(kept=len(sel), far=far, far_pct=round(100 * far / n, 1), whole=whole, whole_pct=round(100 * whole / n, 1),
                         false_total=nfalse, false_per_page=round(nfalse / len(pages), 1))
    res["spans_more_than_one_arc"] = dict(gate_only=sum(v["guard_removed"] for v in per_page.values()),
                                          after_guard=sum(1 for p, M in kept_after if groups_inside(M, list(arcs_rec[p].values()), 16.0) >= 2))
    # uncut: the gate adds nothing to A, so A + gated C loses no A arc by construction
    res["uncut_loss_vs_A_union"] = 0
    json.dump(dict(res=res, kept=[dict(page=p, box=M[2:], cls=M[0], conf=M[1]) for p, M in kept_after]), open(os.path.join(outdir, "gate.%s.json" % plate), "w"))
    print(json.dumps(res))


if __name__ == "__main__":
    main()
