"""Every note the ON arm gained blue (vs OFF), from the written files.  usage: all_blue.py LANE_DIR"""
import json
import sys
W = sys.argv[1] + "/work/"
for plate in ("litolff", "brahms"):
    on = json.load(open(W + plate + ".on.symbols.json"))["hosts"]
    off = {h["rg"]: h for h in json.load(open(W + plate + ".off.symbols.json"))["hosts"] if h.get("rg")}
    for h in on:
        if h.get("rg") in off and h["blue"] and not off[h["rg"]]["blue"]:
            print(plate, h["page"], ",".join(str(round(v)) for v in h["box"]), h["rg"], h["pitch"])
