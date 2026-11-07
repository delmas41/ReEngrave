"""2.274 r3: runs by provenance (plain / linked / thick) and witnessed or NEW.   python3 srcs3.py DIR [STEM ...]"""
import collections
import json
import pathlib
import sys

wd = pathlib.Path(sys.argv[1])
names = sys.argv[2:] or sorted(p.name.replace(".step1.json", "") for p in wd.glob("*.step1.json"))
c = collections.Counter()
for n in names:
    for r in json.load(open(wd / (n + ".step1.json")))["runs"]:
        c[(r.get("src", "?"), "witnessed" if r["witnesses"] else "NEW")] += 1
for k in sorted(c):
    print(k, c[k])
