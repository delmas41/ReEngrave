"""lane-farhead-5-6: `far_head_owner.decide` for the manager's two Horn heads, flag OFF then ON. read_toward -> decide, exactly as
`owner_by_ledgers` does (the neighbour set is the two staves the head lies between). Read only.
  python3 farhead_5_6_owner_decide.py <x7 brahms extract>"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_5_6_diag as D
from tools.omr.annotate import far_head_owner as FO

data, rep = D.load(sys.argv[1])
HORN, S6 = "glyph/5/0/5/5/1", "glyph/5/0/6/5/3"
for flag in (False, True):
    D.FH.READER_KEYWORDS["flank_refine_bounded"] = flag
    for subj in (HORN, S6):
        g = data["glyphs"][subj]
        ctx = rep.adopt_for(5, (g.get("fh") or g.get("fh_abs") or {}).get("shape_source", "page n=0"))
        cls = next((c for (ss, c, b) in rep.boxes_by_page[5] if ss == subj), g.get("cls"))
        per = {"staff/5/0/5 (Horn)": FO.read_toward(ctx, subj, g["box"], cls, rep.head_lines(HORN)),
               "staff/5/0/6 (below)": FO.read_toward(ctx, subj, g["box"], cls, rep.head_lines(S6))}
        owner, word = FO.decide(per)
        print("flank_refine_bounded", flag, "|", subj, "| Horn pos", per["staff/5/0/5 (Horn)"]["pos"], "fits", per["staff/5/0/5 (Horn)"]["fits"],
              "| below pos", per["staff/5/0/6 (below)"]["pos"], "fits", per["staff/5/0/6 (below)"]["fits"], "->", owner, word)
