"""2.306 r14: print the Q.PAGE_STEM row (or abstention) and the glyph box for given glyph keys. Usage: r14_pstem_rows.py REC.json key,key"""
import json
import sys

from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])["record"]
ks = set(sys.argv[2].split(","))
for o in rec["observations"]:
    if o["subject"] in ks and o["quantity"] in ("page_stem", "glyph_box"):
        print(o["subject"], o["quantity"], o.get("value"), json.dumps(o.get("detail"), default=str)[:1500])
for a in rec.get("abstentions") or ():
    if a["subject"] in ks and a.get("quantity") == "page_stem":
        print(a["subject"], "ABSTAIN", a.get("reason"), json.dumps(a.get("detail"), default=str)[:1500])
