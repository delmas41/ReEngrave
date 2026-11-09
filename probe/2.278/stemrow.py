import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT
from tools.omr.staged.record_io import load_record
from tools.omr.staged.record import Q
CAP = {}
orig = EXPORT._place_notes
def place(rec, runs, **kw):
    CAP["rec"] = rec; return orig(rec, runs, **kw)
EXPORT._place_notes = place
d = load_record(sys.argv[1]); EXPORT.to_musicxml(d)
rec = CAP["rec"]
for sub in sys.argv[2:]:
    hs = rec.verdict(Q.HEAD_STEM, sub)
    print(sub, hs["value"], hs["outcome"])
    r = [o for o in rec.obs_of(Q.STEM) if o["id"] == hs["value"]]
    print(r)
    o = rec.obs(Q.GLYPH_BOX, sub)[-1]
    print(o.get("detail"))
