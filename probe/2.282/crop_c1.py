"""2.282 rule-7 look: crop N contested pieces (kind a / b) from c1 rows. Orange = the stroke, blue = the accidental box, green = the head/ledger box.
My own look, not evidence. usage: crop_c1.py PLATE BASE_DIR C1.json PAGES KIND(a|b) N SEED OUT.png"""
import json
import random
import re
import subprocess
import sys

sys.path.insert(0, "probe/2.282")
import crop as C                                        # noqa: E402

plate, base, c1, pages, kind, n, seed, out = sys.argv[1:9]
pages = {int(x) for x in pages.split(",")}
skip = {"key_signature", "clef", "meter", "leading_column", "barline", "word", "bracket"}
rows = []
for r in json.load(open(c1)):
    if r["page"] not in pages or set(r["fams"]) & skip:
        continue
    f = set(r["fams"])
    blob = " ".join(c[4] or "" for c in r["cands"])
    if kind == "b" and f & {"head", "ledger"}:
        rows.append(r)
    elif kind == "a" and ("acc_stem" in blob or "longer_than_an_acc_stem" in blob or "kind=vertical" in blob) and (
            r["state"] in ("refused_claims", "contested") or (r["state"] in ("decided", "merged") and r["owner"] not in ("accidental", None))):
        rows.append(r)
random.Random(int(seed)).shuffle(rows)
rows = rows[:int(n)]
need_s = {(r["cell"], r["ordinal"]) for r in rows}
need_g = {c[0] for r in rows for c in r["cands"]}
sbox, gbox, sp = {}, {}, {}
for line in open(base + "/observations.jsonl"):
    if '"stroke"' in line or '"glyph_box"' in line or '"cell_staff_space"' in line:
        o = json.loads(line)
        q, sub = o["quantity"], o["subject"]
        if q == "stroke" and sub.startswith("glyph/"):
            cell = "cell/" + sub[6:].rsplit("/", 1)[0]
            k = (cell, int(sub.rsplit("/", 1)[1]) - 375000)
            if k in need_s:
                sbox[k] = o["detail"].get("bbox_page_px")
        elif q == "glyph_box" and sub in need_g:
            gbox[sub] = (o["detail"] or {}).get("bbox_page_px")
items = []
for r in rows:
    sb = sbox.get((r["cell"], r["ordinal"]))
    if not sb:
        continue
    bx = []
    for c in r["cands"]:
        b = gbox.get(c[0])
        if b:
            bx.append((b, (0, 90, 255) if c[1] == "accidental" else (0, 170, 60)))
    spp = {"litolff": 15.75, "brahms": 27.2}[plate]
    items.append(dict(plate=plate, page=r["page"], box=sb, sp=spp, boxes=[[b, list(c)] for b, c in bx],
                      label="%s%s %s/%s %s" % (plate[0].upper(), r["cell"][5:], r["state"], r["owner"], "+".join(r["fams"]))))
json.dump(items, open(out + ".json", "w"))
subprocess.run([sys.executable, "probe/2.282/crop.py", out, out + ".json"], check=True)
