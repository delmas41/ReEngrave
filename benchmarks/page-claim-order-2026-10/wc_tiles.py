"""ROADMAP 2.221 word coverage: 12 blind tiles on the word / bracket claims. Read-only.

    python3 benchmarks/page-claim-order-2026-10/wc_tiles.py WORK_DIR OUT_DIR

6 NEW claims (an instrument name, a title, a brace, a tempo mark, a lone dynamic letter, a word), 4 random other claims, 2 still-unclaimed Brahms p0
truth marks. Marker: a thin orange BOX sized to the mark (one staff or one text line, never wider than the tile, no arrows). The tile is the mark
plus a margin; a mark taller than one staff or wider than 1100 px is not eligible. `key.json` is written to OUT_DIR, OUTSIDE tiles/.
The lone letter is the detector's `Q.DYNAMIC_LETTER` row no claim holds (the gather rule `claims.spell_letter_runs` -> `lone_letter`, GUESSED).
"""
from __future__ import annotations

import json
import pathlib
import random
import sys

import cv2
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
import m1_pagewide as M                                      # noqa: E402
import wc_measure as WM                                      # noqa: E402
from tools.omr.staged import lane_report as LR               # noqa: E402
from tools.omr.staged.judged import iter_array               # noqa: E402

MAX_H, MAX_W, MARGIN = 150, 1100, 110


def eligible(b):
    w, h = b[2] - b[0], b[3] - b[1]
    return 12 <= h <= MAX_H and 12 <= w <= MAX_W and w * h >= 400


def main(work, out):
    work, out = pathlib.Path(work), pathlib.Path(out)
    rng = random.Random(2221)
    claims = []
    for plate in ("brahms", "litolff"):
        for c in M._claims(work, plate)[0]:
            claims.append(dict(c, plate=plate, tag=("%s:%s:%s" % (c["owner"], c["source"], c["category"]))))
    cand = [c for c in claims if eligible(c["box"])]
    new = []

    def pick(pred, what):
        pool = [c for c in cand if pred(c) and c not in new]
        if pool:
            new.append(dict(rng.choice(pool), what=what))
        else:
            print("NO CANDIDATE for", what)

    pick(lambda c: c["source"] == "margin_label", "new: instrument name")
    pick(lambda c: c["source"] == "page_heading" and c["box"][2] - c["box"][0] > 60, "new: title")
    pick(lambda c: c["owner"] == "bracket" and c["box"][3] - c["box"][1] <= 450, "new: brace/bracket")
    pick(lambda c: (c.get("text") or "").startswith("Allegro") or c["category"] == "tempo", "new: tempo mark")
    pick(lambda c: c["source"] == "direction_word" and c["category"] != "tempo", "new: word")
    # the lone letter: a Brahms p0 detector letter no claim holds
    mine = [c for c in claims if c["plate"] == "brahms" and c["page"] == 0]
    lone = []
    for o in iter_array(work / "brahms.on.gathered.record.json", "observations"):
        if o.get("quantity") != "dynamic_letter" or LR.page_of(o.get("subject")) != 0:
            continue
        bb = (o.get("detail") or {}).get("bbox_page_px")
        if bb and not any(M._cover(bb, c["box"]) >= 0.5 for c in mine):
            lone.append(dict(plate="brahms", page=0, box=[float(v) for v in bb], text=(o["detail"] or {}).get("letter"), tag="lone_letter",
                             what="new: lone letter", id=o["id"], score=o.get("score")))
    if lone:
        new.append(rng.choice(lone))
    used = {c.get("id") for c in new}
    rest = [c for c in cand if c["id"] not in used and c["tag"] != "word:page_heading:heading" or False]
    rest = [c for c in cand if c["id"] not in used and c["box"][2] - c["box"][0] > 20]
    other = [dict(c, what="random claim") for c in rng.sample(rest, 12 - len(new) - 2)]   # 12 = new + random + 2 unclaimed
    s, _ = WM.score(work)
    unc = [u for u in s["unclaimed_list"] if eligible(u["rect"])]
    un = [dict(plate="brahms", page=0, box=u["rect"], tag="unclaimed truth " + u["kind"], what="unclaimed truth mark", text=u.get("text"), id=None)
          for u in rng.sample(unc, min(2, len(unc)))]
    picks = new + other + un
    rng.shuffle(picks)
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    pages, key, tiles = {}, [], []
    for i, c in enumerate(picks, 1):
        pk = (c["plate"], c["page"])
        if pk not in pages:
            pages[pk] = M._page(*pk)
        img = pages[pk]
        x0, y0, x1, y1 = (int(round(v)) for v in c["box"])
        ox, oy = max(0, x0 - MARGIN), max(0, y0 - MARGIN)
        crop = img[oy:y1 + MARGIN, ox:x1 + MARGIN].copy()
        cv2.rectangle(crop, (x0 - ox - 3, y0 - oy - 3), (x1 - ox + 3, y1 - oy + 3), (0, 140, 255), 2)
        cv2.imwrite(str(out / "tiles" / ("tile_%02d.png" % i)), crop)
        tiles.append(crop)
        key.append(dict(tile=i, what=c["what"], tag=c["tag"], plate=c["plate"], page=c["page"], box=c["box"], text=c.get("text"), id=c.get("id")))
    (out / "key.json").write_text(json.dumps(key, indent=1, default=str))
    (out / "tiles" / "README.md").write_text("# Word coverage tiles\n\nEach picture is a piece of a printed page with ONE thin orange box on it "
                                             "and nothing else drawn.\n\nQuestion, every tile: **What is the ink in the box?**\n\nAnswer by tile number.\n")
    cw, ch = 700, 420
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = np.full((rows * ch, cols * cw, 3), 255, np.uint8)
    for i, t in enumerate(tiles):
        s_ = min((cw - 8) / t.shape[1], (ch - 30) / t.shape[0], 1.0)
        t2 = cv2.resize(t, None, fx=s_, fy=s_, interpolation=cv2.INTER_AREA)
        r, c_ = divmod(i, cols)
        y, x = r * ch + 28, c_ * cw + 4
        sheet[y:y + t2.shape[0], x:x + t2.shape[1]] = t2
        cv2.putText(sheet, str(i + 1), (x + 4, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.imwrite(str(out / "tiles" / "sheet.png"), sheet)
    print("wrote", len(key), "tiles;", [k["what"] for k in key])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
