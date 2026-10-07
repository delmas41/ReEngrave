"""night 2026-10-07: ONE sheet for Sean, 12 seeded-random tiles from pages the rules were NOT written on (Litolff pp.4-16,
Brahms pp.2-26), favouring the biggest kind of change between NEW (`...20261007-night`) and BASE (`...20261006-night-
combined`): far heads (decided where BASE gave up, or decided differently), then owner changes, then in-staff heads whose
position moved because the bar's staff lines moved.  Default mix per document: 2 far heads BASE gave up on, 2 far heads
BASE answered differently, 1 owner change, 1 in-staff head moved by the staff-line fix.

Every drawn line is 1 px (in the 3x tile), in a colour that shows on black ink; each is re-measured against the pixel
rows of the page and the offset is printed.  A line more than 2 px off ink (NEW lines) or with no ink beside the head to
measure is printed.  BASE's own lines are measured too and expected to be off where the text says BASE was wrong.

  python3 night_1007_sheet.py <scratch dir with x/*.json> [--seed 20261007] [--mix 2,2,1,1]
"""
from __future__ import annotations
import collections, json, os, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import farhead_note_first_sheet as NF
import farhead_per_bar_grid_lib as GL
import overnight_1004_report as R
import truth_set_2_44c as ts
from frame import render_page_matching_gather

OUT = HERE.parents[1] / "out/print/night_1007_sample.png"
NEWTAG, BASETAG = "20261007-night", "20261006-night-combined"
PAGES = {"beethoven5-litolff": range(4, 17), "brahms1-breitkopf": range(2, 27)}
SHORT = {"beethoven5-litolff": "litolff", "brahms1-breitkopf": "brahms"}
MAGENTA, LIME, RED, AZURE, ORANGE = (255, 0, 255), (0, 190, 0), (0, 0, 255), (255, 150, 0), (0, 140, 255)
SCALE = 3
ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}


def ordn(n):
    return ORD.get(n, f"{n}th")


def words_pos(p):
    """A position (half-steps, 0 = top staff line, 8 = bottom line) in words; staff lines and spaces counted from the BOTTOM."""
    if p is None:
        return "no answer (abstained)"
    p = int(p)
    if p < 0:
        if p == -1:
            return "in the space just above the top line"
        if p % 2 == 0:
            return f"on the {ordn(-p // 2)} ledger line above the staff"
        return f"in the space above the {ordn((-p - 1) // 2)} ledger line above the staff"
    if p > 8:
        if p == 9:
            return "in the space just below the bottom line"
        if p % 2 == 0:
            return f"on the {ordn((p - 8) // 2)} ledger line below the staff"
        return f"in the space below the {ordn((p - 9) // 2)} ledger line below the staff"
    if p % 2 == 0:
        return f"on staff line {ordn(5 - p // 2)} from the bottom"
    return f"in staff space {ordn((8 - p) // 2 + 1)} from the bottom"


def staff_words(key):
    if not key:
        return "no staff"
    _, p, s, k = key.split("/")
    return f"staff {int(k) + 1} from the top of system {int(s) + 1}"


def load(d, doc):
    N = json.loads((d / "x" / f"{doc}-{NEWTAG}.json").read_text())
    B = json.loads((d / "x" / f"{doc}-{BASETAG}.json").read_text())
    rn = json.loads((d / "x" / f"rep_new_{SHORT[doc]}.json").read_text())["heads"]
    rb = json.loads((d / "x" / f"rep_base_{SHORT[doc]}.json").read_text())["heads"]
    return N, B, rn, rb


