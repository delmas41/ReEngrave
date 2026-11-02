"""ROADMAP 2.254: how often does Sean's repeated-hairpin hint hold on our pages? (DECISIONS 2026-11-02: a HINT, not a rule.)

For every hairpin the reach reader keeps (probe JSON, w >= 1.6 sp), is there a hairpin on ANOTHER staff of the SAME system whose x-span
overlaps it by at least MIN_IOU? Reports hairpins with a mate / without, per page, and the kind agreement of mates.

    python3 benchmarks/hairpin-reach-2026-11/hint.py PROBE_DIR brahms 19 25 ...
"""
import json
import pathlib
import sys

MIN_IOU = 0.5


def iou(a, b):
    i = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    u = max(a[2], b[2]) - min(a[0], b[0])
    return i / u if u else 0.0


def main(d, plate, pages):
    tot = [0, 0]
    for p in pages:
        rows = [r for r in json.load(open(pathlib.Path(d) / ("%s_p%02d_line.json" % (plate, int(p)))))["rows"]
                if r["why"] == "KEPT" and r["w_sp"] >= 1.6]
        mate = 0
        for r in rows:
            if any(o is not r and o["system"] == r["system"] and o["staff"] != r["staff"] and iou(o["bbox"], r["bbox"]) >= MIN_IOU
                   for o in rows):
                mate += 1
        tot[0] += mate
        tot[1] += len(rows)
        print("%s p%s: %d of %d kept hairpins have a same-span mate on another staff of their system" % (plate, p, mate, len(rows)))
    print("TOTAL %d of %d" % tuple(tot))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
