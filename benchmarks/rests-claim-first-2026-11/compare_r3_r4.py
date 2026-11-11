"""ROADMAP 2.288 round 4 -- per page, whole/half rest boxes claimed / refused by reason, r3 vs r4, and the boxes that changed side, read off the two ON records' census rows
(`claimed_area` census, `rest_read_boxes` / `rest_weak_boxes`).

    python3 benchmarks/rests-claim-first-2026-11/compare_r3_r4.py PLATE:R3_RECORD:R4_RECORD:PAGES ...
"""
import collections
import json
import sys


def census(path, pages):
    rec = json.load(open(path))["record"]
    read, weak = collections.defaultdict(list), collections.defaultdict(list)
    for o in rec["observations"]:
        d = o.get("detail") or {}
        if d.get("source") == "page_boxes" and d.get("unit") == "page_ink_census" and o["subject"].startswith("page/"):
            pg = int(o["subject"].split("/")[1])
            if pg in pages:
                read[pg] += [(c, tuple(b), cell, "READ") for c, b, cell in d.get("rest_read_boxes", [])]
                weak[pg] += [(c, tuple(b), cell, why) for c, b, why, cell in d.get("rest_weak_boxes", [])]
    return read, weak


def main():
    for spec in sys.argv[1:]:
        plate, p3, p4, pages = spec.split(":")
        pages = [int(p) for p in pages.split(",")]
        r3 = census(p3, pages)
        r4 = census(p4, pages)
        for pg in pages:
            for name, (read, weak) in (("r3", r3), ("r4", r4)):
                blk = lambda L: [x for x in L if x[0] in ("restWhole", "restHalf")]
                why = collections.Counter(w[3] for w in blk(weak[pg]))
                print("%s p%d %s: whole/half READ %d, refused %d %s" % (plate, pg, name, len(blk(read[pg])), len(blk(weak[pg])), dict(why)))
            v3 = {(x[0], x[2]): x for x in r3[0][pg] + r3[1][pg] if x[0] in ("restWhole", "restHalf")}
            v4 = {(x[0], x[2]): x for x in r4[0][pg] + r4[1][pg] if x[0] in ("restWhole", "restHalf")}
            for k in sorted(set(v3) | set(v4)):
                a, b = v3.get(k), v4.get(k)
                if (a and a[3]) != (b and b[3]):
                    print("   CHANGED %s %s box %s: r3 %s -> r4 %s" % (k[0], k[1], (a or b)[1], a and a[3], b and b[3]))


if __name__ == "__main__":
    main()
