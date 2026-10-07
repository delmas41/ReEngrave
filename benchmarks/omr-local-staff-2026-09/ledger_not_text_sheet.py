"""lane-ledger-not-text (2026-10-05): what the `ledger_not_text` rule changed out of sample. Compares the committed
note-first run (`farhead_note_first_oos_*.json`, rule absent) with the run that has it (`ledger_not_text_oos_*.json`),
counts the decisions that change, and draws up to 12 of them (seeded): the note's box (orange), the staff edge (blue
solid), the ledgers still counted (green solid), the note's line (red solid), and the REJECTED rung (red dashes).
Words before and after under each tile; every drawn line is re-measured against the pixel rows.

  python3 ledger_not_text_sheet.py out.png seed
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import truth_set_2_44c as ts
from frame import render_page_matching_gather
import farhead_note_first_sheet as S

DOCS = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
BLUE, GREEN, RED, ORANGE = S.BLUE, S.GREEN, S.RED, S.ORANGE
SCALE = 3


def load(which):
    before = {r["subject"]: r for r in json.loads((HERE / f"farhead_note_first_oos_{which}.json").read_text())}
    after = {r["subject"]: r for r in json.loads((HERE / f"ledger_not_text_oos_{which}.json").read_text())}
    return before, after


def changed(before, after):
    out = []
    for s, a in after.items():
        b = before.get(s)
        if b is not None and b["new"]["pos"] != a["new"]["pos"]:
            out.append((b, a))
    return out


def say(side, edge_y):
    if side["pos"] is None:
        return "cannot say (" + side["reason"].split(" (")[0].split(" --")[0][:34] + ")"
    below = side["line_y"] > edge_y
    k = side["k"]
    where = "below" if below else "above"
    return (f"on the {S.ordinal(k)} ledger {where}" if side["kind"] == "on"
            else f"in the space {where} the {S.ordinal(k)} ledger")


def rejected_ys(b, a):
    keep = a["new"]["between"] or []
    return [y for y in (b["new"]["between"] or []) if all(abs(y - k) > 1.5 for k in keep)]


def dashed(img, yy, colour):
    for x in range(0, img.shape[1], 14):
        cv2.line(img, (x, yy), (min(x + 8, img.shape[1] - 1), yy), colour, 2)


def tile(b, a, gray, no):
    bn, an = b["new"], a["new"]
    box, lines = bn["box_used"], bn["lines"]
    sp = (max(lines) - min(lines)) / 4.0
    edge, line_y = bn["edge_y"], bn["line_y"]
    rej = rejected_ys(b, a)
    ys = [edge, line_y, box[1], box[3]] + list(bn["between"] or [])
    cx = (box[0] + box[2]) / 2.0
    xa, xb = max(0, int(cx - 3.2 * sp)), int(cx + 3.2 * sp)
    ya, yb = max(0, int(min(ys) - 1.2 * sp)), int(max(ys) + 1.2 * sp)
    crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_NEAREST)
    thr = min(int(np.percentile(gray[ya:yb, xa:xb], 25) + 40), 140)
    left = (int(box[0] - 1.0 * sp), int(box[0] - 0.1 * sp))
    right = (int(box[2] + 0.1 * sp), int(box[2] + 1.0 * sp))
    checks = []

    def draw(y, colour, label, dash=False):
        yy = int(round((y - ya) * SCALE))
        if dash:
            dashed(crop, yy, colour)
        else:
            cv2.line(crop, (0, yy), (crop.shape[1] - 1, yy), colour, 2)
        peaks = [S.remeasure(gray, y, *cols, thr) for cols in (left, right)]
        peaks = [p for p in peaks if p[0] is not None]
        checks.append((no, label, round(float(y), 1), min((abs(p[1]) for p in peaks), default=None)))
    draw(edge, BLUE, "staff edge")
    keep = an["between"] or []
    for i, y in enumerate(bn["between"] or []):
        if y in rej:
            draw(y, RED, "rejected rung", dash=True)
        else:
            draw(y, GREEN, f"ledger {i + 1}")
    draw(line_y, RED, "note line")
    cv2.rectangle(crop, (int((box[0] - xa) * SCALE), int((box[1] - ya) * SCALE)),
                  (int((box[2] - xa) * SCALE), int((box[3] - ya) * SCALE)), ORANGE, 1)
    return crop, checks


def sheet(pairs, grays, out):
    cells, checks_all = [], []
    W = 0
    tiles = []
    for i, (b, a, doc) in enumerate(pairs, 1):
        crop, ch = tile(b, a, grays[(doc, b["page"])], i)
        checks_all += ch
        tiles.append((crop, i, b, a, doc))
        W = max(W, crop.shape[1])
    for crop, i, b, a, doc in tiles:
        H = crop.shape[0]
        canvas = np.full((H + 64, W, 3), 255, np.uint8)
        canvas[:H, :crop.shape[1]] = crop
        cv2.putText(canvas, f"{i}", (6, H + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(canvas, f"{doc[:4]} {b['subject'].replace('glyph/', '')} geom {b['geometry']}",
                    (34, H + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
        cv2.putText(canvas, "before: " + say(b["new"], b["new"]["edge_y"]), (6, H + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 200), 1)
        cv2.putText(canvas, "after:  " + say(a["new"], b["new"]["edge_y"]), (6, H + 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 120, 0), 1)
        cells.append(canvas)
    cols = 4
    rows = []
    for k in range(0, len(cells), cols):
        grp = cells[k:k + cols]
        h = max(c.shape[0] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, 4), (0, 0)), constant_values=255) for c in grp]
        while len(grp) < cols:
            grp.append(np.full((h, W + 8, 3), 255, np.uint8))
        rows.append(np.hstack(grp))
    w = max(r.shape[1] for r in rows)
    img = np.vstack([np.pad(r, ((6, 6), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows])
    legend = np.full((56, img.shape[1], 3), 255, np.uint8)
    cv2.putText(legend, "orange box = the note   blue = the staff's edge   green = a ledger still counted   "
                "red solid = the note's own line", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    cv2.putText(legend, "red DASHES = the rung the rule rejected (text, not a ledger)", (8, 44),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 200), 1)
    cv2.imwrite(out, np.vstack([legend, img]))
    return checks_all


if __name__ == "__main__":
    out, seed = sys.argv[1], int(sys.argv[2])
    pool = []
    for which in ("litolff", "brahms"):
        before, after = load(which)
        ch = changed(before, after)
        kinds = collections.Counter(
            ("decided->abstain" if a["new"]["pos"] is None else
             "abstain->decided" if b["new"]["pos"] is None else "decided->other decision") for b, a in ch)
        print(which, "far heads", len(after), "changed", len(ch), dict(kinds))
        for b, a in ch:
            wrong_vs_geom = (b["new"]["pos"] == b["geometry"], a["new"]["pos"] == a["geometry"]
                             if a["new"]["pos"] is not None else None)
            print("  ", b["subject"], "geom", b["geometry"], "before", b["new"]["pos"], "after", a["new"]["pos"],
                  "| before agreed with geometry:", wrong_vs_geom[0], "| rejected", rejected_ys(b, a))
        pool += [(b, a, which) for b, a in ch if b["new"]["line_y"] is not None and rejected_ys(b, a)]
    rng = random.Random(seed)
    # Sean's crescendo head (tile 12 of note_first_sample.png) is always tile 1; 11 more, seeded
    first = [p for p in pool if p[0]["subject"] == "glyph/5/0/6/3/2"]
    rest = [p for p in pool if p[0]["subject"] != "glyph/5/0/6/3/2"]
    pick = first + rng.sample(rest, min(12 - len(first), len(rest)))
    grays = {}
    for b, a, doc in pick:
        k = (doc, b["page"])
        if k not in grays:
            grays[k] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[DOCS[doc]]["pdf"], b["page"], 600).rgb,
                                    cv2.COLOR_RGB2GRAY)
    checks = sheet(pick, grays, out)
    hidden = [c for c in checks if c[3] is None]
    bad = [c for c in checks if c[3] is not None and c[3] > 2.0]
    print("drawn lines", len(checks), "within 2 px of a flanking ink row", len(checks) - len(bad) - len(hidden),
          "| off by more than 2 px", bad, "| no flanking ink beside the head", len(hidden))
    for i, (b, a, doc) in enumerate(pick, 1):
        print(i, doc, b["subject"], "| before:", say(b["new"], b["new"]["edge_y"]), "| after:", say(a["new"], b["new"]["edge_y"]))
