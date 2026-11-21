"""2306 r9: Sean's tile places as each arm writes them now (every host at the glyph: kind, pitch, value, dots, voice, blue), EXPORT's fate, Sean's answer.
Usage: tiles9.py RFPREFIX_LIT RFPREFIX_BRA ANSWERS.json ..."""
import sys, json
rl, rb = sys.argv[1], sys.argv[2]
arms = {"litolff": {a: json.load(open("%s.%s.json" % (rl, a))) for a in ("off", "on")},
        "brahms": {a: json.load(open("%s.%s.json" % (rb, a))) for a in ("off", "on")}}


def wrote(D, g):
    return ["%s %s %s%s v%s%s" % (h.get("kind"), h.get("pitch") or "", h.get("type"), "." * len((h.get("sub") or {}).get("dot") or []), h.get("voice"),
                                  " BLUE" if h.get("blue") else "") for h in D["hosts"] if h.get("rg") == g]


for f in sys.argv[3:]:
    A = json.load(open(f))
    print("##", f.split("/")[-1])
    for t in A["tiles"]:
        P = arms[t["plate"]]
        g = t["glyph"]
        print("tile %2d %-7s %-20s Sean: %-16s | OFF %s | ON %s | fate ON %s" % (t["tile"], t["plate"], g, t.get("sean"), wrote(P["off"], g),
                                                                              wrote(P["on"], g), P["on"]["fates"].get(g)))
