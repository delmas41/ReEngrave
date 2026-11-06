"""PAGE-INK ARCS feasibility (measure only; STAGED; docs/plan-2026-11-06-page-ink-arcs.md §7). Step 2: candidate arc RUNS from the page's ink.

    python3 runs.py PLATE PAGE WORKDIR [--tag 20261104-night]

Reads WORKDIR/PLATE-pPAGE.canvas.png (canvas.py: staff lines erased per band, barline columns carved) and the saved night GATHER slice of the
page (`lane_report.slice_dir`) for what claims before arcs or is not arc ink. Nothing in tools/ is changed or imported for reading pixels.

1. CLAIMED FIRST (CLAUDE §3 order, approximated from the saved rows): staff lines (erased in the canvas), barline rules (carved in the canvas),
   the page claims of brackets, clef, key, meter, the leading column and words/dynamic runs (`Q.CLAIMED_AREA`, owner != arc), and -- standing in
   for the later per-bar marks the run must cross but never take -- every detector box that is not an arc and not a staff/brace/barline box
   (heads, ledgers, beams, rests, accidentals, flags, dots, dynamics/hairpins, fermatas, articulations ...). Their pixels are blanked.
2. THIN COLUMN RUNS: every column of what is left, at ~16 px/sp, split into vertical ink runs; a run thicker than RUN_MAX_SP (a stem, a head,
   a beam seen end-on) is not arc ink and leaves a hole the tracker may bridge.
3. TRACK left to right: each track predicts its next centre from its own recent slope (curvature continuity); the run nearest the prediction
   within TOL continues it; a track survives a hole of up to GAP_SP (a carved barline, a blanked stem or head it passes over). One run feeds one
   track (two arcs that meet are never fused into one: the closer prediction keeps the run, the other bridges or ends).
4. KEEP a track as a candidate arc run when it is long enough, thin, inked over most of its span, smooth (a quadratic fits it), not a stub on a
   staff line row, and either bowed or short (a long dead-straight run is a hairpin leg, a beam or a line, not an arc).

Writes WORKDIR/PLATE-pPAGE.runs.json: per run, its points (page px, every ~2 px), box, width/sagitta/thickness in sp, and why each rejected track
was rejected (counted).
"""
import json
import pathlib
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

TARGET_SP_PX = 16.0
RUN_MAX_SP = 0.62         # a column run thicker than this is not arc ink (arc middles ~0.15-0.35 sp; a steep arc end is cut off here)
TOL_SP = 0.30             # how far from the predicted centre the next run may lie
GAP_SP = 1.25             # the widest hole a track bridges (a carved rule ~0.2 sp, a blanked stem ~0.3 sp, a head box ~1.3 sp)
SLOPE_SP = 1.5            # the stretch of its own recent points a track predicts from
MIN_WIDTH_SP = 1.4
MAX_THICK_SP = 0.42       # median run thickness
MIN_INKED = 0.6           # inked columns / span
MAX_RESID_SP = 0.12       # rms of a quadratic fit
MAX_CHORD_DEG = 40.0
JAG_SP = 0.08            # v2: rms off the 1-sp running mean
V4 = "--v4" in sys.argv
V3 = "--v3" in sys.argv or V4
CUSP_SP = 0.75            # v4: the stretch each side of a hole the slope is read over
CUSP_GAP_SP = 0.3         # v4: a bridged hole at least this wide (a blanked head is ~1.2 sp)
CUSP_SLOPE = 0.15         # v4: both sides at least this steep, opposite signs
V2 = "--v2" in sys.argv or V3
LINE_STUB_SP = 0.14       # a run whose centre sits this close to a staff line row over most of its length is the eraser's leftover
STRAIGHT_SAG_SP = 0.10    # a run straighter than this ...
STRAIGHT_MAX_SP = 4.0     # ... and longer than this is a line, not an arc

NOT_ARC_SKIP = ("staff", "slur", "tie", "brace", "bracket", "barline", "arpeggiato", "systemicBarline")
CLAIM_OWNERS = ("meter", "clef", "key_signature", "leading_column", "word", "bracket")


