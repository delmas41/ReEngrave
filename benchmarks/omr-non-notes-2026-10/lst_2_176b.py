"""2.176b: turn census_2_176b.py output into the subject list crops_2_176.py takes. usage: lst_2_176b.py CENSUS.json LIST.json [PAGE]"""
import json
import sys

r = json.load(open(sys.argv[1]))
pg = int(sys.argv[3]) if len(sys.argv) > 3 else None
sel = [x["glyph"] for x in r if x["witness"] and (pg is None or x["page"] == pg)]
json.dump(sel, open(sys.argv[2], "w"))
for x in r:
    if x["witness"] and (pg is None or x["page"] == pg):
        print(x["glyph"], x["cls"], x["witness"], x["dur"])
