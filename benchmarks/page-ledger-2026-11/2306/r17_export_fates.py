"""2.306 r17: the named EXPORT fate of every notehead whose fate differs between the OFF and ON arms. Exports each arm's gathered record (its own
stored verdicts, as the lane report does) and captures EXPORT's own per-glyph fate map (the `fates` it hands `marks_census`).
Usage: r17_export_fates.py WORK PLATE PAGES(comma)  -> <WORK>/<plate>.fates.pkl, and a count of (OFF fate -> ON fate)."""
import os, sys, pickle, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record
from tools.omr.staged import export as E
from tools.omr.staged import lane_report as L

work, plate, pages = sys.argv[1], sys.argv[2], {int(p) for p in sys.argv[3].split(",")}
got = {}
orig = E.marks_census


def capture(rec, fates):
    got["fates"] = dict(fates)
    return orig(rec, fates)


E.marks_census = capture
F = {}
for arm in ("off", "on"):
    os.environ["OMR_PAGE_STEMS"] = "1" if arm == "on" else "0"
    res = load_record(os.path.join(work, "%s.%s.gathered.record.json" % (plate, arm)))
    if "record" not in res:
        res = {"record": res, "summary": {}}
    with L.traced_export():
        E.to_musicxml(res)
    F[arm] = {k: v for k, v in got["fates"].items() if k.startswith("glyph/") and int(k.split("/")[1]) in pages}
    del res
pickle.dump(F, open(os.path.join(work, "%s.fates.pkl" % plate), "wb"))
c = collections.Counter()
ex = collections.defaultdict(list)
for k in set(F["off"]) | set(F["on"]):
    a, b = F["off"].get(k, "-"), F["on"].get(k, "-")
    if a != b:
        c[(a, b)] += 1
        ex[(a, b)].append(k)
for (a, b), n in c.most_common(30):
    print("%4d  %-40s -> %-40s %s" % (n, a, b, " ".join(ex[(a, b)][:4])))
