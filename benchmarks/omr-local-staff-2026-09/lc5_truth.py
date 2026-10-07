"""lane-lines-combined: the in-sample truth head Brahms glyph/1/1/8/7/4, read old (raw lines) and new (per-bar grid; run with
OMR_CELL_LINE_FIND=1 for the combined tree), diagnostics saved to JSON for the sheet. Optional env LC5_ARG: key=value overrides
of ledger_grid / far_head_reader constants (a thrown test, never a default)."""
import sys, json, os
sys.path.insert(0, '.')
import farhead_per_bar_grid_eval as E
import lines_combined_5_lib as D
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg
FH.EXCLUSION_RULES["jut_from_ink"] = True
for kv in filter(None, os.environ.get("LC5_ARG", "").split(",")):
    k, v = kv.split("=")
    setattr(lg, k, float(v))
S = "glyph/1/1/8/7/4"
out = {}
for new in (False, True):
    fp, L, far, lf, _ = E.build("brahms1-breitkopf", 1, new)
    FH.READER_KEYWORDS["edge_vs_through"] = True
    h = [x for x in far if x["subject"] == S][0]
    d = D.diagnose(fp, S, h["box"], h["cls"], lf(h))
    out["new" if new else "old"] = d
    print("NEW" if new else "OLD", d["pos"], d["reason"][:90], "rungs", [round(r["y"], 1) for r in d["rungs"]])
if len(sys.argv) > 1:
    json.dump(out, open(sys.argv[1], "w"), default=str)
