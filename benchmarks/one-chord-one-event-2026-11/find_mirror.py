"""2.300: real two-voice onsets (MIRROR CASE): a bar with a voice split whose two streams each hold a note event at one onset
(x within 0.6 head widths) with OPPOSITE stem directions. usage: find_mirror.py EV.json [pages...]"""
import json
import sys

d = json.load(open(sys.argv[1]))
pages = {int(x) for x in sys.argv[2:]}
for b in d["bars"]:
    if pages and b["key"][0] not in pages:
        continue
    ev = b["events"]
    if not b["streams"] or len(b["streams"]) != 2:
        continue
    ups = [i for i, e in enumerate(ev) if e["kind"] == "chord" and e["heads"] and all(h["stem"] == "up" for h in e["heads"])]
    downs = [i for i, e in enumerate(ev) if e["kind"] == "chord" and e["heads"] and all(h["stem"] == "down" for h in e["heads"])]
    for i in ups:
        for j in downs:
            if abs(ev[i]["x"] - ev[j]["x"]) <= 0.6 * ev[i]["heads"][0]["bbox"][2]:
                print("/".join(map(str, b["key"])), "red" if b["red"] else "partial" if b["partial"] else "plain", "up", i, "down", j,
                      [h["pitch"] for h in ev[i]["heads"]], [h["pitch"] for h in ev[j]["heads"]])
