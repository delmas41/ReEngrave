"""2.279 r4: are the 16 tiles Sean is judging still what the flag writes? usage: python3 probe/2.279r3/tiles_still.py WORKDIR"""
import json
import sys

w = sys.argv[1]
on = {p: {h["rg"]: h for h in json.load(open("%s/%s.on.symbols.json" % (w, p)))["hosts"] if h.get("rg")} for p in ("litolff", "brahms")}
for k in ("blue", "red"):
    for t in json.load(open("out/print/2.279-r3/%s/key.json" % k)):
        h = on[t["plate"]].get(t["rg"])
        print(k, t["tile"], t["rg"], "then:", t["value"], "| now:", h and (h["type"], h["blue"]))
