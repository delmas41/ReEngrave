#!/usr/bin/env python3
"""lane-ledger-rungs (2026-10-01): per-head breakdown of the round-3
scoring (f349ffd2), answering two of Sean's questions from the numbers
alone -- publisher (Litolff vs Brahms) and distance-from-staff (ledgers
out) -- never interpreted beyond what is printed here.

MEASUREMENT ONLY. Writes benchmarks/omr-local-staff-2026-09/
ledger_breakdown_r3.csv and prints tables B-E to stdout.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

CSV_PATH = Path(__file__).resolve().parent / "ledger_breakdown_r3.csv"


def _ledgers_out(ref_pos: int) -> int:
    edge_pos = 0 if ref_pos < 0 else 8
    offset = abs(ref_pos - edge_pos)
    return -(-offset // 2)  # ceil(offset / 2)


def build_rows():
    out = []
    for doc_id in ts.DOCS:
        loaded = ts.load_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        boxes_by_page = score._notehead_boxes_by_page(rec)
        r = score.score_doc(doc_id)
        rows_by_sub = {row["subject"]: row for row in score._far_head_rows(doc_id, loaded)}

        for h in r["per_head"]:
            row = rows_by_sub.get(h["subject"])
            if row is None:
                continue
            ref_pos = h["truth_pos"][0]  # onset-exact truth is single-valued here
            side = "above" if ref_pos < 0 else "below"
            ledgers_out = _ledgers_out(ref_pos)

            box = row["page_box"]
            x0, y0, x1, y1 = box
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            line_rows = rec.obs(Q.STAFF_LINES, row["staff_key"])
            lines = sorted(float(v) for v in line_rows[-1]["value"])
            spacing = (lines[-1] - lines[0]) / 4.0
            gray = pages.get(row["page"])
            others = [b for (s, b) in boxes_by_page.get(row["page"], [])
                     if s != row["subject"]]
            items = lg.measure_ledger_rungs(
                gray, lines, cx, head_y=cy, exclude_boxes=others,
                head_box_x=(x0, x1),
            )[side]

            # Gaps between successive measured rungs, nearest-first ->
            # walk outward; ratio = gap / staff spacing.
            ratios = []
            for i in range(len(items) - 1):
                gap = abs(items[i + 1] - items[i])
                ratios.append(gap / spacing if spacing > 0 else None)
            ratios = [rr for rr in ratios if rr is not None]
            max_dev = max((abs(rr - 1.0) for rr in ratios), default=None)

            rungs_verdict = {"right": "right", "wrong": "wrong",
                             "abstain": "undecided"}[h["v_after"]]

            out.append(dict(
                doc=doc_id, subject=h["subject"], ref_pos=ref_pos, side=side,
                ledgers_out=ledgers_out,
                geom_pos=h["geom_pos"], geom_verdict=h["v_geom"],
                rungs_pos=h["after_pos"], rungs_verdict=rungs_verdict,
                n_rungs_found=len(items),
                spacing_px=round(spacing, 3),
                rung_gap_ratios=";".join(f"{rr:.3f}" for rr in ratios),
                max_gap_deviation=(round(max_dev, 3) if max_dev is not None else ""),
            ))
    return out


def write_csv(rows):
    fields = ["doc", "subject", "ref_pos", "side", "ledgers_out",
             "geom_pos", "geom_verdict", "rungs_pos", "rungs_verdict",
             "n_rungs_found", "spacing_px", "rung_gap_ratios",
             "max_gap_deviation"]
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def table_b(rows, doc_id):
    buckets = {1: [], 2: [], 3: [], "4+": []}
    for r in rows:
        if r["doc"] != doc_id:
            continue
        k = r["ledgers_out"] if r["ledgers_out"] <= 3 else "4+"
        buckets[k].append(r)
    print(f"\n=== Table B: {doc_id} -- by ledgers out ===")
    print(f"{'ledgers':<8}{'n':<5}{'geom_right':<12}{'rungs_right':<13}"
         f"{'rungs_undec':<13}{'both_right':<12}{'both_wrong':<12}"
         f"{'only_geom':<11}{'only_rungs':<11}")
    for k in (1, 2, 3, "4+"):
        rs = buckets[k]
        n = len(rs)
        if n == 0:
            print(f"{str(k):<8}{0:<5}" + "-" * 70)
            continue
        geom_right = sum(1 for r in rs if r["geom_verdict"] == "right")
        rungs_right = sum(1 for r in rs if r["rungs_verdict"] == "right")
        rungs_undec = sum(1 for r in rs if r["rungs_verdict"] == "undecided")
        both_right = sum(1 for r in rs if r["geom_verdict"] == "right" and r["rungs_verdict"] == "right")
        both_wrong = sum(1 for r in rs if r["geom_verdict"] == "wrong" and r["rungs_verdict"] in ("wrong", "undecided"))
        only_geom = sum(1 for r in rs if r["geom_verdict"] == "right" and r["rungs_verdict"] != "right")
        only_rungs = sum(1 for r in rs if r["rungs_verdict"] == "right" and r["geom_verdict"] != "right")
        print(f"{str(k):<8}{n:<5}{geom_right:<12}{rungs_right:<13}{rungs_undec:<13}"
             f"{both_right:<12}{both_wrong:<12}{only_geom:<11}{only_rungs:<11}")


def table_c(rows, doc_id):
    print(f"\n=== Table C: {doc_id} -- by above/below the staff ===")
    print(f"{'side':<8}{'n':<5}{'geom_right':<12}{'rungs_right':<13}"
         f"{'rungs_undec':<13}{'both_right':<12}{'both_wrong':<12}"
         f"{'only_geom':<11}{'only_rungs':<11}")
    for side in ("above", "below"):
        rs = [r for r in rows if r["doc"] == doc_id and r["side"] == side]
        n = len(rs)
        if n == 0:
            print(f"{side:<8}{0:<5}")
            continue
        geom_right = sum(1 for r in rs if r["geom_verdict"] == "right")
        rungs_right = sum(1 for r in rs if r["rungs_verdict"] == "right")
        rungs_undec = sum(1 for r in rs if r["rungs_verdict"] == "undecided")
        both_right = sum(1 for r in rs if r["geom_verdict"] == "right" and r["rungs_verdict"] == "right")
        both_wrong = sum(1 for r in rs if r["geom_verdict"] == "wrong" and r["rungs_verdict"] in ("wrong", "undecided"))
        only_geom = sum(1 for r in rs if r["geom_verdict"] == "right" and r["rungs_verdict"] != "right")
        only_rungs = sum(1 for r in rs if r["rungs_verdict"] == "right" and r["geom_verdict"] != "right")
        print(f"{side:<8}{n:<5}{geom_right:<12}{rungs_right:<13}{rungs_undec:<13}"
             f"{both_right:<12}{both_wrong:<12}{only_geom:<11}{only_rungs:<11}")


def table_d(rows, doc_id):
    rs = [r for r in rows if r["doc"] == doc_id]
    devs = [r["max_gap_deviation"] for r in rs if r["max_gap_deviation"] != ""]
    devs_sorted = sorted(devs)
    median = (devs_sorted[len(devs_sorted) // 2] if devs_sorted and len(devs_sorted) % 2
             else (sum(devs_sorted[len(devs_sorted)//2 - 1:len(devs_sorted)//2 + 1]) / 2
                   if devs_sorted else None))
    mx = max(devs_sorted) if devs_sorted else None
    print(f"\n=== Table D: {doc_id} -- printed-ledger unevenness "
         f"(n with >=2 rungs found = {len(devs)} of {len(rs)}) ===")
    print(f"median |gap/spacing - 1| = {median}")
    print(f"max    |gap/spacing - 1| = {mx}")

    # does unevenness predict geometry failing, head by head
    wrong_devs = [r["max_gap_deviation"] for r in rs
                 if r["geom_verdict"] == "wrong" and r["max_gap_deviation"] != ""]
    right_devs = [r["max_gap_deviation"] for r in rs
                 if r["geom_verdict"] == "right" and r["max_gap_deviation"] != ""]
    def _med(xs):
        xs = sorted(xs)
        if not xs:
            return None
        n = len(xs)
        return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
    print(f"geometry WRONG heads (n={len(wrong_devs)}): median dev = {_med(wrong_devs)}")
    print(f"geometry RIGHT heads (n={len(right_devs)}): median dev = {_med(right_devs)}")


def main():
    rows = build_rows()
    write_csv(rows)
    print(f"wrote {len(rows)} rows to {CSV_PATH}")

    for doc_id in ts.DOCS:
        table_b(rows, doc_id)
        table_c(rows, doc_id)
        table_d(rows, doc_id)

    print("\n=== E: 'agree' option, both docs combined ===")
    agree = [r for r in rows if r["geom_pos"] == r["rungs_pos"] and r["rungs_verdict"] != "undecided"]
    disagree = [r for r in rows if r["rungs_verdict"] != "undecided" and r["geom_pos"] != r["rungs_pos"]]
    agree_right = sum(1 for r in agree if r["geom_verdict"] == "right")
    dis_geom_right = sum(1 for r in disagree if r["geom_verdict"] == "right")
    dis_rungs_right = sum(1 for r in disagree if r["rungs_verdict"] == "right")
    print(f"agree (n={len(agree)}): right {agree_right} of {len(agree)}")
    print(f"disagree (n={len(disagree)}): geometry right {dis_geom_right} of {len(disagree)}, "
         f"rungs right {dis_rungs_right} of {len(disagree)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
