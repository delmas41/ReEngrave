"""2.322 measure 1 for a plate from gaps_page.py's own role tallies (same canvas as claim_readout ink; used for Brahms because `claim_readout ink` raised its own
partition check 'weak by kind exceeds the weak line' on that slice).   python3 lines_from_roles.py PLATE DATADIR"""
import collections
import json
import sys

plate, data = sys.argv[1], sys.argv[2]
d = json.load(open("%s/%s_roles.json" % (data, plate)))
st = collections.Counter()
for k, v in d["state_by_role"].items():
    st[k.split("|")[1]] += v
tot = sum(st.values())
one = st["one"] + st["staff_line"]
twice = st["twin"] + st["twin_views"] + st["two_kinds"] + st["views_disagree"] + st["page_not_consulted"]
print(plate, "dark px", tot)
print("one owner %.1f%% (staff line %.1f%%, other %.1f%%) | weak %.2f%% | twice %.1f%% | none %.1f%%" % (
    100.0 * one / tot, 100.0 * st["staff_line"] / tot, 100.0 * st["one"] / tot, 100.0 * st["weak"] / tot, 100.0 * twice / tot, 100.0 * st["none"] / tot))
print("one owner, share of non-staff ink: %.1f%%" % (100.0 * st["one"] / (tot - st["staff_line"])))
ok = collections.Counter()
for k, v in d["one_owner_by_role"].items():
    ok[k.split("|")[1]] += v
print("one owner by kind (% of all ink):", {k: round(100.0 * v / tot, 2) for k, v in ok.most_common(14)})
nc = collections.Counter()
for k, v in d["none_by_class_role"].items():
    nc[k.split("|")[1]] += v
print("no owner by tool class (% of all ink):", {k: round(100.0 * v / tot, 2) for k, v in nc.most_common()})
print("twice parts (% of all ink):", {k: round(100.0 * st[k] / tot, 2) for k in ("twin", "twin_views", "two_kinds", "views_disagree", "page_not_consulted")})
