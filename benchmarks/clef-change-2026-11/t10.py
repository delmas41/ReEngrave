"""Round-2 check of tile 10's F claim area (Litolff p16 s0 staff 3): does it leave the quarter rest out?"""
import sys
sys.path.insert(0, "work-2.251"); sys.path.insert(0, ".")
import numpy as np, crops
from PIL import ImageDraw
from tools.omr.staged import clef_pagewide as CP
ink = np.asarray(crops.page_img("litolff", 16).convert("L")) < 128
d = crops.cmap("litolff", 16)
st = sorted([t for t in d["staves"] if t["system_index"] == 0], key=lambda t: t["line_ys"][0])[3]
ly = st["line_ys"]; sp = (ly[4] - ly[0]) / 4
bb = [926.175, 825.985, 980.8275, 874.18]
g = CP.read_box("clefF", bb, ink, CP.local_lines(ink, ly, sp, bb[0]), sp)
a = CP.f_claim_area(g, bb, sp)
print(g["body"], a)
im = crops.page_img("litolff", 16).crop((880, 790, 1020, 910)).convert("RGB").resize((560, 480))
ImageDraw.Draw(im).rectangle([(a[0] - 880) * 4, (a[1] - 790) * 4, (a[2] - 880) * 4, (a[3] - 790) * 4], outline=(255, 140, 0), width=2)
im.save("work-2.251/t10.png")
