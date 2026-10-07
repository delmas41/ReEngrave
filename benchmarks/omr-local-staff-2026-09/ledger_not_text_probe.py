"""lane-ledger-not-text: probe the thin/flat test on the counted `between` ledgers of the out-of-sample decisions
(read only). Prints, for tile 12, the test at several columns, and over all decisions how many counted ledgers fail.
  python3 ledger_not_text_probe.py"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import truth_set_2_44c as ts
from frame import render_page_matching_gather
from tools.omr.annotate import ledger_grid as lg

rows = json.loads((HERE / "farhead_note_first_oos_brahms.json").read_text())
cfg = ts.DOCS["brahms1-breitkopf"]
gray = cv2.cvtColor(render_page_matching_gather(cfg["pdf"], 5, 600).rgb, cv2.COLOR_RGB2GRAY)
for r in rows:
    if r["subject"] != "glyph/5/0/6/3/2":
        continue
    b = r["new"]["box_used"]; cx = (b[0] + b[2]) / 2; sp = (max(r["new"]["lines"]) - min(r["new"]["lines"])) / 4
    for y in r["new"]["between"]:
        print("between rung", y, "sp", sp)
        for dx in (-1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5):
            print("  dx", dx, "run px", lg._column_ink_run(gray, y, cx + dx * sp, sp))
        print("  thin_flat all", lg.rung_is_thin_and_flat(gray, y, cx, sp),
              "one-sided", lg.rung_is_thin_and_flat(gray, y, cx, sp, require_all_sides=False))
