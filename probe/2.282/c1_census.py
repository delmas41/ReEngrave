"""2.282 step 1 (STAGED, read-only): every stroke whose candidate owners (stroke_owner verdict detail.strokes) include an ACCIDENTAL box, by the other
families that also claim it and by who got it. Reads a re-adjudicated slice (probe/2.282/readj.py output). No decision changes.

usage: c1_census.py SLICE_DIR PLATE OUT.json [pages comma list]
"""
import collections
import json
import sys

d, plate, out = sys.argv[1:4]
pages = {int(x) for x in sys.argv[4].split(",")} if len(sys.argv) > 4 else None

rows = []
fam_sets = collections.Counter()
for l in open(d + "/verdicts.jsonl"):
    if '"stroke_owner"' not in l:
        continue
    v = json.loads(l)
    if v["quantity"] != "stroke_owner":
        continue
    sub = v["subject"]                       # cell/p/s/st/c
    page = int(sub.split("/")[1])
    if pages is not None and page not in pages:
        continue
    for o, e in ((v.get("detail") or {}).get("strokes") or {}).items():
        state, fam, owners, by, cands = e
        fams = sorted({c[1] for c in cands})
        if "accidental" not in fams:
            continue
        key = (state, fam, "+".join(fams))
        fam_sets[key] += 1
        rows.append(dict(cell=sub, page=page, ordinal=int(o), state=state, owner=fam, by=by, fams=fams,
                         cands=[[c[0], c[1], c[2], c[3], c[4][:60]] for c in cands]))
json.dump(rows, open(out, "w"))
print(plate, "strokes with an accidental box among the claimants:", len(rows))
bp = collections.Counter(r["page"] for r in rows)
print("per page", dict(sorted(bp.items())))
for k, n in sorted(fam_sets.items(), key=lambda x: -x[1]):
    print("  state=%-15s owner=%-10s claimants=%s : %d" % (k[0], k[1], k[2], n))
