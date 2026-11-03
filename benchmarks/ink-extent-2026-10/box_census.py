"""2.248 cause census: how often is a NOTEHEAD detector box cut short of a head, and is the short box a cell-edge
twin (the same head detected whole in the neighbouring staff's cell) or the only box on its head?

Reads `glyph_box` observations only (a slice dir's observations.jsonl or a record.json). A box is SHORT when its
height is < 0.75 sp (a printed head is >= 1.0 sp tall, 2.39), i.e. it stops >= 0.25 sp short of the head's ink.
A short box has a WHOLE TWIN when a notehead box of another staff's cell (glyph/p/s/STAFF/...) covers >= 80% of
its width and holds its rows, with a height >= 0.75 sp.

usage: box_census.py PLATE=UNIT_PX=PATH [PAGES=2,4,...] ..."""
import collections
import json
import sys


def rows(path):
    if path.endswith(".jsonl"):
        for l in open(path):
            if '"glyph_box"' in l:
                yield json.loads(l)
    else:
        rec = json.load(open(path))
        rec = rec.get("record", rec)
        for o in rec["observations"]:
            if o["quantity"] == "glyph_box":
                yield o


def main(*args):
    for a in args:
        parts = a.split("=")
        plate, unit, path = parts[0], float(parts[1]), parts[2]
        pages = set(int(p) for p in parts[3].split(",")) if len(parts) > 3 else None
        heads = collections.defaultdict(list)
        for o in rows(path):
            if o.get("quantity") != "glyph_box":
                continue
            d = o.get("detail") or {}
            if d.get("category") != "notehead" or not d.get("bbox_page_px"):
                continue
            k = o["subject"].split("/")
            pg = int(k[1])
            if pages is not None and pg not in pages:
                continue
            heads[pg].append((o["subject"], int(k[3]), str(o["value"][0]), d["bbox_page_px"]))
        c = collections.Counter()
        hist = collections.Counter()
        examples = []
        for pg, hs in heads.items():
            for sub, st, cls, b in hs:
                h = (b[3] - b[1]) / unit
                c["heads"] += 1
                hist[round(h * 4) / 4] += 1
                if h >= 0.75:
                    continue
                c["short (<0.75 sp tall)"] += 1
                twin = None
                for s2, st2, cl2, b2 in hs:
                    if st2 == st or (b2[3] - b2[1]) / unit < 0.75:
                        continue
                    ix = min(b[2], b2[2]) - max(b[0], b2[0])
                    if ix >= 0.8 * (b[2] - b[0]) and b2[1] - 2 <= b[1] and b[3] <= b2[3] + 2:
                        twin = s2
                        break
                if twin:
                    c["short, whole twin in another staff's cell"] += 1
                else:
                    c["short, no whole twin"] += 1
                    if len(examples) < 12:
                        examples.append((sub, cls, [round(v, 1) for v in b], round(h, 2)))
        print(plate, dict(c))
        print("   height(sp) histogram:", dict(sorted(hist.items())))
        for e in examples:
            print("   no-twin example", e)


if __name__ == "__main__":
    main(*sys.argv[1:])
