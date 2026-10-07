"""lane-farhead-5-6 (manager's addition): Brahms p5 `glyph/5/0/5/5/1` and `glyph/5/0/6/5/3` (one mark detected twice, just under the
Horn staff `staff/5/0/5`). Reads BOTH boxes toward the Horn (the Horn's per-bar grid) and toward staff 6, flag OFF and ON, the way the
ledger-owner witness (`far_head_owner.read_toward`) does: same page context, same reader. Read only.
  python3 farhead_5_6_toward_horn.py <x7 brahms extract>"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_5_6_diag as D
import night_1007_replay as NR
import overnight_1004_report as R

data, rep = D.load(sys.argv[1])
HORN, S6 = "glyph/5/0/5/5/1", "glyph/5/0/6/5/3"
for flag in (False, True):
    D.FH.READER_KEYWORDS["flank_refine_bounded"] = flag
    for subj in (HORN, S6):
        g = data["glyphs"][subj]
        ctx = rep.adopt_for(5, (g.get("fh") or g.get("fh_abs") or {}).get("shape_source", "page n=0"))
        cls = next((c for (ss, c, b) in rep.boxes_by_page[5] if ss == subj), g.get("cls"))
        for toward, key in (("Horn (staff 5)", HORN), ("staff 6", S6)):
            r, cap = NR.read_spied(ctx, subj, tuple(g["box"]), cls, rep.head_lines(key))
            print("flank_refine_bounded", flag, "| box of", subj.split("/")[-3:], "read toward", toward, "->", r["pos"], "|", r["reason"][:70])
