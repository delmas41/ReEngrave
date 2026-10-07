"""lane-farhead-per-bar-grid (2026-10-06): the in-sample truth set (Litolff p3 44 far heads, Brahms p1 11), OLD (raw staff-wide
lines, keyword `per_bar_grid` off) vs NEW (per-bar grid, keyword on), both in the gather's deskewed frame. Names every head
that changes and every right head broken. Also prints what the merged edge_vs_through changed (old reader, keyword off/on).
Read-only; no gather (staff detection + measure cells only, to rebuild the grid the gather hands the reader).

  python3 farhead_per_bar_grid_eval.py [--json out.json]
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import frame_drop_arms as F
import edge_census as ec
import farhead_per_bar_grid_lib as GL
from tools.omr.annotate import far_head_reader as FH

SEAN = {"glyph/3/0/0/6/2": [-6]}


def build(doc, page, new):
    """-> (fp, L, far, lines_for) for one arm."""
    F.DOC, F.PAGE = doc, page
    L = F.load()
    FH.READER_KEYWORDS["per_bar_grid"] = new
    grid_of, staves, raw, unmatched, pws, cells = GL.bar_grids(L["rec"], page, L["pi"])
    heads = []
    for h in L["heads"]:
        g = grid_of.get(GL.head_cell(h["subject"])) if new else None
        heads.append(dict(h, global_lines=g or h["global_lines"]))
    shp = L["D"]["shapes"][page]
    shape = dict(width_sp=shp["width_sp"], height_sp=shp["height_sp"], tilt_deg=shp["tilt_deg"])
    fp = FH.FarHeadPage(L["gray_B"], heads, L["page_boxes"], L["staff_lines"])
    fp.adopt(shape, "scorer")
    far = [h for h in L["D"]["far"] if h["page"] == page]
    sk = lambda s: "staff/" + "/".join(s.split("/")[1:4])
    lines_for = lambda h: (grid_of.get(GL.head_cell(h["subject"])) if new else None) or L["staff_lines"][sk(h["subject"])]
    return fp, L, far, lines_for, staves


def run(fp, far, lines_for):
    FH.EXCLUSION_RULES["jut_from_ink"] = True
    out = {}
    for h in far:
        r = fp.read(h["subject"], h["box"], h["cls"], lines_for(h))
        truth = SEAN.get(h["subject"], h["truth"])
        out[h["subject"]] = dict(v=ec.verdict(r["pos"], truth), pos=r["pos"], reason=r["reason"], truth=truth,
                                 lines_used=r.get("lines_used"))
    return out


def tal(res):
    return ec.tally([v["v"] for v in res.values()])


if __name__ == "__main__":
    summary = {}
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        # control for the merged rule: the OLD path with edge_vs_through off, then on
        fp, L, far, lf, _ = build(doc, page, False)
        FH.READER_KEYWORDS["edge_vs_through"] = False
        o_off = run(fp, far, lf)
        FH.READER_KEYWORDS["edge_vs_through"] = True
        old = run(fp, far, lf)
        for s in old:
            if old[s]["pos"] != o_off[s]["pos"]:
                print("  edge_vs_through changes", s, o_off[s]["pos"], "->", old[s]["pos"], "truth", old[s]["truth"])
        for k in FH.GRID_STATS:
            FH.GRID_STATS[k] = 0
        fpn, Ln, farn, lfn, staves = build(doc, page, True)
        for k in FH.GRID_STATS:
            FH.GRID_STATS[k] = 0
        new = run(fpn, farn, lfn)
        print("==", doc, "p%d" % page, "n_far", len(far), "OLD (raw, edge_vs_through off)", tal(o_off), "OLD (raw)", tal(old),
              "NEW (per-bar grid)", tal(new), "| lines re-found/grid-not-found/grid-pair:",
              FH.GRID_STATS["refound"], FH.GRID_STATS["from_grid_not_found"], FH.GRID_STATS["from_grid_pair"])
        broken = []
        for s in old:
            if old[s]["pos"] != new[s]["pos"] or old[s]["v"] != new[s]["v"]:
                print("  ", s, "truth", old[s]["truth"], "old", old[s]["pos"], old[s]["v"], old[s]["reason"][:40],
                      "-> new", new[s]["pos"], new[s]["v"], new[s]["reason"][:60])
            if old[s]["v"] == "right" and new[s]["v"] != "right":
                broken.append(s)
        print("  right heads broken:", broken)
        summary[doc] = dict(old=old, new=new, broken=broken)
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(summary, default=str))
