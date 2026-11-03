"""Per (array, quantity, field) and per verdict `detail` key compact-JSON bytes of a record FILE, streamed (ijson).

usage: field_bytes.py RECORD OUT.json   (ROADMAP 2.249; reads only)
"""
import sys, json, ijson
from collections import defaultdict

src, dst = sys.argv[1:3]
F = defaultdict(int); D = defaultdict(int); N = defaultdict(int); POOL = 0


def enc(x):
    return len(json.dumps(x, separators=(",", ":"), default=str))


with open(src, "rb") as fh:
    for arr in ("observations", "abstentions", "verdicts"):
        fh.seek(0)
        for row in ijson.items(fh, f"record.{arr}.item", use_float=True):
            q = row.get("quantity"); N[(arr, q)] += 1
            for k, v in row.items():
                F[(arr, q, k)] += enc(v)
            if arr == "verdicts":
                for k, v in (row.get("detail") or {}).items():
                    D[(q, k)] += enc(v)
    fh.seek(0)
    for k, v in ijson.kvitems(fh, "record.pools"):
        POOL += enc(v)


def top(d, n):
    return [[*k, round(v / 1e6, 1)] for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:n]]


json.dump({"rows": {f"{a}|{q}": n for (a, q), n in N.items()}, "fields_mb": top(F, 60),
           "detail_mb": top(D, 60), "pools_mb": round(POOL / 1e6, 1)}, open(dst, "w"), indent=1)
print("done", dst)
