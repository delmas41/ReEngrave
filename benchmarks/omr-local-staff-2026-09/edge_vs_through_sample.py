"""lane-edge-vs-through (2026-10-06): a POPULATION the rule was not written on, and a crop sheet of 40 for Sean.

Sean on out-of-sample tiles 9 and 10 of the night sample: both were read ON a line that only touches the head's
STAFF-SIDE edge; the head is in the space beyond. The rule (`ledger_grid.edge_vs_through_evidence`, keyword
`edge_vs_through`) was written on those two tiles and the 27 in-sample far heads
(`tile3_vs_fix1.py`); its constants were committed BEFORE this script was first run (commit message):

    head ink on the staff side of the line beyond the line's half thickness <= 0.175 sp   (hangs beyond it)
    edge line SHOWN: thin flat connected jut >= 0.15 sp past the head
    middle rung shows NO line outside the head;  the two rungs >= 0.30 sp apart

The population: every far head of the 10-06 night-combined records, Litolff pp.4-16 and Brahms pp.2-26 (the pages the
reader's rules were never written on), whose walk offers a thin flat connected line touching or entering the
STAFF-SIDE edge of its box (rung within [-0.35, +0.60] sp of that edge -- the band the through-head rule uses,
`THROUGH_HEAD_NEAR_BAND_SPACES` -- and `thin_flat_jut_evidence` ok), read by the tree's reader with the keyword OFF
(= what the record holds) and ON. A head is eligible only when its OFF replay reproduces the recorded position
(CONTROL: a replay that differs is left out and counted), it reads from its own page's head shape, its box is not
a sliver, and it is not one of the 12 tiles of the 10-06 sample Sean already adjudicated.

  python3 edge_vs_through_sample.py scan  <litolff|brahms> <out.json> <crops.npz>
  python3 edge_vs_through_sample.py sheet <scan_litolff.json> <crops_litolff.npz> <scan_brahms.json> <crops_brahms.npz> \
        <out.png> [--seed 20261006] [--n 40] [--flips]     (--flips: a sheet of the heads the rule CHANGES instead)
"""
from __future__ import annotations

import collections
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import truth_set_2_44c as ts
import farhead_note_first_oos as O
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

NIGHT = "20261006-night-combined"
DOCS = {
    "litolff": ("beethoven5-litolff", f"beethoven5-litolff-mvt1-whole-{NIGHT}.record.json", range(4, 17)),
    "brahms": ("brahms1-breitkopf", f"brahms1-breitkopf-mvt1-whole-{NIGHT}.record.json", range(2, 27)),
}
#: the 12 tiles of out/print/ledgers/night_1006_sample.png, already adjudicated by Sean
SEEN = {"glyph/12/1/0/0/7", "glyph/9/1/2/3/2", "glyph/16/0/0/8/1", "glyph/6/0/7/6/5", "glyph/2/0/3/2/1",
        "glyph/16/0/0/0/2", "glyph/5/0/3/3/3", "glyph/14/1/0/7/3", "glyph/13/0/9/0/4", "glyph/3/1/3/7/9",
        "glyph/7/0/7/15/4", "glyph/5/0/5/9/0"}
NEAR_BAND = lg.THROUGH_HEAD_NEAR_BAND_SPACES
WIN_X, WIN_Y = 1.7, 1.5            # crop margin around the box, in staff spaces
PX_PER_SP = 80.0


def _read_both(ctx, h, cap):
    """Read one far head with the keyword OFF then ON, spying on the note-first call for its inputs."""
    out = {}
    o_nf = lg.derive_note_first_step

    def spy(img, head_box, edge_y, sign, spacing, rungs_y, *a, **kw):
        cap.update(box=tuple(head_box), edge=float(edge_y), sign=float(sign), sp=float(spacing),
                   rungs=[float(r) for r in rungs_y], excl=kw.get("exclude_boxes"))
        return o_nf(img, head_box, edge_y, sign, spacing, rungs_y, *a, **kw)
    lg.derive_note_first_step = spy
    try:
        for name, on in (("off", False), ("on", True)):
            FH.READER_KEYWORDS["edge_vs_through"] = on
            cap_arm = {}
            r = ctx.read(h["subject"], h["box"], h["cls"], h["global_lines"])
            out[name] = r
            if name == "off":
                cap_arm = dict(cap)
                out["cap"] = cap_arm
    finally:
        lg.derive_note_first_step = o_nf
        FH.READER_KEYWORDS["edge_vs_through"] = True
    return out


