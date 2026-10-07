"""lane-lines-combined (2026-10-06): ONE sheet of the 5 right->abstain heads, before (raw staff lines) / after (this combined tree),
numbered. Crop, local lines (cyan, 1 px), box used (orange), every ledger rung the reader found (yellow ticks at both edges),
the line it chose (magenta); the answer in words under each. Then every drawn line is re-measured against the page's pixel rows.

  python3 lc5_sheet.py <litolff_find.json> <brahms_find.json> <truth.json> <out.png> [--arm new]
The JSONs are `farhead_per_bar_grid_oos.py scan` output (the combined arm = 'new' of a run with OMR_CELL_LINE_FIND=1) and
`lc5_truth.py` output."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import lc5_crop as C
import truth_set_2_44c as ts
from frame import render_page_matching_gather
from farhead_per_bar_grid_report import words_pos, ink_row

DOC = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
HEADS = [  # (n, label, doc, page, subject, Sean's / truth answer position, who said)
    (1, "truth set, Brahms p1", "brahms", 1, "glyph/1/1/8/7/4", 13, "the truth encoding"),
    (2, "note_first tile 2 (Sean: right)", "brahms", 19, "glyph/19/1/0/5/10", -3, "Sean"),
    (3, "night tile 12 (Sean: right)", "litolff", 5, "glyph/5/0/5/9/0", -6, "Sean"),
    (4, "edge_flip tile 1 (Sean: right)", "brahms", 4, "glyph/4/0/0/9/15", -3, "Sean"),
    (5, "edge_flip tile 12 (Sean: right)", "brahms", 14, "glyph/14/0/1/0/6", -5, "Sean"),
]
REASON = {
    "no_line_at_the_note_box": "no ledger line found at the head's box",
    "no_rungs": "no ledger line found at all",
    "count_does_not_fit": "the ledgers it counted do not fit one even pitch",
}


def norm(read):
    nf = {"line_y": read.get("line_y")}
    return dict(lines=read["lines"], box_used=read["box_used"], rungs=read.get("rungs") or [], note_first=nf,
                pos=read["pos"], reason=read["reason"], box_source=read.get("box_source"))


def say(d):
    if d["pos"] is not None:
        return "reads: " + words_pos(d["pos"])
    key = next((k for k in REASON if d["reason"].startswith(k)), None)
    return "no answer: " + (REASON[key] if key else d["reason"][:60])


def text_under(im, lines, w):
    pad = 16 * len(lines) + 8
    out = np.full((im.shape[0] + pad, w, 3), 255, np.uint8)
    out[:im.shape[0], :im.shape[1]] = im[:, :w]
    for i, t in enumerate(lines):
        cv2.putText(out, t, (6, im.shape[0] + 14 + 16 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
    return out


def drawn_offsets(gray, d):
    """Offset (px) of each drawn staff line from the page's own darkest-run centre in the flank columns beside the box."""
    x0, y0, x1, y1 = d["box_used"]
    sp = (max(d["lines"]) - min(d["lines"])) / 4.0
    res = []
    for y in d["lines"]:
        vals = []
        for a, b in ((x0 - 1.6 * sp, x0 - 0.3 * sp), (x1 + 0.3 * sp, x1 + 1.6 * sp)):
            seg = gray[max(0, int(y - 0.55 * sp)):int(y + 0.55 * sp) + 1, max(0, int(a)):int(b)]
            if seg.size == 0:
                continue
            rows = seg.astype(float).mean(axis=1)
            thr = (rows.min() + np.median(rows)) / 2.0
            k = int(np.argmin(rows))
            if rows[k] > np.median(rows) - 8:
                continue
            lo = hi = k
            while lo > 0 and rows[lo - 1] <= thr:
                lo -= 1
            while hi < len(rows) - 1 and rows[hi + 1] <= thr:
                hi += 1
            vals.append(max(0, int(y - 0.55 * sp)) + (lo + hi) / 2.0)
        if vals:
            res.append(float(np.mean(vals)) - y)
    return res


def main(lit, bra, truth, out_png, arm="new"):
    data = {"litolff": json.load(open(lit))["heads"], "brahms": json.load(open(bra))["heads"]}
    tr = json.load(open(truth))
    grays, panels, meas = {}, [], []
    for n, label, doc, page, subj, ans, who in HEADS:
        if (doc, page) not in grays:
            cfg = ts.DOCS[DOC[doc]]
            grays[(doc, page)] = cv2.cvtColor(render_page_matching_gather(cfg["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
        g = grays[(doc, page)]
        if n == 1:
            b, a = tr["old"], tr["new"]
            b = dict(b, note_first=b["note_first"]); a = dict(a, note_first=a["note_first"])
        else:
            r = data[doc][subj]
            b, a = norm(r["old"]["read"]), norm(r[arm]["read"])
        cb, ca = C.crop(g, b), C.crop(g, a)
        h = max(cb.shape[0], ca.shape[0])
        padi = lambda im: cv2.copyMakeBorder(im, 0, h - im.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        row = np.hstack([padi(cb), padi(ca)])
        meas.append((n, drawn_offsets(g, b), drawn_offsets(g, a)))
        rg = lambda d: "rungs found: " + (", ".join(f"{x['y']:.0f}" for x in d["rungs"]) or "none")
        lines = [f"{n}. {doc} {subj} -- {label}; the right answer ({who}): {words_pos(ans)}",
                 "BEFORE (raw lines, left)  " + say(b), "AFTER (combined tree, right)  " + say(a),
                 rg(b) + "   |   " + rg(a),
                 f"box used: before {b['box_source']}, after {a['box_source']}"]
        panels.append(text_under(row, lines, row.shape[1]))
    W = max(p.shape[1] for p in panels)
    big = np.vstack([cv2.copyMakeBorder(p, 0, 10, 0, W - p.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for p in panels])
    legend = ("cyan = the staff lines the reader used (1 px at the crop's scale)   orange = the box it used   yellow ticks = every ledger rung "
              "it found   magenta = the line it rested the answer on")
    top = np.full((24, big.shape[1], 3), 255, np.uint8)
    cv2.putText(top, legend, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(out_png, np.vstack([top, big]))
    print("== drawn lines vs the page's pixel rows (px; flank columns beside the box)")
    for n, mb, ma in meas:
        f = lambda v: "n=%d median |off| %.2f max %.2f" % (len(v), np.median(np.abs(v)), np.max(np.abs(v))) if v else "none measured"
        print(f"  {n}: before {f(mb)} | after {f(ma)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], "new")
