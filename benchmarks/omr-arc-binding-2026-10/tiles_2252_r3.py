"""ROADMAP 2.252 r3 -- 12 blind tiles of unison ties, cut from the page at the heads the ON file wrote (STAGED EXPORT).

Each tile: one staff, ONE thin orange box on the head, nothing of ours drawn, wide enough (+-11 spaces) for both ends
of each arc. The key (outside the tile folder) holds what the OFF and ON files wrote there (per voice: tie types).

    python3 benchmarks/omr-arc-binding-2026-10/tiles_2252_r3.py OUT_DIR KEY.json \
        plate:record:census_off.json:census_on.json:off.musicxml:on.musicxml ...
"""
from __future__ import annotations

import collections
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import lane_report as L                      # noqa: E402
from tools.omr.staged.record_io import load_record                  # noqa: E402

import importlib.util                                                # noqa: E402
_spec = importlib.util.spec_from_file_location("unison_census", pathlib.Path(__file__).with_name("unison_census.py"))
UC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(UC)

ORANGE = (255, 140, 0)
README = """# 2.252 round 3 tiles -- unisons

Each picture is a piece of a scanned score page, one staff, with ONE thin orange box and nothing else drawn. The box
only says where to look; it says nothing about what we read. Each picture is wide enough to show the notes before and
after the box and the whole of every arc between them.

**Question, for every tile:** how many notes are in the orange box (one head with a stem each way counts as two), and
is each of them tied (the same note held) to the note before it, the note after it, both, or neither? Where there
are two, say which tie belongs to which (the upper one / the lower one).

Answer by tile number.
"""


def _boxes(rec):
    out = {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                out[o["subject"]] = bp
    return out


def main() -> None:
    out_dir, key_path = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    cands, controls = [], []
    for spec in sys.argv[3:]:
        plate, recp, c_off, c_on, x_off, x_on = spec.split(":")
        rec = load_record(recp)
        rec = rec["record"] if "record" in rec else rec
        boxes = _boxes(rec)
        w_off, w_on = UC.written_by_glyph(pathlib.Path(x_off).read_text()), UC.written_by_glyph(pathlib.Path(x_on).read_text())
        s_off = {(s["mark"], s["side"], s["dirn"]): s for s in json.load(open(c_off))["slots"]}
        s_on = {(s["mark"], s["side"], s["dirn"]): s for s in json.load(open(c_on))["slots"]}
        heads = collections.defaultdict(list)
        for k, s in s_on.items():
            heads[k[0]].append((k, s, s_off.get(k)))
        for h, slots in sorted(heads.items()):
            if h not in boxes or not w_on.get(h):
                continue
            changed = any((s["cause"] != (o or {}).get("cause")) for _k, s, o in slots)
            item = dict(plate=plate, page=int(h.split("/")[1]), rg=h, box=boxes[h], changed=changed,
                        slots_on={"%s %s" % (k[1], k[2]): s["cause"] for k, s, _o in slots},
                        slots_off={"%s %s" % (k[1], k[2]): (o or {}).get("cause") for k, _s, o in slots},
                        written=dict(off=w_off.get(h, []), on=w_on.get(h, [])))
            cands.append(item)
        uni = set(heads)
        # a changed tie START at a head that is not a unison (the mark-group move): a case of its own
        for g, notes in w_on.items():
            if g in uni or g not in boxes:
                continue
            if any("start" in n["tie"] for n in notes) and not any("start" in n["tie"] for n in w_off.get(g, [])):
                cands.append(dict(plate=plate, page=int(g.split("/")[1]), rg=g, box=boxes[g], changed=True,
                                  nonunison=True, written=dict(off=w_off.get(g, []), on=notes)))
        # controls: a tied note that is NOT a unison, written the same in both files (a tie start in both)
        for g, notes in w_on.items():
            if g in uni or g not in boxes or len(notes) != 1 or "start" not in notes[0]["tie"]:
                continue
            if w_off.get(g) == notes:
                controls.append(dict(plate=plate, page=int(g.split("/")[1]), rg=g, box=boxes[g], changed=False,
                                     written=dict(off=w_off[g], on=notes), role="control"))
    rng = random.Random(22523)
    ch = [c for c in cands if c["changed"]]
    rest = [c for c in cands if not c["changed"]]
    pick = ch[:10] if len(ch) >= 10 else ch + rng.sample(rest, min(len(rest), 10 - len(ch)))
    for p in pick:
        p["role"] = ("changed_not_unison" if p.get("nonunison") else
                     "unison_changed" if p["changed"] else "unison_unchanged")
    pick += rng.sample(controls, min(2, len(controls)))
    rng.shuffle(pick)
    cut(pick, out_dir, key_path)


def cut(items, out_dir: pathlib.Path, key_path: pathlib.Path) -> None:
    from PIL import Image, ImageDraw
    from tools.omr.preprocessing import render_page
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*"):
        f.unlink()
    W, tiles, key, cache = 1100, [], [], {}
    for n, it in enumerate(items, 1):
        plate, pg = it["plate"], it["page"]
        if (plate, pg) not in cache:
            cache.clear()
            cache[(plate, pg)] = Image.fromarray(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
        im = cache[(plate, pg)]
        u = L.PLATES[plate]["unit"]
        b = it["box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        x0, y0, x1, y1 = max(0, int(cx - 11 * u)), max(0, int(cy - 6 * u)), int(cx + 11 * u), int(cy + 6 * u)
        crop = im.crop((x0, y0, x1, y1)).copy()
        bb = [b[0] - 2 - x0, b[1] - 2 - y0, b[2] + 2 - x0, b[3] + 2 - y0]
        ImageDraw.Draw(crop).rectangle([round(v) for v in bb], outline=ORANGE, width=max(2, int(u / 8)))
        crop = crop.resize((W, int(W * crop.height / crop.width)))
        crop.save(out_dir / ("tile_%02d.png" % n))
        tiles.append(crop)
        key.append(dict(it, tile=n, crop_box=[x0, y0, x1, y1]))
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    h = max((t.height for t in tiles), default=0)
    sw = 360
    sheet = Image.new("RGB", (cols * (sw + 8) + 8, rows * (int(h * sw / W) + 30) + 8), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, t in enumerate(tiles):
        th = int(t.height * sw / W)
        x, y = 8 + (n % cols) * (sw + 8), 8 + (n // cols) * (int(h * sw / W) + 30)
        d.text((x, y + 2), "%d" % (n + 1), fill=(0, 0, 0))
        sheet.paste(t.resize((sw, th)), (x, y + 18))
    sheet.save(out_dir / "sheet.png")
    (out_dir / "README.md").write_text(README)
    key_path.write_text(json.dumps(key, indent=1, default=str))
    print("tiles:", len(key), collections.Counter(k["role"] for k in key))


if __name__ == "__main__":
    main()
