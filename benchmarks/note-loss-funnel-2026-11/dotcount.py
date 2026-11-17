"""ROADMAP 2.311 small test -- TRY TO FALSIFY "augmentation dots are lost because the detector never draws a box on them,
and that writes a dotted note plain and READ".  Reads SAVED facts/extra only (the frozen-sample `bra-a` gather); nothing is
re-gathered, nothing in tools/ is changed.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:RANKING_LIB python3 benchmarks/note-loss-funnel-2026-11/dotcount.py \
        --facts BRA.facts.json --extra BRA.extra.json --out benchmarks/note-loss-funnel-2026-11/dotcount-results.json

RANKING_LIB = a folder holding `redbars.py` and `redbar_classify.py` from branch origin/lane-2.311-redbar-ranking (not on main yet).

PART A (Brahms page 0, Sean's labels, the cells he fully swept): for each augmentation dot HE labelled
  (a) a detector box on it            (centre of a detector augmentationDot box inside his dot box, grown 0.3 space)
  (b) ... but the note was written with fewer dots than he labelled  (the dot was seen, not attached)
  (c) no detector box, but a dot-sized ink piece with no detector box stands on it (the page ledger holds the ink, unboxed)
  (d) no box and no such piece
and the cost on his dotted heads: written plain and READ (hidden wrong), written plain and GUESSED (blue), not written, written
dotted; in a red bar.  Then the reverse: notes written dotted whose head he did not dot.
PART B (the same page): the "unboxed dot-sized ink right of a plain READ note" test (the red-bar ranking's `ink_never_boxed`),
scored against his labels: how often it fires on a note he dotted, and how often on one he did not.
"""
from __future__ import annotations

import argparse
import collections
import json

import judge as J
from tools.omr.staged.judged import boxes_overlap

import redbar_classify as RC


def c_of(b):
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


