"""2.247: trace the 2.242 r2 tiles (key.json) from GATHER (the detector class + the 2.201 stroke type on the saved slices) to the exported
file (a lane report arm's symbols.json: the accidental written on the note to the right). usage: trace_tiles.py KEY.json SYMBOLS.json [SLICES_ROOT]"""
import json
import sys

ROOT = "library/_shared-records/lane-report-slices-20261029-night"


def page_rows(root, plate, pages):
    boxes, fams = {}, {}
    with open(f"{root}/{plate}/observations.jsonl") as f:
        for line in f:
            if '"glyph_box"' not in line and '"accidental_staff_position"' not in line:
                continue
            r = json.loads(line)
            p = int(r["subject"].split("/")[1])
            if p not in pages:
                continue
            d = r.get("detail") or {}
            if r["quantity"] == "glyph_box":
                name = str(r["value"][0])
                if name.startswith("accidental") or name.startswith("key"):
                    boxes[r["subject"]] = (r["value"][0], d.get("bbox_page_px"))
            elif r["quantity"] == "accidental_staff_position":
                fams[r["subject"]] = d
    return boxes, fams


def overlap(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > 0 and min(a[3], b[3]) - max(a[1], b[1]) > 0


def main(key_path, sym_path, root=ROOT):
    key = json.load(open(key_path))
    sym = json.load(open(sym_path))
    plate = sym["plate"]
    pages = {int(t["page"].split(":")[1]) for t in key if t["plate"] == plate}
    boxes, fams = page_rows(root, plate, pages)
    for t in key:
        if t["plate"] != plate:
            continue
        p = int(t["page"].split(":")[1])
        hits = [(s, b) for s, b in boxes.items() if int(s.split("/")[1]) == p and b[1] and overlap(b[1], t["box"])]
        print(f"tile {t['tile']} {t['page']} box {t['box']} cls {t['cls']}")
        for s, (cls, pb) in hits:
            fam = (fams.get(s) or {}).get("family") or {}
            print(f"   {s} {cls} page{[round(v) for v in pb]} family={fam.get('type')} ({fam.get('why')}) feat={fam.get('features')}")
            notes = [h for h in sym["hosts"] if h.get("kind") == "note" and h.get("page") == p and h.get("box")
                     and -10 <= h["box"][0] - pb[2] <= 60 and h["box"][3] > pb[1] - 10 and h["box"][1] < pb[3] + 10]
            for h in notes[:2]:
                print(f"      written: {h['rg']} {h['pitch']} acc={h['sub'].get('accidental')} blue={h['blue']}")


if __name__ == "__main__":
    main(*sys.argv[1:])
