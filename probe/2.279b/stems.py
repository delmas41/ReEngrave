"""2.279b: for the refused groups on DIFFERENT stems: are the stem ids adjacent (one physical stem cut in pieces?), what is the
x offset of the heads (head widths), the vertical gap (staff spaces), and what does the record hold for each stem id.
usage: stems.py RECORD GROUPS.json"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import load_record      # noqa: E402
from tools.omr.staged.record import Q                   # noqa: E402
from tools.omr.staged import lane_report as LR          # noqa: E402
from tools.omr.staged.export import Record              # noqa: E402

rec = Record(load_record(sys.argv[1]))
plate = "litolff" if "litolff" in sys.argv[1] else "brahms"
u = LR.PLATES[plate]["unit"]
boxes = LR.glyph_boxes(rec.obs_of(Q.GLYPH_BOX))
byid = {}
for o in rec.observations:
    if o.get("id") in set(h["stem"] for g in json.load(open(sys.argv[2])) for h in g["heads"] if h["stem"]):
        byid[o["id"]] = o
print("stem ids found", len(byid))
gs = json.load(open(sys.argv[2]))
n_adj = n_tot = 0
for g in gs:
    if not g["class"].startswith("distinct"):
        continue
    hs = g["heads"]
    stems = sorted({h["stem"] for h in hs if h["stem"]})
    nums = [int(s.split(":")[1]) for s in stems]
    adj = max(nums) - min(nums) <= 3
    n_tot += 1
    n_adj += adj
    bx = [boxes[h["glyph"]]["box"] for h in hs]
    xs = [(b[0] + b[2]) / 2 for b in bx]
    ys = [(b[1] + b[3]) / 2 for b in bx]
    w = sum(b[2] - b[0] for b in bx) / len(bx)
    print(g["cell"], "ids", nums, ("adj" if adj else "-"), "dx_heads %.2f" % ((max(xs) - min(xs)) / w), "dy_sp %.1f" % ((max(ys) - min(ys)) / u),
          [(h["type"], (byid.get(h["stem"]) or {}).get("quantity"), (byid.get(h["stem"]) or {}).get("value")) for h in hs][:2])
print("adjacent ids", n_adj, "of", n_tot)