def page_rows(plate, page, tag):
    from tools.omr.staged import lane_report as L
    d = L.slice_dir(plate, tag)
    boxes, areas, arc_boxes = [], [], []
    with open(d / "observations.jsonl") as fh:
        for line in fh:
            if '"glyph_box"' not in line and '"claimed_area"' not in line:
                continue
            o = json.loads(line)
            s = (o.get("subject") or "").split("/")
            if len(s) < 2 or s[1] != str(page):
                continue
            det = o.get("detail") or {}
            if o["quantity"] == "glyph_box":
                v = o["value"]
                if isinstance(v, str):
                    v = json.loads(v.replace("'", '"'))
                cls = v[0]
                bb = det.get("bbox_page_px")
                if not bb:
                    continue
                if cls in ("slur", "tie"):
                    arc_boxes.append(dict(subject=o["subject"], cls=cls, box=bb))
                elif V3 and (cls.startswith("beam") or "Hairpin" in cls or "hairpin" in cls):
                    continue        # v3: a long stroke box is not blanked as a rectangle (a false 'beam' box over a slur took half of it)
                elif not any(cls.startswith(k) for k in NOT_ARC_SKIP):
                    boxes.append((cls, bb))
            elif o["quantity"] == "claimed_area" and det.get("owner") in CLAIM_OWNERS and det.get("unit") == "area":
                v = o["value"]
                if isinstance(v, str):
                    v = json.loads(v)
                areas.append((det["owner"], v))
    return boxes, areas, arc_boxes


def column_runs(ink, max_run):
    """Per column: list of (top, bottom) ink runs no taller than max_run."""
    H, W = ink.shape
    out = []
    pad = np.zeros((H + 2, W), np.int8)
    pad[1:-1] = ink
    d = np.diff(pad, axis=0)
    for x in range(W):
        starts = np.flatnonzero(d[:, x] == 1)
        ends = np.flatnonzero(d[:, x] == -1)
        runs = [(int(a), int(b)) for a, b in zip(starts, ends) if b - a <= max_run]
        out.append(runs)
    return out


def track(runs, sp, W):
    tol, gap, look = TOL_SP * sp, int(round(GAP_SP * sp)), SLOPE_SP * sp
    active, done = [], []
    for x in range(W):
        cand = [((a + b - 1) / 2.0, b - a) for a, b in runs[x]]
        # predictions
        preds = []
        for ti, t in enumerate(active):
            pts = t["pts"]
            lx, ly = pts[-1][0], pts[-1][1]
            k = len(pts) - 1
            while k > 0 and lx - pts[k - 1][0] <= look:
                k -= 1
            if lx - pts[k][0] >= 3:
                slope = (ly - pts[k][1]) / float(lx - pts[k][0])
            else:
                slope = 0.0
            preds.append(ly + slope * (x - lx))
        pairs = []
        for ti, py in enumerate(preds):
            for ci, (cy, th) in enumerate(cand):
                dy = abs(cy - py)
                if dy <= tol + 0.5 * th:
                    pairs.append((dy, ti, ci))
        pairs.sort()
        used_t, used_c = set(), set()
        for dy, ti, ci in pairs:
            if ti in used_t or ci in used_c:
                continue
            used_t.add(ti)
            used_c.add(ci)
            active[ti]["pts"].append((x, cand[ci][0], cand[ci][1]))
        nxt = []
        for ti, t in enumerate(active):
            if ti in used_t or x - t["pts"][-1][0] <= gap:
                nxt.append(t)
            else:
                done.append(t)
        for ci, (cy, th) in enumerate(cand):
            if ci not in used_c:
                nxt.append(dict(pts=[(x, cy, th)]))
        active = nxt
    return done + active


def line_rows(staves, scale):
    rows = []
    for s in staves:
        rows.extend(y * scale for y in s["lines"])
    return np.array(sorted(rows))


