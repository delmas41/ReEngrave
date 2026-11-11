"""2.280 r3: of the READ heads with NO stem row, how many have a PARTNER head (same cell, centres within 1.3 head widths sideways and 1.5 head heights up/down,
i.e. the other head of a second, or a chord mate) that DOES touch a stem? (the 'head of a second, stem on its partner' bucket of 2.280). usage: partner.py HEADS.jsonl [--pages ..]"""
import collections
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1])]
if "--pages" in sys.argv:
    pg = {int(p) for p in sys.argv[sys.argv.index("--pages") + 1].split(",")}
    rows = [r for r in rows if r["page"] in pg]
COPY = ("owned_by_another_staff", "mark_group_duplicate")
real = [r for r in rows if r["kept"] and r["fate"] not in COPY and r["fate"] != "ink_is_a_whole_rest" and r["page_box"]]
by_cell = collections.defaultdict(list)
for r in real:
    by_cell[r["sub"].rsplit("/", 1)[0]].append(r)
c = collections.Counter()
for r in real:
    if r["n_stem"] > 0:
        continue
    x0, y0, x1, y1 = r["page_box"]
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    part = [o for o in by_cell[r["sub"].rsplit("/", 1)[0]] if o is not r and o["page_box"]
            and abs((o["page_box"][0] + o["page_box"][2]) / 2 - cx) <= 1.3 * w and abs((o["page_box"][1] + o["page_box"][3]) / 2 - cy) <= 1.5 * h]
    sec = [o for o in part if abs((o["page_box"][0] + o["page_box"][2]) / 2 - cx) >= 0.5 * w]    # displaced sideways: a second
    c["no stem row"] += 1
    c["  partner with a stem within reach"] += bool(part)
    c["  of them displaced sideways (a second)"] += bool(sec)
    c["  whole-class / rest-like duration abstained"] += bool(r["duration"] and r["duration"][0] == "abstained")
for k, v in c.items():
    print("%5d %s" % (v, k))
