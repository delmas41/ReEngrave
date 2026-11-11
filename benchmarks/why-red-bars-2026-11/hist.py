"""2.291: how far each red bar is from its meter. usage: hist.py CLASSIFIED.json -- per plate: delta (counted - want, quarters) histogram,
split by the rule's own reason (`why`), by meter reason, and unread-glyph presence."""
import collections
import json
import sys

rows = json.load(open(sys.argv[1]))
for plate in ("litolff", "brahms"):
    rs = [r for r in rows if r["plate"] == plate]
    if not rs:
        continue
    print(plate, len(rs), "red bars,", sum(r["notes"] for r in rs), "notes")
    print("  by why:", dict(collections.Counter(r["why"] for r in rs)))
    print("  by meter reason:", dict(collections.Counter(r["meter"] for r in rs)))
    h = collections.Counter(r["delta"] for r in rs)
    print("  delta histogram:", sorted(h.items()))
