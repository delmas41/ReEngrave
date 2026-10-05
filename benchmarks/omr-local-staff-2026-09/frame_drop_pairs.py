"""out/print/ledgers/frame_drop_pairs.png -- every Litolff p3 far head the reader gets right in one raster and
wrong in the other: left tile = the scorers' raster (fitz render, NOT deskewed), right tile = the gather's
raster (deskewed), cut at the gather's 600 dpi (3x nearest-neighbour enlargement, no smoothing), the SAME
pixel window in both, the record's box and staff lines laid over both exactly as each arm does.
Every drawn row is re-measured against the source pixel rows (`verify`) before the sheet is saved."""
from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np, cv2
import frame_drop_arms as F
import edge_census as ec
from tools.omr.annotate import ledger_grid as lg

SEAN = {"glyph/3/0/0/6/2": [-6]}
S = 3                                           # enlargement
BLUE, GREEN, ORANGE, RED, MAGENTA = (200, 90, 0), (40, 160, 20), (0, 140, 255), (30, 30, 230), (200, 0, 200)  # BGR
OUT = Path(__file__).resolve().parents[2] / "out/print/ledgers/frame_drop_pairs.png"


def capture_read(fp, h, gl):
    """Read `h` and capture what the reader used: the rung rows and the box handed to the step rule."""
    cap = {}
    orig = lg.derive_far_head_step

    def spy(rungs_y, edge_y, sign, head_near_y, spacing, **kw):
        cap.update(rungs=list(rungs_y), box=tuple(kw["head_box"]), edge=edge_y, sign=sign, sp=spacing)
        return orig(rungs_y, edge_y, sign, head_near_y, spacing, **kw)
    lg.derive_far_head_step = spy
    try:
        r = fp.read(h["subject"], h["box"], h["cls"], gl)
    finally:
        lg.derive_far_head_step = orig
    lines = F.FH.frame_lines_for_head(fp.gray, gl, h["box"])
    return r, cap, lines


def y_of_pos(lines, p):
    top, bot = min(lines), max(lines)
    return top + p * (bot - top) / 8.0


