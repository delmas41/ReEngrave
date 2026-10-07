"""lane-farhead-5-6: the in-sample truth set (Litolff p3 far heads, Brahms p1 11) on the 10-07 reader (per-bar grid, all
default-ON switches), `flank_refine_bounded` OFF then ON. Names every head that changes and every right head broken. Read only.
  python3 farhead_5_6_truth.py [--json out.json]"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_per_bar_grid_eval as E
from tools.omr.annotate import far_head_reader as FH

if __name__ == "__main__":
    summary = {}
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        fp, L, far, lf, _ = E.build(doc, page, True)
        FH.READER_KEYWORDS["edge_vs_through"] = True
        FH.READER_KEYWORDS["flank_refine_bounded"] = False
        before = E.run(fp, far, lf)
        FH.READER_KEYWORDS["flank_refine_bounded"] = True
        after = E.run(fp, far, lf)
        print("==", doc, "p%d" % page, "n", len(far), "BEFORE", E.tal(before), "AFTER", E.tal(after))
        broken = []
        for s in before:
            if before[s]["pos"] != after[s]["pos"]:
                print("  ", s, "truth", before[s]["truth"], before[s]["pos"], before[s]["v"], "->", after[s]["pos"], after[s]["v"], after[s]["reason"][:60])
            if before[s]["v"] == "right" and after[s]["v"] != "right":
                broken.append(s)
        print("  right heads broken:", broken)
        summary[doc] = dict(before=before, after=after, broken=broken)
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(summary, default=str))
