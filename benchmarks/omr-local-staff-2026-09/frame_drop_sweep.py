"""How sharp is the reader's knife-edge? Read every Litolff p3 far head on the GATHER raster (B, frames
agree) with its OWN box shifted by (dx, dy) px, everything else untouched. If a 1-3 px shift moves the
tally by several heads, the reader's cut-offs sit on the noise of box placement, and A's 37 is where
the frame mismatch happened to put the boxes -- not evidence about the raster."""
from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np
import frame_drop_arms as F
import frame_drop_experiments as X
import edge_census as ec

if __name__ == "__main__":
    L = F.load()
    shp = L["D"]["shapes"][F.PAGE]
    shape = dict(width_sp=shp["width_sp"], height_sp=shp["height_sp"], tilt_deg=shp["tilt_deg"])
    far = [h for h in L["D"]["far"] if h["page"] == F.PAGE]
    sk = lambda s: "staff/" + "/".join(s.split("/")[1:4])
    SEAN = {"glyph/3/0/0/6/2": [-6]}
    for name, gray in (("B (gather raster)", L["gray_B"]), ("A (fitz raster)", L["gray_A"])):
        fp = F.FH.FarHeadPage(gray, L["heads"], L["page_boxes"], L["staff_lines"])
        fp.adopt(shape, "scorer")
        print("==", name, "own box shifted by (dx,dy) px; right/wrong/abstain vs Sean")
        grid = {}
        for dy in (-6, -4, -3, -2, -1, 0, 1, 2, 3, 4, 6):
            row = []
            for dx in (-4, -2, 0, 2, 4):
                vs = []
                for h in far:
                    b = h["box"]
                    sb = (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy)
                    r = fp.read(h["subject"], sb, h["cls"], L["staff_lines"][sk(h["subject"])])
                    vs.append(ec.verdict(r["pos"], SEAN.get(h["subject"], h["truth"])))
                t = ec.tally(vs)
                row.append(t["right"])
            grid[dy] = row
            print(f"dy={dy:+d}: right by dx[-4,-2,0,+2,+4] = {row}")
