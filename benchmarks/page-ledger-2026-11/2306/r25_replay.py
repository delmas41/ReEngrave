"""2.306 r25: offline replay of page_stems.read on dumped inputs, a set of module switches off vs on; every head whose reading changes.
Usage: replay.py DUMPDIR SWITCH[,SWITCH..] [--quiet]"""
import collections, glob, os, pickle, sys
sys.path.insert(0, os.getcwd())
from tools.omr.staged import page_stems as PS
DD = sys.argv[1]
FL = sys.argv[2].split(",")


def run(D, on):
    for f in FL:
        setattr(PS, f, on)
    return PS.read(D["heads"], D["verticals"], D["held"], crossers=D["crossers"], strokes=D["strokes"])["heads"]


def sig(r):
    return (r["state"], r.get("how"), r.get("stroke"), r.get("direction"), r.get("why"), tuple(sorted((r.get("voices") or {}).items(), key=str)) if r.get("voices") else None)


cnt = collections.Counter()
for plate in ("litolff", "brahms"):
    for f in sorted(glob.glob(f"{DD}/{plate}/p*.pkl"), key=lambda s: int(s.split("/p")[-1][:-4])):
        D = pickle.load(open(f, "rb"))
        a, b = run(D, False), run(D, True)
        for h in D["heads"]:
            ra, rb = a[h["id"]], b[h["id"]]
            if sig(ra) != sig(rb):
                cnt[(plate, ra.get("how"), ra.get("why"), rb.get("how"))] += 1
                if "--quiet" not in sys.argv:
                    print(plate, h["members"][:2], "|", ra["state"], ra.get("how"), ra.get("why"), ra.get("stroke"), ra.get("direction"), "->",
                          rb["state"], rb.get("how"), rb.get("why"), rb.get("stroke"), rb.get("direction"))
for k, n in sorted(cnt.items(), key=lambda t: -t[1]):
    print("%4d %s" % (n, k))
