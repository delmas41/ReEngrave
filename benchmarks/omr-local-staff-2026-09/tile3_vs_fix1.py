#!/usr/bin/env python3
"""lane-tile3-measure (2026-10-04) -- MEASUREMENT + ONE CROP SHEET ONLY.

Question (ROADMAP START HERE, open item 1): Litolff `glyph/3/0/8/6/10` (below
the staff) has a thin line touching its STAFF-SIDE edge; Sean: the head is ON
that line (first ledger below).  Fix 1 (`near_edge_ledgers`) says a ledger
touching the near edge with head ink on the far side only means the head is in
the SPACE beyond it, and that was right on `glyph/3/0/7/0/7` and
`glyph/3/0/8/9/0`.  What separates them?

No reader change; `tools/` untouched.  The reader is only CALLED, to list
which heads fix 1 actually fires on (control: exactly the two right cases on
Litolff, none on Brahms).  Every number is in staff spaces `sp` of the LOCAL
staff lines at the head's x (`h["lines"]`, CLAUDE.md section 10), on the page
raster at the gather DPI (600), ink = gray < 140.

For each far head, each ladder rung (the bare ink walk, `stage0_candidates`,
nearest-the-staff first) within the near-edge band rn in [-0.35, +0.60] sp of
the box's staff-side edge is measured:
  line_row      row of the thin line, refined from the ink on both sides of
                the head (a zone 0.1..1.1 sp beside the box)
  line_t        its thickness in px
  jut_L/jut_R   how far the line's ink runs out past the box, per side (sp)
  ink_near/far  the head's own ink edges (central 60% of the box width, the
                contiguous run through the box middle), sp from the line:
                `above` = ink between the line and the staff side,
                `below` = ink on the far side
  frac_stf      above / (above + below)  <- the candidate separating quantity:
                the share of the head's ink that lies on the STAFF side of the
                line.  ~0 : the line is the head's staff-side edge (head hangs
                beyond it, in the space);  ~0.3-0.5 : the line crosses the
                head (head ON it)
  box vs ink    detector box edge minus ink edge, per side (sp)
  width         widest ink row of the head body (rows off the line), sp
  fill          ink fraction in the middle 50% x 50% of the ink extent
                (filled ~1, hollow << 1)
Truth class per head: ON (reference position == the rung's line position),
SPACE (== the space beyond it), OTHER.

    python3 benchmarks/omr-local-staff-2026-09/tile3_vs_fix1.py [--json f] [--sheet out.png]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import edge_census as ec  # noqa: E402
import score_exclusion as se  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

INK = 140
BAND = (-0.35, 0.60)          # rn: rung distance from the staff-side box edge, sp
TILE3 = "glyph/3/0/8/6/10"
FIX1_RIGHT = ["glyph/3/0/7/0/7", "glyph/3/0/8/9/0"]


def inkmap(h):
    return h["gray"] < INK


def band_rows(ink, xa, xb, y, sp, need=0.5):
    """Rows within y +- 0.7 sp whose ink fraction across columns xa..xb >= need,
    as the contiguous band nearest y: (lo, hi) inclusive or None."""
    H, W = ink.shape
    xa, xb = max(0, int(round(xa))), min(W, int(round(xb)))
    if xb <= xa:
        return None
    r0, r1 = max(0, int(y - 0.35 * sp)), min(H, int(y + 0.35 * sp) + 1)
    frac = ink[r0:r1, xa:xb].mean(axis=1)
    ok = frac >= need
    best = None
    i = 0
    while i < len(ok):
        if ok[i]:
            j = i
            while j + 1 < len(ok) and ok[j + 1]:
                j += 1
            c = (i + j) / 2.0 + r0
            if best is None or abs(c - y) < abs(best[2] - y):
                best = (i + r0, j + r0, c)
            i = j + 1
        else:
            i += 1
    return best


def measure(h, y_rung, sign, sp):
    ink = inkmap(h)
    x0, y0, x1, y1 = h["box"]
    cx = (x0 + x1) / 2.0
    zl = (x0 - 0.30 * sp, x0 + 0.05 * sp)
    zr = (x1 - 0.05 * sp, x1 + 0.30 * sp)
    # jut: ink on the line's row running out past the box on each side
    jut = {}
    yi = int(round(y_rung))
    for nm, sgn, xi in (("L", -1, int(round(x0)) + 3), ("R", 1, int(round(x1)) - 3)):
        n, lim = 0, int(1.6 * sp) + 3
        while n < lim:
            x = xi + sgn * n
            if not (0 <= x < ink.shape[1]) or not ink[max(0, yi - 1):yi + 2, x].any():
                break
            n += 1
        xe = xi + sgn * n
        jut[nm] = round(((xe - x1) if sgn > 0 else (x0 - xe)) / sp, 2)
    # the line's own row: bands in the two zones beside the head
    bl = band_rows(ink, zl[0], zl[1], y_rung, sp, 0.3)
    br = band_rows(ink, zr[0], zr[1], y_rung, sp, 0.3)
    cs = [b[2] for b in (bl, br) if b]
    ts_ = [b[1] - b[0] + 1 for b in (bl, br) if b]
    line_row = float(np.mean(cs)) if cs else float(y_rung)
    line_t = float(max(ts_)) if ts_ else float("nan")
    # head ink extent: central 60% of the box width, contiguous run through the middle
    w = x1 - x0
    xa, xb = int(round(cx - 0.3 * w)), int(round(cx + 0.3 * w)) + 1
    r0, r1 = int(y0 - 0.4 * sp), int(y1 + 0.4 * sp) + 1
    prof = ink[r0:r1, xa:xb].mean(axis=1) >= 0.5
    mid = int(round((y0 + y1) / 2.0)) - r0
    if not prof.any():
        return None
    idx = np.where(prof)[0]
    s = int(idx[np.argmin(np.abs(idx - mid))])
    a = b = s
    gap = 0
    while a > 0 and (prof[a - 1] or (a > 1 and prof[a - 2])):
        a -= 1
    while b < len(prof) - 1 and (prof[b + 1] or (b < len(prof) - 2 and prof[b + 2])):
        b += 1
    top, bot = a + r0, b + r0 + 1.0
    near_ink, far_ink = (bot, top) if sign < 0 else (top, bot)
    above = sign * (line_row - near_ink) / sp       # head ink on the staff side of the line
    below = sign * (far_ink - line_row) / sp        # head ink on the far side
    ht = above + below
    # width / fill of the head body
    off = max(line_t if line_t == line_t else 2.0, 2.0) / 2.0 + 1.0
    widest = 0
    for r in range(int(top), int(bot)):
        if abs(r - line_row) <= off:
            continue
        row = ink[r, int(x0 - 1.0 * sp):int(x1 + 1.0 * sp) + 1]
        # contiguous run through the head centre column
        c = int(cx) - int(x0 - 1.0 * sp)
        if not row[min(max(c, 0), len(row) - 1)]:
            continue
        l = r2 = c
        while l > 0 and row[l - 1]:
            l -= 1
        while r2 < len(row) - 1 and row[r2 + 1]:
            r2 += 1
        widest = max(widest, r2 - l + 1)
    hh = bot - top
    fy0, fy1 = int(top + 0.25 * hh), int(bot - 0.25 * hh)
    fx0, fx1 = int(x0 + 0.25 * w), int(x1 - 0.25 * w) + 1
    fill = float(ink[fy0:fy1, fx0:fx1].mean()) if fy1 > fy0 and fx1 > fx0 else float("nan")
    bt, bb = (y1, y0) if sign < 0 else (y0, y1)   # near-edge, far-edge box rows
    return dict(line_row=round(line_row, 1), line_t=line_t, jut_L=jut["L"], jut_R=jut["R"],
                ink_top=top, ink_bot=bot, above=round(above, 2), below=round(below, 2),
                frac_stf=round(above / ht, 3) if ht > 0 else None, ink_h=round(ht, 2),
                box_minus_ink_near=round(sign * (near_edge(h, sign) - near_ink) / sp, 2),
                box_minus_ink_far=round(sign * (far_ink - far_edge(h, sign)) / sp, 2),
                width_sp=round(widest / sp, 2), fill=round(fill, 2),
                box_w_sp=round(w / sp, 2), box_h_sp=round((y1 - y0) / sp, 2))


def near_edge(h, sign):
    x0, y0, x1, y1 = h["box"]
    return y1 if sign < 0 else y0


def far_edge(h, sign):
    x0, y0, x1, y1 = h["box"]
    return y0 if sign < 0 else y1


def run():
    fires = {}
    calls = []
    orig = lg.near_edge_ledger_evidence

    def wrap(img, y, box, *a, **k):
        r = orig(img, y, box, *a, **k)
        calls.append((y, r))
        return r
    lg.near_edge_ledger_evidence = wrap
    lg.rung_is_near_edge_ledger = lambda *a, **k: bool(wrap(*a, **k)["ok"])
    rows = []
    for d in ts.DOCS:
        for h in ec.load_heads(d):
            calls.clear()
            pos, reason = se.read(h)
            fires[h["subject"]] = [dict(y=y, ok=r["ok"], why=r["why"], body=r.get("body"))
                                   for y, r in calls]
            ys = sorted(float(v) for v in h["lines"])
            sp = (ys[-1] - ys[0]) / 4.0
            side, s0 = ec.stage0_candidates(h)
            sign = -1.0 if side == "above" else 1.0
            edge = ys[0] if sign < 0 else ys[-1]
            lad = []
            for y in sorted(s0, key=lambda v: sign * (v - edge)):
                if lad and abs(y - lad[-1]) < 0.5 * sp:
                    continue
                lad.append(y)
            cand = None
            for n, y in enumerate(lad, start=1):
                rn = ec._rel_numbers(y, h["box"], sp, sign)[0]
                if BAND[0] <= rn <= BAND[1]:
                    cand = (n, y, rn)          # outermost qualifying
            if cand is None:
                continue
            n, y, rn = cand
            base = 0 if sign < 0 else 8
            on_pos = int(base + sign * 2 * n)
            sp_pos = int(base + sign * (2 * n + 1))
            m = measure(h, y, sign, sp)
            if m is None:
                continue
            bi = lg.head_body_ink_either_side(h["gray"], y, h["box"], sign, sp, 2.0, None)
            m["body_staff"], m["body_far"] = round(bi["staff"], 2), round(bi["far"], 2)
            tr = h["truth"]
            cls = "ON" if on_pos in tr else ("SPACE" if sp_pos in tr else "OTHER")
            rows.append(dict(doc=d, subject=h["subject"], page=h["page"], box=list(h["box"]),
                             sign=sign, sp=round(sp, 2), n=n, rung_y=round(y, 1), rn=round(rn, 2),
                             on_pos=on_pos, space_pos=sp_pos, truth=tr, cls=cls,
                             answer=pos, answer_v=ec.verdict(pos, tr), reason=reason,
                             fix1=[c for c in fires[h["subject"]]], **m))
    return rows, fires


# ---------------------------------------------------------------------------
# the crop sheet
# ---------------------------------------------------------------------------
SCALE = 5
RN_MIN = 0.15      # rung INSIDE the box: the only case fix 1 decides


def tile(h, r):
    import cv2
    x0, y0, x1, y1 = h["box"]
    sp = r["sp"]
    gx0, gx1 = int(x0 - 2.2 * sp), int(x1 + 2.2 * sp)
    gy0, gy1 = int(y0 - 1.9 * sp), int(y1 + 1.9 * sp)
    g = h["gray"][max(0, gy0):gy1, max(0, gx0):gx1]
    big = cv2.resize(g, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_NEAREST)
    im = cv2.cvtColor(big, cv2.COLOR_GRAY2BGR)
    W = im.shape[1]
    X = lambda x: int(round((x - gx0 + 0.5) * SCALE))
    Y = lambda y: int(round((y - gy0 + 0.5) * SCALE))
    # local staff lines at the head's x (blue), only those inside the window
    for yl in h["lines"]:
        if gy0 <= yl <= gy1:
            cv2.line(im, (0, Y(yl)), (W - 1, Y(yl)), (255, 120, 0), 1)
    # the measured line row of the near-edge rung (magenta), both sides of the head
    yr = r["line_row"]
    cv2.line(im, (0, Y(yr)), (X(x0) - 4, Y(yr)), (255, 0, 255), 1)
    cv2.line(im, (X(x1) + 4, Y(yr)), (W - 1, Y(yr)), (255, 0, 255), 1)
    # measured head ink top / bottom (orange ticks inside the box columns)
    for yy in (r["ink_top"], r["ink_bot"]):
        cv2.line(im, (X(x0) + 6, Y(yy)), (X(x1) - 6, Y(yy)), (0, 140, 255), 1)
    # corner bracket on the detector box (green)
    L = int(0.35 * sp * SCALE)
    for (cx_, cy_, dx, dy) in ((X(x0), Y(y0), 1, 1), (X(x1), Y(y0), -1, 1),
                               (X(x0), Y(y1), 1, -1), (X(x1), Y(y1), -1, -1)):
        cv2.line(im, (cx_, cy_), (cx_ + dx * L, cy_), (0, 170, 0), 2)
        cv2.line(im, (cx_, cy_), (cx_, cy_ + dy * L), (0, 170, 0), 2)
    return im


def sheet(rows, out):
    import cv2
    heads = {}
    for d in ts.DOCS:
        for h in ec.load_heads(d):
            heads[h["subject"]] = h
    sel = [r for r in rows if r["rn"] >= RN_MIN and r["cls"] in ("ON", "SPACE")]
    order = {TILE3: 0, FIX1_RIGHT[0]: 1, FIX1_RIGHT[1]: 2}
    sel.sort(key=lambda r: (order.get(r["subject"], 9), r["cls"] != "SPACE", r["frac_stf"] or 0))
    tiles = []
    for r in sel:
        im = tile(heads[r["subject"]], r)
        cap = [f"{r['subject']}  ref={r['truth']}  {r['cls']}",
               f"above={r['above']:.2f} below={r['below']:.2f} sp  frac_stf={r['frac_stf']}",
               f"fix1 {'FIRES' if any(c['ok'] for c in r['fix1']) else 'no'}  ours={r['answer']}/{r['answer_v']}"]
        tiles.append((im, cap))
    cw = max(t[0].shape[1] for t in tiles)
    ch = max(t[0].shape[0] for t in tiles)
    tiles = [(cv2.copyMakeBorder(im, 0, ch - im.shape[0], 0, cw - im.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)), cap) for im, cap in tiles]
    cols = 4
    rowsn = (len(tiles) + cols - 1) // cols
    head_h, cap_h = 120, 62
    canvas = np.full((head_h + rowsn * (ch + cap_h), cols * cw, 3), 255, np.uint8)
    key = ["SHEET: Litolff far heads (600 dpi, 5x) whose thin line touches the STAFF-SIDE edge INSIDE the box (rn >= 0.15 sp).",
           "blue = the 5 LOCAL staff lines at the head's x (those in view)   magenta = the measured line row of the near-edge rung (drawn from row pixels)",
           "orange ticks = the head's own ink top and bottom (central 60% of box width)   green corner brackets = the subject head's detector box",
           "first three tiles: tile 3 (Sean: ON the line), then the two fix-1 cases that were right (head in the SPACE beyond). Then the other ON, then SPACE heads."]
    for i, k in enumerate(key):
        cv2.putText(canvas, k, (8, 22 + i * 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    for i, (im, cap) in enumerate(tiles):
        rr, cc = divmod(i, cols)
        y = head_h + rr * (ch + cap_h)
        x = cc * cw
        canvas[y:y + im.shape[0], x:x + im.shape[1]] = im
        for j, c in enumerate(cap):
            cv2.putText(canvas, c, (x + 4, y + ch + 16 + j * 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        (0, 0, 0), 1, cv2.LINE_AA)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out, canvas)
    return sel, heads


def main():
    rows, fires = run()
    print("== which heads fix 1 (rung_is_near_edge_ledger) actually FIRES on (ok=True) ==")
    for s, cs in fires.items():
        if any(c["ok"] for c in cs):
            print("  fires:", s, [(round(c["y"]), c["why"], c["body"]) for c in cs])
    print("  tile 3 calls:", [(round(c["y"]), c["why"], c["body"]) for c in fires.get(TILE3, [])])
    print("\n== heads with a thin-line rung at the near edge (rn in %s), ON/SPACE by reference ==" % (BAND,))
    hdr = ("subject", "cls", "rn", "above", "below", "frac_stf", "ink_h", "line_t", "jutL", "jutR",
           "w_sp", "fill", "bx-ink_n", "bx-ink_f", "fix1")
    print(" ".join(f"{h:>9}" for h in hdr))
    for r in sorted(rows, key=lambda r: (r["cls"], r["frac_stf"] if r["frac_stf"] is not None else 9)):
        f1 = "FIRES" if any(c["ok"] for c in r["fix1"]) else "-"
        print(f"{r['subject'][6:]:>9} {r['cls']:>9} {r['rn']:9.2f} {r['above']:9.2f} {r['below']:9.2f} "
              f"{r['frac_stf']!s:>9} {r['ink_h']:9.2f} {r['line_t']:9.1f} {r['jut_L']:9.2f} {r['jut_R']:9.2f} "
              f"{r['width_sp']:9.2f} {r['fill']:9.2f} {r['box_minus_ink_near']:9.2f} "
              f"{r['box_minus_ink_far']:9.2f} {f1:>9}  ans={r['answer']}/{r['answer_v']}")
    on = [r for r in rows if r["cls"] == "ON" and r["frac_stf"] is not None]
    sp_ = [r for r in rows if r["cls"] == "SPACE" and r["frac_stf"] is not None]
    print(f"\nfrac_stf  ON n={len(on)} min={min(r['frac_stf'] for r in on)} max={max(r['frac_stf'] for r in on)}"
          f" | SPACE n={len(sp_)} min={min(r['frac_stf'] for r in sp_)} max={max(r['frac_stf'] for r in sp_)}")
    for lo in (0.24, 0.245, 0.25):
        print(f"  threshold frac_stf >= {lo}: ON called ON {sum(r['frac_stf'] >= lo for r in on)}/{len(on)};"
              f" SPACE called ON (misfire) {sum(r['frac_stf'] >= lo for r in sp_)}/{len(sp_)}")
    print("fix-1's own body-ink fractions (staff-side band / far-side band), rn>=0.15:")
    for r in rows:
        if r["rn"] >= RN_MIN and r["cls"] in ("ON", "SPACE"):
            print(f"  {r['subject'][6:]:>10} {r['cls']:>5} staff={r['body_staff']:.2f} far={r['body_far']:.2f}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(rows, indent=1, default=str))
    if "--sheet" in sys.argv:
        sel, heads = sheet(rows, sys.argv[sys.argv.index("--sheet") + 1])
        print("sheet tiles:", [r["subject"] for r in sel])
        # re-measure the DRAWN lines against pixel rows (two past lanes drew lines that missed the ink)
        bad = 0
        for r in sel:
            h = heads[r["subject"]]
            ink = inkmap(h)
            x0, y0, x1, y1 = h["box"]
            sp = r["sp"]
            yi = int(round(r["line_row"]))
            ears = [ink[yi - 1:yi + 2, int(x0 - 0.3 * sp):int(x0 + 0.05 * sp) + 1].any(),
                    ink[yi - 1:yi + 2, int(x1 - 0.05 * sp):int(x1 + 0.3 * sp) + 1].any()]
            cx0, cx1 = int((x0 + x1) / 2 - 0.15 * (x1 - x0)), int((x0 + x1) / 2 + 0.15 * (x1 - x0))
            t_in = ink[int(r["ink_top"]):int(r["ink_top"]) + 2, cx0:cx1].any()
            b_in = ink[int(r["ink_bot"]) - 2:int(r["ink_bot"]), cx0:cx1].any()
            t_out = ink[int(r["ink_top"]) - 2:int(r["ink_top"]) - 1, cx0:cx1].any()
            b_out = ink[int(r["ink_bot"]) + 1:int(r["ink_bot"]) + 2, cx0:cx1].any()
            ok = any(ears) and t_in and b_in and not (t_out and b_out)
            bad += (not ok)
            print(f"  drawn-vs-pixels {r['subject'][6:]:>10}: line row has ink at an ear {ears}, "
                  f"ink rows ok {t_in and b_in}, edges clean {not t_out} {not b_out} -> {'OK' if ok else 'MISS'}")
        print("drawn lines missing the ink:", bad)
    return rows


if __name__ == "__main__":
    main()
