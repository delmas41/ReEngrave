"""Head trim fix 2: own place-matched check of every judged tile (benchmarks/acceptance/judged-tiles.json) on the pages of a lane-report
work dir: the written value / pitch / blue flag in the OFF and ON arm's symbols.json, matched by glyph key AND box (never box alone),
blue included, set against Sean's answer. Also lists every host whose type/pitch/blue differs between arms, judged or not.
usage: python3 judged_diff_v2.py WORK_DIR"""
import json, sys, collections

W = sys.argv[1]
T = json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
PAGES = {"litolff": {4, 10}, "brahms": {5, 14}}
for plate, pages in PAGES.items():
    hosts = {}
    for arm in ("off", "on"):
        S = json.load(open("%s/%s.%s.symbols.json" % (W, plate, arm)))
        hosts[arm] = {h["rg"]: h for h in S["hosts"] if h.get("rg")}
    off, on = hosts["off"], hosts["on"]
    print("== %s: %d hosts off, %d on, keys only in one arm: %d" % (plate, len(off), len(on), len(set(off) ^ set(on))))
    moved = [k for k in off if k in on and off[k].get("box") != on[k].get("box")]
    print("   same key, different box: %d" % len(moved))
    diff = [k for k in off if k in on and (off[k].get("type"), off[k].get("pitch"), off[k].get("blue"), off[k].get("chord"),
                                          json.dumps(off[k].get("sub"), sort_keys=True))
            != (on[k].get("type"), on[k].get("pitch"), on[k].get("blue"), on[k].get("chord"), json.dumps(on[k].get("sub"), sort_keys=True))]
    print("   hosts whose written type/pitch/blue/chord/sub differ OFF->ON: %d" % len(diff))
    for k in diff:
        print("     ", k, "OFF", off[k]["type"], off[k]["pitch"], "blue" if off[k]["blue"] else "plain", "| ON", on[k]["type"], on[k]["pitch"],
              "blue" if on[k]["blue"] else "plain")
    n = found = changed = 0
    for t in T:
        if t["doc"] != plate:
            continue
        keys = [t.get("subject") or ""] + list(t.get("subjects") or [])
        for k in keys:
            if not k.startswith("glyph/"):
                continue
            p = int(k.split("/")[1])
            if p not in pages:
                continue
            n += 1
            if k in off and k in on:
                found += 1
                a, b = off[k], on[k]
                if (a["type"], a["pitch"], a["blue"]) != (b["type"], b["pitch"], b["blue"]):
                    changed += 1
                    print("   JUDGED CHANGED", t["item"], t["tile"], k, "Sean:", t["answer"], "| OFF", a["type"], a["pitch"], a["blue"],
                          "| ON", b["type"], b["pitch"], b["blue"])
    print("   judged subject keys on these pages: %d, present in both arms as a written note: %d, changed written value/pitch/blue: %d"
          % (n, found, changed))
