"""Sheet: 8 worst staves, recorded staff-wide lines (RED, what the far-head path reads) and the per-bar
grid (BLUE, what in-staff positions read), drawn on the print at three x positions
(lane-staff-lines-off-ink, 2026-10-06).  Needs the two JSONs from staff_lines_off_ink.py and
staff_lines_per_bar.py (paths on the command line).

    python3 staff_lines_off_ink_sheet.py off_l.json off_b.json pb_l.json pb_b.json out.png
"""
import json, sys
from pathlib import Path
import numpy as np, cv2

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
from frame import render_page_matching_gather  # noqa: E402
import staff_lines_off_ink as M  # noqa: E402

offl, offb, pbl, pbb, outp = sys.argv[1:6]
off = json.load(open(offl)) + json.load(open(offb))
pb = {(r["doc"], r["staff"]): r for r in json.load(open(pbl)) + json.load(open(pbb))}
# worst 8: one staff per page, by the raw worst point; the last two slots are staves whose PER-BAR grid is
# still off (so the sheet shows where blue fails too)
def worst_raw(r): return np.abs(np.array(r["off"])).max() / r["sp"]
chosen, seen = [], set()
for r in sorted(off, key=lambda r: -worst_raw(r)):
    key = (r["doc"], r["page"])
    if key in seen: continue
    seen.add(key); chosen.append(r)
    if len(chosen) == 6: break
def worst_b(r):
    cs = [c for c in pb[(r["doc"], r["staff"])]["cells"] if c.get("n", 0) >= 6]
    return max((abs(c["b_med"]) for c in cs), default=0) / r["sp"]
for r in sorted(off, key=lambda r: -worst_b(r)):
    key = (r["doc"], r["page"])
    if key in seen: continue
    seen.add(key); chosen.append(r)
    if len(chosen) == 8: break

pdfs = {d: M.recorded_staves(d)[:2] for d in M.DOCS}
pages = {}
HALF, TILT_W = 130, 260
rows_img, report = [], []
for n, r in enumerate(chosen, 1):
    doc, p = r["doc"], r["page"]
    pdf, dpi = pdfs[doc]
    if (doc, p) not in pages:
        pages[(doc, p)] = render_page_matching_gather(pdf, p, dpi=dpi)
    pi = pages[(doc, p)]
    gray = pi.rgb.mean(axis=2)
    lines = np.array(r["lines"]); sp = r["sp"]
    scale = 3 if sp < 20 else 2
    cells = pb[(doc, r["staff"])]["cells"]
    # three x: the staff positions where the raw offset is largest at the left end, the right end and the middle
    xs_all = np.array(r["xs"]); offs = np.array(r["off"]).mean(axis=1)
    pick = [xs_all[int(np.argmax(np.abs(offs)))], xs_all[len(xs_all) // 2], xs_all[int(np.argmin(offs)) if np.abs(offs).max() == abs(offs.max()) else int(np.argmax(offs))]]
    pick = sorted(set(int(x) for x in [xs_all[0], xs_all[int(np.argmax(np.abs(offs)))], xs_all[-1]]))
    while len(pick) < 3:
        pick.append(int(xs_all[len(xs_all) // 2])); pick = sorted(set(pick))
    tiles = []
    for x in pick:
        cell = next((c for c in cells if c["x0"] <= x < c["x1"]), None)
        shift = cell["shift"] if cell else 0
        y0 = int(lines[0] - 2.2 * sp - abs(shift)); y1 = int(lines[-1] + 2.2 * sp + abs(shift)) + 1
        xa = max(0, x - HALF); xb = xa + TILT_W
        crop = pi.rgb[y0:y1, xa:xb].astype(np.uint8)
        big = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST).copy()
        mid = (x - xa) * scale
        for yy in lines:
            cv2.line(big, (0, int((yy - y0) * scale)), (mid - 6, int((yy - y0) * scale)), (255, 0, 0), 1)
        for yy in lines + shift:
            cv2.line(big, (mid + 6, int((yy - y0 + 0.0) * scale)), (big.shape[1] - 1, int((yy - y0) * scale)), (0, 80, 255), 1)
        cv2.line(big, (mid, 0), (mid, 10), (0, 160, 0), 1)
        # control: drawn lines vs pixel rows at the nearest clean column
        best = None
        for xx in range(x - 40, x + 41, 3):
            s = M.sample_column(pi.binary, gray, xx, lines[0], lines[-1], list(lines), sp)
            if s is not None: best = s[0]; break
        if best is not None:
            report.append((n, x, float(np.abs(lines - best).max()), float(np.abs(lines + shift - best).max()),
                           float(np.abs(lines - best).mean()), float(np.abs(lines + shift - best).mean()), shift, "cell" if cell else "NO CELL"))
        tiles.append(big)
    h = max(t.shape[0] for t in tiles)
    tiles = [np.pad(t, ((0, h - t.shape[0]), (4, 4), (0, 0)), constant_values=255) for t in tiles]
    row = np.concatenate(tiles, axis=1)
    label = np.full((26, row.shape[1], 3), 255, np.uint8)
    cv2.putText(label, f"{n}  {doc} staff {r['staff']}  x={pick}  max raw offset {worst_raw(r):.2f} sp", (4, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    rows_img.append(np.concatenate([label, row], axis=0))
W = max(r.shape[1] for r in rows_img)
rows_img = [np.pad(r, ((0, 6), (0, W - r.shape[1]), (0, 0)), constant_values=255) for r in rows_img]
sheet = np.concatenate(rows_img, axis=0)
cv2.imwrite(outp, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
print("wrote", outp, sheet.shape)
print("control, drawn lines vs the pixel rows at the nearest clean column (px): staff, x, raw max, bar max, raw mean, bar mean, shift")
for t in report: print("  ", t)
rm = np.array([t[2] for t in report]); bm = np.array([t[3] for t in report])
print(f"within 2 px at EVERY line: red {int((rm <= 2).sum())}/{len(rm)}, blue {int((bm <= 2).sum())}/{len(bm)}")
