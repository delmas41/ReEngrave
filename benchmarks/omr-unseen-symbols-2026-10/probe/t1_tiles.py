"""ROADMAP 2.179 -- Sean's blind tiles: one blue box per tile and nothing else of ours. Tiles and key come from ONE run.

usage: python3 .../t1_tiles.py make SEED   |   python3 .../t1_tiles.py check
make: picks new stem-end head boxes that reached the file (written), half Litolff half Brahms (seeded), plus 3 controls (production
boxes no 2.179 code touched: a confident black head, a confident quarter/eighth rest, a confident hollow head), shuffles, writes
out/print/2.179-review/tile_NN.png + README.md, and the key to benchmarks/omr-unseen-symbols-2026-10/probe/data/tiles_key.json
(outside the tiles folder) with every tile's sha256. check: re-hashes the tiles against the key (names and hashes must match 1:1).
"""
import hashlib
import json
import os
import random
import sys

import cv2

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

TILES = "out/print/2.179-review"
KEY = "benchmarks/omr-unseen-symbols-2026-10/probe/data/tiles_key.json"
S = "/private/tmp/claude-501/s2179"
PDF = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                  "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                 "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
N_NEW = {"litolff": 5, "brahms": 4}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def check():
    key = json.load(open(KEY))
    names = sorted(f for f in os.listdir(TILES) if f.endswith(".png"))
    assert names == sorted(k["file"] for k in key["tiles"]), "tile names differ from the key"
    for k in key["tiles"]:
        assert sha(os.path.join(TILES, k["file"])) == k["sha256"], k["file"]
    print("ok", len(names), "tiles match the key")


def lines_of(rec):
    out = {}
    for o in rec["observations"]:
        if o["quantity"] == "staff_lines" and o["subject"].startswith("staff/"):
            out.setdefault(o["subject"][6:], o["value"])
    return out


def tile(img, box, ys, path):
    sp = (ys[-1] - ys[0]) / 4.0 if ys else (box[3] - box[1])
    cx = (box[0] + box[2]) / 2.0
    X0, X1 = int(max(0, cx - 5 * sp)), int(min(img.shape[1], cx + 5 * sp))
    top = min(ys[0], box[1]) if ys else box[1]
    bot = max(ys[-1], box[3]) if ys else box[3]
    Y0, Y1 = int(max(0, top - 2.5 * sp)), int(min(img.shape[0], bot + 2.5 * sp))
    crop = img[Y0:Y1, X0:X1].copy()
    k = 40.0 / sp
    crop = cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    pad = 4
    cv2.rectangle(crop, (int((box[0] - X0) * k) - pad, int((box[1] - Y0) * k) - pad),
                  (int((box[2] - X0) * k) + pad, int((box[3] - Y0) * k) + pad), (235, 111, 31), 2)
    cv2.imwrite(path, crop)


def make(seed):
    rng = random.Random(seed)
    picks = []
    for doc in ("litolff", "brahms"):
        fates = [f for f in json.load(open("%s/exp/%s.on2.new_glyphs.json" % (S, doc))) if f["placed"]]
        rng.shuffle(fates)
        for f in fates[:N_NEW[doc]]:
            picks.append(dict(doc=doc, kind="new", glyph=f["glyph"], box=f["detail"]["bbox_page_px"], read_from=f["detail"]["read_from"],
                              score=f["score"]))
    # controls: production boxes (reader `detector`), confident, from the OFF record of one plate each
    ctrl_want = [("litolff", "noteheadBlack", 0.8), ("brahms", "rest8th", 0.7), ("litolff", "noteheadHalf", 0.7)]
    recs = {}
    for doc, prefix, floor in ctrl_want:
        if doc not in recs:
            recs[doc] = load_record("%s/%s.base.record.json" % (S, doc))["record"]
        rows = [o for o in recs[doc]["observations"] if o["quantity"] == "glyph_box" and o.get("reader") == "detector"
                and str(o["value"][0]).startswith(prefix) and (o.get("score") or 0) >= floor
                and isinstance((o.get("detail") or {}).get("bbox_page_px"), list)]
        o = rng.choice(rows)
        picks.append(dict(doc=doc, kind="control", glyph=o["subject"], box=o["detail"]["bbox_page_px"], read_from=o["value"][0],
                          score=o.get("score")))
    rng.shuffle(picks)
    os.makedirs(TILES, exist_ok=True)
    for f in os.listdir(TILES):
        if f.endswith(".png"):
            os.remove(os.path.join(TILES, f))
    pages, lines = {}, {}
    for doc in PDF:
        if doc not in recs:
            recs[doc] = load_record("%s/%s.base.record.json" % (S, doc))["record"]
        lines[doc] = lines_of(recs[doc])
    key = []
    for i, p in enumerate(picks, 1):
        pg = int(p["glyph"].split("/")[1])
        if (p["doc"], pg) not in pages:
            pages[(p["doc"], pg)] = cv2.cvtColor(render_page(PDF[p["doc"]], pg).rgb, cv2.COLOR_RGB2BGR)
        st = "/".join(p["glyph"].split("/")[1:4])
        name = "tile_%02d.png" % i
        tile(pages[(p["doc"], pg)], p["box"], lines[p["doc"]].get(st), os.path.join(TILES, name))
        key.append(dict(p, file=name, sha256=sha(os.path.join(TILES, name))))
    open(os.path.join(TILES, "README.md"), "w").write(
        "# 2.179 review -- what is the symbol in the blue box?\n\n"
        "%d tiles, each a crop of the printed score (Beethoven 5 Litolff, or Brahms 1 Breitkopf) with ONE blue box drawn and nothing "
        "else of ours. Please say, for each tile, what the symbol in the blue box is (for example: a black notehead, a half-note "
        "head, a rest, part of a clef, an accidental, nothing). Answers go in `answers.json` beside this file.\n" % len(picks))
    os.makedirs(os.path.dirname(KEY), exist_ok=True)
    json.dump({"seed": seed, "tiles": key}, open(KEY, "w"), indent=1)
    print("wrote", len(key), "tiles")
    check()


if __name__ == "__main__":
    if sys.argv[1] == "make":
        make(int(sys.argv[2]))
    else:
        check()
