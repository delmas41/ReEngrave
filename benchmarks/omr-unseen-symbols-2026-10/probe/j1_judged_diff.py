"""ROADMAP 2.179 -- which of Sean's judged tiles changed status between two `judged score --json` outputs (OFF, ON)."""
import json
import sys

a, b = (json.load(open(p)) for p in sys.argv[1:3])


def key(t):
    return (t.get("item"), t.get("tile"))


A = {key(t): t for t in a["tiles"]}
n = 0
for t in b["tiles"]:
    o = A.get(key(t))
    if o is not None and o.get("status") != t.get("status"):
        n += 1
        print(t.get("item"), t.get("tile"), t.get("subject"), o.get("status"), "->", t.get("status"), "| sean:", t.get("answer"),
              "| off:", str(o.get("ours"))[:80], "| on:", str(t.get("ours"))[:80])
print("changed", n)
