"""2.299: the raw measured slots of every FILLED key staff-system, beside the fixed-order steps for its READ clef.
    PYTHONPATH=. python3 slots_dump.py X.json CENSUS.json [bucket,bucket...]     (X = analyze.py output, CENSUS = census.py output)
"""
import json
import sys

from tools.omr.staged import key_object as KO

d = json.load(open(sys.argv[1]))
cen = json.load(open(sys.argv[2]))
buckets = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
rows = [x for x in cen if x["standing"] == "filled" and x["plate"] == d["plate"] and (buckets is None or x["bucket"] in buckets)]
for x in rows:
    k = x["staff"]
    v = d["staffs"][k]
    clef = v["clef"][0]["value"]
    for row in v["evidence"]["claimed_area"]:
        dt = row["detail"]
        if isinstance(dt, dict) and dt.get("key_object"):
            ko = dt["key_object"]
            print(k, x["bucket"], "clef", clef, "sp", dt["space_page_px"], "N", ko["system_count"], "own", ko["own_slots"], "edge", ko["clef_edge"],
                  "clefbox", ko["clef_measured"], "->", x["slots"]["why"])
            for p in ko["read_pieces"]:
                s = p.get("slot")
                print("    slot", s, "cx", p.get("cx"), "step", p.get("step"), "h", p.get("h"), p.get("basis"), p.get("shape"),
                      "| flat e", KO.expected_step(clef, "b", s), "sharp e", KO.expected_step(clef, "#", s))
            break