def pools(doc, N, B, rn, rb):
    bybox = R.by_page(B["glyphs"])
    widths = sorted(g["box"][2] - g["box"][0] for g in N["glyphs"].values() if "box" in g and R.is_far(g) and "geo" in g)
    med_w = widths[len(widths) // 2]
    far_n = R6far(N)
    P = dict(newly=[], changed=[], owner=[], lines=[])
    for s, g in N["glyphs"].items():
        if "box" not in g or "geo" not in g or R.page_of(s) not in PAGES[doc]:
            continue
        page = R.page_of(s)
        mb, v = R.best_match(g["box"], page, bybox)
        if not mb:
            continue
        bg = mb[1]
        cx_w = g["box"][2] - g["box"][0]
        # far heads
        if s in far_n and (g.get("np") or {}).get("outcome") == "decided" and "fh" in g:
            m = rn.get(s)
            if m and m.get("repro") and m.get("edge_y") is not None and m.get("line_y") is not None \
                    and m.get("between") is not None and cx_w >= 0.6 * med_w:
                newpos = int(round(float(g["np"]["value"])))
                bpos = R.decided_pos(bg) if R.is_far(bg) else None
                rec = dict(doc=doc, subject=s, page=page, box=g["box"], new_pos=newpos, base_pos=bpos, base_subject=mb[0],
                           geometry=R.geo_pos(g), new=dict(m, pos=newpos),
                           base_reason=((bg.get("fh_abs") or {}).get("ledger_reason") or (bg.get("np") or {}).get("reason")),
                           base_rep=rb.get(mb[0]) if bpos is not None else None)
                if bpos is None:
                    P["newly"].append(dict(rec, kind="far_newly"))
                elif bpos != newpos:
                    P["changed"].append(dict(rec, kind="far_changed"))
        # owner
        o, bo = g.get("own"), bg.get("own")
        if o and bo and o["outcome"] == "decided" and (o["outcome"], o["value"]) != (bo["outcome"], bo["value"]) \
                and cx_w >= 0.6 * med_w:
            P["owner"].append(dict(doc=doc, subject=s, page=page, box=g["box"], kind="owner", own=o, base_own=bo,
                                   geometry=R.geo_pos(g), filing="staff/" + "/".join(s.split("/")[1:4])))
        # in-staff position moved
        if s not in far_n and not R.is_far(bg) and R.geo_pos(g) != R.geo_pos(bg):
            P["lines"].append(dict(doc=doc, subject=s, page=page, box=g["box"], kind="lines", new_pos=R.geo_pos(g),
                                   base_pos=R.geo_pos(bg), geometry=R.geo_pos(g)))
    return P


def R6far(N):
    return {s: g for s, g in N["glyphs"].items() if R.is_far(g) and "geo" in g}


_GRID = {}


def grids(doc, page, mode):
    """(grid_of, staves) for `page`: mode 'new' = today's per-bar grid, 'base' = the 10-06 one (OMR_CELL_LINE_FIND=0)."""
    key = (doc, page, mode)
    if key not in _GRID:
        N = _STATE["N"][doc]
        cfg = ts.DOCS[doc]
        pi = render_page_matching_gather(cfg["pdf"], page, 600)

        class _Rec:
            observations = [dict(quantity="staff_lines", subject=k, value=v)
                            for k, v in N["staff_lines"].items() if k.startswith(f"staff/{page}/")]
        old = os.environ.get("OMR_CELL_LINE_FIND")
        os.environ["OMR_CELL_LINE_FIND"] = "1" if mode == "new" else "0"
        try:
            out = GL.bar_grids(_Rec, page, pi)
        finally:
            if old is None:
                os.environ.pop("OMR_CELL_LINE_FIND", None)
            else:
                os.environ["OMR_CELL_LINE_FIND"] = old
        _GRID[key] = (out[0], out[1])
    return _GRID[key]


def seg_lines(staves, key, cx):
    for st in staves:
        if st["key"] == key:
            if not st["grid"]:
                return st["lines"]
            seg = min(st["grid"], key=lambda t: 0 if t[0] <= cx < t[1] else min(abs(cx - t[0]), abs(cx - t[1])))
            return seg[2]
    return None


def draw_tile(gray, r, no, lines):
    """lines = [(y, colour, label, base_line)]; returns crop and the check list."""
    box = r["box"]
    sp = r["sp"]
    ys = [l[0] for l in lines] + [box[1], box[3]]
    cx = (box[0] + box[2]) / 2.0
    xa, xb = max(0, int(cx - 3.2 * sp)), int(cx + 3.2 * sp)
    ya, yb = max(0, int(min(ys) - 1.2 * sp)), int(max(ys) + 1.2 * sp)
    crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_NEAREST)
    thr = min(int(np.percentile(gray[ya:yb, xa:xb], 25) + 40), 140)
    side = (int(box[2] + 0.1 * sp), int(box[2] + 1.0 * sp))
    left = (int(box[0] - 1.0 * sp), int(box[0] - 0.1 * sp))
    checks = []
    for (y, colour, label, base_line) in lines:
        yy = int(round((y - ya) * SCALE)) + SCALE // 2
        cv2.line(crop, (0, yy), (crop.shape[1] - 1, yy), colour, 1)
        peaks = [NF.remeasure(gray, y, *cols, thr) for cols in (left, side)]
        peaks = [p for p in peaks if p[0] is not None]
        off = min((abs(p[1]) for p in peaks), default=None)
        checks.append((no, label, round(float(y), 1), None if off is None else round(off, 1), base_line))
    cv2.rectangle(crop, (int((box[0] - xa) * SCALE), int((box[1] - ya) * SCALE)),
                  (int((box[2] - xa) * SCALE), int((box[3] - ya) * SCALE)), ORANGE, 1)
    return crop, checks


