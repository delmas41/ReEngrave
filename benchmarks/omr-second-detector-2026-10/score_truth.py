"""ROADMAP 2.110 Step A.2/A.3/A.4 -- score detector classes against SEAN'S HAND TRUTH (Brahms 317803 pdf idx 0, 1,566 boxes),
not against box counts, and prove the scorer can fail.

    python3 benchmarks/omr-training-scale-2026-10/score_truth.py --records label=rec.json [label=rec.json ...] --out score.json

Per class group, per arm, over the cells Sean inspected for that family (a box in no inspected cell is unscored):
  recall    = truth boxes matched by a read box of the same class group / truth boxes          (IoU >= 0.3, hollow_graft matcher `RO.match_glyphs`,
                                                                                                 each box used once)
  precision = read boxes of the group that match a truth box / read boxes of the group in scope
  loose     = recall at IoU >= 0.1 (a long thin beam / ledger line shifts a few px and its IoU collapses; this says whether
              the strict recall is the detector or the matcher)
Two views: GATHER (every detector box) and ADJ (the boxes ADJUDICATE did not refuse / give away).

CONTROLS (rule 7), run on the FIRST arm's real glyph list before any number is printed, exit 1 if one does not behave:
  1. truth matched against itself: recall = precision = 1 for every group.
  2. all beams deleted from the read side: beam recall = 0, every other group's recall unchanged.
  3. every box shifted 3 staff spaces in x and y: every group's recall < 0.15 (the scorer is not matching by class counts).
  4. beams only: a read side with 3x the beam boxes (copies shifted 3 spaces): beam recall unchanged, beam precision falls to ~1/4.
"""
from __future__ import annotations

import argparse, collections, json, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from tools.omr.hand_truth import score as SC  # noqa: E402
from tools.omr.hand_truth import store as ST  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402

PAGE = "data/hand-truth/pages/imslp317803/0.json"
HOLLOW = ("noteheadHalf", "noteheadWhole", "noteheadDoubleWhole")
GROUPS = {  # name -> (class predicate, a class used to look up the family Sean inspected)
    "beam": (lambda c: c == "beam", "beam"),
    "ledgerLine": (lambda c: c == "ledgerLine", "ledgerLine"),
    "tie": (lambda c: c == "tie", "tie"),
    "slur": (lambda c: c == "slur", "slur"),
    "hollow heads": (lambda c: c.startswith(HOLLOW), "noteheadHalfInSpace"),
    "black heads": (lambda c: c.startswith("noteheadBlack"), "noteheadBlackInSpace"),
    "timeSig digits": (lambda c: c.startswith("timeSig"), "timeSig8"),
    "augmentationDot": (lambda c: c == "augmentationDot", "augmentationDot"),
}
KEPT_DROP = (RO.REFUSED, RO.GIVEN_AWAY)


def rate(n, d):
    return None if not d else round(n / d, 4)


def score_side(page, truth, read, view, min_iou=0.3):
    """truth: [(cls, rect)], read: [(cls, rect, status)] -> {group: {...}}"""
    out = {}
    for name, (pred, fam_cls) in GROUPS.items():
        cells = SC.cells_inspected_for(page, SC.family(fam_cls))
        if not cells:
            out[name] = {"status": "REFUSED: no cell inspected for this family"}
            continue
        scope = SC.Scope(cells)
        t = [(i, r, c) for i, (c, r) in enumerate(x for x in truth if pred(x[0]) and scope.holds(x[1]))]
        rr = [(c, r, s) for c, r, s in read if pred(c) and scope.holds(r) and (view == "gather" or s not in KEPT_DROP)]
        rd = [(i, r, c) for i, (c, r, s) in enumerate(rr)]
        row = {"truth": len(t), "read": len(rd)}
        for tag, thr in (("", min_iou), ("loose_", 0.1)):
            pairs, only_t, only_r = SC.match_boxes(t, rd, min_iou=thr)
            row[tag + "matched"] = len(pairs)
            row[tag + "recall"] = rate(len(pairs), len(t))
            row[tag + "precision"] = rate(len(pairs), len(rd))
        out[name] = row
    return out


def sides(page, run):
    truth = [(SC.canonical_cls(b.cls), tuple(b.rect)) for b in page.boxes]
    gl = SC.read_glyphs(run, page.pdf_page_index)
    read = [(g.cls, tuple(g.rect), g.status) for g in gl]
    return truth, read


