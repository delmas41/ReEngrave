"""ROADMAP 2.153 -- the attribution table: each judged VALUE error (out/2.153/targets.json, 31 tiles) with Sean's value, the reading
at the time the tile was cut, the reading of main's CURRENT defaults replayed over the same GATHER rows ('main'), and the same with
2.148's `interior_white` row injected from the page raster ('main+iw'; probe, see inject_iw_2_153.py), then a class by what
Sean's value says the cell had that we read differently. Class rules (printed with the table):
  head fill   Sean's value is a half or longer (>= 2 quarters) and we read shorter (black head for a hollow one)
  dot         the undotted value is right and the dot differs
  beams high  we read a value SHORTER than Sean's with a beam level counted (levels > 0)
  mark missed we read a value LONGER than Sean's (a flag/beam not read)
  dot not read  the head value is right and Sean's dot is not in ours
usage: attr_table_2_153.py"""
import collections
import json

T = json.load(open("out/2.153/targets.json"))
TAGS = {"litolff": ("out/2.153/tags_litolff_base1.json", "out/2.153/tags_litolff_iw.json"),
        "brahms_p0p3": ("out/2.153/tags_brahms_p0p3_base1.json", None),
        "brahms": ("out/2.153/tags_brahms_base1.json", "out/2.153/tags_brahms_iw.json")}
tile_rows = {(r["item"], r["n"]): r for r in json.load(open("benchmarks/gather-zoom-layers-2026-10/probe/out/tile_rows.json"))}
BEATS = {"1": 4.0, "2": 2.0, "4": 1.0, "8": 0.5, "16": 0.25, "32": 0.125, "dot 2": 3.0, "dot 4": 1.5, "dot 8": 0.75,
         "dotted quarter": 1.5}


def shown(x):
    if x is None or x.get("missing"):
        return "?"
    return "%s%s" % (x["ours"] if x["outcome"] == "decided" else "{%s}" % ",".join(str(c) for c in (x["cands"] or [])),
                     "" if x["outcome"] == "decided" else "n")


def ok(x, s):
    if x is None or x.get("missing"):
        return None
    if x["outcome"] == "decided":
        return x["ours"] is not None and abs(x["ours"] - s) < 1e-6
    return any(c is not None and abs(c - s) < 1e-6 for c in (x["cands"] or []))


rows = []
for doc, tl in T.items():
    base = json.load(open(TAGS[doc][0]))["base"]
    iw = json.load(open(TAGS[doc][1]))["on"] if TAGS[doc][1] else None
    for t in tl:
        s = BEATS.get(str(t["sean"]).strip().lower())
        x = base.get(t["glyph"])
        y = iw.get(t["glyph"]) if iw else None
        stored = tile_rows[(t["item"], t["n"])]["dur"]
        st = stored[1]["written"] if stored[0] == "decided" and stored[1] else "n"
        ours = x["ours"] if x and x["outcome"] == "decided" else None
        f = (x or {}).get("feats") or {}
        if s is None or ours is None and not (x and x["outcome"] == "narrowed"):
            cls = "other"
        elif s >= 2.0 and (ours is None or ours < 2.0 or (ours is not None and abs(ours - s) > 1e-6 and abs(ours - s) in (1.0, 2.0))):
            cls = "head fill"
        elif ours is not None and ours < s and (f.get("levels_certain") or f.get("flag_levels")):
            cls = "beams high"
        elif ours is not None and ours > s:
            cls = "mark missed"
        elif ours is not None and abs(ours - s) < 1e-6:
            cls = "right now (decided)"
        elif ours is not None and abs(ours * 1.5 - s) < 1e-6:
            cls = "dot not read"
        elif ours is None and ok(x, s):
            cls = "right now (narrowed, holds it)"
        else:
            cls = "other"
        # the one that fixes it: iw right -> 2.148 pending re-gather
        rows.append(dict(doc=doc, item=t["item"], n=t["n"], sean=t["sean"], at_tile=st, main=shown(x), main_ok=ok(x, s),
                         main_iw=shown(y) if y else "-", iw_ok=ok(y, s) if y else None, cls=cls,
                         reason=(x or {}).get("reason"), first=(x or {}).get("first_reason")))
for r in rows:
    print("%-11s %-6s %-3s sean %-6s tile-time %-5s main %-14s %-6s | +iw %-14s %-6s | %-22s %s/%s" % (
        r["doc"], r["item"], r["n"], r["sean"], r["at_tile"], r["main"], r["main_ok"], r["main_iw"], r["iw_ok"], r["cls"], r["first"], r["reason"]))
c = collections.Counter(r["cls"] for r in rows)
print(dict(c))
print("fixed by main's defaults over the night rows (decided right or narrowed holding):", sum(1 for r in rows if r["main_ok"]))
print("fixed once 2.148's row exists (iw):", sum(1 for r in rows if r["iw_ok"]), "of", sum(1 for r in rows if r["iw_ok"] is not None))
json.dump(rows, open("out/2.153/attr_table.json", "w"), indent=0)
