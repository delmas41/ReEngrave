"""2.300 probe: heads with no stem row (flag ON) whose DURATION is decided, with the nearest other head and why the second-join did not fire.
    OMR_ONE_CHORD_ONE_EVENT=1 PYTHONPATH=. python3 benchmarks/one-chord-one-event-2026-11/probe_nostem.py PLATE PAGES
"""
import os
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
sys.path.insert(0, ".")
from tools.omr.staged import conservation as C  # noqa: E402
from tools.omr.staged import one_chord as OC  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

plate, pages = sys.argv[1], [int(x) for x in sys.argv[2].split(",")]
log, _ = RR.rebuild_gather(C.load_pages(plate, pages, C.DEFAULT_TAG))
RR.run_stages(log)
rec = log.to_json()
boxes = {}
for o in rec["observations"]:
    if o["quantity"] == Q.GLYPH_BOX:
        boxes[o["subject"]] = tuple(float(v) for v in o["value"][1:5])
stems = {}
for o in rec["observations"]:
    if o["quantity"] == Q.STEM:
        stems.setdefault(o["subject"], []).append(tuple(float(v) for v in o["value"]))
vd = {}
for v in rec["verdicts"]:
    vd[(v["quantity"], v["subject"])] = v
heads = {o["subject"] for o in rec["observations"] if o["quantity"] == Q.NOTEHEAD_CLASS}
n = nd = near = 0
ex = []
for h in sorted(heads):
    hs = vd.get((Q.HEAD_STEM, h))
    if not hs or hs["outcome"] != "abstained":
        continue
    n += 1
    d = vd.get((Q.DURATION, h))
    if not d or d["outcome"] != "decided":
        continue
    nd += 1
    cell = "cell/" + "/".join(h.split("/")[1:5])
    hb = boxes[h]
    best = None
    for k in heads:
        if k == h or not k.startswith("glyph/" + "/".join(h.split("/")[1:5]) + "/"):
            continue
        kb = boxes[k]
        w = (hb[2] + kb[2]) / 2.0
        hh = (hb[3] + kb[3]) / 2.0
        dx = abs((hb[0] + hb[2] / 2) - (kb[0] + kb[2] / 2)) / w
        dy = abs((hb[1] + hb[3] / 2) - (kb[1] + kb[3] / 2)) / hh
        if best is None or dx + dy < best[0] + best[1]:
            best = (dx, dy, k)
    if best and best[0] <= 2.0 and best[1] <= 1.6:
        near += 1
        if len(ex) < 14:
            ex.append((h[-14:], round(best[0], 2), round(best[1], 2), best[2][-8:], OC.is_second(hb, boxes[best[2]]),
                       (vd.get((Q.HEAD_STEM, best[2])) or {}).get("reason")))
print("no_stem heads", n, "with decided duration", nd, "with another head within 2 widths/1.6 heights", near)
for e in ex:
    print(e)
