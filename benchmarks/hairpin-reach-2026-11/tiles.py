"""ROADMAP 2.254 blind tiles for Sean: one staff each, the whole wedge and the notes above it, ONE thin orange box sized to the wedge,
nothing else drawn. Key (what each tile is, what the lane wrote) goes OUTSIDE the tile folder.

Items, from a lane_report work dir (OFF/ON arms of OMR_HAIRPIN_REACH) and, optionally, a Brahms p8 ON gather:
  * GAINED: a wedge the ON file writes whose start note carries no wedge OFF (seeded draw over the gained);
  * SHORT: an ON CV read 1.6-3 sp long that the ON file does not write (a one-note wedge: hairpin or accent?);
  * WORD: on p8, a read beside a READ word whose word claim was shrunk off it (`wedges_left_out`);
  * CONTROL: a wedge both arms write.

    python3 benchmarks/hairpin-reach-2026-11/tiles.py WORKDIR out/print/2.254-tiles [P8_RECORD]   # key: out/print/2.254-tiles-key.json
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "page-claim-order-2026-11"))

import count as C  # noqa: E402
from tools.omr.staged import cell_map  # noqa: E402
from tools.omr.staged.gather import _spacing, _system_local  # noqa: E402
from tools.omr.staged.judged import iter_array  # noqa: E402

SEED = 2254
ORANGE = (255, 140, 0)


def wedge_rows(rec, pages=None):
    out = []
    for it in iter_array(rec, "observations"):
        if it.get("quantity") == "wedge_box" and it.get("reader") == "cv_hairpins":
            p = int(it["subject"].split("/")[1])
            if pages is None or p in pages:
                d = it["detail"]
                out.append({"subject": it["subject"], "page": p, "kind": it["value"], "box": d["bbox_page_px"],
                            "sp": d["staff_spacing_px"]})
    return out


def word_rows(rec, page):
    out = []
    for it in iter_array(rec, "observations"):
        if it.get("quantity") == "claimed_area" and (it.get("detail") or {}).get("wedges_left_out"):
            if int(it["subject"].split("/")[1]) == page:
                d = it["detail"]
                out.append({"text": d.get("text"), "word_box": d.get("word_box"), "area": it["value"], "wedges": d["wedges_left_out"]})
    return out


def written(work, plate, arm):
    d = json.loads((work / ("%s.%s.symbols.json" % (plate, arm))).read_text())
    return [x for x in d["loose"] + d["hosts"] if x.get("kind") == "wedge"]


def match(w, rows):
    """The CV read a written wedge's start note opens: same page and staff, the read's left end nearest the note (within 4 sp)."""
    sub = w["rg"].split("/")
    best = None
    for r in rows:
        rs = r["subject"].split("/")
        if r["page"] != w["page"] or rs[2:4] != sub[2:4]:
            continue
        dx = abs(r["box"][0] - w["cx"])
        if dx <= 4 * r["sp"] and (best is None or dx < best[0]):
            best = (dx, r)
    return best[1] if best else None


def staff_box(plate, page, system, staff, cache):
    if (plate, page) not in cache:
        (pws, _c), = cell_map.load_prepared(C.EDITIONS[plate][0], [page])
        local = _system_local(pws.staves)
        cache[(plate, page)] = (pws, {v: st for st in pws.staves for k, v in local.items() if k == st.staff_index})
    pws, by = cache[(plate, page)]
    st = by[(system, staff)]
    ys = list(st.line_ys)
    return min(ys), max(ys), _spacing(st), pws


def main(work, out, p8rec=None):
    from PIL import Image, ImageDraw
    work, out = pathlib.Path(work), pathlib.Path(out)
    tdir = out                                      # the tiles; the key goes BESIDE the folder: <out>-key.json
    tdir.mkdir(parents=True, exist_ok=True)
    for f in tdir.glob("*"):
        f.unlink()
    plate = "brahms"
    on_rows = wedge_rows(work / ("%s.on.gathered.record.json" % plate))
    off_rows = wedge_rows(work / ("%s.off.gathered.record.json" % plate))
    w_on, w_off = written(work, plate, "on"), written(work, plate, "off")
    off_rg = {w["rg"] for w in w_off}
    rng = random.Random(SEED)
    gained = [w for w in w_on if w["rg"] not in off_rg]
    both = [w for w in w_on if w["rg"] in off_rg]
    items = []
    for w in rng.sample(gained, min(8, len(gained))):
        r = match(w, on_rows)
        if r:
            items.append(dict(role="GAINED", read=r, note=w, wrote="ON writes a %s from this note (OFF: no wedge)" % w["value"]))
    for w in both[:1]:
        r = match(w, on_rows)
        if r:
            items.append(dict(role="CONTROL", read=r, note=w, wrote="both arms write a %s" % w["value"]))
    used = {i["read"]["subject"] for i in items}
    off_boxes = {tuple(round(v) for v in r["box"]) for r in off_rows}
    short = [r for r in on_rows if 1.6 <= (r["box"][2] - r["box"][0]) / r["sp"] < 3.0 and r["subject"] not in used
             and not any(match(w, [r]) for w in w_on)]
    for r in rng.sample(short, min(3, len(short))):
        items.append(dict(role="SHORT", read=r, wrote="ON reads a %.1f-space wedge here and writes nothing (one note: hairpin or accent?)%s"
                          % ((r["box"][2] - r["box"][0]) / r["sp"], "" if tuple(round(v) for v in r["box"]) not in off_boxes else
                             " (OFF read it too)")))
    if p8rec and len([i for i in items if i["role"] == "SHORT"]) < 3:
        # more one-note wedges from p8: the ON record's own wedge_anchor verdicts say what was done with each
        verdict = {}
        for it in iter_array(pathlib.Path(p8rec), "verdicts"):
            if it.get("quantity") == "wedge_anchor":
                verdict[it["subject"]] = (it.get("outcome"), it.get("reason"))
        pool = [r for r in wedge_rows(pathlib.Path(p8rec), {8}) if 1.6 <= (r["box"][2] - r["box"][0]) / r["sp"] < 3.0
                and verdict.get(r["subject"], ("", ""))[1] == "one_note_wedge"]
        for r in rng.sample(pool, min(3 - len([i for i in items if i["role"] == "SHORT"]), len(pool))):
            items.append(dict(role="SHORT", read=r, wrote="ON reads a %.1f-space wedge whose two tips bind to one note and abstains "
                              "one_note_wedge: nothing written (hairpin or accent?)" % ((r["box"][2] - r["box"][0]) / r["sp"])))
    if p8rec:
        p8w = word_rows(pathlib.Path(p8rec), 8)
        p8r = wedge_rows(pathlib.Path(p8rec), {8})
        for wd in p8w[:2]:
            b = wd["wedges"][0]
            r = next((x for x in p8r if abs(x["box"][0] - b[0]) < 10 and abs(x["box"][1] - b[1]) < 10), None)
            items.append(dict(role="WORD", read=r or {"subject": "?/8/?/?", "page": 8, "box": b, "sp": 27.8, "kind": "?"},
                              wrote="word claim '%s' shrunk from %s to %s; the wedge is left for the hairpin reader%s"
                                    % (wd["text"], wd["word_box"], wd["area"], "" if r else " (no CV read matched)")))
    items = items[:12]
    rng.shuffle(items)
    cache, key, tiles = {}, [], []
    renders = {}
    for n, it in enumerate(items, 1):
        r = it["read"]
        s = r["subject"].split("/")
        page = r["page"]
        top, bot, sp, pws = staff_box(plate, page, int(s[2]), int(s[3]), cache)
        if page not in renders:
            from tools.omr.preprocessing import render_page
            renders.clear()
            renders[page] = Image.fromarray(render_page(C.EDITIONS[plate][0], page, dpi=600).rgb).convert("RGB")
        im = renders[page]
        b = r["box"]
        half = max((b[2] - b[0]) / 2 + 4 * sp, 8 * sp)          # at least 16 spaces wide: the notes around a short wedge
        cx = (b[0] + b[2]) / 2
        x0, x1 = int(max(0, cx - half)), int(cx + half)
        y0, y1 = int(max(0, top - 2.5 * sp)), int(max(b[3], bot) + 1.5 * sp)
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([b[0] - 3 - x0, b[1] - 3 - y0, b[2] + 3 - x0, b[3] + 3 - y0], outline=ORANGE, width=3)
        W = 640
        crop = crop.resize((W, max(1, int(W * crop.height / crop.width))))
        crop.save(tdir / ("tile_%02d.png" % n))
        tiles.append(crop)
        key.append(dict(tile=n, role=it["role"], plate=plate, page=page, subject=r["subject"], box=[round(v, 1) for v in b],
                        width_spaces=round((b[2] - b[0]) / sp, 2), read_kind=r.get("kind"), lane_wrote=it["wrote"],
                        start_note=(it.get("note") or {}).get("rg"), crop_origin=[x0, y0]))
    cols = 3
    h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cols * 648 + 8, ((len(tiles) + cols - 1) // cols) * (h + 30) + 8), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, t in enumerate(tiles):
        x, y = 8 + (n % cols) * 648, 8 + (n // cols) * (h + 30)
        d.text((x, y + 2), "%d" % (n + 1), fill=(0, 0, 0))
        sheet.paste(t, (x, y + 18))
    sheet.save(tdir / "sheet.png")
    (tdir / "README.md").write_text(
        "# 2.254 hairpin tiles\n\nEach picture is one staff of a scanned Brahms page with ONE thin orange box and nothing else drawn. "
        "The box only says where to look.\n\n**Question, for every tile:** is the mark in the box a hairpin (crescendo or "
        "diminuendo), an accent, or something else? If a hairpin: which staff does it belong to, and on which notes does it start "
        "and stop?\n\nAnswer by tile number.\n")
    (out.parent / (out.name + "-key.json")).write_text(json.dumps(key, indent=1, default=str))
    print("tiles", len(key), {k: sum(x["role"] == k for x in key) for k in ("GAINED", "SHORT", "WORD", "CONTROL")})


if __name__ == "__main__":
    main(*sys.argv[1:4])
