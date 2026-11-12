"""ROADMAP 2.303 PART 1 round 2: one blind tile per CHANGED PLACE of `OMR_UNREAD_WORD_SIBLING` (ADJUDICATE replay of the saved gather, OFF vs ON, on the frozen sample's pages).

    python3 benchmarks/dynamics-not-words-2026-11/tiles_303p1_r2.py OUT_DIR [N]

A place = a bar of a staff whose dynamic verdict or direction verdict differs between the arms. The thin orange box is sized to the MARK that changes: the letters of the dynamic that one
arm writes and the other does not, or the ink of the guessed / unread word. The tile is the staff above plus the text line, wide enough for the whole word, nothing else drawn. key.json
says what OFF and ON each write there (never on the tile).
"""
import json
import os
import pathlib
import random
import sys

import fitz
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
PAGES = {"litolff": {2, 4, 6, 8, 9, 10, 11, 16}, "brahms": {0, 4, 5, 8, 12, 14, 19, 25}}
UNIT = {"litolff": 15.75, "brahms": 32.0}


def build(plate, flag):
    os.environ["OMR_UNREAD_WORD_SIBLING"] = flag
    from tools.omr.staged import adjudicate, adjudicators  # noqa: F401
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Log
    sl = LIB / "_shared-records" / "lane-report-slices-20261029-night" / plate
    log = Log()
    for fn, kind in (("observations.jsonl", "obs"), ("abstentions.jsonl", "abs")):
        for line in open(sl / fn):
            r = json.loads(line)
            if r.get("quantity") not in ("dynamic_letter", "dynamic_letter_neighbours", "direction_word"):
                continue
            if not r["subject"].startswith("glyph/") or int(r["subject"].split("/")[1]) not in PAGES[plate]:
                continue
            sub, d = R.Subject.from_key(r["subject"]), dict(r.get("detail") or {})
            if kind == "obs":
                log.observe(sub, r["quantity"], r["value"], reader=r["reader"], frame=r["frame"], score=r.get("score"), **d)
            else:
                log.abstain(sub, r["quantity"], reader=r["reader"], frame=r["frame"], reason=r["reason"], **d)
    log.freeze()
    adjudicate.run(log)
    return log


def marks(log, plate):
    """{cell key: dict(dyn=text, dyn_boxes, word=text or None, word_box, kind)} for the bars with a dynamic verdict or a direction verdict."""
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Q
    box = {r.id: [float(v) for v in r.detail["bbox_page_px"]] for r in log.rows(Q.DYNAMIC_LETTER, R.Subject.from_key("document"), scope=R.Scope.SELF_AND_DESCENDANTS) if r.detail.get("bbox_page_px")}
    out = {}
    for v in log.verdicts(Q.DYNAMIC, R.Subject.from_key("document"), scope=R.Scope.SELF_AND_DESCENDANTS):
        d = v.detail or {}
        ws = d.get("words") or []
        txt = v.value if isinstance(v.value, list) else None
        if not ws:
            continue
        shown = " ".join(txt) if txt else "dyn."
        bx = [box[i] for w in ws for i in w.get("letters", ()) if i in box]
        out.setdefault(v.subject.to_key(), {})["dyn"] = (shown, bx)
    for v in log.verdicts(Q.DIRECTION, R.Subject.from_key("document"), scope=R.Scope.SELF_AND_DESCENDANTS):
        d = v.detail or {}
        for g in d.get("guessed_words") or ():
            out.setdefault(v.subject.to_key(), {})["word"] = ("guessed word: " + g["text"], [g["box"]])
        for g in d.get("unread_lines") or ():
            out.setdefault(v.subject.to_key(), {})["word"] = ("red mark: unread text", [g["box"]])
    return out


def union(bs):
    return [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]


