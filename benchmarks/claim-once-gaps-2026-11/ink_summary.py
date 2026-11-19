"""2.322 measure 1 from claim_readout ink's ink_number.json.   python3 ink_summary.py INK_NUMBER_JSON"""
import json
import sys

d = json.load(open(sys.argv[1]))
t = d["total"]
tot = t["ink_px"]
print("pages", d["pages"], "dark px", tot)
print("four lines %:", {k: round(100.0 * v / tot, 2) for k, v in t["lines"].items()})
nonstaff = tot - t["one"]["by_kind"].get("staff_line", 0)
print("one owner, share of non-staff ink: %.1f%%" % (100.0 * (t["lines"]["one"] - t["one"]["by_kind"].get("staff_line", 0)) / nonstaff))
print("one owner by kind %:", {k: round(100.0 * v / tot, 2) for k, v in sorted(t["one"]["by_kind"].items(), key=lambda kv: -kv[1])})
print("none by class %:", {k: round(100.0 * v / tot, 2) for k, v in t["none"]["by_class"].items()})
tw = t["twice"]
print("twice parts %:", {k: round(100.0 * tw[k] / tot, 2) for k in ("twin_px", "twin_views_px", "two_kinds_px", "views_disagree_px", "page_not_consulted_px")})
print("twice by kind (one kind twice) %:", {k: round(100.0 * v / tot, 2) for k, v in sorted(tw["twin_by_kind"].items(), key=lambda kv: -kv[1])[:6]})
print("twice two-kind pairs %:", {k: round(100.0 * v / tot, 2) for k, v in sorted(tw["pairs"].items(), key=lambda kv: -kv[1])[:8]})
print("per page:", {p: {k: round(100.0 * v / r["ink_px"], 1) for k, v in r["lines"].items()} for p, r in d["per_page"].items()})
