"""ROADMAP 2.290 build, step 1 -- the head identities compared on the SAME gather pair (same tree, cells, detector cache; READ-ONLY, no stage run).

    python3 benchmarks/page-heads-ledger-2026-11/partitions_compare.py OFF.record.json ON.record.json [--out DIR]

For the notehead boxes of every page of the pair: the partition by `Q.MARK_GROUP` OFF (box IoU > 0.3 in one system, `gather.cluster_marks`), by
`Q.PAGE_MARK` OFF (2.240: two cells' boxes sharing half the smaller box's ink), by M6a's fold (IoU >= 0.5, same staff; recomputed here from the boxes,
`page_heads.fold`), and by the ONE identity ON (`Q.MARK_GROUP` rows with `identity: page_head`, which carry each box's head ink, its centre and the
boxes it was kept apart from, with the reason). Prints the counts, the box pairs each joins, and every pair the ONE identity disagrees with an old one
on, classed by the rule that decides it:

  DECIDED BY RULE
    two_ovals   the two boxes' head-ink centres are at least one step (0.5 sp) apart along the staff or a head's width (1.3 sp) across: two printed
                heads (page-facts: stacked heads of a chord stay separate; a second's heads stand either side of the stem) -> two heads
    same_ink    joined ON (same pixels, one oval) where an old identity kept them apart: a twin box on the same ink -> one head
    no_ink      one of the boxes stands on no head ink: it makes no head (joined only by the old twin rule, `no_head_ink_twin`)
  UNDECIDED (to Sean's tiles)
    near_oval   centres apart by less than a step / a head's width but beyond the oval (0.4 / 0.65 sp)
    little_ink  the boxes overlap but share little head ink (share_below / no_shared_ink) while an old identity joined them
"""
import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))


def rows(path):
    d = json.loads(pathlib.Path(path).read_text())
    rec = d.get("record", d)
    return rec["observations"]


def heads_of(obs):
    boxes, mg, pm = {}, {}, {}
    for o in obs:
        q, s = o.get("quantity"), o.get("subject", "")
        if not s.startswith("glyph/"):
            continue
        d = o.get("detail") or {}
        if q == "glyph_box" and d.get("category") == "notehead":
            boxes[s] = (tuple(d.get("bbox_page_px") or ()), float(o.get("score") or 0.0))
        elif q == "mark_group":
            mg[s] = (o["value"], d)
        elif q == "page_mark" and d.get("family") == "head":
            pm[s] = (int(s.split("/")[1]), o["value"])
    return boxes, mg, pm


def pairs_of(part, keys):
    by = collections.defaultdict(list)
    for k in keys:
        if k in part:
            by[part[k]].append(k)
    out = set()
    for g in by.values():
        g = sorted(g)
        for a in range(len(g)):
            for b in range(a + 1, len(g)):
                out.add((g[a], g[b]))
    return out


