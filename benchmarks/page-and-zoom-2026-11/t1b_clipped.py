"""ROADMAP 2.307 T1b -- detector boxes clipped at a cell edge, by class family (measure only).

    python3 benchmarks/page-and-zoom-2026-11/t1b_clipped.py SLICES_DIR OUT.json

Reads the GATHER slices (observations.jsonl) of the frozen pages: every `glyph_box` row of reader `detector` carries its page box
(`detail.bbox_page_px`); every cell its padded page box (`cell_box`). A box is CLIPPED at an edge where it lies within TOL page px of that
edge of its own cell's crop (left/right = barline side, top/bottom = the padding's end). Context pages (Litolff 1) are left out.
"""
import collections
import json
import sys

TOL = 2.0
PAGES = {"litolff": {5, 8, 13, 15}, "brahms": {0, 11, 18, 20}}


def family(cls: str) -> str:
    c = cls.lower()
    if c.startswith("notehead"):
        if "whole" in c or "doublewhole" in c:
            return "head_whole"
        if "half" in c:
            return "head_hollow"
        return "head_filled"
    for pre, fam in (("rest", "rest"), ("accidental", "accidental"), ("flag", "flag"), ("augmentationdot", "dot"),
                     ("clef", "clef"), ("key", "keysig"), ("timesig", "meter"), ("slur", "arc"), ("tie", "arc"),
                     ("beam", "beam"), ("dynamic", "dynamic"), ("ledger", "ledger"), ("stem", "stem")):
        if c.startswith(pre):
            return fam
    return "other"


def main():
    root, outp = sys.argv[1], sys.argv[2]
    res = {}
    for plate in ("litolff", "brahms"):
        cells, boxes = {}, []
        for line in open("%s/%s/observations.jsonl" % (root, plate)):
            o = json.loads(line)
            q = o["quantity"]
            if q == "cell_box":
                cells[o["subject"]] = o["value"]
            elif q == "glyph_box" and o.get("reader") == "detector":
                boxes.append(o)
        tab = collections.defaultdict(collections.Counter)
        for o in boxes:
            sub = o["subject"].split("/")
            if int(sub[1]) not in PAGES[plate]:
                continue
            cb = cells.get("cell/" + "/".join(sub[1:5]))
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if cb is None or pb is None:
                continue
            fam = family(o["value"][0])
            t = tab[fam]
            t["boxes"] += 1
            edges = [n for n, hit in (("left", pb[0] <= cb[0] + TOL), ("right", pb[2] >= cb[2] - TOL),
                                      ("top", pb[1] <= cb[1] + TOL), ("bottom", pb[3] >= cb[3] - TOL)) if hit]
            for e in edges:
                t[e] += 1
            if edges:
                t["clipped_any"] += 1
            if "left" in edges or "right" in edges:
                t["clipped_lr"] += 1
        res[plate] = {k: dict(v) for k, v in sorted(tab.items())}
        print(plate)
        for fam, t in sorted(tab.items(), key=lambda kv: -kv[1]["boxes"]):
            print("  %-12s boxes %5d  clipped %4d (left %d right %d top %d bottom %d)" % (
                fam, t["boxes"], t["clipped_any"], t["left"], t["right"], t["top"], t["bottom"]))
    json.dump(res, open(outp, "w"), indent=1)


if __name__ == "__main__":
    main()
