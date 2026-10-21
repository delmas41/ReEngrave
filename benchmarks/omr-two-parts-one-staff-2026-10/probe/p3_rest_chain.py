"""ROADMAP 2.182 Part B -- every rest refused `rest_is_a_duplicate_box`: what outranked it, and was THAT box kept?

usage: python3 benchmarks/omr-two-parts-one-staff-2026-10/probe/p3_rest_chain.py RECORD [OUT.json]
Classes: kept_partner (a kept rest stands on the ink -- nothing lost), chain_refused_partner (every partner is itself refused
for a reason OTHER than the duplicate rule -- the 2.179 chain), mutual_disagreement (a different-class pair refused each
other -- nobody else refused them), mixed. Read-only.
"""
import collections
import json
import sys

rec = json.load(open(sys.argv[1]))["record"]
rowsub = {}
for o in rec["observations"]:
    if o.get("quantity") == "glyph_box":
        rowsub[o["id"]] = o["subject"]
ref = {}
for v in rec["verdicts"]:
    if v.get("quantity") == "rest_is_not_a_rest":
        ref[v["subject"]] = (v.get("value"), v.get("reason"), v.get("detail") or {})
c = collections.Counter()
out = []
for s, (val, reason, det) in ref.items():
    if reason != "rest_is_a_duplicate_box":
        continue
    partners = [rowsub.get(r) for r in (det.get("duplicate_disagrees_with") or ([det["duplicate_of"]] if det.get("duplicate_of") else []))]
    fates = [ref.get(p, (None, None, {}))[:2] for p in partners]
    if any(f[0] is False for f in fates):
        k = "kept_partner"
    elif fates and all(f[0] is True and f[1] != "rest_is_a_duplicate_box" for f in fates):
        k = "chain_refused_partner"
    elif fates and all(f[1] == "rest_is_a_duplicate_box" for f in fates):
        k = "mutual_disagreement" if det.get("duplicate_disagrees_with") else "chain_partner_duplicate"
    else:
        k = "mixed"
    c[k] += 1
    out.append(dict(subject=s, kind=k, cls=det.get("class"), partners=partners, fates=fates))
cells = collections.defaultdict(set)
for o in out:
    cells[o["kind"]].add("/".join(o["subject"].split("/")[1:5]))
print(dict(c))
print({k: len(v) for k, v in cells.items()})
pr = collections.Counter(f[1] for o in out if o["kind"] == "chain_refused_partner" for f in o["fates"])
print("chain partner reasons", dict(pr))
pc = collections.Counter((o["cls"], tuple(sorted(str(ref.get(p, (0, 0, {}))[2].get("class")) for p in o["partners"]))) for o in out if o["kind"] == "mutual_disagreement")
print("mutual pairs", pc.most_common(8))
if len(sys.argv) > 2:
    json.dump(out, open(sys.argv[2], "w"), default=str)