def split_at_cusps(t, sp):
    """v4: two arcs that meet at a note (a tie chain, a slur ending where the next begins) bridge the blanked head between them and chain into
    one track. An arc turns smoothly through ONE apex; where two meet, the track crosses a HOLE (the claimed head) and turns the other way in
    a V. Split at a bridged hole of at least CUSP_GAP_SP where the track's slope either side (over CUSP_SP) has opposite signs, each at least
    CUSP_SLOPE steep -- a smooth apex has a shallow slope both sides and almost never sits on a hole."""
    p = t["pts"]
    if len(p) < 8:
        return [t]
    x = np.array([q[0] for q in p], float)
    y = np.array([q[1] for q in p], float)
    w = CUSP_SP * sp
    cuts = []
    for i in range(1, len(p)):
        if x[i] - x[i - 1] < CUSP_GAP_SP * sp:
            continue
        lo = np.searchsorted(x, x[i - 1] - w)
        hi = np.searchsorted(x, x[i] + w, side="right")
        L, Rr = slice(lo, i), slice(i, hi)
        if i - lo < 3 or hi - i < 3:
            continue
        sl = np.polyfit(x[L], y[L], 1)[0]
        sr = np.polyfit(x[Rr], y[Rr], 1)[0]
        if sl * sr < 0 and min(abs(sl), abs(sr)) >= CUSP_SLOPE:
            cuts.append(i)
    if not cuts:
        return [t]
    out, a = [], 0
    for c in cuts:
        out.append(dict(pts=p[a:c]))
        a = c
    out.append(dict(pts=p[a:]))
    return out


def judge(t, sp, lines):
    p = np.array(t["pts"], float)
    x, y, th = p[:, 0], p[:, 1], p[:, 2]
    width = x[-1] - x[0] + 1
    if width < MIN_WIDTH_SP * sp:
        return "short", None
    inked = len(np.unique(x)) / width
    if inked < MIN_INKED:
        return "sparse", None
    if np.median(th) > MAX_THICK_SP * sp:
        return "thick", None
    c = np.polyfit(x, y, 2)
    fit = np.polyval(c, x)
    resid = float(np.sqrt(np.mean((fit - y) ** 2)))
    if V2:
        # v2 (after one look at Brahms p0's misses): a long slur is flat in the middle and bends at its ends, so a quadratic over its whole
        # length says nothing about jags. Jag = rms off its own 1-sp running mean; and an arc bows ONE way (the chord deviation keeps its sign).
        k = max(3, int(round(sp)))
        ys_ = np.convolve(y, np.ones(k) / k, mode="same")
        inner = slice(k, len(y) - k) if len(y) > 2 * k + 2 else slice(0, len(y))
        resid = float(np.sqrt(np.mean((ys_[inner] - y[inner]) ** 2)))
        if resid > JAG_SP * sp:
            return "rough", None
        deg = 4 if width > 8 * sp else 2
        c = np.polyfit(x, y, deg)
        fit = np.polyval(c, x)
    elif resid > MAX_RESID_SP * sp:
        return "rough", None
    chord = np.degrees(np.arctan2(abs(fit[-1] - fit[0]), width))
    if chord > MAX_CHORD_DEG:
        return "steep", None
    line_y = fit[0] + (fit[-1] - fit[0]) * (x - x[0]) / max(1.0, x[-1] - x[0])
    dev = fit - line_y
    sag = float(dev[np.argmax(np.abs(dev))])
    if len(lines):
        dist = np.min(np.abs(y[:, None] - lines[None, :]), axis=1)
        if np.mean(dist < LINE_STUB_SP * sp) > 0.7:
            return "on_a_line", None
    if abs(sag) < STRAIGHT_SAG_SP * sp and width > STRAIGHT_MAX_SP * sp:
        return "straight", None
    if V2 and abs(sag) >= STRAIGHT_SAG_SP * sp:
        inner = np.abs(dev) > 0.03 * sp
        if inner.sum() >= 5 and np.mean(np.sign(dev[inner]) == np.sign(sag)) < 0.85:
            return "two_bows", None
    return "arc", dict(width_sp=round(width / sp, 2), sagitta_sp=round(sag / sp, 3), thick_sp=round(float(np.median(th)) / sp, 3),
                       resid_sp=round(resid / sp, 3), inked=round(inked, 2), chord_deg=round(float(chord), 1))


