"""ROADMAP 2.254 round 2 blind tiles: one staff each, the whole hairpin and the notes above it, ONE thin orange box sized to the hairpin
at its own staff, nothing of ours drawn. Every item is a hairpin the EXPORTED ON file writes (its start / stop notes read off the written
MusicXML by `spans.py`); the key (what we wrote, start and stop) goes OUTSIDE the tile folder.

  * WORD:    Brahms p8, a hairpin inside a word's OCR box on the OFF arm (the word reader no longer reads it ON);
  * SPAN:    a written hairpin (seeded draw), its written start and stop in the key, to set beside Sean's answer;
  * CONTROL: a hairpin both arms write with the same start and stop.

    python3 benchmarks/hairpin-reach-2026-11/tiles_r2.py P8_WORK SUBSET_WORK out/print/2.254-r2-tiles   # key: out/print/2.254-r2-tiles-key.json
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spans as SPN  # noqa: E402
import tiles as T1  # noqa: E402
from tools.omr.staged.judged import iter_array  # noqa: E402

SEED = 22542
PLATE = "brahms"


def word_boxes(rec, page):
    out = []
    for it in iter_array(rec, "observations"):
        if it.get("quantity") == "direction_word" and int(it["subject"].split("/")[1]) == page:
            out.append({"text": it.get("value"), "box": (it.get("detail") or {}).get("bbox_page_px")})
    return [w for w in out if w["box"]]


def inside(a, b, share=0.5):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy >= share * max(1.0, (a[2] - a[0]) * (a[3] - a[1]))


def written_spans(work, arm):
    xml = work / ("%s.%s.musicxml" % (PLATE, arm))
    return {s["start"]["rg"]: s for s in SPN.spans(str(xml)) if s["start"]["rg"]}


def describe(s):
    if not s:
        return "no hairpin written here"
    ons = " ".join(("rest " if o["rest"] else "") + o["type"] for o in s["onsets"])
    return "%s written from the %s in bar %s to the %s in bar %s (onsets: %s)" % (
        s["kind"], s["start"]["type"], s["start"]["measure"], s["stop"]["type"], s["stop"]["measure"], ons)


def items_for(work, rng, n_span, words=False, control=False):
    on_rows = T1.wedge_rows(work / ("%s.on.gathered.record.json" % PLATE))
    sp_on, sp_off = written_spans(work, "on"), written_spans(work, "off")
    w_on = T1.written(work, PLATE, "on")
    out = []
    pairs = []
    for w in w_on:
        r = T1.match(w, on_rows)
        if r and w["rg"] in sp_on:
            pairs.append((w, r, sp_on[w["rg"]]))
    used = set()
    if words:
        pages = sorted({r["page"] for r in on_rows})
        for pg in pages:
            wb = word_boxes(work / ("%s.off.gathered.record.json" % PLATE), pg)
            for w, r, s in pairs:
                hit = next((x for x in wb if x["text"] and inside(r["box"], x["box"])), None)
                if hit and r["subject"] not in used:
                    used.add(r["subject"])
                    out.append(dict(role="WORD", read=r, note=w, wrote="OFF: the word reader's box '%s' %s held this hairpin. ON: %s"
                                    % (hit["text"], [round(v) for v in hit["box"]], describe(s)), span=s))
    if control:
        same = [(w, r, s) for w, r, s in pairs if w["rg"] in sp_off and sp_off[w["rg"]]["stop"]["rg"] == s["stop"]["rg"]
                and r["subject"] not in used]
        if same:
            w, r, s = rng.choice(same)
            used.add(r["subject"])
            out.append(dict(role="CONTROL", read=r, note=w, wrote="both arms: " + describe(s), span=s))
    pool = [(w, r, s) for w, r, s in pairs if r["subject"] not in used]
    for w, r, s in rng.sample(pool, min(n_span, len(pool))):
        out.append(dict(role="SPAN", read=r, note=w, wrote=("ON (OFF wrote the same)" if w["rg"] in sp_off else "ON (OFF: none)")
                        + ": " + describe(s), span=s))
    return out


def main(p8_work, sub_work, out):
    from PIL import Image, ImageDraw
    from tools.omr.preprocessing import render_page
    p8_work, sub_work, out = pathlib.Path(p8_work), pathlib.Path(sub_work), pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    rng = random.Random(SEED)
    items = items_for(p8_work, rng, 0, words=True)[:3]
    items += items_for(sub_work, rng, 11 - len(items), control=True)
    items = items[:12]
    rng.shuffle(items)
    cache, key, tiles, renders = {}, [], [], {}
    for n, it in enumerate(items, 1):
        r = it["read"]
        s = r["subject"].split("/")
        page = r["page"]
        top, bot, sp, _pws = T1.staff_box(PLATE, page, int(s[2]), int(s[3]), cache)
        if page not in renders:
            renders.clear()
            renders[page] = Image.fromarray(render_page(T1.C.EDITIONS[PLATE][0], page, dpi=600).rgb).convert("RGB")
        im = renders[page]
        b = r["box"]
        half = max((b[2] - b[0]) / 2 + 4 * sp, 8 * sp)          # both ends and the notes around them
        cx = (b[0] + b[2]) / 2
        x0, x1 = int(max(0, cx - half)), int(cx + half)
        y0, y1 = int(max(0, top - 2.5 * sp)), int(max(b[3], bot) + 1.5 * sp)
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([b[0] - 3 - x0, b[1] - 3 - y0, b[2] + 3 - x0, b[3] + 3 - y0], outline=T1.ORANGE, width=3)
        W = 640
        crop = crop.resize((W, max(1, int(W * crop.height / crop.width))))
        crop.save(out / ("tile_%02d.png" % n))
        tiles.append(crop)
        sp_ = it.get("span") or {}
        key.append(dict(tile=n, role=it["role"], plate=PLATE, page=page, subject=r["subject"], box=[round(v, 1) for v in b],
                        width_spaces=round((b[2] - b[0]) / sp, 2), read_kind=r.get("kind"), lane_wrote=it["wrote"],
                        start_note=(sp_.get("start") or {}).get("rg"), stop_note=(sp_.get("stop") or {}).get("rg"), crop_origin=[x0, y0]))
    cols = 3
    h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cols * 648 + 8, ((len(tiles) + cols - 1) // cols) * (h + 30) + 8), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, t in enumerate(tiles):
        x, y = 8 + (n % cols) * 648, 8 + (n // cols) * (h + 30)
        d.text((x, y + 2), "%d" % (n + 1), fill=(0, 0, 0))
        sheet.paste(t, (x, y + 18))
    sheet.save(out / "sheet.png")
    (out / "README.md").write_text(
        "# 2.254 round 2 hairpin tiles\n\nEach picture is one staff of a scanned Brahms page with ONE thin orange box and nothing else "
        "drawn. The box only says where to look.\n\n**Question, for every tile:** the mark in the box -- on which note does it start, "
        "and on which note does it stop? (If it is not a hairpin, say what it is.)\n\nAnswer by tile number.\n")
    (out.parent / (out.name + "-key.json")).write_text(json.dumps(key, indent=1, default=str))
    print("tiles", len(key), {k: sum(x["role"] == k for x in key) for k in ("WORD", "SPAN", "CONTROL")})


if __name__ == "__main__":
    main(*sys.argv[1:4])
