"""lane-farhead-5-6 (2026-10-07): ONE sheet. Tiles 5 and 6 of Sean's `brahms_1007_worse_cases.png` first, then 10 seeded Brahms heads whose
answer `flank_refine_bounded` changes (always including `glyph/5/0/5/5/1`, the manager's Horn head). Each tile: the page crop at the
gather's frame (600 dpi, x3), the per-bar grid the reader used (azure, 1 px, drawn ON the ink), the head's box (magenta), the line the note
rests on BEFORE (red tick, left) and AFTER (green tick, right), the staff named at left, the answer in WORDS before/after. Every drawn line
is checked against the pixel rows (printed, and flagged on the tile if off by > 2 px).

  python3 farhead_5_6_sheet.py <x/new.json (names)> <x7 brahms extract> <census off.json> <census on.json> <out.png> [--seed N]
"""
from __future__ import annotations
import json, random, sys, textwrap
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import farhead_5_6_diag as D
import night_1007_sheet as NS
import overnight_1004_report as R

SC = 3
AZURE, MAGENTA, RED, GREEN, GREY = (255, 150, 0), (255, 0, 255), (0, 0, 255), (0, 170, 0), (90, 90, 90)
FIRST = ["glyph/25/1/5/5/1", "glyph/18/1/0/5/21"]
FORCE = ["glyph/5/0/5/5/1"]


def row_check(gray, y, box, sp, near=False):
    """offset (px) from `y` to the CENTRE of the inked run (rows >= 80% of the best flank coverage) beside the head, or None.
    near=False: columns 0.2..2.2 sp out (a staff line runs the whole width); near=True: 0.1..0.9 sp (a ledger stub is short)."""
    x0, y0, x1, y1 = box
    lo, hi = (0.1, 0.9) if near else (0.2, 2.2)
    cols = list(range(int(x0 - hi * sp), int(x0 - lo * sp))) + list(range(int(x1 + lo * sp), int(x1 + hi * sp)))
    cols = [c for c in cols if 0 <= c < gray.shape[1]]
    rows = [r for r in range(int(y) - 8, int(y) + 9) if 0 <= r < gray.shape[0]]
    f = {r: float((gray[r, cols] <= 126).mean()) for r in rows}
    best = max(f.values()) if f else 0.0
    if best < 0.2:
        return None
    arg = max(rows, key=lambda r: f[r])
    lo_r = hi_r = arg
    while lo_r - 1 in f and f[lo_r - 1] >= 0.8 * best:
        lo_r -= 1
    while hi_r + 1 in f and f[hi_r + 1] >= 0.8 * best:
        hi_r += 1
    return float((lo_r + hi_r) / 2.0 - y)


def tile(gray, g, lines, y_off, y_on, sp, name, words_off, words_on, header, chk):
    x0, y0, x1, y1 = g["box"]
    X0, X1 = int(x0 - 3.2 * sp), int(x1 + 3.2 * sp)
    Y0, Y1 = int(min(y0, lines[0]) - 2.0 * sp), int(max(y1, lines[-1]) + 1.2 * sp)
    Y0 = max(0, min(Y0, int(y0 - 3.5 * sp))); Y1 = min(gray.shape[0], max(Y1, int(y1 + 3.5 * sp)))
    if y1 > lines[-1]:
        Y0, Y1 = int(lines[-1] - 1.2 * sp), int(y1 + 3.0 * sp)
    else:
        Y0, Y1 = int(y0 - 3.0 * sp), int(lines[0] + 1.2 * sp)
    Y0 = max(0, Y0); Y1 = min(gray.shape[0], Y1)
    crop = cv2.cvtColor(gray[Y0:Y1, X0:X1], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SC, fy=SC, interpolation=cv2.INTER_NEAREST)
    W = crop.shape[1]
    Y = lambda y: int(round((y - Y0) * SC + SC / 2))
    for y in lines:
        if Y0 <= y <= Y1:
            cv2.line(crop, (0, Y(y)), (W, Y(y)), AZURE, 1)
    cv2.rectangle(crop, (int((x0 - X0) * SC), Y(y0)), (int((x1 - X0) * SC), Y(y1)), MAGENTA, 1)
    if y_off is not None:
        cv2.line(crop, (0, Y(y_off)), (int(W * 0.30), Y(y_off)), RED, 2)
    if y_on is not None:
        cv2.line(crop, (int(W * 0.70), Y(y_on)), (W, Y(y_on)), GREEN, 2)
    cap = [header, name, "BEFORE (red): " + words_off, "AFTER (green): " + words_on, chk, "azure = the bar's five staff lines used; magenta = the note's box"]
    pad = 18 * len(cap) + 8
    out = np.full((crop.shape[0] + pad, W, 3), 255, np.uint8)
    out[pad:] = crop
    for i, t in enumerate(cap):
        cv2.putText(out, t[:int(W / 7.2)], (4, 14 + 18 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0) if i < 2 else (RED if i == 2 else GREEN if i == 3 else GREY), 1)
    return out


