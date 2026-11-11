"""2.291: cut the default pages out of a wide capture. usage: subset.py WIDE.bars.json OUT.bars.json PAGE[,PAGE]  -- prints red-bar count"""
import json
import sys

bars = json.load(open(sys.argv[1]))
keep = {int(x) for x in sys.argv[3].split(",")}
sub = [b for b in bars if b["key"][0] in keep]
json.dump(sub, open(sys.argv[2], "w"))
print(len(sub), "bars,", sum(1 for b in sub if b["red"]), "red,", sum(b["red"]["noteheads_and_rests"] for b in sub if b["red"]), "notes in red")
