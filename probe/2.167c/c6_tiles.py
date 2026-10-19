"""2.167c probe 6: the 10 side-by-side tiles for Sean (NOT blind) + index.json + README.md, one run; checks tiles == index.
LEFT original page crop of the bar (nothing drawn; ticks below mark where each event we read stands); RIGHT what we read.
usage: c6_tiles.py OUTDIR   (run from the repo root; reads scr/*_held.json, scr/*_sheets/sample.json made by c1/c4)"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
import c3_render as R   # noqa: E402

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

# (plate, index in that plate's seeded sample, cause family, plain cause sentence)
PICKS = [
    ("lit", 2, "b", "a note: the quarter-note head left of the rest was never boxed, so it is not in our count"),
    ("bra", 38, "b", "notes: two heads were boxed but refused (duration not decided), so only one eighth is counted"),
    ("lit", 19, "b", "a note: the first head on the staff was never boxed"),
    ("bra", 28, "c", "the flat sign before the chord was counted as a half note"),
    ("lit", 29, "c", "ink at the barline (the next bar's note) was counted as a half note in this bar"),
    ("bra", 43, "c", "one chord (two heads a second apart on one stem) was counted as two separate dotted halves"),
    ("bra", 23, "d", "both F2 notes have a flag on the page (eighths) but were read as quarters, with no blue mark"),
    ("bra", 30, "d", "both notes carry a dot on the page (dotted quarters); the dots were not read"),
    ("lit", 39, "d", "the first head belongs to the beamed group (an eighth) but was guessed a quarter"),
    ("bra", 5, "a", "looks like two oboe parts on one staff (stems up, stems down) added together as one; our reading, the least sure of the ten"),
]
FAM = {"a": "(a) two voices summed as one", "b": "(b) a note missing (never boxed / refused)",
       "c": "(c) an extra non-note or duplicate counted", "d": "(d) a wrong value"}
DATA = {}
for plate in ("lit", "bra"):
    rows = json.load(open("scr/%s_held.json" % ("lit" if plate == "lit" else "brahms")))
    S = json.load(open("scr/%s_sheets/sample.json" % plate))
    by = {(r["page"], r["system"], r["staff"], r["cell"]): r for r in rows}
    DATA[plate] = (by, S)

fo, fb, fs = R.font(15), R.font(17), R.font(13)


def wrap(text, width_px, font, d):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) > width_px and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


index = []
for n, (plate, si, fam, cause) in enumerate(PICKS, 1):
    by, S = DATA[plate]
    k = tuple(S[si])
    r = by[k]
    zoom = 2.4 if plate == "lit" else 1.0
    im, box, f = R.crop(plate, r, zoom)
    div = r["held"]["divisions"]
    evs = r["events"]
    wr = {h.get("glyph") for e in evs for h in e.get("heads", [])} | {(e["rest"] or {}).get("glyph") for e in evs}
    unread = [b for b in r.get("boxes", [])
              if b["sub"] not in wr and b.get("bbox") and b["fate"] in ("duration_narrowed", "chord_value_undecided", "ink_is_a_whole_rest")]
    # strip below the crop: tick + number per event, colour by status, aligned with the crop's x
    strip_h = 26
    left = Image.new("RGB", (im.width, im.height + strip_h), "white")
    left.paste(im, (0, 0))
    d = ImageDraw.Draw(left)
    for i, e in enumerate(evs):
        xs = [h["bbox_page"][0] + h["bbox_page"][2] / 2 for h in e.get("heads", []) if h.get("bbox_page")]
        if e["kind"] == "rest" and (e["rest"] or {}).get("bbox_page"):
            b = e["rest"]["bbox_page"]
            xs = [b[0] + b[2] / 2]
        if not xs:
            continue
        x = (sum(xs) / len(xs) - box[0]) * f
        col = R.BLUE if R.ev_status(e) == "G" else R.BLACK
        d.line([(x, im.height), (x, im.height + 6)], fill=col, width=2)
        d.text((x - 4, im.height + 7), str(i + 1), fill=col, font=fb)
    for b in unread:
        bb = b["bbox"]
        x = ((bb[0] + bb[2]) / 2 - box[0]) * f
        d.line([(x, im.height), (x, im.height + 6)], fill=R.RED, width=2)
        d.text((x - 4, im.height + 7), "x", fill=R.RED, font=fb)
    # right panel
    PW = 390
    right = Image.new("RGB", (PW, left.height), (250, 250, 250))
    d2 = ImageDraw.Draw(right)
    d2.text((8, 6), "What we read, left to right", fill=R.BLACK, font=fb)
    y = 32
    lines = R.events_text(r)
    for i, (t, col) in enumerate(lines):
        d2.text((8, y), t, fill=col, font=fo)
        y += 20
    for b in unread:
        d2.text((8, y), "x  head NOT written (%s)" % b["fate"].replace("_", " "), fill=R.RED, font=fo)
        y += 20
    total_q = sum(e["units"] for e in evs) / div
    want = r["held"]["want_quarters"]
    cap_lines = ["bar should hold %.4g quarters; we counted %.4g (voice 1: %s; voice 2: none read); cause: %s"
                 % (want, total_q, "+".join("%.4g" % (e["units"] / div) for e in evs), cause)]
    W = left.width + PW
    dm = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    wrapped = wrap(cap_lines[0], W - 20, fo, dm)
    head = "Tile %d   %s    %s p%d  system %d  staff %d  bar cell %d  (%s)" % (
        n, FAM[fam], "Beethoven 5 / Litolff" if plate == "lit" else "Brahms 1 / Breitkopf", r["page"], r["system"], r["staff"], r["cell"], r["name"])
    tile = Image.new("RGB", (W, 30 + left.height + 14 + 22 * len(wrapped) + 8), "white")
    td = ImageDraw.Draw(tile)
    td.text((8, 7), head, fill=R.BLACK, font=fb)
    tile.paste(left, (0, 30))
    tile.paste(right, (left.width, 30))
    yy = 30 + left.height + 8
    for ln in wrapped:
        td.text((10, yy), ln, fill=R.BLACK, font=fo)
        yy += 22
    fn = "tile_%02d.png" % n
    tile.save(os.path.join(OUT, fn))
    index.append(dict(tile=n, file=fn, plate=plate, page=r["page"], system=r["system"], staff=r["staff"], cell=r["cell"],
                      part=r["name"], family=fam, cause=cause, want_quarters=want, counted_quarters=round(total_q, 4),
                      events=[{"kind": e["kind"], "value": R.val(e), "quarters": e["units"] / div,
                               "pitch": "+".join(h.get("pitch", "?") for h in e["heads"]) or None,
                               "status": "GUESSED" if R.ev_status(e) == "G" else "READ",
                               "stem": e.get("stem_direction")} for e in evs],
                      not_written=[{"fate": b["fate"], "bbox_page": b["bbox"]} for b in unread]))

json.dump(index, open(os.path.join(OUT, "index.json"), "w"), indent=1)
# equality check: tiles on disk == index == PICKS
files = sorted(x for x in os.listdir(OUT) if x.startswith("tile_") and x.endswith(".png"))
assert files == [e["file"] for e in index] == ["tile_%02d.png" % i for i in range(1, len(PICKS) + 1)], (files,)
for e, p in zip(index, PICKS):
    assert e["family"] == p[2] and e["counted_quarters"] != e["want_quarters"]
print("OK", len(files), "tiles == index entries == picks")