def inside(pt, box, grow):
    return box[0] - grow <= pt[0] <= box[2] + grow and box[1] - grow <= pt[1] <= box[3] + grow


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", required=True)
    ap.add_argument("--extra", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    f = json.load(open(a.facts))
    extra = json.load(open(a.extra))
    page_no = 0
    page, truth, u, in_scope, swept = J.load_truth(J.TRUTH)
    heads, att = J.attach(truth, u)
    heads_by_id = {h.id: h for h in heads}
    dots = [t for t in truth if t.family == "augmentation_dot"]
    glyphs = f["glyphs"]
    pg = {k: g for k, g in glyphs.items() if g["page"] == page_no}
    dboxes = [(k, g) for k, g in pg.items() if g["cls"] == "augmentationDot"]
    ink = [(k, g) for k, g in pg.items() if g["cls"] is None and int(k.split("/")[5]) >= RC.INK_MIN]
    # pair written notes to his heads exactly as judge.py does (best overlap first, one each)
    wnotes = [h for h in f["written"] if h["page"] == page_no and h["kind"] == "note"]
    pairs = sorted(((boxes_overlap(h["box"], t.rect)[1], i, j) for i, t in enumerate(heads) for j, h in enumerate(wnotes)
                    if boxes_overlap(h["box"], t.rect)[0]), reverse=True)
    t2w, used = {}, set()
    for _iou, i, j in pairs:
        if i in t2w or j in used:
            continue
        t2w[i] = j
        used.add(j)
    # red bars (every list the export report draws red) keyed (page, system, staff, cell)
    red = set()
    for lst in (f["bars"]["red_not_add_up"], f["bars"]["unread_empty"], f["bars"]["held"],
                [b for b in f["bars"]["partial"] if b.get("status") == "partial"]):
        for b in lst:
            if b.get("page") == page_no and not b.get("doubled_staff_copy"):
                red.add((b["page"], b["system"], b["staff"], b["cell"]))

    def bar_of(rg):
        p = rg.split("/")
        return (int(p[1]), int(p[2]), int(p[3]), int(p[4]))

    # which head each dot of his belongs to (judge.attach's rule, recomputed so each DOT is kept)
    owner = {}
    for d in dots:
        best = None
        for h in heads:
            dx, dy = (J.cx(d.rect) - h.rect[2]) / u, abs(J.cy(d.rect) - J.cy(h.rect)) / u
            if -0.2 <= dx <= 2.0 and dy <= 0.8 and (best is None or dx + dy < best[0]):
                best = (dx + dy, h)
        owner[d.id] = best[1] if best else None
    per_head = collections.defaultdict(list)
    for d in dots:
        if owner[d.id] is not None:
            per_head[owner[d.id].id].append(d)
    tally = collections.Counter()
    rows = []
    for d in dots:
        h = owner[d.id]
        r = dict(dot=d.id, box=[round(x, 1) for x in d.rect], head=h.id if h else None)
        boxed = [(k, g) for k, g in dboxes if inside(c_of(g["box"]), d.rect, 0.3 * u)]
        r["detector_box"] = [k for k, _ in boxed]
        r["dot_role"] = [extra["dot_role"].get(k) for k, _ in boxed]
        r["other_class_box"] = [g["cls"] for k, g in pg.items()
                                if g["cls"] not in (None, "augmentationDot", "staffLine") and inside(c_of(d.rect), g["box"], 0)][:4]
        if h is None:
            r["state"] = "no_head_of_his"
        else:
            i = [n for n, t in enumerate(heads) if t.id == h.id][0]
            w = wnotes[t2w[i]] if i in t2w else None
            wd = len((w.get("sub") or {}).get("dot") or []) if w else None
            r["head_written"] = None if w is None else dict(type=w["type"], dots=wd, blue=w["blue"], rg=w["rg"],
                                                            red_bar=bar_of(w["rg"]) in red)
            # attached = the note carries at least as many dots as he labelled on its stem (judge.attach's per-head count)
            r["attached"] = bool(w is not None and wd is not None and wd >= att[h.id]["dots"])
        has_box = bool(boxed)
        near_ink = [k for k, g in ink if inside(c_of(g["box"]), d.rect, 0.3 * u)]
        r["unboxed_ink_piece"] = near_ink
        if r["head"] is None:
            tally["no_head"] += 1
        if has_box:
            tally["a_box"] += 1
            if r.get("head_written") is None:
                tally["a_box__note_not_written"] += 1
            elif r["attached"]:
                tally["a_box__attached"] += 1
            else:
                tally["b_box_not_attached"] += 1
        elif near_ink:
            tally["c_no_box_unboxed_ink_piece"] += 1
        else:
            tally["d_no_box_no_ink_piece"] += 1
        rows.append(r)
    # the cost, per head he dotted
    cost = collections.Counter()
    cost_rows = []
    for hid, ds in per_head.items():
        h = heads_by_id[hid]
        i = [n for n, t in enumerate(heads) if t.id == hid][0]
        k = att[hid]["dots"]
        if i not in t2w:
            cost["head_not_written"] += 1
            cost_rows.append((hid, "not_written"))
            continue
        w = wnotes[t2w[i]]
        wd = len((w.get("sub") or {}).get("dot") or [])
        inred = bar_of(w["rg"]) in red
        if wd >= k:
            cost["written_dotted_right"] += 1
            st = "dotted_right"
        elif wd == 0:
            cost["written_plain_" + ("GUESSED_blue" if w["blue"] else "READ")] += 1
            st = "plain_" + ("GUESSED" if w["blue"] else "READ")
        else:
            cost["written_fewer_dots"] += 1
            st = "fewer"
        if st.startswith("plain") or st == "fewer":
            cost["short_dot_head_in_red_bar" if inred else "short_dot_head_not_in_red_bar"] += 1
        cost_rows.append((hid, st, w["rg"], inred))
    heads_dotted = len(per_head)
    # reverse: written dotted, he labelled none
    rev = collections.Counter()
    rev_rows = []
    for j, w in enumerate(wnotes):
        wd = len((w.get("sub") or {}).get("dot") or [])
        if not wd or not in_scope(w["box"]):
            continue
        ti = [i for i, jj in t2w.items() if jj == j]
        if not ti:
            rev["written_dotted_no_head_of_his_at_the_place"] += 1
            continue
        t = heads[ti[0]]
        if att[t.id]["dots"] == 0:
            rev["written_dotted_he_labelled_no_dot"] += 1
            rev_rows.append(dict(rg=w["rg"], box=[round(x, 1) for x in w["box"]], type=w["type"], blue=w["blue"]))
        elif att[t.id]["dots"] < wd:
            rev["written_more_dots_than_he"] += 1
        else:
            rev["dotted_both"] += 1
    # PART B: the ink-never-boxed test, against his labels
    ctx = RC.Ctx("brahms", f, extra, {page_no})
    B = collections.Counter()
    b_rows = []
    for i, t in enumerate(heads):
        if i not in t2w:
            continue
        w = wnotes[t2w[i]]
        if w.get("blue") or (w.get("sub") or {}).get("dot") or RC._dur(w) is None:
            continue
        key = bar_of(w["rg"])
        ln = ctx.sp(key)
        if not ln:
            continue
        ev = RC._near_dot_evidence(ctx, key, w, ln)
        dotted = att[t.id]["dots"] > 0
        B[(ev, "he_dotted" if dotted else "he_did_not")] += 1
        if ev == "ink_never_boxed":
            b_rows.append(dict(rg=w["rg"], he_dotted=dotted))
    res = dict(n_his_dots=len(dots), n_his_heads_dotted=heads_dotted, n_detector_dot_boxes_page0=len(dboxes),
               dots=dict(tally), cost=dict(cost), reverse=dict(rev), reverse_rows=rev_rows,
               ink_never_boxed_test={"%s/%s" % k: v for k, v in B.items()}, ink_never_boxed_rows=b_rows, rows=rows)
    print(json.dumps({k: v for k, v in res.items() if k not in ("rows", "reverse_rows", "ink_never_boxed_rows")}, indent=1))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=0, default=str)


if __name__ == "__main__":
    main()
