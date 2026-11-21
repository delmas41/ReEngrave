"""2.306 r19 (hollow head's outline covers the whole ring): cut `tools/omr/tests/data_head_ring_2_306.npz` from Brahms 317803 page 0.

Crops of the page raster (600 dpi `render_page(...).binary`, nothing erased) around written notes' detector boxes from the 2026-11-21 frozen-sample
OFF record's `symbols.json` (read-only). Keys `<rg with / -> _>`: `_ink` (packbits), `_shape`, `_box` (crop px), `_origin` (the crop's page px), `_sp`, `_kind`, `_type`.
Kinds: `ring` -- the hollow heads whose outline the old reading cut; `second` -- two filled heads of a second, fused on the page; `slash` --
half notes with a tremolo slash on their stem; `ledger` -- filled heads next to a line whose line rows are stripped.

Usage (cwd = tree): python3 benchmarks/page-ledger-2026-11/2306/r19_ring_fixture.py SYMBOLS_JSON"""
import json
import os
import sys

import numpy as np

from tools.omr.preprocessing import render_page
from tools.omr.staged import head_extent as HE

PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
SP = 33.0                      # Brahms p0 staff space, read off the staff lines at x 2300-2700 (lines 33 px apart)
PAD = 90
OUT = "tools/omr/tests/data_head_ring_2_306.npz"

sym = json.load(open(sys.argv[1]))
b = render_page(PDF, 0, dpi=600).binary
notes, seen = [], set()
for h in sym["hosts"]:
    if h.get("kind") == "note" and h.get("page") == 0 and h.get("box") and h["rg"] not in seen:
        seen.add(h["rg"])
        notes.append(h)

pick = {}
for h in notes:
    os.environ.pop("OMR_PAGE_STEMS", None)
    a = HE.ink_extent(b, h["box"], SP)
    os.environ["OMR_PAGE_STEMS"] = "1"
    z = HE.ink_extent(b, h["box"], SP)
    if a["extent"] != z["extent"]:
        pick[h["rg"]] = ("ring", h)
    elif h["type"] != "half" and a.get("line_rows_stripped") and len([k for k in pick.values() if k[0] == "ledger"]) < 4:
        pick[h["rg"]] = ("ledger", h)
for rg in ("glyph/0/0/6/1/2", "glyph/0/0/6/1/11"):
    pick[rg] = ("second", next(h for h in notes if h["rg"] == rg))
for h in notes:                # staff 8, bars 2-6: half notes with a tremolo slash on the stem (Sean's labels `tremolo1`)
    if h["rg"].startswith("glyph/0/0/8/") and h["type"] == "half" and h["rg"] not in pick:
        pick[h["rg"]] = ("slash", h)

arr = {}
for rg, (kind, h) in pick.items():
    x0, y0, x1, y1 = h["box"]
    cx0, cy0 = int(x0) - PAD, int(y0) - PAD
    crop = b[cy0:int(y1) + PAD, cx0:int(x1) + PAD]
    k = rg.replace("/", "_")
    arr[k + "_ink"] = np.packbits((crop == 0).ravel())
    arr[k + "_shape"] = np.array(crop.shape)
    arr[k + "_box"] = np.array([x0 - cx0, y0 - cy0, x1 - cx0, y1 - cy0])
    arr[k + "_origin"] = np.array([cx0, cy0])
    arr[k + "_sp"] = np.array(SP)
    arr[k + "_kind"] = np.array(kind)
    arr[k + "_type"] = np.array(h["type"])
    print(kind, rg, h["type"], [round(v) for v in h["box"]])
np.savez_compressed(OUT, **arr)
print(len(pick), "->", OUT)
