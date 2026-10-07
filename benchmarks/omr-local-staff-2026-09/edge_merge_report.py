"""lane-edge-merge-unseen-ledgers (2026-10-06): the report on `farhead_per_bar_grid_oos.py scan` (BEFORE = the combined tree's reader,
the record's `new` arm) against `edge_merge_oos.py scan` (AFTER = the same reader with the three switches on).

  python3 edge_merge_report.py <before_litolff.json> <before_brahms.json> <after_litolff.json> <after_brahms.json> \
        [--sheet out.png] [--five out5.png --truth truth_head.json] [--seed 20261006]

Prints: population before -> after (decided / abstained / implausible, changes by kind), Sean's 44 confirmed tiles, the list of changed
heads, and (with --sheet) ONE sheet of 12 seeded changed heads (before | after; staff lines CYAN 1 px, every ledger rung the reader
found YELLOW 1 px, the line it rested the answer on MAGENTA, the box ORANGE; the answer in words) with every drawn line re-measured
against the page's pixel rows. --five draws the five heads of 2026-10-06 the same way.
"""
from __future__ import annotations

import collections, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import farhead_per_bar_grid_report as R
import truth_set_2_44c as ts
from frame import render_page_matching_gather

CYAN, YEL, ORG, MAG = (255, 255, 0), (0, 255, 255), (0, 140, 255), (255, 0, 255)   # BGR
DOC = R.DOC
FIVE = [  # (n, label, doc, page, subject, Sean's / truth answer position)
    (1, "truth set, Brahms p1 (the truth encoding)", "brahms", 1, "glyph/1/1/8/7/4", 13),
    (2, "note_first tile 2 (Sean: right)", "brahms", 19, "glyph/19/1/0/5/10", -3),
    (3, "night tile 12 (Sean: right)", "litolff", 5, "glyph/5/0/5/9/0", -6),
    (4, "edge_flip tile 1 (Sean: right)", "brahms", 4, "glyph/4/0/0/9/15", -3),
    (5, "edge_flip tile 12 (Sean: right)", "brahms", 14, "glyph/14/0/1/0/6", -5),
]
REASON = {"no_line_at_the_note_box": "no ledger line found at the head's box", "no_rungs": "no ledger line found at all",
          "count_does_not_fit": "the ledgers it counted do not fit one even pitch"}


def merge(before_paths, after_paths):
    heads = {}
    for which, bp, ap in zip(("litolff", "brahms"), before_paths, after_paths):
        b = json.loads(Path(bp).read_text())["heads"]
        a = json.loads(Path(ap).read_text())["heads"]
        for s, rb in b.items():
            ra = a.get(s)
            if ra is None or rb.get("new") is None or ra.get("new") is None:
                continue
            heads[(which, s)] = dict(old=rb["new"], new=ra["new"], recorded=rb["recorded"], page=rb["page"], which=which, subject=s)
    return heads


def say(d):
    if d["pos"] is not None:
        return R.words_pos(d["pos"])
    key = next((k for k in REASON if d["reason"].startswith(k)), None)
    return "no answer: " + (REASON[key] if key else d["reason"][:60])


def norm(read):
    return dict(lines=read["lines"], box_used=read["box_used"], rungs=read.get("rungs") or [],
                note_first={"line_y": read.get("line_y")}, pos=read["pos"], reason=read["reason"], box_source=read.get("box_source"))