def draw_tile(gray, win, lines, cap, read_pos, ref_pos, title, drawn):
    x0, y0, x1, y1 = win
    crop = gray[y0:y1, x0:x1]
    img = cv2.cvtColor(cv2.resize(crop, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)
    H, W = img.shape[:2]

    def row_of(y):                                # row y (pixel centre y+0.5) -> output row
        return int(round((y - y0 + 0.5) * S - 0.5))

    def col_of(x):
        return int(round((x - x0) * S))

    for y in lines:                                # local staff lines
        r = row_of(y)
        if 0 <= r < H:
            img[r, :] = BLUE
            drawn.append(("staff", y, r, title))
    for y in cap.get("rungs", []):                 # the ledger rows the reader used (dashed)
        r = row_of(y)
        if 0 <= r < H:
            for c in range(0, W, 12):
                img[r, c:c + 7] = GREEN
            drawn.append(("ledger", y, r, title))
    if "box" in cap:                               # the box the step rule used
        b = cap["box"]
        cv2.rectangle(img, (col_of(b[0]), row_of(b[1])), (col_of(b[2]), row_of(b[3])), ORANGE, 2)
    for p, col, side, tag in ((read_pos, RED, 0, "read"), (ref_pos, MAGENTA, 1, "ref")):
        if p is None:
            continue
        y = y_of_pos(lines, p)
        r = row_of(y)
        if 0 <= r < H:
            c0, c1 = (0, 22) if side == 0 else (W - 22, W)
            img[r - 1:r + 2, c0:c1] = col
            drawn.append((tag, y, r, title))
    img = cv2.copyMakeBorder(img, 20, 20, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(img, title, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    return img


def band_centre(gray, y, x0, x1, reach=5, max_thick=8):
    """Centre row of the dark run (gray < 128) nearest the overlay row `y`, taken column by column over
    [x0, x1) and median-ed; only runs thinner than `max_thick` px count (a head or stem is not a line)."""
    cs = []
    yi = int(round(y))
    for x in range(x0, x1):
        col = gray[yi - reach - 8:yi + reach + 9, x] < 128
        base = yi - reach - 8
        runs, i = [], 0
        while i < len(col):
            if col[i]:
                j = i
                while j < len(col) and col[j]:
                    j += 1
                runs.append((base + i, base + j - 1))
                i = j
            else:
                i += 1
        runs = [(a_, b_) for a_, b_ in runs if (b_ - a_ + 1) <= max_thick and a_ - 1 <= y <= b_ + reach]
        if runs:
            a_, b_ = min(runs, key=lambda r: abs((r[0] + r[1]) / 2.0 - y))
            cs.append((a_ + b_) / 2.0)
    return float(np.median(cs)) if len(cs) >= 8 else None


def verify(drawn, rasters, wins):
    """Re-measure every drawn row against pixel rows. (1) the output row of each overlay must map back to the
    source y it was drawn for (checked to 1/6 px); (2) each staff/ledger overlay is compared with the centre
    of the dark band under it, measured independently in the tile's two flank strips. Returns per-kind lists of
    (overlay - band centre) in source px."""
    off = {"staff": [], "ledger": []}
    for kind, y, r, title in drawn:
        if kind not in off:
            continue
        gray, win = rasters[title], wins[title]
        back = (r + 0.5) / S + win[1] - 0.5
        assert abs(back - y) <= 0.5 / S + 1e-6, (kind, y, back)
        cx = (win[0] + win[2]) // 2
        strips = ((win[0], win[0] + 18), (win[2] - 18, win[2])) if kind == "staff" else ((cx - 30, cx - 13), (cx + 14, cx + 31))
        for a_, b_ in strips:
            c = band_centre(gray, y, a_, b_)
            if c is not None:
                off[kind].append(y - c)
    return off


if __name__ == "__main__":
    L = F.load()
    shp = L["D"]["shapes"][F.PAGE]
    shape = dict(width_sp=shp["width_sp"], height_sp=shp["height_sp"], tilt_deg=shp["tilt_deg"])
    sk = lambda s: "staff/" + "/".join(s.split("/")[1:4])
    far = {h["subject"]: h for h in L["D"]["far"] if h["page"] == F.PAGE}
    fps = {}
    for name, gray in (("A", L["gray_A"]), ("B", L["gray_B"])):
        fp = F.FH.FarHeadPage(gray, L["heads"], L["page_boxes"], L["staff_lines"])
        fp.adopt(shape, "scorer")
        fps[name] = fp
    results = {}
    for s, h in far.items():
        ref = SEAN.get(s, h["truth"])
        gl = L["staff_lines"][sk(s)]
        results[s] = {k: capture_read(fps[k], h, gl) for k in "AB"}
        results[s]["ref"] = ref
    flips = [s for s in far if (ec.verdict(results[s]["A"][0]["pos"], results[s]["ref"]) == "right")
             != (ec.verdict(results[s]["B"][0]["pos"], results[s]["ref"]) == "right")]
    print("heads right in one raster only:", len(flips), flips)
    tiles, drawn, rasters, wins = [], [], {}, {}
    for s in flips:
        h = far[s]
        ref = results[s]["ref"]
        b = h["box"]
        row = []
        # window: same pixels in both rasters; tall enough for the staff edge, the head, ledgers and both ticks
        ys = [b[1], b[3]]
        for k in "AB":
            r, cap, lines = results[s][k]
            ys += [min(lines), max(lines)] + cap.get("rungs", [])
            ys += [y_of_pos(lines, p) for p in (r["pos"], ref[0]) if p is not None]
        edge_pick = min(ys, key=lambda y: abs(y - (b[1] + b[3]) / 2)) if False else None
        cy = (b[1] + b[3]) / 2
        top_lines = min(min(results[s][k][2]) for k in "AB")
        bot_lines = max(max(results[s][k][2]) for k in "AB")
        near_staff = top_lines if cy < top_lines else bot_lines
        lo, hi = sorted([cy, near_staff])
        pad = 22
        x0, x1 = int(round((b[0] + b[2]) / 2 - 42)), int(round((b[0] + b[2]) / 2 + 42))
        y0, y1 = int(lo - 2 * 15.75 - pad), int(hi + 15.75 + pad)
        y1 = max(y1, int(hi + pad))
        win = (x0, y0, x1, y1)
        for k, gray in (("A", L["gray_A"]), ("B", L["gray_B"])):
            r, cap, lines = results[s][k]
            title = f"{'A undeskewed' if k == 'A' else 'B deskewed'} {s.replace('glyph/', '')}"
            rasters[title], wins[title] = gray, win
            ok = ec.verdict(r["pos"], ref)
            sub = f"read {r['pos']} ref {ref[0]} {ok}"
            img = draw_tile(gray, win, lines, cap, r["pos"], ref[0], title, drawn)
            cv2.putText(img, sub, (4, img.shape[0] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        (0, 120, 0) if ok == "right" else (0, 0, 200), 1, cv2.LINE_AA)
            row.append(img)
        tiles.append(row)
    off = verify(drawn, rasters, wins)
    n_led = sum(1 for d in drawn if d[0] == "ledger")
    print("ledger rows drawn:", n_led, "(each sampled in two flank strips; rows with no ink band there are rungs the reader restored/implied, not seen)")
    for kind, v in off.items():
        v = np.array(v)
        print(f"re-measured {kind} overlays vs dark-band centre (overlay minus ink, px): n={len(v)} "
              f"median {np.median(v):+.2f} p10 {np.percentile(v, 10):+.2f} p90 {np.percentile(v, 90):+.2f}")
    for t in ("A undeskewed", "B deskewed"):
        v = np.array([y - c for kind, y, r, title in drawn if kind == "staff" and title.startswith(t)
                      for c in [band_centre(rasters[title], y, wins[title][0], wins[title][0] + 18)] if c is not None])
        print(f"  staff overlays, {t}: median {np.median(v):+.2f} px (n={len(v)})")
    # lay out: 3 pairs per sheet row
    per = 3
    sheet_rows = []
    for i in range(0, len(tiles), per):
        group = tiles[i:i + per]
        hmax = max(t.shape[0] for pair in group for t in pair)
        cells = []
        for pair in group:
            for t in pair:
                pad_b = hmax - t.shape[0]
                cells.append(cv2.copyMakeBorder(t, 0, pad_b, 3, 3, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
            cells.append(np.full((hmax, 14, 3), 90, np.uint8))
        sheet_rows.append(np.hstack(cells[:-1]))
    Wmax = max(r.shape[1] for r in sheet_rows)
    sheet_rows = [cv2.copyMakeBorder(r, 0, 10, 0, Wmax - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in sheet_rows]
    body = np.vstack(sheet_rows)
    caps = [("blue", BLUE, "the five staff lines, re-measured in THAT raster at the head's x"),
            ("green dashes", GREEN, "the ledger rows the reader counted"),
            ("orange box", ORANGE, "the head box the through-the-head test used, as the record gives it"),
            ("red bar (left edge)", RED, "the position the reader read"),
            ("magenta bar (right edge)", MAGENTA, "the reference position (Sean's -6 for 6/2)")]
    top = np.full((len(caps) * 20 + 56, body.shape[1], 3), 255, np.uint8)
    cv2.putText(top, "Left of each pair: undeskewed fitz render (what the 10-04 scorers read). Right: the gather's deskewed raster. Same pixels, 3x, record boxes laid on both.",
                (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(top, "Title colour of the verdict line: green = read matches the reference, red = it does not.", (6, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    for i, (nm, col, txt) in enumerate(caps):
        y = 56 + i * 20
        cv2.rectangle(top, (6, y - 11), (30, y + 3), col, -1)
        cv2.putText(top, f"{nm}: {txt}.", (38, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    out = np.vstack([top, body])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), out)
    print("wrote", OUT, out.shape)
