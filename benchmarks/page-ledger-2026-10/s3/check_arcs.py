"""Sean's s2 answers on arcs (tile 5 above, tile 8 below) against the arc owner of this round.
    python3 benchmarks/page-ledger-2026-10/s3/check_arcs.py"""
import json
import pathlib

H = pathlib.Path(__file__).parent
key = {t["tile"]: t for t in json.load(open("out/print/2.240-s2-tiles/key.json"))}
want = {5: ("litolff6", 6), 8: ("brahms", 5)}


def ov(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max(1e-9, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


for t, (plate, pg) in want.items():
    r = json.load(open(H / ("measure_%s.json" % plate)))
    box = key[t]["span"]["box"]
    hit = [a for a in r["arcs"]["rows"] if a["page"] == pg and ov(a["box"], box) > 0.5]
    print("tile", t, "s2 staves", key[t]["staves"], "Sean:", "above" if t == 5 else "below", "->",
          [(a["status"], a["owner"], a["reason"], a["seen_from"]) for a in hit])
