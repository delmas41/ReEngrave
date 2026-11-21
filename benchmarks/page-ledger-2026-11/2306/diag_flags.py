"""Lost flags: the written host OFF vs ON (type, beam, flag) and the glyph's duration / stem_direction / head_stem OFF vs ON."""
import sys, json, collections
pre = sys.argv[1]
pages = {int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")} if "--pages" in sys.argv else None
A = json.load(open(pre + ".off.json"))
B = json.load(open(pre + ".on.json"))
VA = {(v["q"], v["s"]): v for v in A["verdicts"]}
VB = {(v["q"], v["s"]): v for v in B["verdicts"]}


def hosts(D):
    o = collections.defaultdict(list)
    for h in D["hosts"]:
        if h.get("rg"):
            o[h["rg"]].append(h)
    return o


HA, HB = hosts(A), hosts(B)
cls = collections.Counter()
for rg, hs in HA.items():
    if pages and int(rg.split("/")[1]) not in pages:
        continue
    na = sum(len((h.get("sub") or {}).get("flag") or ()) for h in hs)
    nb = sum(len((h.get("sub") or {}).get("flag") or ()) for h in HB.get(rg, ()))
    if na <= nb:
        continue
    ha = [(h.get("type"), dict((k, v) for k, v in (h.get("sub") or {}).items() if v and k in ("flag", "beam"))) for h in hs]
    hb = [(h.get("type"), dict((k, v) for k, v in (h.get("sub") or {}).items() if v and k in ("flag", "beam"))) for h in HB.get(rg, ())]
    da, db = VA.get(("duration", rg)), VB.get(("duration", rg))
    sa, sb = VA.get(("stem_direction", rg)), VB.get(("stem_direction", rg))
    wa = da and isinstance(da["v"], dict) and da["v"].get("written")
    wb = db and isinstance(db["v"], dict) and db["v"].get("written")
    k = "gone" if not hb else ("now beamed" if any(x[1].get("beam") for x in hb) else ("value %s->%s" % (wa, wb)))
    cls[k] += 1
    print(rg, ha, "->", hb, "| dur", da and (da["r"], wa), "->", db and (db["r"], wb), "| dir", sa and (sa["r"], sa["v"]), "->", sb and (sb["r"], sb["v"]))
print(dict(cls))
