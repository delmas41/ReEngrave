"""ROADMAP 2.290 r1 -- READ-ONLY: a head box dropped as `owned_by_another_staff` / `mark_group_duplicate` / duplicate / stacked-duplicate whose nearest WRITTEN head box
is at IoU < 0.1 ('orphan'): is there ANY other box on the same ink (IoU >= 0.3), and what happened to it? No box at all = the page owner moved the head to a staff that
holds no box of it (the export has nothing to relocate onto)."""
import collections
import json
import sys

TWIN = ("owned_by_another_staff", "mark_group_duplicate", "not_a_notehead:notehead_is_a_duplicate_box", "not_a_notehead:stacked_head_duplicate")


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def main(paths):
    c = collections.Counter()
    ex = collections.defaultdict(list)
    for p in paths:
        rows = json.load(open(p))
        pages = collections.defaultdict(list)
        for r in rows:
            pages[r["sub"].split("/")[1]].append(r)
        for pg, rs in pages.items():
            for r in rs:
                if r["fate"] not in TWIN or r.get("_best_iou", 1) >= 0.1:
                    continue
                others = [(iou(r["box"], q["box"]), q) for q in rs if q is not r]
                others = [(v, q) for v, q in others if v >= 0.3]
                key = (r["fate"], "no_other_box" if not others else "other_box_fate=" + max(others, key=lambda t: t[0])[1]["fate"])
                c[key] += 1
                if len(ex[key]) < 3:
                    ex[key].append(r["sub"])
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print(v, k, ex[k])


if __name__ == "__main__":
    main(sys.argv[1:])
