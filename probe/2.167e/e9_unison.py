"""2.167e probe 9 (Q1): heads with two stems (head_stem narrowed two_stems / unison). What duration did they get, and was a flag box seen on each side?
usage: e9_unison.py ALL.json OUT.json"""
import json
import sys
import collections

G = json.load(open(sys.argv[1]))
HS = collections.Counter()
rows = []
cells = collections.defaultdict(list)
for sub, g in G.items():
    cells[tuple(sub.split("/")[1:5])].append(sub)
for sub, g in G.items():
    if not str(g.get("cls", "")).startswith("notehead"):
        continue
    V = g.get("V", {})
    hs = V.get("head_stem")
    if hs:
        HS[(hs[0], hs[1])] += 1
    if not hs or hs[1] not in ("two_stems", "unison_two_voices"):
        continue
    d = V.get("duration") or [None, None, None]
    sv = V.get("stem_value") or [None, None, None]
    own = V.get("glyph_owner") or [None] * 3
    # flags in the same cell near this head's x
    bb = g.get("bb") or [0, 0, 0, 0]
    fl = []
    for s2 in cells[tuple(sub.split("/")[1:5])]:
        g2 = G[s2]
        if str(g2.get("cls", "")).startswith("flag") and g2.get("bb"):
            b2 = g2["bb"]
            if b2[2] >= bb[0] - 10 and b2[0] <= bb[2] + 10:
                fl.append((g2["cls"], g2.get("conf"), (g2.get("V", {}).get("flag_is_not_a_flag") or [None, None, None])[2]))
    rows.append(dict(sub=sub, cls=g["cls"], conf=g.get("conf"), hs=hs, dur=d, sv=sv, flags=fl, ink=g.get("ink")))
print("head_stem outcomes on noteheads:", HS.most_common())
print("two_stems heads:", len(rows))
print("duration outcome/reason:", collections.Counter((r["dur"][0], r["dur"][1]) for r in rows).most_common())
print("stem_value outcome/reason:", collections.Counter((r["sv"][0], r["sv"][1]) for r in rows).most_common())
both = [r for r in rows if {"flag8thUp", "flag8thDown"} <= {f[0] for f in r["flags"] if f[2] is False} or
        (any(f[0].endswith("Up") for f in r["flags"] if f[2] is False) and any(f[0].endswith("Down") for f in r["flags"] if f[2] is False))]
print("two_stems heads with a kept flag box on BOTH sides (up and down):", len(both))
print("two_stems heads with ANY kept flag box near:", sum(1 for r in rows if any(f[2] is False for f in r["flags"])))
json.dump(rows, open(sys.argv[2], "w"))
