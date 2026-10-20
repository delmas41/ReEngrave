"""2.167e probe 8 (Q4): heads whose standing duration is a WHOLE (written 4.0), split by the head's own ink (centre window of the three rasters)
and by stem state. A hollow whole has centre ink low and no stem. usage: e8_whole.py ALL.json OUT_LIST.json"""
import json
import sys
import collections

G = json.load(open(sys.argv[1]))
rows = []
for sub, g in G.items():
    if not str(g.get("cls", "")).startswith("notehead"):
        continue
    V = g.get("V", {})
    d = V.get("duration")
    if not d or d[0] != "deci" or not isinstance(d[2], dict) or d[2].get("written") != 4.0:
        continue
    nn = V.get("notehead_is_not_a_notehead")
    if nn and nn[2] is True:
        continue
    hs = V.get("head_stem", [None, None, None])
    win = g.get("ink_win") or {}
    center = win.get("center")
    ring = win.get("ring")
    stem_verdict = (hs[0] == "deci" and hs[1] in ("one_stem", "stem_by_side", "stem_by_reach", "stem_by_flush", "stem_by_one_per_head")) or hs[0] == "narr"
    rows.append(dict(sub=sub, cls=g["cls"], conf=g.get("conf"), bb=g.get("bb"), center=center, ring=ring, cross=g.get("cross"), reach=g.get("reach"),
                     dur_reason=d[1], hs=[hs[0], hs[1]], stem_verdict=stem_verdict, owner=(V.get("glyph_owner") or [None, None])[1]))
print("heads with a standing decided WHOLE (written 4.0):", len(rows))
for r in rows:
    r["filled"] = r["center"] is not None and r["center"] >= 0.6
    r["stem_ink"] = r["stem_verdict"] or (r["reach"] in ("up", "down", "both")) or r["cross"] is not None
tab = collections.Counter((("filled" if r["filled"] else "hollow/unread"), ("stem" if r["stem_ink"] else "no stem")) for r in rows)
for k, n in tab.most_common():
    print("  ", n, k)
print("INVENTED WHOLE (filled centre OR stem ink):", sum(1 for r in rows if r["filled"] or r["stem_ink"]))
print("  by duration reason:", collections.Counter(r["dur_reason"] for r in rows if r["filled"] or r["stem_ink"]).most_common())
print("  by detector class:", collections.Counter(r["cls"] for r in rows if r["filled"] or r["stem_ink"]).most_common())
print("  conf quartiles:", sorted(round(r["conf"], 2) for r in rows if r["filled"] or r["stem_ink"])[::max(1, len(rows) // 8)])
print("hollow and stem-free (a real whole):", sum(1 for r in rows if not r["filled"] and not r["stem_ink"]))
json.dump(rows, open(sys.argv[2], "w"))
