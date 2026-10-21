"""ROADMAP 2.182 -- Sean's blind tiles: ONE blue box around a BAR on one staff, nothing else of ours. Tiles and key from ONE run.

usage: python3 .../t1_tiles.py make SEED ON.json RECORD.json DOC [CONTROLS_FROM.json]  |  python3 .../t1_tiles.py check
make: picks bars the ON arm split as two parts (`two_parts` in m1_replay's ON json, seeded), up to 9, plus 3 controls
(2 bars the ON arm leaves one line and that add up -- `one_voice_sums`; 1 bar main already writes as two voices by Sean's
rule 1 -- `two_voices_same_beat`), shuffles, writes out/print/2.182-review/tile_NN.png + README.md, and the key to
benchmarks/omr-two-parts-one-staff-2026-10/probe/data/tiles_key.json (outside the tiles folder) with every tile's sha256.
check: re-hashes the tiles against the key (names and hashes must match 1:1).
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

TILES = "out/print/2.182-review"
KEY = "benchmarks/omr-two-parts-one-staff-2026-10/probe/data/tiles_key.json"
PDF = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                  "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                 "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
N_SPLIT, N_ONE, N_RULE1 = 9, 2, 1


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def check():
    key = json.load(open(KEY))
    names = sorted(f for f in os.listdir(TILES) if f.endswith(".png"))
    assert names == sorted(k["file"] for k in key["tiles"]), "tile names differ from the key"
    for k in key["tiles"]:
        assert sha(os.path.join(TILES, k["file"])) == k["sha256"], k["file"]
    print("ok", len(names), "tiles match the key")


def tile(img, box, ys, path):
    """The bar's own cell box on its staff, drawn blue, with two staff-heights of context above and below."""
    sp = (ys[-1] - ys[0]) / 4.0 if ys else (box[3] - box[1]) / 4.0
    X0, X1 = int(max(0, box[0] - 3 * sp)), int(min(img.shape[1], box[2] + 3 * sp))
    top, bot = (ys[0], ys[-1]) if ys else (box[1], box[3])
    Y0, Y1 = int(max(0, top - 9 * sp)), int(min(img.shape[0], bot + 9 * sp))
    crop = img[Y0:Y1, X0:X1].copy()
    k = 30.0 / sp
    crop = cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
    y0, y1 = top - 3 * sp, bot + 3 * sp
    cv2.rectangle(crop, (int((box[0] - X0) * k), int((y0 - Y0) * k)), (int((box[2] - X0) * k), int((y1 - Y0) * k)),
                  (235, 111, 31), 3)
    cv2.imwrite(path, crop)


def make(seed, on_path, rec_path, doc, controls_from=None):
    rng = random.Random(seed)
    on = json.load(open(on_path))
    red = set(on["red_bars"])
    split = sorted(on["two_parts"])
    rng.shuffle(split)
    picks = [dict(doc=doc, kind="split", bar=b, reason=on["two_parts"][b]["reason"], red_on=b in red,
                  voices=on["two_parts"][b]["voices"], guessed=on["two_parts"][b]["guessed"]) for b in split[:N_SPLIT]]
    ctl = json.load(open(controls_from)) if controls_from else on
    ones = sorted(b for b, v in ctl["voices"].items() if v[1] == "one_voice_sums" and b not in red)
    rule1 = sorted(b for b, v in ctl["voices"].items() if v[1] == "two_voices_same_beat" and b not in red)
    rng.shuffle(ones)
    rng.shuffle(rule1)
    picks += [dict(doc=doc, kind="control_one_line", bar=b) for b in ones[:N_ONE]]
    picks += [dict(doc=doc, kind="control_rule_1_two_voices", bar=b) for b in rule1[:N_RULE1]]
    rng.shuffle(picks)
    rec = load_record(rec_path)["record"]
    cell_box, lines = {}, {}
    for o in rec["observations"]:
        if o["quantity"] == "cell_box" and o["subject"].startswith("cell/"):
            cell_box.setdefault(o["subject"][5:], o["value"])
        elif o["quantity"] == "staff_lines" and o["subject"].startswith("staff/"):
            lines.setdefault(o["subject"][6:], o["value"])
    del rec
    os.makedirs(TILES, exist_ok=True)
    for f in os.listdir(TILES):
        if f.endswith(".png"):
            os.remove(os.path.join(TILES, f))
    pages, key = {}, []
    for i, p in enumerate(picks, 1):
        pg = int(p["bar"].split("/")[0])
        if pg not in pages:
            pages.clear()
            pages[pg] = cv2.cvtColor(render_page(PDF[doc], pg).rgb, cv2.COLOR_RGB2BGR)
        st = "/".join(p["bar"].split("/")[:3])
        name = "tile_%02d.png" % i
        tile(pages[pg], cell_box[p["bar"]], lines.get(st), os.path.join(TILES, name))
        key.append(dict(p, file=name, sha256=sha(os.path.join(TILES, name))))
    open(os.path.join(TILES, "README.md"), "w").write(
        "# 2.182 review -- how many parts are in the bar in the blue box?\n\n"
        "%d tiles, each a crop of the printed score (Brahms 1, Breitkopf) with ONE blue box drawn around ONE BAR on ONE staff, "
        "and nothing else of ours. The blue box is only the place to look; it is not a reading.\n\n"
        "For each tile: **how many parts are in this bar, and what are the notes' values in each part (upper / lower)?** "
        "For example `2 parts: upper 8 8 8 rest8 / lower dotted half`, or `1 part: q q q`. Answers go in `answers.json` "
        "beside this file.\n" % len(picks))
    os.makedirs(os.path.dirname(KEY), exist_ok=True)
    json.dump({"seed": seed, "tiles": key}, open(KEY, "w"), indent=1)
    print("wrote", len(key), "tiles")
    check()


if __name__ == "__main__":
    if sys.argv[1] == "make":
        make(int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6] if len(sys.argv) > 6 else None)
    else:
        check()