def fold_partition(boxes):
    from tools.omr.staged import page_heads as PH
    keys = sorted(boxes)
    groups = PH.fold([boxes[k][0] for k in keys], ["/".join(k.split("/")[1:4]) for k in keys])
    return {keys[i]: n for n, g in enumerate(groups) for i in g}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("off")
    ap.add_argument("on")
    ap.add_argument("--out")
    ap.add_argument("--sp", type=float, default=None, help="staff space px (default: from the boxes' cells, else 15.75 Litolff / 22 Brahms)")
    a = ap.parse_args()
    b_off, mg_off, pm_off = heads_of(rows(a.off))
    b_on, mg_on, _pm_on = heads_of(rows(a.on))
    keys = sorted(set(b_off) & set(b_on))
    lost = sorted(set(b_off) ^ set(b_on))
    one = {k: mg_on[k][0] for k in keys if k in mg_on}
    det = {k: mg_on[k][1] for k in keys if k in mg_on}
    parts = {"MARK_GROUP (IoU 0.3)": {k: mg_off[k][0] for k in keys if k in mg_off},
             "PAGE_MARK (shared ink 0.5)": {k: pm_off[k] for k in keys if k in pm_off},
             "M6a fold (IoU 0.5, staff)": fold_partition({k: b_off[k] for k in keys}),
             "ONE (ink + oval)": one}
    pairs = {n: pairs_of(p, keys) for n, p in parts.items()}
    sp = a.sp or (15.75 if "litolff" in a.off else 22.0)
    lines = ["boxes %d (box sets differ between arms: %d)" % (len(keys), len(lost))]
    lines.append("%-28s %8s %8s" % ("identity", "heads", "pairs"))
    for n, p in parts.items():
        lines.append("%-28s %8d %8d" % (n, len(set(p.values())), len(pairs[n])))
    allp = set().union(*pairs.values())
    combo = collections.Counter()
    for pr in allp:
        combo[tuple(int(pr in pairs[n]) for n in parts)] += 1
    lines.append("pairs by which identities join them (MG, PM, M6a, ONE): " + ", ".join("%s %d" % ("".join(map(str, k)), v) for k, v in sorted(combo.items(), key=lambda kv: -kv[1])))
    # every disagreement of ONE with MARK_GROUP or PAGE_MARK, classed
    cls = collections.Counter()
    listing = []
    for x, y in sorted(allp):
        in_one = (x, y) in pairs["ONE (ink + oval)"]
        old = [n for n in ("MARK_GROUP (IoU 0.3)", "PAGE_MARK (shared ink 0.5)") if (x, y) in pairs[n]]
        same_cell = x.split("/")[1:5] == y.split("/")[1:5]
        # PAGE_MARK never joins two boxes of ONE cell (by design): there it has no opinion, and only MARK_GROUP is compared
        opinions = [("MARK_GROUP (IoU 0.3)" in old)] + ([] if same_cell else [("PAGE_MARK (shared ink 0.5)" in old)])
        if all(o == in_one for o in opinions):
            continue
        dx_, dy_ = det.get(x) or {}, det.get(y) or {}
        cxy, cyy = dx_.get("ink_centre"), dy_.get("ink_centre")
        dx = abs(cxy[0] - cyy[0]) / sp if (cxy and cyy) else None
        dy = abs(cxy[1] - cyy[1]) / sp if (cxy and cyy) else None
        reason = None
        for k2, why, sh in (dx_.get("apart") or ()):
            if k2 == y:
                reason = (why, sh)
        if not in_one:
            why = reason[0] if reason else "not_overlapping"
            if why == "no_head_ink" or not dx_.get("head_ink_px") or not dy_.get("head_ink_px"):
                c = "no_ink"
            elif why == "two_ovals":
                c = "two_ovals" if (dy is not None and (dy >= 0.5 or dx >= 1.3)) else "near_oval"
            elif why == "tall_read":
                c = "tall_read"
            else:
                c = "little_ink"
        else:
            c = "same_ink" if (dx_.get("head_ink_px") and dy_.get("head_ink_px")) else "no_ink"
        side = "ONE joins, old apart" if in_one else "old joins, ONE apart"
        cls[(side, c, ",".join(o.split(" ")[0] for o in old) or "-")] += 1
        listing.append(dict(a=x, b=y, side=side, cls=c, old=old, dx_sp=None if dx is None else round(dx, 2), dy_sp=None if dy is None else round(dy, 2),
                            reason=reason, box_a=b_off[x][0], box_b=b_off[y][0]))
    lines.append("disagreements with an old identity (side, class, which old identity joined):")
    for k, v in sorted(cls.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append("  %-24s %-12s %-22s %d" % (k[0], k[1], k[2], v))
    print("\n".join(lines))
    if a.out:
        od = pathlib.Path(a.out)
        od.mkdir(parents=True, exist_ok=True)
        (od / "partitions.txt").write_text("\n".join(lines) + "\n")
        (od / "disagreements.json").write_text(json.dumps(listing, indent=0, default=str))


if __name__ == "__main__":
    main()
