"""Compact table from results/res.<plate>.json.   python3 summary.py > results/summary.txt"""
import json
import os

H = os.path.dirname(os.path.abspath(__file__)) + "/results/"
for plate in ("litolff", "brahms"):
    r = json.load(open(H + "res.%s.json" % plate))["res"]
    n = r["n_items"]
    print("==", plate, "pages", r["pages"], "| cut items", n, "(pairs %d, lone %d) | uncut real arcs %d" % (r["n_pairs"], n - r["n_pairs"], r["n_uncut"]))
    c = r["control"]
    print("  CONTROL A re-detect vs saved record: cells %d/%d matched by cell box; record arc boxes reproduced %d/%d (IoU>=.9 same class); A arcs not in record %d"
          % (c["cells_matched"], c["cells"], c["rec_arcs_found"], c["rec_arcs"], c["a_arcs"] - c["a_arcs_in_rec"]))
    print("  CONTROL FAIL-CASE same cells at imgsz 1024: reproduced %d/%d" % (c["bad_found"], c["bad_rec_arcs"]))
    print("  A alone: far half boxed only where the cut test saw a pair: %d/%d = %.0f%%" % (r["A_alone_far"], n, 100 * r["A_alone_far"] / n))
    for a, x in r["cut_items"].items():
        print("  %-3s far half boxed %3d/%d = %3.0f%% (whole %3d = %3.0f%%) | A+%s covers both sides %3d = %3.0f%% | still miss %3d = %3.0f%% | lone far %d/%d"
              % (a, x["far"], n, 100 * x["far"] / n, x["whole"], 100 * x["whole"] / n, a, x["together"], 100 * x["together"] / n, x["miss"], 100 * x["miss"] / n,
                 x["lone_far"], x["lone_n"]))
    for a, x in r["uncut"].items():
        extra = " | in a window %d, found there %d" % (x["in_a_window"], x["found_in_window"]) if a.startswith("B") else ""
        print("  %-3s uncut arcs found: IoU>=.5 %d/%d = %.0f%%, lenient %d = %.0f%%%s" % (a, x["found_iou50"], x["n"], 100 * x["found_iou50"] / x["n"],
                                                                                       x["found_lenient"], 100 * x["found_lenient"] / x["n"], extra))
    for a, x in r["new_arc_boxes"].items():
        print("  %-3s NEW arc boxes (no record arc under them, not a far-half): %.1f per page %s | under them: %s" % (a, x["mean_per_page"], x["per_page"], x["on_A_glyph_class"]))
    print("  runtime s/page (detect only; prepare %.1f s): %s | calls/page %s | most boxes in one call %s" % (r["prepare_s_per_page"], r["runtime_s_per_page"], r["calls_per_page"], r["max_boxes_one_call"]))
    for a, x in r["in_passing"].items():
        print("  in passing %-3s boxes not in A %d (top %s) | A boxes not in X %d (top %s)" % (a, x["not_in_A"], x["top_not_in_A"][:5], x["A_not_in_X"], x["top_A_not_in_X"][:5]))
