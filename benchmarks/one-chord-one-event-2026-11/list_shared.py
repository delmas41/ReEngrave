"""2.300: list every pair of events whose heads share one stem id (OFF run). usage: list_shared.py EV.json [red|partial|clean]"""
import json
import sys

d = json.load(open(sys.argv[1]))
want = sys.argv[2] if len(sys.argv) > 2 else None
red = {tuple(r[k] for k in ("page", "system", "staff", "cell")): r for r in d["red_bars"]}
for b in d["bars"]:
    ev = b["events"]
    st = "red" if b["red"] else "partial" if b["partial"] else "clean"
    if want and st != want:
        continue
    for i in range(len(ev)):
        for j in range(i + 1, len(ev)):
            ids = {h["stem_id"] for h in ev[i]["heads"] if h["stem_id"]} & {h["stem_id"] for h in ev[j]["heads"] if h["stem_id"]}
            if ids:
                r = red.get(tuple(b["key"]))
                print("%s %s i=%d j=%d beats=%s/%s types=%s/%s dirs=%s/%s want=%s counted=%s" % (
                    st, "/".join(map(str, b["key"])), i, j, ev[i]["beats"], ev[j]["beats"],
                    [h["type"] for h in ev[i]["heads"]], [h["type"] for h in ev[j]["heads"]],
                    [h["stem"] for h in ev[i]["heads"]], [h["stem"] for h in ev[j]["heads"]],
                    r and r["want_quarters"], r and r["counted_quarters"]))
