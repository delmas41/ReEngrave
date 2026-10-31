"""2.240 step 3 tiles for Sean: one staff a tile, ONE thin orange box sized to the mark, nothing else drawn; key.json BESIDE tiles/.

    PYTHONPATH=. python3 benchmarks/page-ledger-2026-10/s4/tiles.py rules OUT_DIR WRITTEN_OFF.record.json[:plate] ...   # distance / range_veto vs owner
    PYTHONPATH=. python3 benchmarks/page-ledger-2026-10/s4/tiles.py items OUT_DIR ITEMS.json                            # a prepared list

An item: {pdf, page, box [x0,y0,x1,y1] page px, staff (the staff drawn), ...anything for the key}.
"""
import collections
import json
import pathlib
import random
import sys

from tools.omr.staged import cell_map as CM
from tools.omr.staged import page_owner as PO
from tools.omr.staged.gather import _system_local
from tools.omr.staged.judged import iter_array

LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
README = ("# One plain question\n\nEach picture is a piece of a score page with ONE thin orange box on it and nothing else drawn. "
          "The box only says where to look.\n\n**For every tile:** what is the ink in the box, and which staff does it belong to -- "
          "the full five-line staff in the picture, or another one (above or below, partly shown or not shown)?\n\nAnswer by tile number.\n")


def cut(items, out_dir):
    from PIL import Image, ImageDraw
    out_dir = pathlib.Path(out_dir)
    tdir = out_dir / "tiles"
    tdir.mkdir(parents=True, exist_ok=True)
    for f in tdir.glob("*"):
        f.unlink()
    imgs, key, thumbs = {}, [], []
    for i, it in enumerate(items, 1):
        ik = (it["pdf"], it["page"])
        if ik not in imgs:
            (pws, cells), = CM.load_prepared(pathlib.Path(it["pdf"]), [it["page"]], root=CM.ROOT_DEFAULT)
            imgs[ik] = (Image.fromarray(pws.page.rgb).convert("RGB"), PO.staff_frames(cells, _system_local(pws.staves)))
        im, frames = imgs[ik]
        bb = [it["box"][0] - 2, it["box"][1] - 2, it["box"][2] + 2, it["box"][3] + 2]
        bar = PO.lines_at(frames, it["staff"], (bb[0] + bb[2]) / 2.0)
        u = bar.sp if bar else 16.0
        top, bot = (bar.ys[0], bar.ys[-1]) if bar else (bb[1], bb[3])
        cx = (bb[0] + bb[2]) / 2.0
        x0, x1 = max(0, int(min(cx - 6 * u, bb[0] - 1.5 * u))), int(max(cx + 6 * u, bb[2] + 1.5 * u))
        y0, y1 = max(0, int(min(top - 1.5 * u, bb[1] - 1.0 * u))), int(max(bot + 1.5 * u, bb[3] + 1.0 * u))
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([round(bb[0] - x0), round(bb[1] - y0), round(bb[2] - x0), round(bb[3] - y0)],
                                       outline=(255, 140, 0), width=max(2, int(u / 10)))
        crop = crop.resize((560, max(1, int(560 * crop.height / crop.width))))
        crop.save(tdir / ("tile_%02d.png" % i))
        thumbs.append(crop)
        key.append(dict(it, tile=i, crop_origin=[x0, y0]))
    (tdir / "README.md").write_text(README)
    (out_dir / "key.json").write_text(json.dumps(key, indent=1, default=str))
    # the sheet: every tile with its number, nothing of ours
    W = 560 * 3
    rows = [thumbs[i:i + 3] for i in range(0, len(thumbs), 3)]
    H = sum(max(t.height for t in r) + 28 for r in rows)
    sheet = Image.new("RGB", (W, H), "white")
    d, y = ImageDraw.Draw(sheet), 0
    for ri, r in enumerate(rows):
        for ci, t in enumerate(r):
            d.text((ci * 560 + 6, y + 6), str(ri * 3 + ci + 1), fill=(0, 0, 0))
            sheet.paste(t, (ci * 560, y + 24))
        y += max(t.height for t in r) + 28
    sheet.save(out_dir / "sheet.png")


def rules_pool(path, plate):
    """Every head where the OLD `glyph_owner` decided on `distance` or `range_veto` and the page owner (as filed) names another staff."""
    own, boxes, pdf = {}, {}, None
    for kind in ("observations", "abstentions"):
        for o in iter_array(path, kind):
            q = o.get("quantity")
            if q == "page_mark_owner" and kind == "observations":
                d = o.get("detail") or {}
                for m in d.get("members") or [o["subject"]]:
                    own[m] = (o.get("value"), d.get("status"), d.get("reason"), d.get("family"), d.get("candidates"))
            elif q == "glyph_box" and kind == "observations":
                bb = (o.get("detail") or {}).get("bbox_page_px")
                if bb:
                    boxes[o["subject"]] = bb
            elif q == "edition_info" or (q == "document_source"):
                pdf = (o.get("value") or {}).get("edition_path") if isinstance(o.get("value"), dict) else pdf
    out = []
    for v in iter_array(path, "verdicts"):
        if v.get("quantity") != "glyph_owner" or v.get("outcome") != "decided" or v.get("reason") not in ("distance", "range_veto"):
            continue
        s = v["subject"]
        po = own.get(s)
        if not po or po[3] != "head" or po[1] not in ("decided", "guessed") or po[0] == v.get("value") or s not in boxes:
            continue
        out.append(dict(plate=plate, kind="rules", rule=v["reason"], page=int(s.split("/")[1]), glyph=s, box=boxes[s],
                        old_owner=v.get("value"), page_owner=po[0], page_owner_status=po[1], page_owner_reason=po[2],
                        staff=v.get("value")))
    return out


def main():
    cmd, out_dir = sys.argv[1], sys.argv[2]
    if cmd == "items":
        cut(json.loads(pathlib.Path(sys.argv[3]).read_text()), out_dir)
        return
    pool = []
    pdfs = {"litolff": str(LIB / "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
            "brahms": str(LIB / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
    for spec in sys.argv[3:]:
        path, plate = spec.rsplit(":", 1)
        got = rules_pool(pathlib.Path(path), plate)
        for g in got:
            g["pdf"] = pdfs[plate]
        print(plate, len(got), dict(collections.Counter(g["rule"] for g in got)))
        pool += got
    # one per place (a mark's two copies are one place), stratified by rule and plate, seeded
    seen, uniq = set(), []
    for g in pool:
        k = (g["plate"], g["page"], round(g["box"][0] / 8), round(g["box"][1] / 8))
        if k not in seen:
            seen.add(k)
            uniq.append(g)
    rng = random.Random(22403)
    by = collections.defaultdict(list)
    for g in uniq:
        by[(g["rule"], g["plate"])].append(g)
    for v in by.values():
        rng.shuffle(v)
    pick = []
    while len(pick) < 12 and any(by.values()):
        for k in sorted(by):
            if by[k] and len(pick) < 12:
                pick.append(by[k].pop())
    rng.shuffle(pick)
    print("pool %d places, picked %d: %s" % (len(uniq), len(pick), dict(collections.Counter((g["rule"], g["plate"]) for g in pick))))
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(out_dir) / "pool.json").write_text(json.dumps(uniq, indent=1, default=str))
    cut(pick, out_dir)


if __name__ == "__main__":
    main()
