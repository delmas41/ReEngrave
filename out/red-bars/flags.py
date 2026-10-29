"""flags.py PLATE : per red bar record-own flags, tabulated. Writes work/PLATE.flags.json"""
import json, sys, collections
plate = sys.argv[1]
F = json.load(open("out/red-bars/work/%s.feat.json" % plate))
C = {c["key"]: c for c in json.load(open("out/red-bars/work/%s.cls.json" % plate))}
out = {}
for b in F:
    c = C[b["key"]]
    me = "staff/%d/%d/%d" % (b["page"], b["system"], b["staff"])
    rows = b["rows"]
    fl = {}
    fl["foreign_owner_rows"] = [r["glyph"] for r in rows if r["owner"] and r["owner"] != me]
    fl["unboxed_rows"] = [r["glyph"] for r in rows if r["cls"] is None]
    fl["far_rows"] = [r["glyph"] for r in rows if r["staffpos"] is not None and abs(r["staffpos"]) > 7.5 and r["kind"] == "note"]
    fl["whole_rest"] = [r["glyph"] for r in rows if r["kind"] == "rest" and (r.get("measure_rest") or r["cls"] == "restWhole")]
    fl["guessed_rows"] = [r["glyph"] for r in rows if r["status"] == "GUESSED"]
    fl["dur_reasons"] = sorted({(r["dur"] or {}).get("reason") or "-" for r in rows})
    fl["narrowed_rows"] = [r["glyph"] for r in rows if (r["dur"] or {}).get("outcome") == "narrowed"]
    out[b["key"]] = fl
json.dump(out, open("out/red-bars/work/%s.flags.json" % plate, "w"))
n = len(F)
for name in ("foreign_owner_rows", "unboxed_rows", "far_rows", "whole_rest", "guessed_rows", "narrowed_rows"):
    ov = sum(1 for b in F if out[b["key"]][name] and C[b["key"]]["over"])
    sh = sum(1 for b in F if out[b["key"]][name] and not C[b["key"]]["over"])
    print("%-20s over %3d short %3d" % (name, ov, sh))
print("dur reasons over", collections.Counter(r for b in F if C[b["key"]]["over"] for r in out[b["key"]]["dur_reasons"]).most_common(12))
print("dur reasons short", collections.Counter(r for b in F if not C[b["key"]]["over"] for r in out[b["key"]]["dur_reasons"]).most_common(12))
