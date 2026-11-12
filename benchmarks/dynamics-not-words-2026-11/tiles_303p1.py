"""ROADMAP 2.303 PART 1: blind tiles of every place `OMR_UNREAD_WORD_SIBLING` filed a guessed word or an unread line (read off the ON arm's saved verdicts, `lane_report` work dir).

    python3 benchmarks/dynamics-not-words-2026-11/tiles_303p1.py REPORT_DIR OUT_DIR [N]

One staff band per tile (the line's own staff above it and the line), a thin orange box round the line's ink union, nothing else drawn, wide enough for the whole word. The key (kind, text,
plate, page, staff/cell, what OFF wrote there) is in key.json, never on the tile. Pages are rendered from the PDF at 600 dpi.
"""
import json
import pathlib
import random
import re
import sys

import fitz
from PIL import Image, ImageDraw

LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}


def objects(txt, marker):
    pos = 0
    while True:
        i = txt.find(marker, pos)
        if i < 0:
            return
        s = txt.rfind('{"id"', 0, i)
        depth, j = 0, s
        while True:
            c = txt[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        yield json.loads(txt[s:j + 1])
        pos = j


def main():
    rep, out, n = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 12
    items = []
    import os
    os.environ["OMR_UNREAD_WORD_SIBLING"] = "1"
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    from tools.omr.staged import adjudicate, adjudicators  # noqa: F401
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Log, Q
    pages = {"litolff": {2, 6, 8, 9, 4, 10, 11, 16}, "brahms": {0, 4, 5, 8, 12, 14, 19, 25}}
    for plate in ("litolff", "brahms"):
        sl = LIB / "_shared-records" / "lane-report-slices-20261029-night" / plate
        log = Log()
        for fn, kind in (("observations.jsonl", "obs"), ("abstentions.jsonl", "abs")):
            for line in open(sl / fn):
                r = json.loads(line)
                if r.get("quantity") not in ("dynamic_letter", "dynamic_letter_neighbours", "direction_word"):
                    continue
                if not r["subject"].startswith("glyph/") or int(r["subject"].split("/")[1]) not in pages[plate]:
                    continue
                sub, d = R.Subject.from_key(r["subject"]), dict(r.get("detail") or {})
                if kind == "obs":
                    log.observe(sub, r["quantity"], r["value"], reader=r["reader"], frame=r["frame"], score=r.get("score"), **d)
                else:
                    log.abstain(sub, r["quantity"], reader=r["reader"], frame=r["frame"], reason=r["reason"], **d)
        log.freeze()
        adjudicate.run(log)
        for v in log.verdicts(Q.DIRECTION, R.Subject.from_key("document"), scope=R.Scope.SELF_AND_DESCENDANTS):
            d = v.detail or {}
            for kind, key in (("guessed word", "guessed_words"), ("unread line", "unread_lines")):
                for g in d.get(key) or ():
                    items.append(dict(plate=plate, subject=v.subject.to_key(), kind=kind, text=g.get("text"), box=g["box"], withheld=g.get("withheld"), why=g.get("why")))
    random.Random(2303).shuffle(items)
    sel = items[:n]
    out.mkdir(parents=True, exist_ok=True)
    docs, key, tiles = {}, [], []
    for i, it in enumerate(sel, 1):
        page = int(it["subject"].split("/")[1])
        d = docs.setdefault(it["plate"], fitz.open(LIB / PDF[it["plate"]]))
        pix = d[page].get_pixmap(dpi=600)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        x0, y0, x1, y1 = it["box"]
        u = 15.75 if it["plate"] == "litolff" else 32.0
        c = (max(0, x0 - 4 * u), max(0, y0 - 7 * u), min(im.width, x1 + 4 * u), min(im.height, y1 + 1.5 * u))
        t = im.crop(tuple(int(v) for v in c)).convert("RGB")
        dr = ImageDraw.Draw(t)
        dr.rectangle([x0 - c[0], y0 - c[1], x1 - c[0], y1 - c[1]], outline=(255, 140, 0), width=2)
        t.save(out / ("tile_%02d.png" % i))
        tiles.append(t)
        key.append(dict(tile=i, **{k: v for k, v in it.items() if k != "box"}, box=it["box"], page=page))
    W = max(t.width for t in tiles)
    sheet = Image.new("RGB", (W, sum(t.height + 6 for t in tiles)), "white")
    y = 0
    for t in tiles:
        sheet.paste(t, (0, y))
        y += t.height + 6
    sheet.save(out / "sheet.png")
    json.dump(dict(n_places=len(items), tiles=key), open(out / "key.json", "w"), indent=1)
    print(len(items), "places;", len(sel), "tiles ->", out)


main()
