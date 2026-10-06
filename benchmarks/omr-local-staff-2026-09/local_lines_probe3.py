"""lane-local-staff-lines probe: the reader's note-first detail for ONE truth-set head, old vs new local lines.
  python3 local_lines_probe3.py <doc> <page> <glyph subject>"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import jut_from_ink_eval as J, farhead_all_wired_eval as W
from tools.omr.annotate import far_head_reader as FH
W.arm(True)
doc, page, s = sys.argv[1], int(sys.argv[2]), sys.argv[3]
L, fp, far = J.prepare(doc, page)
h = [x for x in far if x["subject"] == s][0]
gl = L["staff_lines"]["staff/" + "/".join(s.split("/")[1:4])]
for kw in (False, True):
    FH.READER_KEYWORDS["local_lines_in_window"] = kw
    r = fp.read(s, h["box"], h["cls"], gl)
    d = r["detail"]
    nf = d.get("note_first") or {}
    print(kw, r["pos"], r["reason"], "lines", [round(v, 1) for v in r["lines_used"]],
          "box_used", [round(v, 1) for v in r["box_used"]], "edge", d.get("edge_y"))
    print("   nf", {k: v for k, v in nf.items() if k != "refused_rungs"})
    print("   refused", [(round(x["y"], 1), x["why"]) for x in nf.get("refused_rungs") or []])
