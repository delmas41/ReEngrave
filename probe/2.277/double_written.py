"""2.277: marks (copies by position, IoU >= 0.7) whose boxes are BOTH written as a note in the exported file. usage: double_written.py DUMP_ON.json SYMBOLS.json"""
import collections, json, sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from tools.omr.staged import claim_final as CF
D = json.load(open(sys.argv[1]))
S = json.load(open(sys.argv[2]))
marks = {}
for c in D["cf"].values():
    marks.update(c.get("marks") or {})
rows = {r["sub"]: r for r in D["rows"]}
hosts = collections.defaultdict(list)
for h in S["hosts"]:
    hosts[h["page"]].append(h)
written = set()
for k in marks:
    r = rows.get(k)
    if not r:
        continue
    pg = int(k.split("/")[1])
    for h in hosts[pg]:
        if h.get("rg") == k:
            written.add(k)
print("marks:", len(set(marks.values())), " boxes in marks:", len(marks), " boxes named as a host's glyph:", len(written))
dm = CF.double_marks(marks, written)
print("marks with more than one box named by a written host:", len(dm), dm[:5])
