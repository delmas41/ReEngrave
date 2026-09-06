import json, sys
r = json.load(open(sys.argv[1]))
pg = next(p for p in r["pages"] if p.get("systems"))
print("page keys:", sorted(pg))
sy = pg["systems"][0]
print("system keys:", sorted(sy))
st = sy["staves"][0]
print("staff keys:", sorted(st))
for k in sorted(st):
    if k in ("measures", "detections"):
        continue
    print("   ", k, "=", repr(st[k])[:120])
print()
print("contextual keys:", sorted((r.get("contextual") or {})))
