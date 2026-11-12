"""ROADMAP 2.290 r1 -- READ-ONLY: three head identities already on the record. For the head boxes of the given pages: how many marks does `Q.MARK_GROUP` (IoU 0.3, page+system),
`Q.PAGE_MARK` (2.240: shared ink, ON) say there are, and how do the two partitions agree?

    python3 benchmarks/page-heads-ledger-2026-11/identity_partitions.py SLICE_DIR PAGES      (reads the slice's observations.jsonl; no stage is run)
"""
import collections
import json
import sys


def main(slice_dir, pages):
    pages = set(int(x) for x in pages.split(","))
    box_cls = {}
    mg, pm = {}, {}
    pm_members = {}
    with open(slice_dir + "/observations.jsonl") as fh:
        for line in fh:
            if '"page_mark"' not in line and '"mark_group"' not in line and '"glyph_box"' not in line:
                continue
            o = json.loads(line)
            s = o["subject"]
            if not s.startswith("glyph/"):
                continue
            if int(s.split("/")[1]) not in pages:
                continue
            q = o["quantity"]
            if q == "glyph_box":
                if (o.get("detail") or {}).get("category") == "notehead":
                    box_cls[s] = 1
            elif q == "mark_group":
                mg[s] = o["value"]
            elif q == "page_mark":
                d = o.get("detail") or {}
                if d.get("family") == "head":
                    pm[s] = (int(s.split("/")[1]), o["value"])
                    pm_members[(int(s.split("/")[1]), o["value"])] = d.get("why")
    heads = [s for s in box_cls]
    n = len(heads)
    n_mg = len(set(mg[s] for s in heads if s in mg))
    n_pm = len(set(pm[s] for s in heads if s in pm))
    print("head boxes", n, "| MARK_GROUP marks", n_mg, "| PAGE_MARK marks", n_pm, "| boxes with no page_mark row", sum(1 for s in heads if s not in pm))
    # partition agreement: boxes joined by one and not the other
    by_mg = collections.defaultdict(set)
    by_pm = collections.defaultdict(set)
    for s in heads:
        if s in mg:
            by_mg[mg[s]].add(s)
        if s in pm:
            by_pm[pm[s]].add(s)
    only_mg = only_pm = both = 0
    seen = set()
    for g in by_mg.values():
        for a in g:
            for b in g:
                if a < b:
                    same_pm = a in pm and b in pm and pm[a] == pm[b]
                    if same_pm:
                        both += 1
                    else:
                        only_mg += 1
    for g in by_pm.values():
        for a in g:
            for b in g:
                if a < b:
                    if not (a in mg and b in mg and mg[a] == mg[b]):
                        only_pm += 1
    print("box pairs joined by both", both, "| only MARK_GROUP (IoU) %d" % only_mg, "| only PAGE_MARK (ink) %d" % only_pm)
    sizes_mg = collections.Counter(len(g) for g in by_mg.values())
    sizes_pm = collections.Counter(len(g) for g in by_pm.values())
    print("group sizes MARK_GROUP", dict(sorted(sizes_mg.items())), "| PAGE_MARK", dict(sorted(sizes_pm.items())))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
