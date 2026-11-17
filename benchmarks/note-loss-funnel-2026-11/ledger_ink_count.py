"""ROADMAP 2.311 small test -- OUR OWN count of the ledger strokes at each far head's x, from the un-erased page (not truth).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/ledger_ink_count.py LH.json OUT.json

For every head `ledger_heights.py` held that the record places outside its staff (by FINAL or by geometry): the dark rows, in a window
+-0.85 staff space either side of the box centre, that run nearly the whole window (a ledger line is longer than a head), between
the staff's outer line and the head's centre. Heads in a second beside each other can fake a line; the 40-per-plate sample is
looked at on a sheet and the disagreements checked by eye (rule 7: we ask who says it is right -- the print).
"""
import collections, json, random, sys
import numpy as np
from checksheet import page_image
from ledger_heights import owed, side

def count(img, box, lines, win=0.85, frac=0.88):
    sp = (lines[4] - lines[0]) / 4.0
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    x0, x1 = int(cx - win * sp), int(cx + win * sp)
    if cy < lines[0]:
        ya, yb = int(cy - 0.3 * sp), int(lines[0] - 0.5 * sp)
    else:
        ya, yb = int(lines[4] + 0.5 * sp), int(cy + 0.3 * sp)
    if yb <= ya:
        return 0, []
    strip = img[ya:yb, x0:x1]
    fr = strip.mean(axis=1)
    on = fr >= frac
    runs, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j + 1 < len(on) and on[j + 1]:
                j += 1
            runs.append((ya + i, ya + j))
            i = j + 1
        else:
            i += 1
    runs = [r for r in runs if r[1] - r[0] + 1 >= max(2, 0.08 * sp)]
    return len(runs), runs

def main(lh, out):
    res = json.load(open(lh))
    o = {}
    for plate in ("litolff", "brahms"):
        hs = [h for h in res[plate]["heads"] if not h["other_staff"] and h["lines"] and (owed(h["final"]) > 0 or owed(h["geom_round"]) > 0)]
        by = collections.defaultdict(list)
        for h in hs:
            by[h["page"]].append(h)
        for pg, lst in by.items():
            im = np.array(page_image(plate, pg).convert("L")) < 128
            for h in lst:
                n, runs = count(im, h["box"], h["lines"])
                h["ink_count"], h["ink_runs"] = n, runs
        o[plate] = hs
        print(plate, len(hs))
    json.dump(o, open(out, "w"))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
