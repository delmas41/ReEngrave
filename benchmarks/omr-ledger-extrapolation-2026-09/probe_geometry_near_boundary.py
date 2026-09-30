"""Near-boundary heads: is plain GEOMETRY (round(NOTEHEAD_STAFF_POSITION))
right, measured on the PAGE binary at the gather's own 600 dpi render?

One gather (+ decide through EVALUATE, for the clef) per page on the 2.44
branch. For each head: map canonical -> page, then MEASURE on the binary:
  * the staff's five lines beside the head (row of max ink near each mapped
    line, over +-3 spaces of x) -- also calibrates the canonical->page y;
  * ledger lines: rows whose horizontal ink run through the head's column is
    >= 1.7 spaces long (a notehead alone is ~1.3), grouped into bands <= 0.35
    spaces thick, walked outward from the staff edge at 0.7..1.45 spaces;
  * the head's own ink rows: contiguous rows inked in the head's middle
    columns (+-0.4 sp), with a line band trimmed off either END (a ledger
    the head merely touches).
Verdict: a ladder line inside the head's middle third -> ON that line;
otherwise the SPACE the head centre sits in (or the space just past the last
found ledger when the head touches it). A head taller than 1.3 spaces
(merged stack) or shorter than 0.55 is UNREADABLE, never guessed.
"""
import json, math, random, sys
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab56d1d321c30c4bd")
import numpy as np

from tools.omr.staged import gather as G
from tools.omr.staged.pipeline import prepare_pages, decide
from tools.omr.staged.record import Q, Subject
from tools.omr.staged import record as R
from tools.omr.annotate.ledger_grid import measure_ledger_rungs
from tools.omr.annotate.server import snap_to_staff
from tools.omr.yolo_detector import YoloDetector
from tools.omr.pitch_resolver import _pitch_from_position

W = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
MARGIN = 0.15
SEAN = {"glyph/3/0/0/2/9": "D6", "glyph/3/0/0/2/4": "F6",
        "glyph/3/0/0/2/3": "D6", "glyph/3/0/0/2/1": "F6"}


def hrun(row, x, sp):
    """(start, end) of the ink run through column x, white gaps <= 0.35 sp
    bridged; None where x is not on or beside ink."""
    xs = np.flatnonzero(row)
    if xs.size == 0:
        return None
    gap = 0.35 * sp
    spans = []
    s = e = xs[0]
    for v in xs[1:]:
        if v - e <= gap:
            e = v
        else:
            spans.append((s, e)); s = e = v
    spans.append((s, e))
    for s, e in spans:
        if s - 1 <= x <= e + 1:
            return (int(s), int(e))
    return None


def hlen(row, x, sp):
    r = hrun(row, x, sp)
    return 0.0 if r is None else float(r[1] - r[0] + 1)


