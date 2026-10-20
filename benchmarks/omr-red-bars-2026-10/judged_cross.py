"""usage: judged_cross.py JUDGED.json RED_ROWS.json -- which of Sean's judged tiles stand in a bar that is now written red
(held before). `judged score` compares VERDICTS, and this change is EXPORT-only, so the verdict statuses cannot move; what moves is
whether the judged note REACHES THE FILE. Prints, by status (right/wrong/narrowed/...), how many judged subjects were held and are
now in the file (in a red bar), split by whether the glyph's own status in the bar is READ or GUESSED."""
import collections
import json
import sys

j = json.load(open(sys.argv[1]))
red = json.load(open(sys.argv[2]))
in_red = {}
for b in red:
    for r in b["rows"]:
        if r.get("glyph"):
            in_red[str(r["glyph"])] = (r["status"], b["bar_key"])
tot = collections.Counter(t["status"] for t in j["tiles"])
now = collections.Counter()
by = collections.defaultdict(collections.Counter)
listing = []
for t in j["tiles"]:
    gs = t.get("subject")
    gs = gs if isinstance(gs, list) else [gs]
    g = next((x for x in gs if x in in_red), None)
    if g is not None:
        now[t["status"]] += 1
        by[t["status"]][in_red[g][0]] += 1
        listing.append((t["item"], t["tile"], g, t["status"], t.get("answer"), in_red[g][0]))
print("judged tiles by status (this doc):", dict(tot))
print("judged tiles whose glyph is in a RED bar (held before, in the file now):", dict(now))
for st, c in by.items():
    print("  ", st, dict(c))
for row in listing:
    print("  ", row)
