"""Page stems (owner-stem claims of a record) vs Sean's Brahms p0 stem labels: right / not his / missed, and how many cover 90% of his stem's height."""
import sys, os, json
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record
rec = load_record(sys.argv[1])["record"]
T = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
ts = [b["rect"] for b in T["boxes"] if b["cls"] == "stem"]
mine = [o["detail"]["stem_box"] for o in rec["observations"] if o["quantity"] == "claimed_area" and o["subject"] == "page/0"
        and (o.get("detail") or {}).get("owner") == "stem" and o["value"] != "census"]


def hit(t, b):
    tx, bx = (t[0] + t[2]) / 2.0, (b[0] + b[2]) / 2.0
    ov = min(t[3], b[3]) - max(t[1], b[1])
    return abs(tx - bx) <= 8 and ov >= 0.5 * min(t[3] - t[1], b[3] - b[1])


def full(t, b):
    return abs((t[0] + t[2]) / 2.0 - (b[0] + b[2]) / 2.0) <= 8 and (min(t[3], b[3]) - max(t[1], b[1])) >= 0.9 * (t[3] - t[1])


found = sum(1 for t in ts if any(hit(t, b) for b in mine))
whole = sum(1 for t in ts if any(full(t, b) for b in mine))
right = sum(1 for b in mine if any(hit(t, b) for t in ts))
print("page stems %d vs Sean's %d: right %d, not his %d, his missed %d; his stems covered to 90%% of their length %d" % (
    len(mine), len(ts), right, len(mine) - right, len(ts) - found, whole))
