#!/usr/bin/env python3
"""l288_truth: every head Sean has judged on the print whose VALUE is a half or a non-half and which the 2.88 question (is a hollow-reading
head with a stem a half?) can be scored against. Sources are his committed answers on `out/print/`:

  2.65-headfill  (3 Litolff halves, page boxes)        2.70-review (8 Litolff halves)      2.73-review (7 halves, 2 Brahms eighths)
  2.83-review    (tile_10: a filled QUARTER read hollow; tile_06: Brahms, not a head)   2.83-fix-review (tile_06 half; tile_01/05/08 quarters)

Each entry: movement, pdf page, a page box (match by overlap) or a glyph key (match by key), Sean's value in written beats (undotted),
the source tile.  Read-only.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PRINT = REPO / "out" / "print"


def _m(d):
    m = json.loads((PRINT / d / "manifest.json").read_text())
    return m["tiles"] if isinstance(m, dict) else m


def _a(d):
    return json.loads((PRINT / d / "answers.json").read_text())


def truth():
    t = []
    # 2.70: eight Litolff halves (Sean: "Half note" x8)
    for x in _m("2.70-review"):
        t.append(dict(movement="litolff", page=x["pdf_page_index"], box=x["page_box"], beats=2.0, src=f"2.70-review/{x['n']}"))
    # 2.73: six Litolff halves + 1 more (9), two Brahms eighths (7, 8), tile 10 is a dynamic (not a head)
    ans = _a("2.73-review")
    for x in _m("2.73-review"):
        v = ans[str(x["n"])]
        mv = "brahms" if "Brahms" in x["label"] else "litolff"
        if v == "Half":
            t.append(dict(movement=mv, page=x["page"], box=x["page_box"], beats=2.0, src=f"2.73-review/{x['n']}"))
        elif v == "8th":
            t.append(dict(movement=mv, page=x["page"], box=x["page_box"], beats=0.5, src=f"2.73-review/{x['n']}"))
    # 2.65 head-fill: Litolff pdf 6 halves (tiles 3, 5, 6)
    ans = _a("2.65-headfill")
    for x in _m("2.65-headfill"):
        if str(x["n"]) in ("3", "5", "6"):
            pg = int(x["subject_2_23"].split("/")[1])
            t.append(dict(movement="litolff", page=pg, box=x["page_box"], beats=2.0, src=f"2.65-headfill/{x['n']}"))
    # 2.83 first round: tile_10 -- a filled QUARTER (Litolff 15 `15/1/3/17/5`), read hollow on a 2.8-space box
    t.append(dict(movement="litolff", page=15, key="glyph/15/1/3/17/5", beats=1.0, src="2.83-review/tile_10"))
    # 2.83 fix round: tile_06 half (Litolff 10); tiles 01, 05, 08 quarters
    t.append(dict(movement="litolff", page=10, key="glyph/10/1/4/8/7", beats=2.0, src="2.83-fix-review/tile_06"))
    t.append(dict(movement="litolff", page=3, key="glyph/3/1/4/12/3", beats=1.0, src="2.83-fix-review/tile_01"))
    t.append(dict(movement="litolff", page=4, key="glyph/4/0/7/7/10", beats=1.0, src="2.83-fix-review/tile_05"))
    t.append(dict(movement="litolff", page=11, key="glyph/11/1/8/16/3", beats=1.0, src="2.83-fix-review/tile_08"))
    return t


if __name__ == "__main__":
    for e in truth():
        print(e)