def main():
    out, n = pathlib.Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 12
    items = []
    for plate in ("litolff", "brahms"):
        off, on = marks(build(plate, "0"), plate), marks(build(plate, "1"), plate)
        for cell in sorted(set(off) | set(on)):
            a, b = off.get(cell, {}), on.get(cell, {})
            for part in ("dyn", "word"):
                x, y = a.get(part), b.get(part)
                if (x and x[0]) == (y and y[0]):
                    continue
                boxes = (y or x)[1] if (y and y[1]) else (x[1] if x else [])
                if not boxes:
                    continue
                items.append(dict(plate=plate, cell=cell, part=part, off=x[0] if x else "nothing", on=y[0] if y else "nothing", box=union(boxes)))
    if os.environ.get("TILES_ONLY_PREFIX"):       # round 3: only the places that changed since the sheet Sean saw (e.g. `cell/4/0/10/`)
        items = [it for it in items if it["cell"].startswith(os.environ["TILES_ONLY_PREFIX"])]
        n = len(items)
    random.Random(2303).shuffle(items)
    sel = items[:n]
    # tiles 13-15: changed places not yet shown, preferring a dynamic ON removes with no word change in its bar (not visibly inside a guessed word)
    rest = items[n:]
    word_cells = {it["cell"] for it in items if it["part"] == "word"}
    pref = [it for it in rest if it["part"] == "dyn" and it["on"] == "nothing" and it["cell"] not in word_cells]
    extra = (pref + [it for it in rest if it not in pref])[:3]
    sel = sel + (extra if not os.environ.get("TILES_ONLY_PREFIX") else [])
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("tile_*.png"):
        old.unlink()
    from PIL import ImageFont
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
    except Exception:
        font = ImageFont.load_default()
    docs, key, tiles = {}, [], []
    TW, SPACES_ACROSS = 760, 70.0          # every tile: the same 70 staff spaces across, shown 760 px wide (same scale for all)
    for i, it in enumerate(sel, 1):
        page = int(it["cell"].split("/")[1])
        d = docs.setdefault(it["plate"], fitz.open(LIB / PDF[it["plate"]]))
        pix = d[page].get_pixmap(dpi=600)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        x0, y0, x1, y1 = it["box"]
        u = UNIT[it["plate"]]
        cx = (x0 + x1) / 2
        half = SPACES_ACROSS * u / 2
        c = (cx - half, max(0, y0 - 6.5 * u), cx + half, min(im.height, y1 + 1.2 * u))
        ci = tuple(int(round(v)) for v in c)
        t = Image.new("RGB", (ci[2] - ci[0], ci[3] - ci[1]), "white")      # off the page edge: white, same width
        t.paste(im.crop((max(0, ci[0]), max(0, ci[1]), min(im.width, ci[2]), min(im.height, ci[3]))), (max(0, -ci[0]), max(0, -ci[1])))
        ImageDraw.Draw(t).rectangle([x0 - c[0], y0 - c[1], x1 - c[0], y1 - c[1]], outline=(255, 140, 0), width=3)
        t = t.resize((TW, int(round(t.height * TW / t.width))), Image.LANCZOS)
        tiles.append(t)
        t.save(out / ("tile_%02d.png" % i))
        key.append(dict(tile=i, plate=it["plate"], page=page, cell=it["cell"], mark=it["part"], OFF_writes=it["off"], ON_writes=it["on"], box=it["box"]))
    cols, pad, lab = 4, 14, 44
    rows = (len(tiles) + cols - 1) // cols
    rh = [max(t.height for t in tiles[r * cols:(r + 1) * cols]) + lab for r in range(rows)]
    sheet = Image.new("RGB", (cols * (TW + pad) + pad, sum(rh) + pad * (rows + 1)), "white")
    dr = ImageDraw.Draw(sheet)
    y = pad
    for r in range(rows):
        for k, t in enumerate(tiles[r * cols:(r + 1) * cols]):
            x = pad + k * (TW + pad)
            dr.text((x, y), "Tile %d" % (r * cols + k + 1), fill=(0, 0, 0), font=font)
            sheet.paste(t, (x, y + lab))
        y += rh[r] + pad
    sheet.save(out / "sheet.png")
    json.dump(dict(n_changed_places=len(items), tiles=key), open(out / "key.json", "w"), indent=1)
    print(len(items), "changed places;", len(sel), "tiles ->", out)


main()