def crop(gray, d, sc=3, pad_x_sp=2.2, pad_y_sp=3.0):
    lines = d["lines"]
    sp = (max(lines) - min(lines)) / 4.0
    x0, y0, x1, y1 = d["box_used"]
    cx = (x0 + x1) / 2.0
    ax0, ax1 = int(cx - (pad_x_sp + 0.7) * sp), int(cx + (pad_x_sp + 0.7) * sp)
    cy0, cy1 = int(y0 - pad_y_sp * sp), int(y1 + pad_y_sp * sp)
    H, W = gray.shape
    ax0, ax1, cy0, cy1 = max(0, ax0), min(W, ax1), max(0, cy0), min(H, cy1)
    im = cv2.resize(cv2.cvtColor(gray[cy0:cy1, ax0:ax1], cv2.COLOR_GRAY2BGR), None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    Y = lambda y: int(round((y - cy0 + 0.5) * sc))
    X = lambda x: int(round((x - ax0 + 0.5) * sc))
    w = im.shape[1]
    for y in lines:
        if cy0 <= y < cy1:
            cv2.line(im, (0, Y(y)), (w - 1, Y(y)), CYAN, 1)
    for r in d.get("rungs") or []:
        if cy0 <= r["y"] < cy1:
            cv2.line(im, (0, Y(r["y"])), (w - 1, Y(r["y"])), YEL, 1)
    ly = (d.get("note_first") or {}).get("line_y")
    if ly is not None and cy0 <= ly < cy1:
        cv2.line(im, (w // 2 - 40, Y(ly)), (w // 2 + 40, Y(ly)), MAG, 1)
    cv2.rectangle(im, (X(x0), Y(y0)), (X(x1), Y(y1)), ORG, 1)
    return im


def text_under(im, lines, w):
    pad = 16 * len(lines) + 8
    out = np.full((im.shape[0] + pad, w, 3), 255, np.uint8)
    out[:im.shape[0], :im.shape[1]] = im[:, :w]
    for i, t in enumerate(lines):
        cv2.putText(out, t, (6, im.shape[0] + 14 + 16 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
    return out


def drawn_staff_offsets(gray, d):
    return R_offsets(gray, d)


def R_offsets(gray, d):
    """px offset of each drawn staff line from the page's darkest-run centre in the flank columns beside the box."""
    import lc5_sheet as S
    return S.drawn_offsets(gray, d)


def drawn_rung_offsets(gray, d):
    """px offset of each drawn ledger rung from the ink row nearest it in the columns just OUTSIDE the box edges (where a ledger
    juts); rungs whose jut is under 0.05 sp or is not there are reported as None."""
    x0, y0, x1, y1 = d["box_used"]
    sp = (max(d["lines"]) - min(d["lines"])) / 4.0
    box = (x0, y0, x1, y1)
    thr = min(int(np.percentile(gray[int(y0) - 100:int(y1) + 100, int(x0) - 100:int(x1) + 100], 25) + 40), 140)
    cols = [(x0 - 0.6 * sp, x0 - 0.04 * sp), (x1 + 0.04 * sp, x1 + 0.6 * sp)]
    out = []
    for r in d.get("rungs") or []:
        c = R.ink_row(gray, r["y"], sp, cols, thr)
        out.append(None if c is None else c - r["y"])
    return out


def panel_text(n, label, doc, subj, ans, b, a):
    rg = lambda d: "rungs: " + (", ".join(f"{x['y']:.0f}" for x in d["rungs"]) or "none")
    t = [f"{n}. {doc} {subj.replace('glyph/', '')} -- {label}"]
    if ans is not None:
        t.append(f"the right answer: {R.words_pos(ans)}")
    t += ["BEFORE (left): " + say(b), "AFTER (right): " + say(a), rg(b) + "   |   " + rg(a),
          f"box used: before {b['box_source']}, after {a['box_source']}"]
    return t


def sheet(items, out_png, grays_for, title):
    panels, meas = [], []
    for n, label, doc, subj, ans, b, a, g in items:
        cb, ca = crop(g, b), crop(g, a)
        h = max(cb.shape[0], ca.shape[0])
        padi = lambda im: cv2.copyMakeBorder(im, 0, h - im.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        row = np.hstack([padi(cb), padi(ca)])
        panels.append(text_under(row, panel_text(n, label, doc, subj, ans, b, a), row.shape[1]))
        meas.append((n, drawn_staff_offsets(g, b), drawn_staff_offsets(g, a), drawn_rung_offsets(g, b), drawn_rung_offsets(g, a)))
    cols = 2
    rowsimg = []
    for k in range(0, len(panels), cols):
        grp = panels[k:k + cols]
        h = max(p.shape[0] for p in grp)
        w = max(p.shape[1] for p in panels)
        grp = [np.pad(p, ((0, h - p.shape[0]), (0, w - p.shape[1] + 14), (0, 0)), constant_values=255) for p in grp]
        while len(grp) < cols:
            grp.append(np.full((h, w + 14, 3), 255, np.uint8))
        rowsimg.append(np.hstack(grp))
    W = max(r.shape[1] for r in rowsimg)
    big = np.vstack([np.pad(r, ((0, 12), (0, W - r.shape[1]), (0, 0)), constant_values=255) for r in rowsimg])
    legend = (title + "   cyan = the staff lines the reader used (1 px)   yellow = every ledger rung it found (1 px)   "
              "magenta = the line it rested the answer on   orange = the box it used")
    top = np.full((24, big.shape[1], 3), 255, np.uint8)
    cv2.putText(top, legend, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(str(out_png), np.vstack([top, big]))
    f = lambda v: ("n=%d median |off| %.2f max %.2f" % (len(v), np.median(np.abs(v)), np.max(np.abs(v)))) if v else "none measured"
    flat = lambda i: [x for m in meas for x in m[i]]
    nn = lambda i: sum(x is None for m in meas for x in m[i])
    print("== drawn lines vs the page's pixel rows (px)")
    print("  staff lines  before", f(flat(1)), "| after", f(flat(2)))
    rb = [x for x in flat(3) if x is not None]
    ra = [x for x in flat(4) if x is not None]
    print("  ledger rungs before", f(rb), "(%d with no jut ink to measure)" % nn(3), "| after", f(ra), "(%d with none)" % nn(4))
    for m in meas:
        print("   tile", m[0], "rung offsets before", [None if x is None else round(x, 1) for x in m[3]], "after",
              [None if x is None else round(x, 1) for x in m[4]])


if __name__ == "__main__":
    args = sys.argv[1:5]
    heads = merge(args[0:2], args[2:4])
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 20261006
    pop = R.population(heads)
    for which, c in pop.items():
        print("==", which, "heads read in both:", c["n"], "| decided", c["decided_old"], "->", c["decided_new"],
              "| abstained", c["n"] - c["decided_old"], "->", c["n"] - c["decided_new"],
              "| implausible", c["implausible_old"], "->", c["implausible_new"],
              "| abstain->decided", c["abstain_to_decided"], "decided->abstain", c["decided_to_abstain"],
              "position changed", c["position_changed"], "| box detector", c["box_detector_old"], "->", c["box_detector_new"])
    rows, broken = R.tile_table(heads)
    print("== Sean's 44 confirmed tiles:", len(rows), "| BROKEN by this change:", len(broken), "| not read:", sum(r[5] == "NOT READ" for r in rows))
    for r in rows:
        if r[5] not in ("keeps",):
            print("  ", r)
    gained = [r for r in rows if r[5].startswith("keeps (today")]
    print("   (regained a confirmed answer:", len(gained), ")")
    changed = [(k, r) for k, r in heads.items() if R.pos(r, "old") != R.pos(r, "new")]
    kinds = collections.Counter()
    for k, r in changed:
        a, b = R.pos(r, "old"), R.pos(r, "new")
        kinds["abstain->decided" if a is None else ("decided->abstain" if b is None else "moved")] += 1
    print("== changed heads (position):", len(changed), dict(kinds))
    if "--list" in sys.argv:
        for (w, s), r in sorted(changed):
            print("  ", w, s, R.pos(r, "old"), "->", R.pos(r, "new"), "|", r["old"]["read"]["reason"][:40], "->", r["new"]["read"]["reason"][:50])
    FIVE_SUBJ = {(d, s) for (_n, _l, d, _p, s, _a) in FIVE}
    if "--sheet" in sys.argv:
        pool = [(k, r) for k, r in changed if k not in FIVE_SUBJ and r["new"]["read"]["box_used"] and r["old"]["read"]["box_used"]]
        rng = random.Random(seed)
        picks = []
        for which in ("litolff", "brahms"):
            p = sorted([x for x in pool if x[0][0] == which])
            picks += rng.sample(p, min(6, len(p)))
        grays, items = {}, []
        for i, ((w, s), r) in enumerate(picks, 1):
            kk = (w, r["page"])
            if kk not in grays:
                grays[kk] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[DOC[w]]["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
            items.append((i, "out of sample", w, s, None, norm(r["old"]["read"]), norm(r["new"]["read"]), grays[kk]))
        sheet(items, sys.argv[sys.argv.index("--sheet") + 1], None, "12 seeded changes")
        for i, ((w, s), r) in enumerate(picks, 1):
            print("  tile", i, w, s, "pos", R.pos(r, "old"), "->", R.pos(r, "new"))
    if "--movers" in sys.argv:
        # every head that was DECIDED before and moved or went to abstain (never a gain): the cost side
        pool = sorted([(k, r) for k, r in changed if R.pos(r, "old") is not None])
        grays, items = {}, []
        for i, ((w, s), r) in enumerate(pool, 1):
            kk = (w, r["page"])
            if kk not in grays:
                grays[kk] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[DOC[w]]["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
            items.append((i, "decided before, changed", w, s, None, norm(r["old"]["read"]), norm(r["new"]["read"]), grays[kk]))
        sheet(items, sys.argv[sys.argv.index("--movers") + 1], None, "the %d decided heads that changed" % len(pool))
    if "--five" in sys.argv:
        tr = json.loads(Path(sys.argv[sys.argv.index("--truth") + 1]).read_text())
        grays, items = {}, []
        for n, label, doc, page, subj, ans in FIVE:
            kk = (doc, page)
            if kk not in grays:
                grays[kk] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[DOC[doc]]["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
            if n == 1:
                b, a = tr["before"], tr["after"]
                b = dict(b, note_first=b["note_first"]); a = dict(a, note_first=a["note_first"])
            else:
                r = heads[(doc, subj)]
                b, a = norm(r["old"]["read"]), norm(r["new"]["read"])
            items.append((n, label, doc, subj, ans, b, a, grays[kk]))
        sheet(items, sys.argv[sys.argv.index("--five") + 1], None, "the five heads")