def build_tile(r, gray, no):
    doc = r["doc"]
    box = r["box"]
    cx = (box[0] + box[2]) / 2.0
    cy = (box[1] + box[3]) / 2.0
    page = r["page"]
    if r["kind"] in ("far_newly", "far_changed"):
        nf = r["new"]
        r["sp"] = (max(nf["lines"]) - min(nf["lines"])) / 4.0
        r["box"] = box = nf["box_used"] if nf.get("box_used") else box
        L = [(nf["edge_y"], MAGENTA, "staff edge", False)]
        L += [(b, LIME, f"ledger {i + 1}", False) for i, b in enumerate(nf["between"] or [])]
        L.append((nf["line_y"], RED, "note line", False))
        if r["kind"] == "far_changed" and r.get("base_rep") and r["base_rep"].get("line_y") is not None:
            L.append((r["base_rep"]["line_y"], AZURE, "BASE note line", True))
        new_txt = "NEW: " + words_pos(r["new_pos"])
        base_txt = "BASE: " + (words_pos(r["base_pos"]) if r["base_pos"] is not None else f"no answer (gave up: {str(r['base_reason'])[:40]})")
        what = "far head, BASE gave up" if r["kind"] == "far_newly" else "far head, BASE answered differently"
    elif r["kind"] == "owner":
        gn, sn = grids(doc, page, "new")
        o, bo = r["own"], r["base_own"]
        sp_ = None
        L = []
        for key, colour, label, base_line in ((o["value"], MAGENTA, "NEW owner staff, line nearest the note", False),
                                              (bo.get("value") if bo["outcome"] == "decided" else None, AZURE,
                                               "BASE owner staff, line nearest the note", True)):
            if not key:
                continue
            st = next((s_ for s_ in sn if s_["key"] == key), None)
            lines = seg_lines(sn, key, cx)
            if not lines:
                continue
            sp_ = sp_ or (max(lines) - min(lines)) / 4.0
            near = min(lines, key=lambda y: abs(y - cy))
            L.append((near, colour, label, base_line))
        r["sp"] = sp_ or 15.0
        filing = r["filing"]
        new_txt = "NEW: belongs to " + staff_words(o["value"]) + (" (the one it is filed on)" if o["value"] == filing else " (NOT the one it is filed on)")
        base_txt = "BASE: " + ("belongs to " + staff_words(bo["value"]) if bo["outcome"] == "decided" else "no answer (gave up)")
        what = f"owner, rule: {o.get('reason')}"
    else:
        gn, sn = grids(doc, page, "new")
        gb, sb = grids(doc, page, "base")
        _, p_, sy, sk, cell, gi = r["subject"].split("/")
        k3 = (int(sy), int(sk), int(cell))
        ln, lb = gn.get(k3), gb.get(k3)
        r["sp"] = (max(ln) - min(ln)) / 4.0
        L = [(y, MAGENTA, f"NEW line {i + 1}", False) for i, y in enumerate(ln)]
        L += [(y, AZURE, f"BASE line {i + 1}", True) for i, y in enumerate(lb)]
        new_txt = "NEW: " + words_pos(r["new_pos"])
        base_txt = "BASE: " + words_pos(r["base_pos"])
        what = "in-staff head, the bar's staff lines moved"
    crop, ch = draw_tile(gray, r, no, L)
    return crop, ch, new_txt, base_txt, what


_STATE = {}


