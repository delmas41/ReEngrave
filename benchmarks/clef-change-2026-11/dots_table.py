"""2.251 step 3: tabulate `dots_scan.py` output, flag OFF vs ON. python3 work-2.251/dots_table.py PLATE OFF.json ON.json [MIN_RADIUS]
A PLACE is (page, system, staff, cell); its score is the best dots+body score of any pair there (radius >= MIN_RADIUS, the dot blob's
distance-transform radius in staff spaces, default 0 = no radius cut). Real F clefs after the header: a place with a boxed F change claim
plus the unboxed REAL ones (Sean / the encoding). Prints the real places' scores and the non-clef top, each arm."""
import json, sys

REAL = {"litolff": {(2, 1, 3, 3): "bar 38", (4, 1, 3, 13): "bar 111", (5, 0, 3, 2): "bar 115", (12, 0, 10, 7): "Vc 346", (14, 0, 10, 12): "Vc 411"},
        "brahms": {}}
plate, off, on = sys.argv[1:4]
minr = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0


def places(path):
    best = {}
    boxed = set()
    for pr in json.load(open(path)):
        for r in pr["pairs"]:
            k = (r["page"], r["system"], r["staff"], r["cell"])
            if any(n.startswith("F/") and "(hdr)" not in n for n in r["near"]):
                boxed.add(k)
            if (r.get("radius") or 0) < minr:
                continue
            if r["score"] > best.get(k, (0, 0))[0]:
                best[k] = (r["score"], r.get("radius"))
    return best, boxed


def report(name, path):
    best, boxed = places(path)
    real = dict(REAL[plate])
    for k in boxed:
        real.setdefault(k, "boxed")
    print("== %s  places with a pair: %d" % (name, len(best)))
    rs = sorted([(best.get(k, (0, None))[0], v, k, best.get(k, (0, None))[1]) for k, v in real.items()])
    print("  real F (%d), lowest first:" % len(rs), [(s, v, k, r) for s, v, k, r in rs[:10]])
    non = sorted([(s, k, r) for k, (s, r) in best.items() if k not in real], reverse=True)
    print("  non-clef top 8:", non[:8])
    return best, real


A, ra = report("OFF", off)
B, rb = report("ON", on)
