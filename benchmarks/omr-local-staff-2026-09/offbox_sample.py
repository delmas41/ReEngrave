"""lane-offbox-check: out/print/ledgers/offbox_sample.png -- 8 seeded-random decided far heads from the 10-04 RUN 2 whose
READER answer fails the off-box check (4 Litolff, 4 Brahms; replay reproduced the record; rows = the reader's measured
ledgers).  Red full-width line = the line the answer names (for an in-space answer: the line on its staff side, the
one the rule tests); orange = the detector box; blue = the local staff lines; green dashes = the ledger rows the
reader measured.  Every drawn row is re-measured against pixel rows (`verify`) and the named line against the ink
beside the head.

  python3 offbox_sample.py <offbox.json> <dir with m_RUN2_<doc>.json> [--seed 20261005]
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np, cv2
import frame_drop_pairs as P
import offbox_check as C
import overnight_1004_report as R
import truth_set_2_44c as ts
from frame import render_page_matching_gather

S = P.S
BLUE, GREEN, ORANGE, RED = P.BLUE, P.GREEN, P.ORANGE, P.RED
OUT = HERE.parents[1] / "out/print/ledgers/offbox_sample.png"
ORD = {1: "1st", 2: "2nd", 3: "3rd"}


def ordinal(n):
    return ORD.get(n, f"{n}th")


def words(q):
    """'on 3rd ledger below' / 'in the space above the 2nd ledger above' ..."""
    if 0 <= q <= 8:
        if q % 2 == 0:
            return f"on staff line {q // 2 + 1} (top = 1)"
        return f"in staff space {(q + 1) // 2} (top = 1)"
    side = "above" if q < 0 else "below"
    if q % 2 == 0:
        n = (-q // 2) if q < 0 else ((q - 8) // 2)
        return f"on {ordinal(n)} ledger {side}"
    if q == -1:
        return "in the space above the top line"
    if q == 9:
        return "in the space below the bottom line"
    n = ((-q - 1) // 2) if q < 0 else ((q - 9) // 2)
    return f"in the space {side} the {ordinal(n)} ledger {side}"


def named_row(q, rows):
    """The row of the line the answer names (an in-space answer: the line on its staff side)."""
    if q % 2 == 0:
        return rows.y(q)
    return rows.y(C.bounding_lines(q)[0])


def draw(gray, g, rows, rungs, q_read, q_geo, title, num, drawn, rasters, wins, meas):
    box = g["box"]
    lines = g["lines"]
    sp = rows.sp
    cx = (box[0] + box[2]) / 2
    yn = named_row(q_read, rows)
    ys = [box[1], box[3], yn, rows.top if box[3] < rows.top else rows.bot] + list(rungs)
    y0, y1 = int(min(ys) - 0.9 * sp), int(max(ys) + 0.9 * sp)
    # keep the staff edge nearest the head in view so the count of ledgers is visible
    win = (int(round(cx - 3.2 * sp)), y0, int(round(cx + 3.2 * sp)), y1)
    x0, y0, x1, y1 = win
    crop = gray[y0:y1, x0:x1]
    img = cv2.cvtColor(cv2.resize(crop, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)
    H, W = img.shape[:2]
    row_of = lambda y: int(round((y - y0 + 0.5) * S - 0.5))
    col_of = lambda x: int(round((x - x0) * S))
    for y in lines:
        r = row_of(y)
        if 0 <= r < H:
            img[r, :] = BLUE
            drawn.append(("staff", y, r, title))
    for y in rungs:
        r = row_of(y)
        if 0 <= r < H:
            for c in range(0, W, 12):
                img[r, c:c + 7] = GREEN
    b = box
    cv2.rectangle(img, (col_of(b[0]), row_of(b[1])), (col_of(b[2]), row_of(b[3])), ORANGE, 2)
    r = row_of(yn)
    if 0 <= r < H:
        img[max(0, r - 1):r + 1, :] = RED
        drawn.append(("named", yn, r, title))
    rasters[title], wins[title] = gray, win
    # re-measure the named line against the ink beside the head (flank strips just outside the box)
    fl = []
    for a_, b_ in ((int(b[0]) - 16, int(b[0]) - 3), (int(b[2]) + 3, int(b[2]) + 16)):
        c = P.band_centre(gray, yn, a_, b_)
        if c is not None:
            fl.append(yn - c)
    meas.append(("named_line_vs_ink", fl))
    near = C.off_steps(q_read, box, rows)
    k = C.named_kinds(q_read, rows)
    img = cv2.copyMakeBorder(img, 54, 0, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(img, f"{num}  {title}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(img, f"reader says: {words(q_read)}", (4, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 200), 1, cv2.LINE_AA)
    cv2.putText(img, f"geometry: {words(q_geo)}", (4, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 0, 150), 1, cv2.LINE_AA)
    cv2.putText(img, f"nearest passing: {'none' if near is None else str(near) + ' step(s)'}; line {'/'.join(k)}", (4, 53),
                cv2.FONT_HERSHEY_SIMPLEX, 0.34, (60, 60, 60), 1, cv2.LINE_AA)
    return img


def main(path, mdir, seed=20261005):
    res = json.loads(Path(path).read_text())
    rng = random.Random(seed)
    tiles, drawn, rasters, wins, meas, meta = [], [], {}, {}, [], []
    for doc, D in res.items():
        M = json.loads((Path(mdir) / f"m_RUN2_{doc}.json").read_text())["heads"]
        H = D["heads"]["RUN2"]
        cand = sorted(s for s, g in H.items() if g["dec"] is not None and M.get(s, {}).get("repro")
                      and not C.passes(g["dec"], g["box"], C.Rows(g["lines"], M[s]["rungs"])))
        print(doc, "off-box reader answers (repro):", len(cand))
        pick = rng.sample(cand, 4)
        pdf = ts.DOCS[doc]["pdf"]
        for s in pick:
            g = H[s]
            page = R.page_of(s)
            pi = render_page_matching_gather(pdf, page, 600)
            gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
            rows = C.Rows(g["lines"], M[s]["rungs"])
            title = f"{doc.split('-')[0][:5]} p{page} {s.replace('glyph/', '')}"
            tiles.append(draw(gray, g, rows, M[s]["rungs"], g["dec"], g["geo"], title, len(tiles) + 1, drawn, rasters, wins, meas))
            meta.append(dict(n=len(tiles), doc=doc, subject=s, reader=g["dec"], geometry=g["geo"], box_source=g["box_source"],
                             nearest_passing_steps=C.off_steps(g["dec"], g["box"], rows), kinds=C.named_kinds(g["dec"], rows),
                             geometry_passes=bool(C.passes(g["geo"], g["box"], rows))))
    off = P.verify(drawn, rasters, wins)
    v = np.array(off["staff"])
    print(f"re-measured staff overlays vs dark-band centre (px): n={len(v)} median {np.median(v):+.2f} p10 {np.percentile(v, 10):+.2f} p90 {np.percentile(v, 90):+.2f}")
    assert abs(np.median(v)) <= 1.5, "staff overlay off the ink: sheet NOT saved"
    named = [x for (_, fl) in meas for x in fl]
    ink_tiles = sum(1 for (_, fl) in meas if fl)
    if named:
        print(f"named line vs ink beside the head: tiles with ink under the line {ink_tiles}/{len(meas)}; offsets n={len(named)} "
              f"median {np.median(named):+.2f} px (overlay minus ink)")
    else:
        print("named line vs ink beside the head: no tile has ink under the line")
    per = 4
    rows_img = []
    for i in range(0, len(tiles), per):
        grp = tiles[i:i + per]
        hmax = max(t.shape[0] for t in grp)
        cells = []
        for t in grp:
            cells.append(cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 3, 3, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
            cells.append(np.full((hmax, 8, 3), 90, np.uint8))
        rows_img.append(np.hstack(cells[:-1]))
    Wm = max(r.shape[1] for r in rows_img)
    rows_img = [cv2.copyMakeBorder(r, 0, 10, 0, Wm - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows_img]
    body = np.vstack(rows_img)
    caps = [("red full-width line", RED, "the line the reader's answer names (an in-space answer: the line on its staff side)"),
            ("orange box", ORANGE, "the detector's box for the head"),
            ("blue", BLUE, "the local staff lines at the head"),
            ("green dashes", GREEN, "the ledger rows the reader measured (from a replay of the reader)")]
    top = np.full((len(caps) * 18 + 44, Wm, 3), 255, np.uint8)
    cv2.putText(top, "Reader answers that fail Sean's rule (named line must run through the box, or sit on its staff-side edge). "
                "8 seeded draws (seed %d), 4 Litolff / 4 Brahms, 10-04 RUN 2; 3x, gather frame." % seed, (6, 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
    for i, (nm, col, txt) in enumerate(caps):
        y = 40 + i * 18
        cv2.rectangle(top, (6, y - 10), (28, y + 2), col, -1)
        cv2.putText(top, f"{nm}: {txt}.", (36, y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
    out = np.vstack([top, body])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), out)
    (OUT.parent / "offbox_sample.json").write_text(json.dumps(dict(seed=seed, tiles=meta), indent=1))
    print("wrote", OUT, out.shape)
    for m in meta:
        print(m)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261005)
