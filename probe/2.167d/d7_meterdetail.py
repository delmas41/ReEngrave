"""2.167d probe 7: the detail of the rest_is_a_meter_digit verdicts on the real rests of Brahms sample bars 4 and 14: the meter column span vs the rest's x.
usage: d7_meterdetail.py"""
import json
import os

import ijson

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = ROOT + "/probe/2.167d/data/"
bf = json.load(open(D + "bra_boxfates.json"))
rec = json.load(open(D + "bra_rec.json"))
want = {}
for key, rows in bf.items():
    for r in rows:
        if "rest_is_a_meter_digit" in r["fate"]:
            g = [g for g in rec["cells"][key]["glyphs"] if g["sub"] == r["sub"]][0]
            want[r["sub"]] = (key, g["cls"], g["bbox"])
print(len(want), "rests refused as meter digit in the 45 Brahms bars")
path = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/brahms1-breitkopf-mvt1-whole-20261018-night.record.json"
with open(path, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        if v.get("subject") in want and v["quantity"] == "rest_is_not_a_rest":
            print(want[v["subject"]], v.get("reason"), (v.get("detail") or {}).get("meter_column_page_px"), (v.get("detail") or {}).get("meter_digit_rows"))
