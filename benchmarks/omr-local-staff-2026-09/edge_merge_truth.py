"""lane-edge-merge-unseen-ledgers (2026-10-06): the in-sample truth set (Litolff p3 41 far heads, Brahms p1 11) on the per-bar-grid
reader (the combined tree's default), with the three new switches OFF then ON. Names every head that changes and every right
head broken. Read-only; no gather.

  python3 edge_merge_truth.py [--json out.json]
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_per_bar_grid_eval as E
from tools.omr.annotate import far_head_reader as FH

SW = ("edge_jut_kept", "split_welded_bands", "rows_clear_of_box")   # walk_tol is off by default (refused)


def arm(on):
    for k in SW:
        FH.READER_KEYWORDS[k] = on


if __name__ == "__main__":
    summary = {}
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        fp, L, far, lf, _ = E.build(doc, page, True)
        FH.READER_KEYWORDS["edge_vs_through"] = True
        arm(False); before = E.run(fp, far, lf)
        arm(True); after = E.run(fp, far, lf)
        print("==", doc, "p%d" % page, "n_far", len(far), "BEFORE (switches off)", E.tal(before), "AFTER (on)", E.tal(after))
        broken, gained = [], []
        for s in before:
            if before[s]["pos"] != after[s]["pos"] or before[s]["v"] != after[s]["v"]:
                print("  ", s, "truth", before[s]["truth"], "before", before[s]["pos"], before[s]["v"], before[s]["reason"][:40],
                      "-> after", after[s]["pos"], after[s]["v"], after[s]["reason"][:60])
            if before[s]["v"] == "right" and after[s]["v"] != "right":
                broken.append(s)
            if before[s]["v"] != "right" and after[s]["v"] == "right":
                gained.append(s)
        print("  right heads broken:", broken, " gained:", gained)
        summary[doc] = dict(before=before, after=after, broken=broken, gained=gained)
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(summary, default=str))
