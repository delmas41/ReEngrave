"""2.99 against Sean's hand truth (Brahms 1, Breitkopf 317803, PDF index 0).

    python3 .../handtruth_2_99.py REC.json [--page 0] [--truth data/hand-truth/pages/imslp317803/0.json]

PATH: STAGED, GATHER + ADJUDICATE rows only. Two questions, both over cells Sean
SWEPT (`inspected` holds `all-ink`: a box missing there means "not printed", not
"not looked at"):

  FOUND    of the truth's `rest8th` / `restQuarter` boxes in swept cells, how many
           does the reader read as the right rest on the INK ALONE (the standing
           detector box's coverage zeroed -- the same control `controls_2_99.py`
           runs)? That is the reader's recall on rests the detector DID box (every
           truth rest on this page is `prefill-confirmed`, i.e. the detector's own).
  INVENTED every cluster the reader DECIDED a rest, with no detector box over it,
           whose centre is in a swept cell: does a truth box of a REST class lie
           over it (not invented), a truth box of ANOTHER class (named: a flat is
           a flat), or none (the truth says nothing is printed there)?

Frame control: the truth and the record share a frame only if the truth's rests
overlap clusters the record filed. It prints how many did; a zero stops the run.
"""
import argparse
import collections
import json
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import unboxed_rest_2_99 as U  # noqa: E402
from tools.omr.staged import adjudicate  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Log, Q, READERS  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("record")
ap.add_argument("--page", type=int, default=0)
ap.add_argument("--truth", default="data/hand-truth/pages/imslp317803/0.json")
a = ap.parse_args()
truth = json.load(open(a.truth))
rows = [r for r in U.rows(U.load(a.record))
        if int(r["subject"].split("/")[1]) == a.page and r.get("bbox_page_px")]
swept = [c["rect"] for c in truth["cells"] if "all-ink" in (c.get("inspected") or [])]


def inside(cx, cy, rect):
    return rect[0] <= cx <= rect[2] and rect[1] <= cy <= rect[3]


def in_swept(box):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return any(inside(cx, cy, r) for r in swept)


def iou(a_, b_):
    ix = max(0, min(a_[2], b_[2]) - max(a_[0], b_[0]))
    iy = max(0, min(a_[3], b_[3]) - max(a_[1], b_[1]))
    inter = ix * iy
    ua = (a_[2] - a_[0]) * (a_[3] - a_[1]) + (b_[2] - b_[0]) * (b_[3] - b_[1]) - inter
    return inter / ua if ua > 0 else 0.0


def overlap_min(a_, b_):
    ix = max(0, min(a_[2], b_[2]) - max(a_[0], b_[0]))
    iy = max(0, min(a_[3], b_[3]) - max(a_[1], b_[1]))
    sm = min((a_[2] - a_[0]) * (a_[3] - a_[1]), (b_[2] - b_[0]) * (b_[3] - b_[1]))
    return ix * iy / sm if sm > 0 else 0.0


adjudicate._ensure_decisions()


def ink_only_reading(r, cover=0.0):
    lg = Log()
    g = R.glyph(0, 0, 0, 1, 350000)
    det = {x: r.get(x) for x in (
        "width_spaces", "height_spaces", "staff_step", "n_pieces", "fill",
        "max_column_share", "mass_y", "column_profile", "covered_by",
        "right_head", "first_cell", "left_of_header", "header_known",
        "touches_cell_edge")}
    det.update(coverage=cover, bbox_canonical=[0, 0, 1, 1],
               bbox_page_px=r["bbox_page_px"])
    lg.observe(g, Q.UNBOXED_REST_SHAPE, r["height_spaces"],
               reader=READERS.CV_UNBOXED_REST_SHAPE, frame="cell:1", **det)
    lg.freeze()
    adjudicate.run(lg, order=(Q.UNBOXED_INK_IS_A_REST,))
    v = lg.verdict(Q.UNBOXED_INK_IS_A_REST, g)
    return str(v.value) if v.outcome.value == "decided" else "abstain:" + v.reason


# FOUND
t_rests = [b for b in truth["boxes"] if b["cls"] in ("rest8th", "restQuarter")]
found = collections.Counter()
matched = 0
for b in t_rests:
    rect = b["rect"]
    if not in_swept(rect):
        found[(b["cls"], "unswept")] += 1
        continue
    best = max(rows, key=lambda r: iou(rect, r["bbox_page_px"]), default=None)
    if best is None or iou(rect, best["bbox_page_px"]) < 0.3:
        found[(b["cls"], "no_cluster_filed")] += 1
        continue
    matched += 1
    said = ink_only_reading(best)
    want = "eighth" if b["cls"] == "rest8th" else "quarter"
    found[(b["cls"], "READ " + want if said == want else "said " + said)] += 1
print("FRAME CONTROL: truth rests that overlap a filed cluster:", matched,
      "of", len(t_rests))
if not matched:
    sys.exit(3)
print("FOUND (ink alone, coverage zeroed):")
for k, n in sorted(found.items()):
    print("  ", n, k)

# INVENTED
inv = collections.Counter()
detail = []
# RE-DECIDED on today's tree from the filed rows (the record's own verdicts
# were made by whatever tree gathered it).
for r in rows:
    r["now"] = ink_only_reading(r, cover=r.get("coverage") or 0.0)
decided = [r for r in rows if r["now"] in ("eighth", "quarter")]
for r in decided:
    if (r.get("coverage") or 0) >= 0.1 or not in_swept(r["bbox_page_px"]):
        inv["not_unboxed_or_unswept"] += 1
        continue
    over = [b for b in truth["boxes"]
            if overlap_min(r["bbox_page_px"], b["rect"]) >= 0.3
            and b["cls"] not in ("staff", "ledgerLine", "stem", "beam", "slur", "tie")]
    classes = sorted({b["cls"] for b in over})
    if any(c.startswith("rest") for c in classes):
        inv["truth_has_a_rest_here"] += 1
    elif classes:
        inv["truth_says_another_mark:" + "+".join(classes)] += 1
    else:
        inv["truth_says_nothing_printed"] += 1
    detail.append({"subject": r["subject"], "value": r["now"],
                   "box": r["bbox_page_px"], "truth_classes": classes})
print("DECIDED unboxed rests in swept cells:", len(decided))
for k, n in sorted(inv.items()):
    print("  ", n, k)
for d_ in detail:
    print("   ", d_)
