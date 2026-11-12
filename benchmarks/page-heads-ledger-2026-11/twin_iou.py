"""ROADMAP 2.290 r1 -- READ-ONLY: for every head box dropped as a TWIN (owned_by_another_staff, mark_group_duplicate, notehead_is_a_duplicate_box,
stacked_head_duplicate) the IoU with the nearest WRITTEN head box (any staff) on the same page. A true twin sits at IoU > 0.5; a low IoU is a second printed
head that a twin rule may have thrown away; no written box at IoU > 0.1 = 'none' = possibly a lost head. Writes FATES.twin.json beside each input."""
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
    out = {}
    for p in paths:
        d = json.load(open(p))
        rows = d["rows"]
        by_page = collections.defaultdict(list)
        for r in rows:
            by_page[r["sub"].split("/")[1]].append(r)
        for pg, rs in by_page.items():
            w = [r for r in rs if r["fate"].startswith("written")]
            for r in rs:
                if r["fate"] not in TWIN:
                    continue
                best, bi = 0.0, None
                for q in w:
                    v = iou(r["box"], q["box"])
                    if v > best:
                        best, bi = v, q
                b = "none<0.1" if best < 0.1 else ("0.1-0.3" if best < 0.3 else ("0.3-0.5" if best < 0.5 else ">=0.5"))
                out.setdefault((d["plate"], r["fate"]), collections.Counter())[b] += 1
                r["_best_iou"] = round(best, 3)
                r["_best"] = bi["sub"] if bi else None
        json.dump(rows, open(p.replace(".json", ".twin.json"), "w"))
    for k, v in sorted(out.items()):
        print(k, dict(v))


if __name__ == "__main__":
    main(sys.argv[1:])
