"""2.248: for each head place Sean called 'box too small', the tile's box and every notehead box of ANOTHER staff's cell
that overlaps it (a whole twin of the same head).  usage: trace_tiles.py LITOLFF_OBS.jsonl BRAHMS_OBS.jsonl"""
import json
import sys

TILES = {"L": [("s4-1", "glyph/6/1/2/9/7"), ("s4-7", "glyph/10/1/7/9/12"), ("s4-9", "glyph/16/1/6/4/9"),
               ("rules-3", "glyph/6/1/0/11/7"), ("rules-4", "glyph/8/1/0/13/18"), ("rules-6", "glyph/10/1/8/7/11"),
               ("rules-11", "glyph/1/0/11/2/5")],
         "B": [("s4-6", "glyph/5/1/10/5/8"), ("rules-7", "glyph/0/0/11/3/21")]}


def main(lpath, bpath):
    for p, path in (("L", lpath), ("B", bpath)):
        ts = TILES[p]
        pages = {g.split("/")[1] for _, g in ts}
        boxes = {}
        for line in open(path):
            if '"glyph_box"' not in line:
                continue
            o = json.loads(line)
            s = o["subject"]
            d = o.get("detail") or {}
            if s.split("/")[1] not in pages or d.get("category") != "notehead":
                continue
            boxes[s] = (o["value"][0], d["bbox_page_px"])
        for t, g in ts:
            if g not in boxes:
                print(t, g, "MISSING")
                continue
            c, b = boxes[g]
            tw = [(s, c2, [round(v) for v in b2]) for s, (c2, b2) in boxes.items()
                  if s != g and s.split("/")[:3] == g.split("/")[:3] and s.split("/")[3] != g.split("/")[3]
                  and min(b[2], b2[2]) - max(b[0], b2[0]) > 0.5 * (b[2] - b[0])
                  and min(b[3], b2[3]) - max(b[1], b2[1]) > 0]
            print(t, g, c, [round(v, 1) for v in b], "h=%.1f" % (b[3] - b[1]), "twins:", tw)


if __name__ == "__main__":
    main(*sys.argv[1:])
