"""ROADMAP 2.180 -- OFF vs ON on the replayed exported files: file counts and every note whose standing duration changed,
with its direction. usage: diff_2_180.py REPLAYDIR DOC [OUT.json]"""
import collections
import json
import sys

RD, DOC = sys.argv[1], sys.argv[2]
off = json.load(open("%s/%s.off.json" % (RD, DOC)))
on = json.load(open("%s/%s.on.json" % (RD, DOC)))
print(DOC)
for k in ("xml", "bars_written_red", "red_rows", "notes_not_written_total", "guessed_by_rule", "bars_add_up"):
    print("  %-24s OFF %s\n  %-24s ON  %s" % (k, off.get(k), "", on.get(k)))
w0, w1 = off.get("written") or {}, on.get("written") or {}
print("  written.notes OFF %s ON %s" % (w0.get("notes"), w1.get("notes")))
nn0, nn1 = off.get("notes_not_written") or {}, on.get("notes_not_written") or {}
print("  notes_not_written moved:", {k: (nn0.get(k), nn1.get(k)) for k in set(nn0) | set(nn1) if nn0.get(k) != nn1.get(k)})
roles = collections.Counter()
for g in set(off["role"]) | set(on["role"]):
    a, b = off["role"].get(g), on["role"].get(g)
    if a != b:
        roles[(str(a and a[2]), str(b and b[2]))] += 1
print("  dot roles changed:", dict(roles))
ch = []
dirs = collections.Counter()
for g in set(off["dur"]) | set(on["dur"]):
    a, b = off["dur"].get(g), on["dur"].get(g)
    if a == b:
        continue
    wa = a[1] if a and a[0] == "deci" else None
    wb = b[1] if b and b[0] == "deci" else None
    if wa is not None and wb is not None:
        d = "longer" if wb > wa else ("shorter" if wb < wa else "same_written")
    else:
        d = "%s->%s" % (a and a[0], b and b[0])
    dirs[d] += 1
    ch.append(dict(glyph=g, off=a, on=b, direction=d))
print("  durations changed:", len(ch), dict(dirs))
for c in sorted(ch, key=lambda c: c["glyph"])[:60]:
    print("   ", c["glyph"], c["off"][:5] if c["off"] else None, "->", c["on"][:5] if c["on"] else None)
if len(sys.argv) > 3:
    json.dump(ch, open(sys.argv[3], "w"), default=str)
