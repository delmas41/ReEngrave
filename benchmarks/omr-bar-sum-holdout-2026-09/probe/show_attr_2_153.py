"""ROADMAP 2.153 -- print the replay chain + live detail of chosen targets from attribute_2_153.py outputs.
usage: show_attr_2_153.py ATTR.json ITEM:N [ITEM:N ...]"""
import json
import sys

rows = json.load(open(sys.argv[1]))
want = set(sys.argv[2:])
for r in rows:
    if "%s:%s" % (r["item"], r["n"]) not in want:
        continue
    print("=====", r["item"], r["n"], r["glyph"], "Sean:", r["sean"])
    for tag in ("stored", "replay"):
        print(" ", tag)
        for v in r[tag]:
            print("    ", v["id"], v["decider"], v["reason"], v["outcome"], v["value"], v["cands"], "sup", v["supersedes"])
    print("  live detail:", r.get("replay_live_detail"))
