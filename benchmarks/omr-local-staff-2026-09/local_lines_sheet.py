"""lane-local-staff-lines (Sean 2026-10-06): ONE sheet of 12 seeded far heads whose answer or owner changes when the local
five lines are fitted in windows. Each tile draws, for BOTH candidate staves (the head's own and its neighbour), the OLD
local lines (RED dashed) and the NEW ones (BLUE), the head box (ORANGE), and the answer / owner in words before and after;
every drawn line is re-measured against the pixel rows beside the head. Tile 1 is Sean's tile 6 (Litolff p16).

  python3 local_lines_sheet.py <audit_lito.json> <audit_brah.json> [--seed 20261006]
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import farhead_note_first_sheet as NF
import night_1006_sheet as NS
import truth_set_2_44c as ts
from frame import render_page_matching_gather

OUT = HERE.parents[1] / "out/print/ledgers/local_staff_lines.png"
TILE6 = ("beethoven5-litolff", "glyph/16/0/0/0/2")
SC = 2
RED, BLUE, ORANGE = NF.RED, NF.BLUE, NF.ORANGE


def owner_words(res, own):
    ow = res["owner"]
    if ow is None:
        return "no owner (silent: %s)" % res["word"]
    return ("this staff (%s)" % own.replace("staff/", "")) if ow == own else "the OTHER staff (%s)" % ow.replace("staff/", "")


def dashed(img, yy, col):
    for x in range(0, img.shape[1], 12):
        cv2.line(img, (x, yy), (min(x + 6, img.shape[1] - 1), yy), col, 1)


def tile(r, gray, no):
    x0, y0, x1, y1 = r["box"]
    sp = 15.75
    ys = [y0, y1]
    cy = (y0 + y1) / 2.0
    for v in r["cand"].values():           # only the lines within 9 spaces of the head: a far staff is off the tile
        ys += [y for y in list(v["old"]) + list(v["new"] or []) if abs(y - cy) <= 9 * sp]
    cx = (x0 + x1) / 2.0
    xa, xb = max(0, int(cx - 4.5 * sp)), int(cx + 4.5 * sp)
    ya, yb = max(0, int(min(ys) - sp)), int(max(ys) + sp)
    crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SC, fy=SC, interpolation=cv2.INTER_NEAREST)
    thr = min(int(np.percentile(gray[ya:yb, xa:xb], 25) + 40), 140)
    cols = ((int(x1 + 0.1 * sp), int(x1 + 1.0 * sp)), (int(x0 - 1.0 * sp), int(x0 - 0.1 * sp)))
    checks = {"old": [], "new": []}
    for k, v in r["cand"].items():
        for arm, lines, col in (("old", v["old"], RED), ("new", v["new"], BLUE)):
            if not lines:
                continue
            for y in lines:
                if not (ya <= y < yb):
                    continue
                yy = int(round((y - ya) * SC))
                if arm == "old":
                    dashed(crop, yy, col)
                else:
                    cv2.line(crop, (0, yy), (crop.shape[1] - 1, yy), col, 1)
                pk = [NF.remeasure(gray, y, *c, thr) for c in cols]
                pk = [p for p in pk if p[0] is not None]
                checks[arm].append((no, k[-5:], round(float(y), 1), min((abs(p[1]) for p in pk), default=None)))
    cv2.rectangle(crop, (int((x0 - xa) * SC), int((y0 - ya) * SC)), (int((x1 - xa) * SC), int((y1 - ya) * SC)), ORANGE, 2)
    return crop, checks


def main(lito, brah, seed):
    rows = []
    for p in (lito, brah):
        rows += [r for r in json.load(open(p))["rows"] if "old" in r and r.get("repro")]
    pool = [r for r in rows if r["old"]["pos"] != r["new"]["pos"]
            or (r["old"]["owner"], r["old"]["word"]) != (r["new"]["owner"], r["new"]["word"])]
    t6 = [r for r in pool if (r["doc"], r["subject"]) == TILE6]
    rest = [r for r in pool if (r["doc"], r["subject"]) != TILE6]
    pick = t6 + random.Random(seed).sample(rest, min(12 - len(t6), len(rest)))
    grays, cells, allc = {}, [], {"old": [], "new": []}
    for r in pick:
        k = (r["doc"], r["page"])
        if k not in grays:
            grays[k] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[r["doc"]]["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
    W = 0
    for i, r in enumerate(pick, 1):
        crop, ch = tile(r, grays[(r["doc"], r["page"])], i)
        for a in ("old", "new"):
            allc[a] += ch[a]
        H = crop.shape[0]
        cv = np.full((H + 112, crop.shape[1], 3), 255, np.uint8)
        cv[:H] = crop
        nb_state = {k[-5:]: ("not fitted: " + str(v["why"]) if v["new"] is None else "fallback lines %s" % v["fallback"] if v["fallback"] else "fitted")
                    for k, v in r["cand"].items()}
        lines = [("%d  %s p%d %s" % (i, "lito" if "beeth" in r["doc"] else "brah", r["page"], r["subject"].replace("glyph/", "")), (0, 0, 0)),
                 ("BEFORE: " + NS.words_pos(r["old"]["pos"]), (150, 0, 150)),
                 ("   owner: " + owner_words(r["old"], r["own"]), (150, 0, 150)),
                 ("AFTER:  " + NS.words_pos(r["new"]["pos"]), (200, 0, 0)),
                 ("   owner: " + owner_words(r["new"], r["own"]), (200, 0, 0)),
                 ("new lines: " + "; ".join("%s %s" % kv for kv in nb_state.items()), (90, 90, 90))]
        for j, (t, c) in enumerate(lines):
            cv2.putText(cv, t[:64], (4, H + 16 + 18 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.42, c, 1, cv2.LINE_AA)
        cells.append(cv)
        W = max(W, cv.shape[1])
    cols = 4
    rowsimg = []
    for k in range(0, len(cells), cols):
        grp = cells[k:k + cols]
        h = max(c.shape[0] for c in grp)
        rowsimg.append(np.hstack([np.pad(c, ((0, h - c.shape[0]), (4, W - c.shape[1] + 4), (0, 0)), constant_values=255) for c in grp]))
    w = max(x.shape[1] for x in rowsimg)
    img = np.vstack([np.pad(x, ((6, 6), (0, w - x.shape[1]), (0, 0)), constant_values=255) for x in rowsimg])
    leg = np.full((70, img.shape[1], 3), 255, np.uint8)
    for j, (t, c) in enumerate((("RED DASHED = the five local lines the OLD read measured, for the head's own staff and the neighbour.", RED),
                                ("BLUE = the five lines the NEW read fits (a comb on the known staff, one line per narrow window). ORANGE = the note.", BLUE),
                                ("Tile 1 is Sean's tile 6 (night sheet); 2-12 seeded random heads whose answer or owner changes (seed %d)." % seed, (0, 0, 0)))):
        cv2.putText(leg, t, (8, 20 + 22 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.55, c, 1, cv2.LINE_AA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), np.vstack([leg, img]))
    for a in ("old", "new"):
        c = allc[a]
        hid = [x for x in c if x[3] is None]
        bad = [x for x in c if x[3] is not None and x[3] > 2.0]
        print("%s lines drawn %d | within 2 px of an ink row %d | off by more than 2 px %d | no ink beside the head to measure %d"
              % (a, len(c), len(c) - len(bad) - len(hid), len(bad), len(hid)))
    for i, r in enumerate(pick, 1):
        print(i, r["doc"][:6], r["subject"], "| BEFORE", NS.words_pos(r["old"]["pos"]), "|", owner_words(r["old"], r["own"]),
              "| AFTER", NS.words_pos(r["new"]["pos"]), "|", owner_words(r["new"], r["own"]))
    print("wrote", OUT, "pool", len(pool))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261006)