def _arm(r):
    d = r.get("detail") or {}
    nf = d.get("note_first") or {}
    return dict(pos=r["pos"], reason=r["reason"], kind=nf.get("kind"), how=nf.get("how"),
                line_y=nf.get("line_y"), k=nf.get("k"), evt=nf.get("edge_vs_through"))


def scan(which, out_json, out_npz):
    doc, fname, pages = DOCS[which]
    cfg = ts.DOCS[doc]
    rec = EXP.Record(load_record(O.SHARED / fname))
    glyphs = collections.defaultdict(list)
    for o in rec.observations:
        if o["quantity"] != Q.GLYPH_BOX or not o.get("value"):
            continue
        pb = (o.get("detail") or {}).get("bbox_page_px")
        if pb:
            glyphs[int(o["subject"].split("/")[1])].append(
                (o["subject"], o["value"][0], tuple(float(v) for v in pb),
                 float(o.get("score") if o.get("score") is not None else 1.0)))
    stats = collections.Counter()
    rows, crops = [], {}
    widths = []
    for page in pages:
        if page not in glyphs:
            continue
        heads, staff_lines, page_boxes = O.page_inputs(rec, page, glyphs[page])
        far = [h for h in heads if lg.far_head_needs_ledger_read(h["pos"])]
        if not far:
            continue
        gray = cv2.cvtColor(render_page_matching_gather(cfg["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
        ctx = FH.FarHeadPage(gray, heads, page_boxes, staff_lines)
        print(which, "page", page, "far", len(far), "shape", ctx.shape_source, flush=True)
        for h in far:
            stats["far_heads"] += 1
            sub = h["subject"]
            fr = rec.obs(Q.FAR_HEAD_LEDGER_POSITION, sub)
            if not fr:
                stats["no_recorded_decision"] += 1
                continue
            recorded = int(round(float(fr[-1]["value"])))
            sh = (fr[-1].get("detail") or {}).get("shape_source") or ""
            if not sh.startswith("page") or ctx.shape_source != sh:
                stats["not_own_page_shape"] += 1
                continue
            cap = {}
            both = _read_both(ctx, h, cap)
            off, on = _arm(both["off"]), _arm(both["on"])
            if off["pos"] != recorded:
                stats["replay_not_reproduced"] += 1
                continue
            stats["reproduced"] += 1
            if both["off"].get("box_source") == "chord_split":
                stats["chord_split_left_out"] += 1
                continue
            c = both["cap"]
            if not c:
                stats["no_note_first_call"] += 1
                continue
            box, sign, sp, rungs, excl = c["box"], c["sign"], c["sp"], c["rungs"], c["excl"]
            widths.append(box[2] - box[0])
            near_y = box[3] if sign < 0 else box[1]
            qual = []
            for r in rungs:
                rn = sign * (r - near_y) / sp
                if NEAR_BAND[0] <= rn <= NEAR_BAND[1]:
                    ev = lg.thin_flat_jut_evidence(gray, r, box, sp, excl)
                    if ev["ok"]:
                        qual.append(dict(y=r, rn=rn, t=max(ev["thickness"])))
            # the line the reader (keyword off) names, and what the rule's quantity says about it
            ly = off["line_y"]
            q = None
            if ly is not None:
                rn = sign * (ly - near_y) / sp
                ev = lg.thin_flat_jut_evidence(gray, ly, box, sp, excl)
                if ev["ok"] and NEAR_BAND[0] - 0.1 <= rn <= NEAR_BAND[1] + 0.1:
                    t = max(ev["thickness"])
                    q = dict(rn=rn, t=t, excess=lg.head_ink_staff_excess(gray, ly, box, sign, sp, t),
                             frac=lg.head_ink_staff_fraction(gray, ly, box, sign, sp))
            row = dict(doc=doc, which=which, subject=sub, page=page, geometry=h["pos"], recorded=recorded,
                       box=list(box), sign=sign, sp=sp, edge=c["edge"], rungs=rungs, qual=qual, off=off, on=on,
                       line_q=q, box_source=both["off"].get("box_source"))
            rows.append(row)
            if qual or on["pos"] != off["pos"]:
                x0, y0, x1, y1 = box
                gx0, gx1 = int(x0 - WIN_X * sp), int(x1 + WIN_X * sp) + 1
                gy0, gy1 = int(y0 - WIN_Y * sp), int(y1 + WIN_Y * sp) + 1
                gx0, gy0 = max(0, gx0), max(0, gy0)
                crops[sub] = np.asarray(gray[gy0:gy1, gx0:gx1])
                row["crop_origin"] = [gx0, gy0]
        del gray, ctx
    med_w = sorted(widths)[len(widths) // 2] if widths else 0
    for r in rows:
        r["sliver"] = (r["box"][2] - r["box"][0]) < 0.6 * med_w
    Path(out_json).write_text(json.dumps(dict(which=which, stats=dict(stats), med_w=med_w, rows=rows), default=float))
    np.savez_compressed(out_npz, **{k.replace("/", "_"): v for k, v in crops.items()})
    print("stats", dict(stats), "rows", len(rows), "with a near-edge line", sum(1 for r in rows if r["qual"]))


# ---------------------------------------------------------------------------
def ordinal(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def words(arm, sign):
    """The reader's answer in words: ON ledger k / in the space beyond ledger k, above or below the staff."""
    if arm["pos"] is None:
        return "no answer"
    side = "above" if sign < 0 else "below"
    k = arm["k"]
    if arm["kind"] == "space":
        return f"in the space beyond ledger {k}, {side} the staff"
    return f"ON the {ordinal(k)} ledger {side} the staff"


def remeasure(gray_crop, origin, y, box, sp):
    """Distance in px from the drawn row `y` to the centre of the line's ink just beside the head: the columns
    0.05..0.40 sp past the box on each side (a ledger juts that far; farther out is other ink), the rows within
    0.35 sp of `y` that are inked across at least half of those columns. None = no line ink beside the head."""
    x0, y0, x1, y1 = box
    gx0, gy0 = origin
    best = None
    for a, b in ((x0 - 0.40 * sp, x0 - 0.05 * sp), (x1 + 0.05 * sp, x1 + 0.40 * sp)):
        a, b = int(a) - gx0, int(b) - gx0
        a, b = max(0, a), min(gray_crop.shape[1], b)
        if b <= a:
            continue
        m = int(0.35 * sp)
        rows = [r for r in range(int(y) - gy0 - m, int(y) - gy0 + m + 1)
                if 0 <= r < gray_crop.shape[0] and (gray_crop[r, a:b] < 140).mean() >= 0.5]
        if not rows:
            continue
        runs, cur = [], [rows[0]]
        for r in rows[1:]:
            if r == cur[-1] + 1:
                cur.append(r)
            else:
                runs.append(cur)
                cur = [r]
        runs.append(cur)
        run = min(runs, key=lambda c: abs(np.mean(c) + gy0 - y))
        d = abs(float(np.mean(run)) + gy0 - y)
        best = d if best is None else min(best, d)
    return best


def tile(row, crop, number):
    sp = row["sp"]
    gx0, gy0 = row["crop_origin"]
    sc = PX_PER_SP / sp
    big = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    im = cv2.cvtColor(big, cv2.COLOR_GRAY2BGR)
    X = lambda x: int(round((x - gx0 + 0.5) * sc))
    Y = lambda y: int(round((y - gy0 + 0.5) * sc))
    x0, y0, x1, y1 = row["box"]
    cv2.rectangle(im, (X(x0), Y(y0)), (X(x1), Y(y1)), (0, 140, 255), 2)       # box: orange
    checks = []
    ly = row["off"]["line_y"]
    if ly is not None:
        cv2.line(im, (0, Y(ly)), (im.shape[1] - 1, Y(ly)), (0, 0, 255), 1)    # the reader's line: red
        checks.append(("red", ly, remeasure(crop, (gx0, gy0), ly, row["box"], sp)))
    if row["on"]["pos"] != row["off"]["pos"] and row["on"]["line_y"] is not None:
        ry = row["on"]["line_y"]
        cv2.line(im, (0, Y(ry)), (im.shape[1] - 1, Y(ry)), (200, 0, 200), 1)  # the rule's line: magenta
        checks.append(("magenta", ry, remeasure(crop, (gx0, gy0), ry, row["box"], sp)))
    if gy0 <= row["edge"] < gy0 + crop.shape[0]:
        cv2.line(im, (0, Y(row["edge"])), (im.shape[1] - 1, Y(row["edge"])), (255, 100, 0), 1)  # staff edge: blue
    return im, checks


def sheet(argv):
    seed = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else 20261006
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 40
    flips_only = "--flips" in argv
    sl, cl, sb, cb, out = argv[:5]
    pools, crops = {}, {}
    for which, s, c in (("litolff", sl, cl), ("brahms", sb, cb)):
        d = json.loads(Path(s).read_text())
        z = np.load(c)
        pools[which] = d
        for k in z.files:
            crops[k] = z[k]
    rng = random.Random(seed)
    picks, pool_counts = [], {}
    for which in ("litolff", "brahms"):
        if flips_only:
            elig = [r for r in pools[which]["rows"] if r["on"]["pos"] != r["off"]["pos"] and r["subject"] not in SEEN]
        else:
            elig = [r for r in pools[which]["rows"] if r["qual"] and not r["sliver"] and r["subject"] not in SEEN
                    and r["off"]["pos"] is not None]
        pool_counts[which] = len(elig)
        picks += rng.sample(sorted(elig, key=lambda r: r["subject"]), min(n // 2 if not flips_only else n, len(elig)))
    rng.shuffle(picks)
    tiles = []
    allchecks = []
    for i, r in enumerate(picks, 1):
        im, ch = tile(r, crops[r["subject"].replace("/", "_")], i)
        allchecks += [(i,) + c for c in ch]
        tiles.append((im, i, r))
    W = max(t[0].shape[1] for t in tiles)
    Hh = max(t[0].shape[0] for t in tiles)
    cap_h = 92
    cols = 5
    cells = []
    for im, i, r in tiles:
        c = np.full((Hh + cap_h, W, 3), 255, np.uint8)
        c[:im.shape[0], :im.shape[1]] = im
        short = r["subject"].replace("glyph/", "")
        cv2.putText(c, f"{i}", (6, Hh + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 2)
        cv2.putText(c, f"{r['which'][:4]} p{r['page']} {short}", (44, Hh + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
        cv2.putText(c, "reader: " + words(r["off"], r["sign"]), (6, Hh + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (0, 0, 200), 1)
        if r["on"]["pos"] != r["off"]["pos"]:
            cv2.putText(c, "rule: " + words(r["on"], r["sign"]), (6, Hh + 64), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (170, 0, 170), 1)
        else:
            cv2.putText(c, "rule: no change", (6, Hh + 64), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (110, 110, 110), 1)
        q = r["line_q"]
        cv2.putText(c, "head ink beyond the line: " + (f"{q['excess']:+.2f} sp" if q and q["excess"] is not None else "n/a"),
                    (6, Hh + 84), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (90, 90, 90), 1)
        cells.append(c)
    rowsimg = []
    for k in range(0, len(cells), cols):
        grp = cells[k:k + cols]
        grp += [np.full_like(cells[0], 255)] * (cols - len(grp))
        rowsimg.append(np.hstack([np.pad(g, ((4, 4), (4, 4), (0, 0)), constant_values=255) for g in grp]))
    img = np.vstack(rowsimg)
    legend = np.full((86, img.shape[1], 3), 255, np.uint8)
    for j, (txt, col) in enumerate((
            ("ORANGE box = the note the reader was asked about.   RED line = the line the reader says the note is ON or just beyond.", (0, 120, 230)),
            ("MAGENTA line (only where the new rule changes the answer) = the line the rule says the note is beyond.   BLUE line = the staff's edge.", (170, 0, 170)),
            ("Question for each tile: is the note ON a line, or in the space beyond the line it touches?   Tell me the tile numbers the reader has WRONG.", (0, 0, 0)))):
        cv2.putText(legend, txt, (8, 22 + 24 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1, cv2.LINE_AA)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out, np.vstack([legend, img]))
    bad = [c for c in allchecks if c[3] is not None and c[3] > 2.0]
    hidden = [c for c in allchecks if c[3] is None]
    print("drawn lines", len(allchecks), "| within 2 px of the line's ink beside the head:",
          len(allchecks) - len(bad) - len(hidden), "| off by more than 2 px:", len(bad), bad,
          "| no line ink beside the head to measure:", len(hidden), [(c[0], c[1]) for c in hidden])
    # the split, over the 40 and over the whole eligible population
    Path(out).with_suffix(".json").write_text(json.dumps(
        [dict(n=i, subject=r["subject"], which=r["which"], page=r["page"], sign=r["sign"], reader=r["off"], rule=r["on"],
              line_q=r["line_q"], checks=[c[1:] for c in allchecks if c[0] == i]) for i, r in enumerate(picks, 1)],
        default=float))
    report(pools, picks, pool_counts, seed)


def report(pools, picks, pool_counts, seed):
    X = lg.EDGE_VS_THROUGH_STAFF_EXCESS_MAX_SPACES

    def split(rows, label):
        c = collections.Counter()
        for r in rows:
            q = r["line_q"]
            if q is None or q["excess"] is None:
                c["reader's line not a shown line at the staff-side edge (quantity undefined)"] += 1
                continue
            hangs = q["excess"] <= X
            kind = r["off"]["kind"]
            c[f"reader {('ON' if kind == 'on' else 'space'):>5} | head {'hangs beyond line' if hangs else 'crosses line':<17}"] += 1
        flips = sum(1 for r in rows if r["on"]["pos"] != r["off"]["pos"])
        print(f"== {label}: n={len(rows)}; the rule changes {flips}")
        for k, v in sorted(c.items()):
            print(f"   {v:4d}  {k}")
    print(f"threshold stated before scoring: head ink beyond the line's half thickness <= {X} sp = hangs beyond the line")
    print("eligible pool per document:", pool_counts, "| seed", seed)
    split(picks, "THE SAMPLE OF 40")
    allp = [r for w in pools.values() for r in w["rows"] if r["qual"] and not r["sliver"] and r["subject"] not in SEEN
            and r["off"]["pos"] is not None]
    split(allp, "WHOLE ELIGIBLE POPULATION")
    flips = [r for w in pools.values() for r in w["rows"] if r["on"]["pos"] != r["off"]["pos"]]
    print("== EVERY head the rule changes (all far heads of both records in the page ranges, reproduced, own-page shape):", len(flips))
    for r in flips:
        print("  ", r["subject"], "reader", r["off"]["pos"], r["off"]["how"], "->", r["on"]["pos"], r["on"]["how"],
              "| seen already" if r["subject"] in SEEN else "")
    for w, d in pools.items():
        print("stats", w, d["stats"])


if __name__ == "__main__":
    if sys.argv[1] == "scan":
        scan(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sheet(sys.argv[2:])
