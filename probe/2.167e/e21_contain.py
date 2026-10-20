"""2.167e probe 21 (Q4): for every whole-valued head, how much of its box lies inside ANOTHER family's box in the same cell (rest*, timeSig*, accidental*, dynamic*, clef*,
key*, arpeggiato)? The existing duplicate gates ask IoU >= ~0.9; a FRAGMENT of a larger mark (the loop of an 8, the curl of a rest) has IoU ~0.3-0.5 but is mostly CONTAINED.
usage: e21_contain.py"""
import json
import collections

d = "probe/2.167e/data/"
for pl in ("lit", "bra"):
    G = json.load(open(d + "%s_all.json" % pl))
    cells = collections.defaultdict(list)
    for s, g in G.items():
        cells[tuple(s.split("/")[1:5])].append(s)
    rows = json.load(open(d + "%s_whole.json" % pl))
    out = collections.Counter()
    for r in rows:
        g = G[r["sub"]]
        a = g["bb"]
        area = max((a[2] - a[0]) * (a[3] - a[1]), 1.0)
        best = (0.0, None, None)
        for s2 in cells[tuple(r["sub"].split("/")[1:5])]:
            if s2 == r["sub"]:
                continue
            g2 = G[s2]
            c2 = str(g2.get("cls", ""))
            if not c2.startswith(("rest", "timeSig", "accidental", "dynamic", "clef", "key", "arpeggiato", "tuplet")) or not g2.get("bb"):
                continue
            b = g2["bb"]
            iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            frac = iw * ih / area
            kept = not (c2.startswith("rest") and (g2.get("V", {}).get("rest_is_not_a_rest", [0, 0, False])[2] is True))
            if frac > best[0]:
                best = (frac, c2, kept)
        band = "none" if best[0] < 0.05 else ("0.05-0.5" if best[0] < 0.5 else ">=0.5")
        out[(band, best[1] if best[0] >= 0.05 else None)] += 1
    print(pl, len(rows), "whole-valued heads; contained fraction of the head box inside another family's box in its cell:")
    for k, n in sorted(out.items(), key=lambda t: -t[1]):
        print("   ", n, k)