def measure(B, px, py, lines_m, sp, side):
    """B: bool ink page. Returns dict with ladder, head extent, verdict."""
    H, Wd = B.shape
    # the head blob first: contiguous rows inked in the head's middle columns
    hx0, hx1 = int(px - 0.4 * sp), int(px + 0.4 * sp) + 1
    col = B[:, hx0:hx1].mean(axis=1) >= 0.2
    start = None
    for d in range(0, int(0.4 * sp) + 1):
        for y in (int(round(py)) + d, int(round(py)) - d):
            if 0 <= y < H and col[y]:
                start = y; break
        if start is not None:
            break
    t0 = b0 = start
    if start is not None:
        while t0 - 1 >= 0 and col[t0 - 1] and start - t0 < 4 * sp:
            t0 -= 1
        while b0 + 1 < H and col[b0 + 1] and b0 - start < 4 * sp:
            b0 += 1
    x0 = int(max(0, px - 2.2 * sp)); x1 = int(min(Wd, px + 2.2 * sp))
    lx = px - x0
    Wh = 1.25 * sp
    if start is not None:
        ws = [hlen(B[y, x0:x1], lx, sp) for y in range(t0, b0 + 1)]
        ws = [w for w in ws if w > 0]
        if ws:
            Wh = max(1.1 * sp, float(np.median(ws)))
    top, bot = lines_m[0], lines_m[-1]
    if side == "above":
        ya, yb = int(py - 2.2 * sp), int(top - 0.4 * sp)
    else:
        ya, yb = int(bot + 0.4 * sp), int(py + 2.2 * sp)
    ya, yb = max(0, ya), min(H, yb)
    # LEDGERS, the peer's way (Sean's own measurement of 2026-09-30): sample
    # single columns just PAST the head's own left and right ink edges; a
    # ledger shows there as a THIN vertical ink run. The stem is a long run
    # and drops out; so does a neighbour's body.
    rows_c = [y for y in range(int(py - 0.3 * sp), int(py + 0.3 * sp) + 1) if 0 <= y < H]
    runs = [hrun(B[y, x0:x1], lx, sp) for y in rows_c]
    runs = [q for q in runs if q is not None]
    if runs:
        hl = x0 + int(np.median([q[0] for q in runs])); hr_ = x0 + int(np.median([q[1] for q in runs]))
    else:
        hl, hr_ = int(px - 0.65 * sp), int(px + 0.65 * sp)
    off = max(3, int(round(0.2 * sp)))
    maxthin = 0.35 * sp
    found = []   # (centre y, side)
    for side_x, cols in (("L", [hl - 1 - k for k in range(off)]), ("R", [hr_ + 1 + k for k in range(off)])):
        per_col = []
        for cx_ in cols:
            if not (0 <= cx_ < Wd):
                continue
            colv = B[ya:yb, cx_]
            cs = []
            yy = 0
            while yy < len(colv):
                if colv[yy]:
                    z = yy
                    while z + 1 < len(colv) and colv[z + 1]:
                        z += 1
                    if z - yy + 1 <= maxthin:
                        cs.append(ya + (yy + z) / 2.0)
                    yy = z + 1
                else:
                    yy += 1
            per_col.append(cs)
        # a band present in at least half this side's columns
        allc = sorted(c for cs in per_col for c in cs)
        grp = []
        for c in allc:
            if grp and c - grp[-1][-1] <= 0.2 * sp:
                grp[-1].append(c)
            else:
                grp.append([c])
        for g in grp:
            if len(g) >= max(1, len(per_col) // 2):
                found.append((float(np.mean(g)), side_x))
    # merge the two sides' bands
    found.sort()
    bands, thick = [], []
    for c, _ in found:
        if bands and abs(c - bands[-1][-1]) <= 0.2 * sp:
            bands[-1].append(c)
        else:
            bands.append([c])
    bands = [float(np.mean(g)) for g in bands]
    # walk the ladder outward from the staff edge
    edge = top if side == "above" else bot
    sign = -1 if side == "above" else 1
    ladder, anchor = [], edge
    while True:
        cands = [b for b in bands if 0.7 * sp <= sign * (b - anchor) <= 1.45 * sp]
        if not cands:
            break
        nb = min(cands, key=lambda b: abs(b - (anchor + sign * sp)))
        ladder.append(nb); anchor = nb
    res = dict(ladder=[round(v, 1) for v in ladder], thick_bands=thick,
               staff=[round(v, 1) for v in lines_m])
    gaps = np.diff(sorted(lines_m)); mg = float(np.median(gaps))
    if np.any(np.abs(gaps - mg) > 0.25 * mg):
        res.update(verdict="unreadable", why=f"staff lines not measured (gaps {[round(float(g), 1) for g in gaps]})",
                   C=None, C_why="staff lines not measured")
        return res
    if start is None:
        res.update(verdict="unreadable", why="no head ink at the mapped centre", C=None, C_why="no head"); return res
    t, b = t0, b0
    all_lines = sorted(list(lines_m) + ladder)
    edge = top if side == "above" else bot
    edge_step = 0 if side == "above" else 2 * (len(lines_m) - 1)
    steps = {L: 2 * k for k, L in enumerate(lines_m)}
    for n, L in enumerate(ladder, 1):
        steps[L] = edge_step + sign * 2 * n
    lt = 0.2 * sp   # about a line thickness (Litolff 3 px of 15.75)

    def trim(t, b):
        for L in all_lines:
            if abs(L - t) <= lt and (b - t) > 0.8 * sp:
                t = int(math.ceil(L + lt * 0.75))
            if abs(L - b) <= lt and (b - t) > 0.8 * sp:
                b = int(math.floor(L - lt * 0.75))
        return t, b

    # a merged two-head stack. (a) a ladder line inside the blob's middle
    # third separates a third: the heads sit in the spaces either side of it.
    # (b) no line there: two heads on two lines, split at the narrowest run
    # (the waist, which lies in the space between them).
    heads = [(t, b)]
    stacked = None
    preset = {}
    Hb = b - t + 1
    if 1.7 * sp <= Hb <= 2.7 * sp:
        m0, m1 = t + Hb / 3.0, b - Hb / 3.0
        mid_lines = [L for L in all_lines if m0 <= L <= m1]
        if len(mid_lines) == 1:
            L = mid_lines[0]
            heads = [(t, int(math.floor(L - lt))), (int(math.ceil(L + lt)), b)]
            preset = {0: (steps[L] - 1, f"stack split by the line y={L:.1f}: in the space ABOVE it"),
                      1: (steps[L] + 1, f"stack split by the line y={L:.1f}: in the space BELOW it")}
            stacked = "line"
        elif not mid_lines:
            x0w, x1w = int(px - 1.3 * sp), int(px + 1.3 * sp)
            widths = {y: hlen(B[y, x0w:x1w], px - x0w, sp) for y in range(int(math.ceil(m0)), int(m1) + 1)}
            if widths:
                w = min(widths, key=widths.get)
                heads = [(t, w - 1), (w + 1, b)]
                stacked = "waist"
    res["stacked"] = stacked
    # the sub-head nearest the detector's centre is THIS subject
    which = min(range(len(heads)), key=lambda k: abs((heads[k][0] + heads[k][1]) / 2 - py))
    if preset:
        t, b = heads[which]
    else:
        t, b = trim(*heads[which])
    h = b - t + 1
    res.update(head_rows=[t, b], head_h_sp=round(h / sp, 2),
               stack_part=None if not stacked else ("far" if (which == 0) == (side == "above") else "near"))
    if not preset and not (0.55 * sp <= h <= 1.5 * sp):
        kind = ("vertical stroke through the mapped centre (not a separable head)" if h > 3 * sp
                else "merged/fragmented")
        res.update(verdict="unreadable", why=f"head ink {h} px = {h / sp:.2f} sp tall -- {kind}",
                   C=None, C_why="head not separable")
        return res
    # ---- TRUTH by the head's middle third
    mid0, mid1 = t + h / 3.0, b - h / 3.0
    on = [L for L in all_lines if mid0 <= L <= mid1]
    hc = (t + b) / 2.0
    if preset:
        res.update(step=preset[which][0], words=preset[which][1])
    elif len(on) > 1:
        res.update(verdict="unreadable", why="two lines inside the head's middle third")
    elif on:
        res.update(step=steps[on[0]], words=f"on line y={on[0]:.1f}")
    else:
        done = False
        for a, c in zip(all_lines, all_lines[1:]):
            if a < hc < c:
                if 0.6 * sp <= c - a <= 1.6 * sp:
                    res.update(step=(steps[a] + steps[c]) // 2,
                               words=f"in space between y={a:.1f} and y={c:.1f}")
                else:
                    res.update(verdict="unreadable", why=f"bracketing lines {a:.1f}/{c:.1f} not one space apart")
                done = True; break
        if not done:
            last = ladder[-1] if ladder else edge
            near_edge = b if side == "above" else t
            if abs(near_edge - last) <= 0.35 * sp and sign * (hc - last) > 0:
                res.update(step=steps[last] + sign, words=f"in space just past the last line y={last:.1f} (touches it)")
            else:
                res.update(verdict="unreadable",
                           why=f"head sits {abs(near_edge - last) / sp:.2f} sp past the last found line with no ledger between -- a missed ledger, or not this staff's note")
    # ---- C: Sean's clean-ledger count (DECISIONS 2026-09-30)
    if stacked and res["stack_part"] == "far":
        res.update(C=None, C_why="far head of a stack: its near edge is the other head, not a ledger")
        return res
    near_edge = b if side == "above" else t
    # clean = lies between the staff and the head; the head may TOUCH it
    # (edge overlap under 0.3 sp -- Litolff heads sit low and overlap the
    # ledger beneath by a few px), but no line through its body counts.
    ov = 0.3 * sp
    clean = [L for L in ladder if sign * (near_edge - L) >= -ov]
    n = len(clean)
    lastc = clean[-1] if clean else edge
    d = sign * (near_edge - lastc)     # >0: a white gap between line and head
    if -ov <= d <= 1.5 * lt:
        res.update(C=edge_step + sign * (2 * n + 1), C_why=f"{n} clean ledger(s); near edge touches y={lastc:.1f} ({d / sp:+.2f} sp) -> space beyond it")
    elif 0.3 * sp < d <= 0.8 * sp:
        res.update(C=edge_step + sign * (2 * n + 2), C_why=f"{n} clean ledger(s); near edge {d / sp:.2f} sp past y={lastc:.1f} -> on the next ledger")
    else:
        res.update(C=None, C_why=f"{n} clean ledger(s); near edge {d / sp:+.2f} sp from y={lastc:.1f}: neither touching nor half a space")
    return res


def run(pdf, page, tag):
    captured = {}
    orig = G.gather_ledger_printed_position
    def spy(log, cells, local, detections):
        captured.update(cells=cells, local=local, dets=detections)
        return orig(log, cells, local, detections)
    G.gather_ledger_printed_position = spy
    prepared = prepare_pages(pdf, [page], dpi=600)
    log = G.gather(prepared, detector=YoloDetector(W), pdf_path=pdf)
    decide(log, through="evaluate")
    G.gather_ledger_printed_position = orig
    pws = prepared[0][0]
    Bpage = pws.page.binary == 0
    cells, local, dets = captured["cells"], captured["local"], captured["dets"]
    by_key = {}
    for c in cells:
        k = local.get(c.staff_index)
        if k is not None:
            by_key[(c.page_index, k[0], k[1], c.measure_index)] = c
    far = []
    for cell_key, ds in dets.items():
        sub = Subject.from_key(cell_key)
        c = by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None or len(c.staff_line_ys_canonical or []) < 5:
            continue
        for gi, d in enumerate(ds):
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            rows = log.rows(Q.LEDGER_PRINTED_POSITION, g)
            refs = log.refusals(Q.LEDGER_PRINTED_POSITION, g)
            if not rows and not refs:
                continue
            nsp = log.rows(Q.NOTEHEAD_STAFF_POSITION, g)
            if not nsp:
                continue
            far.append((g, c, d, float(nsp[-1].value), rows, sub))
    rnd = random.Random(20260930)
    near = [f for f in far if abs((f[3] - math.floor(f[3])) - 0.5) <= MARGIN]
    conf = [f for f in far if abs(f[3] - round(f[3])) <= 0.1]
    ctrl = rnd.sample(conf, min(10, len(conf)))
    sean = [f for f in far if f[0].to_key() in SEAN]
    out = []
    for group, lst in (("near", near), ("control", ctrl), ("sean", sean)):
        for g, c, d, pos, rows, sub in lst:
            lines = list(c.staff_line_ys_canonical)
            sp_c = (lines[-1] - lines[0]) / 4.0
            cx = d.x_canonical + d.width_canonical / 2; cy = d.y_canonical + d.height_canonical / 2
            rc = log.rows(Q.NOTEHEAD_RECENTRE, g)
            cxr, cyr = cx, cy
            if rc:
                cxr += rc[-1].value[0] * sp_c; cyr += rc[-1].value[1] * sp_c
            up = c.upscale_factor; bx0, by0 = c.bbox_page_px[0], c.bbox_page_px[1]
            # measured staff lines on the page, and the canonical->page y offset
            px = bx0 + cxr / up
            sp_p = sp_c / up
            lines_m = []
            for L in lines:
                ym = by0 + L / up
                ys = range(int(ym - 0.3 * sp_p) - 1, int(ym + 0.3 * sp_p) + 2)
                xa, xb = int(px - 3 * sp_p), int(px + 3 * sp_p)
                best = max(ys, key=lambda y: Bpage[y, xa:xb].mean())
                # centre of the ink band around best
                y0 = y1 = best
                while Bpage[y0 - 1, xa:xb].mean() > 0.5 * Bpage[best, xa:xb].mean(): y0 -= 1
                while Bpage[y1 + 1, xa:xb].mean() > 0.5 * Bpage[best, xa:xb].mean(): y1 += 1
                lines_m.append((y0 + y1) / 2.0)
            dy = float(np.median([m - (by0 + L / up) for m, L in zip(lines_m, lines)]))
            sp = (lines_m[-1] - lines_m[0]) / 4.0
            py = by0 + cyr / up + dy
            side = "above" if pos < 0 else "below"
            m = measure(Bpage, px, py, lines_m, sp, side)
            geo = int(round(pos))
            clef = log.verdict(Q.CLEF, R.staff(sub.page, sub.system, sub.staff))
            clefv = str(clef.value) if clef is not None and clef.value is not None else None
            gray = c.image if c.image.ndim == 2 else c.image.mean(axis=2).astype(np.uint8)
            rungs = measure_ledger_rungs(gray, lines, cxr)
            sB = snap_to_staff(lines, cyr, rungs)
            nB = len(rungs.get(side, []))
            dB = abs(sB["step"] - (0 if side == "above" else 8))
            Bv = sB["step"] if (nB > 0 and dB <= 2 * nB + 1) else None
            A = int(rows[-1].value) if rows else None
            Acorr = None if A is None else (A if side == "above" else A + 8)
            pv = log.verdict(Q.PITCH, g)
            out.append(dict(group=group, subject=g.to_key(), staff_pos=round(pos, 2),
                            geometry=geo, lo=math.floor(pos), hi=math.ceil(pos),
                            side=side, px=round(px, 1), py=round(py, 1), sp=round(sp, 2),
                            clef=clefv, measured=m, A_raw=A, A=Acorr, B=Bv,
                            pitch_verdict=str(pv.value) if pv is not None else None,
                            sean=SEAN.get(g.to_key())))
    json.dump(out, open(f"{tag}-geom.json", "w"), indent=1, default=str)
    np.save(f"{tag}-page.npy", Bpage)
    print(tag, "far", len(far), "near", len(near), "control", len(ctrl), "sean", len(sean), file=sys.stderr)


if __name__ == "__main__":
    run(sys.argv[1], int(sys.argv[2]), sys.argv[3])
