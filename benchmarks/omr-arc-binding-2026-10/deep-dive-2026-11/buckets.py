"""Break the biggest dropped buckets of a ledger into features (measure only): python3 buckets.py LEDGER.json"""
import collections
import json
import sys

res = json.load(open(sys.argv[1]))
rows = res["rows"]


def feat(r):
    pb = r.get("binding") or {}
    l, rr = pb.get("left") or {}, pb.get("right") or {}
    return dict(
        cls="/".join(sorted(set(r["classes"]))), pieces=r["n_pieces"], curve=r["has_curve"], cut=r.get("cut"),
        why=pb.get("why"), lu=l.get("unbound"), ru=rr.get("unbound"), relation=pb.get("relation"),
        kind_ruled=pb.get("kind"), shape=r.get("shape"))


def table(title, sel, keys):
    sub = [r for r in rows if sel(r)]
    print("\n##", title, len(sub))
    for k in keys:
        c = collections.Counter(str(feat(r).get(k)) for r in sub)
        print("  by", k, dict(c.most_common(8)))


table("slur box path dropped (arc_binds_fewer_than_two_notes_or_not_in_file)",
      lambda r: r.get("fate") == "dropped" and (r.get("lost_rule") or "").startswith("export:arc_binds"),
      ["cls", "pieces", "curve", "cut", "why", "lu", "ru", "shape"])
table("tie_not_in_file", lambda r: r.get("lost_rule") == "export:tie_not_in_file", ["cls", "pieces", "cut", "relation", "why"])
table("tie_pair abstained", lambda r: (r.get("lost_rule") or "").startswith("tie_pair"), ["cls", "pieces", "cut", "why", "lu", "ru", "shape", "kind_ruled"])
table("slur_bound_not_in_file", lambda r: r.get("lost_rule") == "export:slur_bound_not_in_file", ["cls", "pieces", "cut", "relation", "why"])
table("ALL real", lambda r: r["fate"] != "not_an_arc", ["cls", "pieces", "curve", "cut", "why", "shape"])