def main(names_json, src, off_json, on_json, out_png, seed=20261007):
    names = json.loads(Path(names_json).read_text())["allv"]
    inst = {}
    for k, v in names.items():
        if k.startswith("instrument|") and v[0] == "decided":
            inst[k.split("|", 1)[1]] = (json.loads(v[1]) or {}).get("name")
    off = json.loads(Path(off_json).read_text()); on = json.loads(Path(on_json).read_text())
    changed = [s for s in off if s in on and off[s].get("pos") != on[s].get("pos") and on[s].get("pos") is not None]
    rng = random.Random(seed)
    rest = [s for s in changed if s not in FIRST + FORCE]
    pick = FIRST + FORCE + rng.sample(rest, 10 - len(FORCE))
    data, rep = D.load(src)
    tiles, report = [], []
    for n, s in enumerate(pick, 1):
        res = {}
        for arm in (False, True):
            D.FH.READER_KEYWORDS["flank_refine_bounded"] = arm
            g, r, cap, gl, ctx = D.read_one(rep, data, s)
            nf = (r.get("detail") or {}).get("note_first") or {}
            res[arm] = (r["pos"], r["reason"], nf.get("line_y"), cap["sp"])
        D.FH.READER_KEYWORDS["flank_refine_bounded"] = False
        page = R.page_of(s)
        gray = rep.gray_of(page)
        sk = "staff/" + "/".join(s.split("/")[1:4])
        _, p, sy, sf = sk.split("/")
        nm = inst.get(sk) or "staff with no name read"
        name = f"{nm}  (page {int(p)}, system {int(sy) + 1}, staff {int(sf) + 1} from the top)   subject {s}"
        sp = res[True][3]
        checks = []
        for lab, y in (("grid", None),):
            pass
        offs = []
        for yy in gl:
            o = row_check(gray, yy, g["box"], sp)
            offs.append(o)
        ysn = [res[a][2] for a in (False, True)]
        note_chk = [row_check(gray, y, g["box"], sp, near=True) if y is not None else None for y in ysn]
        bad = [("grid line %d" % (i + 1), o) for i, o in enumerate(offs) if o is not None and abs(o) > 2]
        bad += [(lab, o) for lab, o in zip(("note line BEFORE", "note line AFTER"), note_chk) if o is not None and abs(o) > 2]
        chk = ("lines vs pixel rows: grid offsets " + ",".join("-" if o is None else "%.0f" % o for o in offs) + " px; note line before/after "
               + "/".join("-" if o is None else "%.0f" % o for o in note_chk) + " px" + ("   OFF > 2px: " + str(bad) if bad else ""))
        wo = NS.words_pos(res[False][0]) + ("" if res[False][0] is not None else "  [" + res[False][1][:60] + "]")
        wn = NS.words_pos(res[True][0]) + ("" if res[True][0] is not None else "  [" + res[True][1][:60] + "]")
        hd = f"TILE {n}" + ("  (Sean's worse-cases tile %s)" % ("6" if s == FIRST[0] else "5") if s in FIRST else ("  (manager's Horn head)" if s in FORCE else "  (seeded)"))
        grid = rep.head_lines(s)
        tiles.append(tile(gray, g, grid, res[False][2], res[True][2], sp, name, wo, wn, hd, chk))
        report.append(dict(n=n, subject=s, before=res[False][:3], after=res[True][:3], grid=[float(v) for v in grid], offs=offs, note_chk=note_chk))
        print(n, s, "BEFORE", res[False][0], "AFTER", res[True][0], "| grid offs", offs, "note", note_chk, flush=True)
    wmax = max(t.shape[1] for t in tiles)
    rows = []
    for i in range(0, len(tiles), 2):
        pair = tiles[i:i + 2]
        h = max(t.shape[0] for t in pair)
        row = np.full((h, wmax * 2 + 10, 3), 255, np.uint8)
        for j, t in enumerate(pair):
            row[:t.shape[0], j * (wmax + 10):j * (wmax + 10) + t.shape[1]] = t
        rows.append(row)
    sheet = np.vstack([np.pad(r, ((0, 12), (0, 0), (0, 0)), constant_values=255) for r in rows])
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out_png, sheet)
    Path(out_png).with_suffix(".json").write_text(json.dumps(report, default=str))
    print("wrote", out_png, sheet.shape)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(*a[:5], seed=int(a[a.index("--seed") + 1]) if "--seed" in a else 20261007)
