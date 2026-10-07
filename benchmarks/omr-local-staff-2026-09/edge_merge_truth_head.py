"""lane-edge-merge-unseen-ledgers: the in-sample truth head Brahms `glyph/1/1/8/7/4`, read on the per-bar-grid reader with the three new
switches OFF (before) then ON (after); diagnostics (lines, box, every rung, the note line) to JSON for the sheet.

  python3 edge_merge_truth_head.py out.json
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_per_bar_grid_eval as E
import lines_combined_5_lib as D
from tools.omr.annotate import far_head_reader as FH

FH.EXCLUSION_RULES["jut_from_ink"] = True
S = "glyph/1/1/8/7/4"
out = {}
fp, L, far, lf, _ = E.build("brahms1-breitkopf", 1, True)
FH.READER_KEYWORDS["edge_vs_through"] = True
h = [x for x in far if x["subject"] == S][0]
for name, on in (("before", False), ("after", True)):
    for k in ("edge_jut_kept", "split_welded_bands", "rows_clear_of_box"):
        FH.READER_KEYWORDS[k] = on
    d = D.diagnose(fp, S, h["box"], h["cls"], lf(h))
    out[name] = d
    print(name, d["pos"], d["reason"][:90], "rungs", [round(r["y"], 1) for r in d["rungs"]])
json.dump(out, open(sys.argv[1], "w"), default=str)
