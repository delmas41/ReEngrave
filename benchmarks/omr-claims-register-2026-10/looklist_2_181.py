"""2.181: the glyphs the register CHANGED (from compare_2_181's DOC.diff.json), with their page boxes, as a look-list for crops.
usage: looklist_2_181.py DOC OUTDIR SLICEDIR OUT.json"""
import json
import sys

DOC, OUT, SD, DEST = sys.argv[1:5]
d = json.load(open("%s/%s.diff.json" % (OUT, DOC)))
want = {}
for g, v in d["new_refused"].items():
    want[g] = "new_refused:" + str(v[1])
for g, v in d["rests_new"].items():
    want[g] = "rest_new_refused:" + str(v[1])
for g, v in d["gone_refused"].items():
    want[g] = "no_longer_refused:" + str(v[1])
for g, v in d["rests_restored"].items():
    want[g] = "rest_restored:" + str(v[1])
for g, v in d["newly_narrowed"].items():
    want[g] = "newly_narrowed:" + str(v[0]) + ":" + str((v[1] or {}).get("why"))
for g, v in d["rest_narrowed"].items():
    want.setdefault(g, "rest_narrowed:" + str(v[0]) + ":" + str((v[1] or {}).get("why")))
pages = sorted({int(g.split("/")[1]) for g in want})
out = []
sp_of = {}
for pg in pages:
    for line in open("%s/%s/p%02d.observations.jsonl" % (SD, DOC, pg)):
        if '"glyph_box"' not in line and '"staff_spacing"' not in line:
            continue
        o = json.loads(line)
        if o["quantity"] == "staff_spacing":
            sp_of["/".join(o["subject"].split("/")[1:])] = o["value"]
        elif o["subject"] in want:
            out.append(dict(g=o["subject"], cls=o["value"][0], pb=o["detail"]["bbox_page_px"], reason=want[o["subject"]]))
for r in out:
    r["sp"] = sp_of.get("/".join(r["g"].split("/")[1:4]), 25)
json.dump(out, open(DEST, "w"), indent=0)
print(len(out), "of", len(want))
