"""2.197 C12: the role x type table, % right at each stage and where the loss happens. usage: c12_tables.py CENSUS.json [src-filter]"""
import sys, json, collections, statistics
cen = json.load(open(sys.argv[1])); flt = sys.argv[2] if len(sys.argv) > 2 else None
cen = [x for x in cen if (flt is None or x["src"] == flt)]
def pct(a, n): return "%3d%%" % round(100.0 * a / n) if n else "  - "
print("%-34s %-8s %4s | %-18s %-18s %-18s %-18s | %s" % ("role", "type", "n", "GATHER boxed", "GATHER right class", "ADJ owner decided", "ADJ+right type", "EXPORT note right (at Sean's head)"))
for role in sorted({x["role"] for x in cen}):
    for t in ("natural", "flat", "sharp"):
        xs = [x for x in cen if x["role"] == role and x["type"] == t]
        if not xs: continue
        n = len(xs)
        if role.startswith("1_"):
            boxed = sum(1 for x in xs if x["G"] != "not_boxed")
            right = sum(1 for x in xs if x.get("offered_right_kind") or (x["boxes_on_ink"] and any(b["cls"].lower().startswith("key") for b in x["boxes_on_ink"])))
            km = sum(1 for x in xs if x.get("KS") and x["KS"][0] == "decided" and x["KS"][1] in ("markers",))
            print("%-34s %-8s %4d | boxed %s (%d)   key-class box %s   acc-class only %s | staff key from markers %s (n=%d key items)" % (
                role, t, n, pct(boxed, n), boxed, pct(sum(1 for x in xs if any(b["cls"].lower().startswith("key") for b in x["boxes_on_ink"])), n),
                pct(sum(1 for x in xs if x["boxes_on_ink"] and not any(b["cls"].lower().startswith("key") for b in x["boxes_on_ink"])), n), pct(km, n), n))
            continue
        boxed = sum(1 for x in xs if x["G"] != "not_boxed")
        right = sum(1 for x in xs if x.get("offered_right_kind"))
        dec = sum(1 for x in xs if x.get("A") == "owner_decided")
        decr = sum(1 for x in xs if x.get("A") == "owner_decided" and x.get("A_type_right"))
        e2 = sum(1 for x in xs if x.get("E2") == "alter_right/elem_right")
        print("%-34s %-8s %4d | %s (%2d)           %s (%2d)           %s (%2d)           %s (%2d)           | %s (%2d)" % (role, t, n, pct(boxed, n), boxed, pct(right, n), right, pct(dec, n), dec, pct(decr, n), decr, pct(e2, n), e2))
print()
print("Where the in-bar loss happens (count of items; each item counted once at the FIRST stage that fails):")
for t in ("natural", "flat", "sharp", "ALL"):
    xs = [x for x in cen if x["role"] == "3_in_bar" and (t == "ALL" or x["type"] == t)]
    c = collections.Counter()
    for x in xs:
        if x["G"] == "not_boxed": c["1 GATHER: no box on the ink"] += 1
        elif not x.get("offered_right_kind"): c["2 GATHER: boxes on the ink, none of the right class"] += 1
        elif x.get("A") != "owner_decided": c["3 ADJUDICATE: owner abstains (" + str(x.get("A")).split(":")[-1][:30] + ")"] += 1
        elif not x.get("A_type_right"): c["4 ADJUDICATE/merge: right class was offered, a wrong class owns the head"] += 1
        elif x.get("E2") == "alter_right/elem_right": c["0 right at export"] += 1
        else: c["5 after the owner: note at Sean's head written " + str(x.get("E2"))] += 1
    print(" ", t, len(xs)); [print("     %3d  %s" % (v, k)) for k, v in sorted(c.items())]
