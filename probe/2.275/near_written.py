"""2.275: for each ink-not-in-file representative, is a WRITTEN notehead box (any staff, same page) centred within R staff spaces of its
centre? A cut/narrow fragment of a head that IS written one box over is a copy of in-file ink that IoU did not join.
usage: near_written.py PLATE PART.rows.jsonl INK.json OUT.json"""
import collections
import json
import sys

plate, rows_p, ink_p, out = sys.argv[1:5]
SP = 27.3 if plate == "brahms" else 15.75
rows = [json.loads(l) for l in open(rows_p)]
ink = json.load(open(ink_p))
by = {r["sub"]: r for r in rows}
W = collections.defaultdict(list)
for r in rows:
    if r["bucket"] in ("WRITTEN", "partial_bar_cell"):
        b = r["bbox"]
        W[(r["sub"].split("/")[1], int(((b[0] + b[2]) / 2) // 100), int(((b[1] + b[3]) / 2) // 100))].append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, r))
res = {}
for R in (0.5, 1.0):
    tab = collections.defaultdict(lambda: [0, 0])
    for bk, subs in ink["members"].items():
        for s in subs:
            b = by[s]["bbox"]
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            pg = s.split("/")[1]
            hit = False
            for gx in (int(cx // 100) - 1, int(cx // 100), int(cx // 100) + 1):
                for gy in (int(cy // 100) - 1, int(cy // 100), int(cy // 100) + 1):
                    for x, y, w in W.get((pg, gx, gy), ()):
                        if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 <= R * SP:
                            hit = True
            tab[bk][0] += 1
            tab[bk][1] += hit
    res[str(R)] = dict(tab)
    print(plate, "R=%.1f sp: bucket, n, with a written head centred within R" % R)
    for bk, (n, h) in sorted(tab.items(), key=lambda kv: -kv[1][0])[:10]:
        print("  %-52s %5d %5d" % (bk, n, h))
json.dump(res, open(out, "w"))
