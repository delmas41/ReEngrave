"""2.167e probe 9b (Q1): shared heads (one head, a stem each side): `unison_two_voices` (the rule fired) and `two_stems` heads whose stems stand flush left AND flush right
(the rule did NOT fire). What duration each head got; the number of voices = 1 by construction. usage: e9b_unison.py PLATE"""
import json
import sys
import collections

pl = sys.argv[1]
G = json.load(open("probe/2.167e/data/%s_all.json" % pl))
red = json.load(open("probe/2.167e/data/%s_red_rows.json" % pl))
redcells = {(b["page"], b["system"], b["staff"], b["cell"]) for b in red}
rows = []
for sub, g in G.items():
    if not str(g.get("cls", "")).startswith("notehead"):
        continue
    V = g.get("V", {})
    nn = V.get("notehead_is_not_a_notehead")
    if nn and nn[2] is True:
        continue
    hs = V.get("head_stem")
    if not hs or hs[0] != "narr":
        continue
    kind = None
    if hs[1] == "unison_two_voices":
        kind = "unison_two_voices"
    elif hs[1] == "two_stems":
        st = (hs[5] or {}).get("stems") or []
        fl = sorted(s[1] for s in st if s and s[1])
        if len(st) == 2 and fl == ["left", "right"]:
            kind = "two_stems_left_and_right"
        else:
            kind = "two_stems_other"
    if kind is None:
        continue
    d = V.get("duration") or [None, None, None]
    rows.append(dict(sub=sub, kind=kind, dur=d[:2], red=tuple(int(x) for x in sub.split("/")[1:5]) in redcells))
c = collections.Counter(r["kind"] for r in rows)
print(pl, "heads kept, head_stem narrowed:", dict(c))
for k in ("unison_two_voices", "two_stems_left_and_right", "two_stems_other"):
    rr = [r for r in rows if r["kind"] == k]
    print(" ", k, len(rr), "in red bars", sum(r["red"] for r in rr), "| duration:", collections.Counter((r["dur"][0], r["dur"][1]) for r in rr).most_common(6))
json.dump(rows, open("probe/2.167e/data/%s_unison2.json" % pl, "w"))
