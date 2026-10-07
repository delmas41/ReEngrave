"""out/print/ledgers/jut_from_ink.png -- every Litolff p3 far head whose read CHANGES when the jut is measured
from the head's ink instead of the box edge. Correct frame only (the gather's deskewed raster, the record's
boxes). Left tile: box-edge test (old). Right tile: ink-edge test (new). Same pixels, 3x nearest-neighbour,
cut at the gather's 600 dpi. Every drawn row is re-measured against the source pixel rows before saving."""
from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np, cv2
import frame_drop_arms as F
import frame_drop_pairs as P
import jut_from_ink_eval as J
from tools.omr.annotate import ledger_grid as lg

S = P.S
CYAN, YELLOW = (200, 200, 0), (0, 215, 255)
OUT = Path(__file__).resolve().parents[2] / "out/print/ledgers/jut_from_ink.png"


def read_with(fp, h, gl, mode):
    F.FH.EXCLUSION_RULES["jut_from_ink"] = (mode == "ink")
    return P.capture_read(fp, h, gl)


def ink_edges(gray, box, lines):
    """Where the ink test puts the head's edges (page x) and the ledger run's ends, at the box middle."""
    spacing = (max(lines) - min(lines)) / 4.0
    r = lg._jut_from_head_ink(gray, box, spacing)
    return r


def draw_ink_marks(img, win, box, gray, lines, tag):
    r = ink_edges(gray, box, lines)
    x0, y0 = win[0], win[1]
    cy = (box[1] + box[3]) / 2.0
    row = int(round((cy - y0 + 0.5) * S - 0.5))
    if "head_x" in r:
        for x, col in ((r["head_x"][0], YELLOW), (r["head_x"][1], YELLOW), (r["run_x"][0], CYAN), (r["run_x"][1], CYAN)):
            c = int(round((x - x0) * S))
            img[max(0, row - 14):row + 15, max(0, c - 1):c + 1] = col
    return r


if __name__ == "__main__":
    L, fp, far = J.prepare("beethoven5-litolff", 3)
    sk = lambda s: "staff/" + "/".join(s.split("/")[1:4])
    old, new = J.run(L, fp, far, "box"), J.run(L, fp, far, "ink")
    changed = [s for s in old if old[s][1] != new[s][1]]
    byid = {h["subject"]: h for h in far}
    print("changed:", changed)
    tiles, drawn, rasters, wins = [], [], {}, {}
    for s in changed:
        h = byid[s]
        ref = J.SEAN.get(s, h["truth"])
        gl = L["staff_lines"][sk(s)]
        b = h["box"]
        res = {m: read_with(fp, h, gl, m) for m in ("box", "ink")}
        cy = (b[1] + b[3]) / 2
        lines = res["box"][2]
        near_staff = min(lines) if cy < min(lines) else max(lines)
        lo, hi = sorted([cy, near_staff])
        pad = 22
        cx = (b[0] + b[2]) / 2
        win = (int(round(cx - 42)), int(lo - 2 * 15.75 - pad), int(round(cx + 42)), max(int(hi + 15.75 + pad), int(hi + pad)))
        row = []
        for m, nm in (("box", "box edge (old)"), ("ink", "ink edge (new)")):
            r, cap, lines = res[m]
            title = f"{nm} {s.replace('glyph/', '')}"
            rasters[title], wins[title] = L["gray_B"], win
            ok = ec_verdict = J.ec.verdict(r["pos"], ref)
            img = P.draw_tile(L["gray_B"], win, lines, cap, r["pos"], ref[0], title, drawn)
            if m == "ink":
                draw_ink_marks(img, win, b, L["gray_B"], lines, m)
            cv2.putText(img, f"read {r['pos']} ref {ref[0]} {ok}", (4, img.shape[0] - 5), cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, (0, 120, 0) if ok == "right" else (0, 0, 200), 1, cv2.LINE_AA)
            row.append(img)
        tiles.append(row)
    off = P.verify(drawn, rasters, wins)
    for kind, v in off.items():
        v = np.array(v)
        print(f"re-measured {kind} overlays vs dark-band centre (overlay minus ink, px): n={len(v)} "
              f"median {np.median(v):+.2f} p10 {np.percentile(v, 10):+.2f} p90 {np.percentile(v, 90):+.2f}")
    per = 3
    rows = []
    for i in range(0, len(tiles), per):
        group = tiles[i:i + per]
        hmax = max(t.shape[0] for pair in group for t in pair)
        cells = []
        for pair in group:
            for t in pair:
                cells.append(cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 3, 3, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
            cells.append(np.full((hmax, 14, 3), 90, np.uint8))
        rows.append(np.hstack(cells[:-1]))
    W = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, 10, 0, W - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]
    body = np.vstack(rows)
    caps = [("blue", P.BLUE, "the five staff lines, re-measured at the head's x"),
            ("green dashes", P.GREEN, "the ledger rows the reader counted"),
            ("orange box", P.ORANGE, "the detector box (the old test measured the jut from its edge)"),
            ("yellow ticks", YELLOW, "where the head's own ink ends on the middle row (the new test measures from here)"),
            ("cyan ticks", CYAN, "where the ledger line ends on that row"),
            ("red bar (left edge)", P.RED, "the position the reader read"),
            ("magenta bar (right edge)", P.MAGENTA, "the reference position (Sean's -6 for 6/2)")]
    top = np.full((len(caps) * 20 + 40, body.shape[1], 3), 255, np.uint8)
    cv2.putText(top, "Left of each pair: jut measured from the box edge. Right: from the head's ink. Same gather raster, same boxes, 3x.",
                (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    for i, (nm, col, txt) in enumerate(caps):
        y = 40 + i * 20
        cv2.rectangle(top, (6, y - 11), (30, y + 3), col, -1)
        cv2.putText(top, f"{nm}: {txt}.", (38, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    out = np.vstack([top, body])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), out)
    print("wrote", OUT, out.shape)
