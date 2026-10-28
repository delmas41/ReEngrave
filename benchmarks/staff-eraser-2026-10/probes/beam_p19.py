"""2.206f (Task B): Brahms p19 cell 0/13/0 -- the dotted eighth's second beam level. usage: beam_p19.py ; writes NPZ + crops to out/print/2.206f-beam.
Runs prepare_pages twice (OMR_ERASER_FIX 0 then 1) in one process; the flag is read at cell cut."""
import os, sys, numpy as np, cv2
sys.path.insert(0, ".")
from tools.omr.staged import gather as G, pipeline
PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
out = {}
for fl in ("0", "1"):
    os.environ["OMR_ERASER_FIX"] = fl
    pws, cells = pipeline.prepare_pages(PDF, [19], dpi=600)[0]
    loc = G.gather_geometry(G.Log(), pws)
    for c in cells:
        key = loc.get(c.staff_index)
        if key and tuple(key) == (0, 13) and c.measure_index == 0:
            out[fl] = (c.binary.copy(), c.image_no_staff.copy(), list(c.staff_line_ys_canonical))
            print(fl, c.binary.shape, out[fl][2])
np.savez("out/print/2.206f-beam/cells.npz", bin=out["0"][0], off=out["0"][1], on=out["1"][1], lines=np.array(out["0"][2]))
