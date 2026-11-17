"""ROADMAP 2.313 -- print a saved record's provenance and where the staff names were read (reads only).

    python3 benchmarks/landing-check-2026-11/prov.py REC.record.json
"""
import collections
import sys

from tools.omr.staged.record_io import load_record

r = load_record(sys.argv[1])
p = r.get("provenance") or {}
print("commit", p.get("commit"), "env", (p.get("settings") or {}).get("env_overrides"), "pages", ((p.get("settings") or {}).get("args") or {}).get("pages"))
rec = r["record"]
ml = [o for o in rec["observations"] if o["quantity"] == "margin_label"]
print("margin_label observations by page:", sorted(collections.Counter(str(o["subject"]).split("/")[1] if "/" in str(o["subject"]) else "?" for o in ml).items()))
print("sample subjects", [o["subject"] for o in ml[:3]])
qv = collections.Counter((v["quantity"], v.get("outcome")) for v in rec["verdicts"] if v["quantity"] in ("instrument", "part_name"))
print("verdicts", qv.most_common())