def controls(page, truth, read):
    ok = True
    log = []
    base = score_side(page, truth, read, "gather")
    # 1 self-match
    s1 = score_side(page, truth, [(c, r, "kept") for c, r in truth], "gather")
    bad = {k: v for k, v in s1.items() if "recall" in v and (v["recall"] != 1.0 or v["precision"] != 1.0)}
    log.append(f"1 truth vs itself: every group recall=precision=1 -> {'PASS' if not bad else 'FAIL ' + str(bad)}")
    ok &= not bad
    # 2 drop beams
    s2 = score_side(page, truth, [x for x in read if x[0] != "beam"], "gather")
    chg = [k for k in base if "recall" in base[k] and k != "beam" and s2[k]["recall"] != base[k]["recall"]]
    p2 = s2["beam"]["recall"] == 0.0 and not chg
    log.append(f"2 all beams deleted: beam recall {base['beam']['recall']} -> {s2['beam']['recall']}, other groups changed: {chg or 'none'} -> {'PASS' if p2 else 'FAIL'}")
    ok &= p2
    # 3 shift 3 spaces
    space = statistics.median(b.space for b in SC.staff_bands(page))
    d = 3 * space
    s3 = score_side(page, truth, [(c, (r[0] + d, r[1] + d, r[2] + d, r[3] + d), s) for c, r, s in read], "gather")
    hi = {k: (base[k]["recall"], s3[k]["recall"]) for k in s3 if "recall" in s3[k] and (s3[k]["recall"] or 0) >= 0.15}
    log.append(f"3 all boxes shifted 3 spaces ({d:.1f}px): max recall now {max((v['recall'] or 0) for v in s3.values() if 'recall' in v)} -> {'PASS' if not hi else 'FAIL ' + str(hi)}")
    ok &= not hi
    # 4 triple the beams with shifted copies
    extra = [(c, (r[0] + d, r[1] + d, r[2] + d, r[3] + d), s) for c, r, s in read if c == "beam"] * 2
    s4 = score_side(page, truth, read + extra, "gather")
    p4 = s4["beam"]["recall"] == base["beam"]["recall"] and (s4["beam"]["precision"] or 0) < 0.5 * (base["beam"]["precision"] or 1)
    log.append(f"4 beam boxes x3 (2 shifted copies): recall {base['beam']['recall']}->{s4['beam']['recall']}, precision {base['beam']['precision']}->{s4['beam']['precision']} -> {'PASS' if p4 else 'FAIL'}")
    ok &= p4
    return ok, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", nargs="+", required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    page = ST.load(Path.cwd() / PAGE)
    runs = {s.split("=", 1)[0]: RO.load_run(s.split("=", 1)[1]) for s in a.records}
    first = next(iter(runs))
    truth, read0 = sides(page, runs[first])
    ok, log = controls(page, truth, read0)
    print(f"controls (run on the real glyph list of arm '{first}'):")
    for l in log:
        print("  ", l)
    if not ok:
        print("CONTROL FAILED -- numbers withheld"); return 1
    res = {"truth_boxes": len(truth), "controls": log, "arms": {}}
    for lab, run in runs.items():
        _, read = sides(page, run)
        res["arms"][lab] = {v: score_side(page, truth, read, v) for v in ("gather", "adj")}
        res["arms"][lab]["box_counts_all_classes"] = dict(collections.Counter(c for c, _, _ in read).most_common(40))
    print("\nrecall / precision (strict IoU>=.3)  [loose recall IoU>=.1] ; GATHER view then ADJ view")
    for view in ("gather", "adj"):
        print(f"--- {view}")
        print(f"{'group':16s} {'truth':>5s} " + " ".join(f"{l:>26s}" for l in runs))
        for g in GROUPS:
            row = []
            for lab in runs:
                r = res["arms"][lab][view][g]
                row.append("n/a" if "recall" not in r else f"R {r['matched']}/{r['truth']}={r['recall']:.2f} P {r['precision'] if r['precision'] is None else format(r['precision'], '.2f')} [{r['loose_recall']:.2f}] n={r['read']}")
            t = res["arms"][first][view][g].get("truth", "")
            print(f"{g:16s} {t:>5} " + " ".join(f"{x:>26s}" for x in row))
    if a.out:
        a.out.write_text(json.dumps(res, indent=1))
    return 0

if __name__ == "__main__":
    sys.exit(main())
