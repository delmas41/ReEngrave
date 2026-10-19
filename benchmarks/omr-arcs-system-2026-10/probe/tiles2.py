"""ROADMAP 2.166 round 2 -- blind tiles for the ties `tie_pair` now takes from the joined system arc (`paired_by_system_arc`),
into out/print/2.166-review-2/ (at most 10), the key apart in out/2.166/tiles2-key.json. ONE run of this one script writes
the tiles, the manifest and the key together and asserts they agree.

NOTHING of ours is drawn: the tile is the plain page between the two notes we paired (plus 2 spaces either side).
Question on every tile: "Do the first and last notes in this picture have ONE arc joining them (tie), a different arc
(slur) or none?"  Glyphs Sean has already judged are never asked again. 1 CONTROL: a tie the per-bar reading already
paired and the joined curve agrees with.
usage: tiles2.py   (reads out/2.166/ab_<doc>_p<page>.json and its .on.record.json)
"""
import json
import os
import sys

sys.path.insert(0, ".")
import cv2  # noqa: E402

from tools.omr import acceptance as ACC  # noqa: E402
from tools.omr.staged import pipeline  # noqa: E402

OUT = "out/print/2.166-review-2"
KEY = "out/2.166/tiles2-key.json"
PAGES = [("litolff", 3), ("litolff", 13), ("brahms", 1), ("brahms", 18)]
DOCS = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
SCALE = 3

man = json.load(open("benchmarks/acceptance/manifest.json"))
SEEN = set()
for t in json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]:
    for g in [t.get("subject")] + list(t.get("subjects") or []):
        if g:
            SEEN.add(str(g))

items = []
for doc, pg in PAGES:
    ab = json.load(open("out/2.166/ab_%s_p%d.json" % (doc, pg)))
    rec = json.load(open("out/2.166/ab_%s_p%d.on.record.json" % (doc, pg)))["record"]
    boxes = {g: b["detail"]["bbox_page_px"] for g, b in ab["boxes"].items()
             if (b.get("detail") or {}).get("bbox_page_px")}
    sysarcs = {}
    for a in ab["sysarc"]:
        for p in a["detail"]["pieces"]:
            sysarcs[p] = a
    tp = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "tie_pair" and v["outcome"] == "decided":
            tp[v["subject"]] = v
    for g, v in tp.items():
        if g in SEEN or v["value"]["start"] not in boxes or v["value"]["stop"] not in boxes:
            continue
        a = sysarcs.get(g)
        sp = (a or {}).get("detail", {}).get("space_page_px") or 15.0
        role = None
        if v["reason"] == "paired_by_system_arc":
            role = "new"
        elif (a and a["detail"]["anchor_left"] == v["value"]["start"] and a["detail"]["anchor_right"] == v["value"]["stop"]
              and not a["detail"]["cut_at_barline"]):
            role = "control"
        if role:
            items.append(dict(doc=doc, page=pg, glyph=g, role=role, start=v["value"]["start"], stop=v["value"]["stop"],
                              sp=sp, boxes=[boxes[v["value"]["start"]], boxes[v["value"]["stop"]]]))
new = [i for i in items if i["role"] == "new"]
ctl = [i for i in items if i["role"] == "control"]
chosen = new[:9] + ctl[:1]
chosen.sort(key=lambda i: (i["glyph"]))
pages = {}
for doc, pg in PAGES:
    pdf = str(ACC.resolve_path([d for d in man["documents"] if d["id"] == DOCS[doc]][0]["pdf"]))
    (pws, cells), = pipeline.prepare_pages(pdf, [pg])
    img = getattr(pws.page, "rgb", None)
    pages[(doc, pg)] = img if img is not None else pws.page.binary
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.startswith("tile_"):
        os.remove(os.path.join(OUT, f))
key, manifest = [], []
q = "Do the first and last notes in this picture have ONE arc joining them (a tie), a different arc (a slur), or none?"
for n, it in enumerate(chosen, 1):
    img = pages[(it["doc"], it["page"])]
    sp = it["sp"]
    b0, b1 = it["boxes"]
    x0 = int(max(0, min(b0[0], b1[0]) - 2 * sp))
    x1 = int(min(img.shape[1], max(b0[2], b1[2]) + 2 * sp))
    y0 = int(max(0, min(b0[1], b1[1]) - 3 * sp))
    y1 = int(min(img.shape[0], max(b0[3], b1[3]) + 3 * sp))
    crop = img[y0:y1, x0:x1]
    if crop.ndim == 2:
        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)
    cv2.putText(crop, "Tile %d" % n, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    f = "tile_%02d.png" % n
    cv2.imwrite(os.path.join(OUT, f), crop)
    manifest.append(dict(n=n, file=f, question=q))
    key.append(dict(n=n, file=f, page_crop=[x0, y0, x1, y1], **{k: v for k, v in it.items() if k != "boxes"}))
json.dump(dict(colours="Nothing is drawn on any tile: each is the plain page.", tiles=manifest),
          open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
if not os.path.exists(os.path.join(OUT, "answers.json")):
    json.dump({}, open(os.path.join(OUT, "answers.json"), "w"))
json.dump(dict(tiles=key), open(KEY, "w"), indent=1)
files = sorted(f for f in os.listdir(OUT) if f.startswith("tile_"))
assert files == [m["file"] for m in manifest] == [k["file"] for k in key], (files, len(manifest), len(key))
print("tiles", len(chosen), "new", sum(1 for c in chosen if c["role"] == "new"), "control",
      sum(1 for c in chosen if c["role"] == "control"), "of new candidates", len(new))
