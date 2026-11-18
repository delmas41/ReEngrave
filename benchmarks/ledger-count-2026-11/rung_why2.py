"""ROADMAP 2.312 Part 1 step 1b -- for the seeded 30: run the reader's own position function on the page ink with (a) no other head removed and (b) every other head's box on the page removed,
as the reader does. Where (a) reads and (b) refuses, the cause is the removal of a neighbour head's ink (the line is fused with, or shared by, a neighbour head).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/ledger-count-2026-11 python3 benchmarks/ledger-count-2026-11/rung_why2.py WHY.json
"""
import json
import sys

import numpy as np

from checksheet import page_image
from ledger_heights import load
from tools.omr.annotate import far_head_reader as FH

why = json.load(open(sys.argv[1]))
rows, _ = load("litolff")
sl = rows["staff_lines"]
boxes_by_page = {}
for sub, o in rows["notehead_class"].items():
    gb = rows["glyph_box"].get(sub)
    if gb:
        boxes_by_page.setdefault(int(sub.split("/")[1]), []).append((sub, tuple(gb["detail"]["bbox_page_px"])))
acc_by_page = {}
for sub, gb in rows["glyph_box"].items():
    pass
res = []
for w in why:
    p = int(w["key"].split("/")[1])
    s, st = w["key"].split("/")[2:4]
    ys = sl["staff/%s/%s/%s" % (p, s, st)]["value"]
    box = tuple(rows["glyph_box"][w["key"]]["detail"]["bbox_page_px"])
    gray = np.array(page_image("litolff", p).convert("L"))
    a = FH.read_absolute_position(gray, [float(v) for v in ys], box, w["key"], [], [])
    b = FH.read_absolute_position(gray, [float(v) for v in ys], box, w["key"], boxes_by_page.get(p, []), [])
    res.append((w["i"], w["key"], w["reason"].split(" (")[0], a, b))
    print(w["i"], w["key"], w["reason"].split(" (")[0][:22], "| no other heads removed:", a, "| others removed:", b)