def main(d, seed, mix):
    d = Path(d)
    rng = random.Random(seed)
    data = {doc: load(d, doc) for doc in PAGES}
    _STATE["N"] = {doc: data[doc][0] for doc in PAGES}
    picks = []
    stats = {}
    for doc in PAGES:
        N, B, rn, rb = data[doc]
        P = pools(doc, N, B, rn, rb)
        stats[doc] = {k: len(v) for k, v in P.items()}
        want = dict(newly=mix[0], changed=mix[1], owner=mix[2], lines=mix[3])
        got = []
        for k in ("newly", "changed", "owner", "lines"):
            got += rng.sample(P[k], min(want[k], len(P[k])))
        short = 6 - len(got)
        if short > 0:
            rest = [r for r in P["newly"] + P["changed"] if r not in got]
            got += rng.sample(rest, short)
        picks += got
    print("pools:", stats)
    rng.shuffle(picks)
    grays = {}
    for r in picks:
        key = (r["doc"], r["page"])
        if key not in grays:
            grays[key] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[r["doc"]]["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
    tiles, allchecks, info = [], [], []
    for i, r in enumerate(picks, 1):
        crop, ch, nt, bt, what = build_tile(r, grays[(r["doc"], r["page"])], i)
        allchecks += ch
        tiles.append((crop, i, r, nt, bt, what))
        info.append(dict(n=i, doc=r["doc"], subject=r["subject"], page=r["page"], kind=r["kind"], new=nt, base=bt))
    W = max(t[0].shape[1] for t in tiles)
    cells = []
    for crop, i, r, nt, bt, what in tiles:
        cap_h = 88
        H = crop.shape[0]
        canvas = np.full((H + cap_h, W, 3), 255, np.uint8)
        canvas[:H, :crop.shape[1]] = crop
        short = r["subject"].replace("glyph/", "")
        cv2.putText(canvas, f"{i}", (6, H + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(canvas, f"{SHORT[r['doc']][:4]} p{r['page']} {short}", (34, H + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
        cv2.putText(canvas, nt[:62], (6, H + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 200), 1)
        cv2.putText(canvas, bt[:62], (6, H + 62), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (170, 90, 0), 1)
        cv2.putText(canvas, what, (6, H + 82), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (90, 90, 90), 1)
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
    legend = np.full((124, img.shape[1], 3), 255, np.uint8)
    for j, (txt, col) in enumerate((
            ("ORANGE box = the note the question is about (the detector's box).", ORANGE),
            ("MAGENTA line = the staff line NEW works from: the edge of the staff the far note is filed on; the line nearest the note of the staff NEW names; or the bar's five lines.", MAGENTA),
            ("GREEN line = each ledger line NEW counted out from the staff edge to the note.", LIME),
            ("RED line = the line NEW says the note sits on, or sits just beyond.", RED),
            ("AZURE line = the same thing for BASE (its note line, its staff, or its five staff lines) where BASE differs.", AZURE))):
        cv2.putText(legend, txt, (8, 20 + 22 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.52, col, 1, cv2.LINE_AA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), np.vstack([legend, img]))
    OUT.with_suffix(".json").write_text(json.dumps(info, indent=1, default=str))
    new_checks = [c for c in allchecks if not c[4]]
    hidden = [c for c in new_checks if c[3] is None]
    bad = [c for c in new_checks if c[3] is not None and c[3] > 2.0]
    base_checks = [c for c in allchecks if c[4]]
    print(f"NEW drawn lines {len(new_checks)}: within 2 px of an ink row {len(new_checks) - len(bad) - len(hidden)}; "
          f"off by more than 2 px {len(bad)} {bad}; no ink beside the head to measure {len(hidden)}")
    print(f"BASE drawn lines {len(base_checks)}: offsets px (None = no ink within 6 px):",
          [(c[0], c[1], c[3]) for c in base_checks])
    for t in info:
        print(t["n"], t["doc"][:6], t["subject"], "|", t["kind"], "|", t["new"], "|", t["base"])
    print("wrote", OUT)


if __name__ == "__main__":
    a = sys.argv[1:]
    mix = tuple(int(v) for v in a[a.index("--mix") + 1].split(",")) if "--mix" in a else (2, 2, 1, 1)
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261007, mix)