def main():
    argv = sys.argv[1:]
    tag = "20261104-night"
    if "--tag" in argv:
        i = argv.index("--tag")
        tag = argv[i + 1]
        del argv[i:i + 2]
    argv = [a for a in argv if a not in ("--v2", "--v3", "--v4")]
    plate, page, wd = argv[0], int(argv[1]), pathlib.Path(argv[2])
    stem = "%s-p%d" % (plate, page)
    tag_out = ".v4" if V4 else ".v3" if V3 else ".v2" if V2 else ""
    meta = json.load(open(wd / (stem + ".page.json")))
    canvas = cv2.imread(str(wd / (stem + ".canvas.png")), 0)
    ink = canvas == 0
    boxes, areas, arc_boxes = page_rows(plate, page, tag)
    H, W = ink.shape
    blank = np.zeros_like(ink)
    for cls, (x0, y0, x1, y1) in boxes:
        blank[max(0, int(y0) - 1):min(H, int(np.ceil(y1)) + 1), max(0, int(x0) - 1):min(W, int(np.ceil(x1)) + 1)] = True
    if V2:
        # v2: an AREA claim takes the ink components wholly inside it (+1 px) -- `stroke_owner._areas`' own page-wide predicate, as 2.269
        # names page strokes -- never the rectangle (v1 blanked a word area that covered half of a slur on Brahms p0)
        n, lab, st, _c = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
        take = np.zeros(n, bool)
        for own, (x0, y0, x1, y1) in areas:
            bx, by, bw, bh = st[:, 0], st[:, 1], st[:, 2], st[:, 3]
            take |= (bx >= x0 - 1) & (by >= y0 - 1) & (bx + bw <= x1 + 1) & (by + bh <= y1 + 1)
        take[0] = False
        blank |= take[lab]
    else:
        for own, (x0, y0, x1, y1) in areas:
            blank[max(0, int(y0)):min(H, int(np.ceil(y1))), max(0, int(x0)):min(W, int(np.ceil(x1)))] = True
    ink2 = ink & ~blank
    sp_page = float(meta["sp"])
    scale = min(1.0, TARGET_SP_PX / sp_page)
    small = cv2.resize(ink2.astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) > 96 if scale < 1 else ink2
    sp = sp_page * scale
    runs = column_runs(small.astype(np.int8), int(round(RUN_MAX_SP * sp)))
    tracks = track(runs, sp, small.shape[1])
    lines = line_rows(meta["staves"], scale)
    why = {}
    out = []
    if V4:
        tracks = [q for t in tracks for q in split_at_cusps(t, sp)]
    for t in tracks:
        if len(t["pts"]) < 3:
            why["tiny"] = why.get("tiny", 0) + 1
            continue
        v, info = judge(t, sp, lines)
        why[v] = why.get(v, 0) + 1
        if v != "arc":
            continue
        p = np.array(t["pts"], float)
        pts = [[round(px / scale, 1), round(py / scale, 1)] for px, py, _ in p[::max(1, int(2 * scale))]]
        pts.append([round(p[-1, 0] / scale, 1), round(p[-1, 1] / scale, 1)])
        xs, ys = p[:, 0] / scale, p[:, 1] / scale
        half = p[:, 2].max() / scale / 2
        info.update(id=len(out), pts=pts, box=[float(xs.min()), float(ys.min() - half), float(xs.max()), float(ys.max() + half)])
        out.append(info)
    json.dump(dict(plate=plate, page=page, sp=sp_page, n_blanked_boxes=len(boxes), n_claim_areas=len(areas), arc_boxes=arc_boxes,
                   tracks_total=len(tracks), why=why, runs=out), open(wd / (stem + tag_out + ".runs.json"), "w"))
    print(stem, "tracks", len(tracks), "candidate arc runs", len(out), "why", why, "blanked boxes", len(boxes), "claim areas", len(areas))


if __name__ == "__main__":
    main()
