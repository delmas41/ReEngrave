"""2.172 (f): the tiles of Sean's judged index whose scored status differs between the OFF and the ON record of a plate."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for pl in ("lit", "bra"):
    a = json.load(open(ROOT / ("probe/2.172/data/judged_%s_off.json" % pl)))["tiles"]
    b = json.load(open(ROOT / ("probe/2.172/data/judged_%s_on.json" % pl)))["tiles"]
    if isinstance(a, dict):
        a, b = list(a.values()), list(b.values())
    print(pl, len(a), len(b), list(a[0].keys()) if a else None)
    ka = {(t.get("item"), t.get("tile")): t for t in a}
    n = 0
    for t in b:
        o = ka.get((t.get("item"), t.get("tile")))
        if o is not None and o.get("status") != t.get("status"):
            n += 1
            print(" ", t.get("item"), t.get("tile"), t.get("subject"), "| sean:", str(t.get("answer"))[:40], "| OFF:", o.get("status"), str(o.get("got") or o.get("detail") or "")[:60],
                  "| ON:", t.get("status"), str(t.get("got") or t.get("detail") or "")[:60])
    print(" differing:", n)
