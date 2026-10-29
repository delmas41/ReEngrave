"""2.229: for each unread-empty bar, is there an unclaimed rest-sized blob stroke (length 1.0-1.7 spaces, thickness 0.5-1.0) in the cell?
A whole/half rest is a short fat bar; a notehead is a roughly round blob. Reads the slice's `stroke` observations (shared ink map, GATHER).
usage: blobs.py WORKDIR PLATE SLICEDIR"""
import json, collections, sys
work, plate, sl = sys.argv[1:4]
D = json.load(open("%s/%s.fates.json" % (work, plate)))
cells = {tuple(map(int, o["key"].split("/"))): o["kind"] for o in D["bars"]}
blobs = collections.defaultdict(list)
for l in open("%s/%s/observations.jsonl" % (sl, plate)):
    if '"quantity": "stroke"' not in l: continue
    o = json.loads(l)
    p = o["subject"].split("/")
    if p[0] != "glyph" or o["value"] != "blob": continue
    k = tuple(int(x) for x in p[1:5])
    if k not in cells: continue
    d = o["detail"]
    if 1.0 <= d["length_spaces"] <= 1.7 and 0.45 <= d["thickness_spaces"] <= 1.0:
        blobs[k].append((o["subject"].split("/")[5], d["length_spaces"], d["thickness_spaces"]))
c = collections.Counter(); tot = collections.Counter()
for k, kind in cells.items():
    tot[kind] += 1
    if blobs.get(k): c[kind] += 1
for kind in tot: print("%-45s bars %3d  with a rest-sized blob stroke %3d" % (kind, tot[kind], c[kind]))
print("total", sum(tot.values()), "with blob", sum(c.values()))
json.dump({"/".join(map(str, k)): v for k, v in blobs.items()}, open("%s/%s.blobs.json" % (work, plate), "w"))
