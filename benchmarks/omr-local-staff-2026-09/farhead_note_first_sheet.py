"""lane-farhead-note-first (2026-10-05): ONE sheet of 12 seeded-random OUT-OF-SAMPLE decisions of the note-first
far-head reader. Each tile: the note's box (orange), the staff's edge (blue), every ledger counted between the edge
and the note's line (green), the note's own line drawn full width (red), and the reading in WORDS under it.
Every drawn line is re-measured against the pixel rows of the page (ink peak within a few rows of the drawn y; the
table prints the offset, and a line more than 2 px off ink is flagged on the tile).

  python3 farhead_note_first_sheet.py out.png seed oos_litolff.json[:litolff] [oos_brahms.json:brahms]
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import truth_set_2_44c as ts
from frame import render_page_matching_gather

DOCS = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
ORD = {1: "1st", 2: "2nd", 3: "3rd"}
SCALE = 3
BLUE, GREEN, RED, ORANGE = (255, 80, 0), (0, 170, 0), (0, 0, 255), (0, 140, 255)


def ordinal(n):
    return ORD.get(n, f"{n}th")


def words(row):
    nf = row["new"]
    below = nf["line_y"] > nf["edge_y"]
    side = "below" if below else "above"
    k = nf["k"]
    if nf["kind"] == "on":
        return f"on the {ordinal(k)} ledger {side}"
    return f"in the space {side} the {ordinal(k)} ledger"


def remeasure(gray, y, x0, x1, thr):
    """The ink row nearest the drawn y (within 6 px) in columns x0..x1: the centre of the contiguous run of rows
    whose ink fraction there is >= 0.6, as (centre, offset_px); (None, None) where no row there is inked."""
    x0, x1 = max(0, x0), min(gray.shape[1], x1)
    if x1 <= x0:
        return None, None
    rows = [r for r in range(int(y) - 6, int(y) + 7)
            if 0 <= r < gray.shape[0] and (gray[r, x0:x1] <= thr).mean() >= 0.6]
    if not rows:
        return None, None
    runs, cur = [], [rows[0]]
    for r in rows[1:]:
        if r == cur[-1] + 1:
            cur.append(r)
        else:
            runs.append(cur); cur = [r]
    runs.append(cur)
    best = min(runs, key=lambda c: abs(np.mean(c) - y))
    peak = float(np.mean(best))
    return peak, peak - y


def tile(row, gray, no):
    nf = row["new"]
    box = row["new"]["box_used"]
    lines = row["new"]["lines"]
    sp = (max(lines) - min(lines)) / 4.0
    edge, line_y = nf["edge_y"], nf["line_y"]
    ys = [edge, line_y, box[1], box[3]] + list(nf["between"] or [])
    cx = (box[0] + box[2]) / 2.0
    xa, xb = int(cx - 3.2 * sp), int(cx + 3.2 * sp)
    ya, yb = int(min(ys) - 1.2 * sp), int(max(ys) + 1.2 * sp)
    xa, ya = max(0, xa), max(0, ya)
    crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_NEAREST)
    thr = int(np.percentile(gray[ya:yb, xa:xb], 25) + 40)
    thr = min(thr, 140)
    side_cols = (int(box[2] + 0.1 * sp), int(box[2] + 1.0 * sp))   # flanking the head, where a ledger juts
    left_cols = (int(box[0] - 1.0 * sp), int(box[0] - 0.1 * sp))
    checks = []

    def draw(y, colour, label):
        yy = int(round((y - ya) * SCALE))
        cv2.line(crop, (0, yy), (crop.shape[1] - 1, yy), colour, 2)
        peaks = [remeasure(gray, y, *cols, thr) for cols in (left_cols, side_cols)]
        peaks = [p for p in peaks if p[0] is not None]
        off = min((abs(p[1]) for p in peaks), default=None)   # None: no ink flanks the head there (hidden by it)
        checks.append((no, label, round(float(y), 1), None if off is None else round(off, 1)))
        return off
    draw(edge, BLUE, "staff edge")
    for i, b in enumerate(nf["between"] or []):
        draw(b, GREEN, f"ledger {i + 1}")
    off_note = draw(line_y, RED, "note line")
    cv2.rectangle(crop, (int((box[0] - xa) * SCALE), int((box[1] - ya) * SCALE)),
                  (int((box[2] - xa) * SCALE), int((box[3] - ya) * SCALE)), ORANGE, 1)
    return crop, checks


def sheet(rows, grays, out):
    tiles, allchecks = [], []
    for i, r in enumerate(rows, 1):
        crop, ch = tile(r, grays[(r["doc"], r["page"])], i)
        allchecks += ch
        tiles.append((crop, i, r))
    W = max(t[0].shape[1] for t in tiles)
    cells = []
    for crop, i, r in tiles:
        cap_h = 62
        H = crop.shape[0]
        canvas = np.full((H + cap_h, W, 3), 255, np.uint8)
        canvas[:H, :crop.shape[1]] = crop
        short = r["subject"].replace("glyph/", "")
        cv2.putText(canvas, f"{i}", (6, H + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(canvas, f"{r['doc'][:4]} {short}  pos {r['new']['pos']} (geom {r['geometry']})",
                    (34, H + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
        txt = words(r) + ("" if r["new"].get("seen") else "  [no full stub beside head]")
        cv2.putText(canvas, txt, (6, H + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 200), 1)
        cv2.putText(canvas, f"old reader: {r['old']['pos']}  run-2 rec: {r['run2_recorded']}",
                    (6, H + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (90, 90, 90), 1)
        cells.append(canvas)
    cols = 4
    rowsimg = []
    for k in range(0, len(cells), cols):
        grp = cells[k:k + cols]
        h = max(c.shape[0] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, 4), (0, 0)), constant_values=255) for c in grp]
        while len(grp) < cols:
            grp.append(np.full((h, W + 8, 3), 255, np.uint8))
        rowsimg.append(np.hstack(grp))
    w = max(r.shape[1] for r in rowsimg)
    img = np.vstack([np.pad(r, ((6, 6), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rowsimg])
    legend = np.full((34, img.shape[1], 3), 255, np.uint8)
    cv2.putText(legend, "orange = the note's box   blue = staff edge   green = each ledger counted between   "
                "red = the note's line (full width)", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    cv2.imwrite(out, np.vstack([legend, img]))
    return allchecks


if __name__ == "__main__":
    out, seed = sys.argv[1], int(sys.argv[2])
    pool = []
    for spec in sys.argv[3:]:
        path, which = spec.split(":")
        for r in json.loads(Path(path).read_text()):
            if r["new"]["pos"] is not None and r["new"]["line_y"] is not None:
                r["doc"] = which
                pool.append(r)
    rng = random.Random(seed)
    pick = rng.sample(pool, 12)
    grays = {}
    for r in pick:
        key = (r["doc"], r["page"])
        if key not in grays:
            cfg = ts.DOCS[DOCS[r["doc"]]]
            grays[key] = cv2.cvtColor(render_page_matching_gather(cfg["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
    checks = sheet(pick, grays, out)
    hidden = [c for c in checks if c[3] is None]
    bad = [c for c in checks if c[3] is not None and c[3] > 2.0]
    print("drawn lines", len(checks), "within 2 px of a flanking ink row:", len(checks) - len(bad) - len(hidden),
          "| off by more than 2 px:", bad, "| no flanking ink (line hidden behind the head):", hidden)
    for i, r in enumerate(pick, 1):
        print(i, r["doc"], r["subject"], "->", words(r), "| pos", r["new"]["pos"], "geometry", r["geometry"],
              "old", r["old"]["pos"], "run2", r["run2_recorded"], "|", r["new"]["how"])
