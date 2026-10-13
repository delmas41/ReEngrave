"""2.100 against Sean's hand truth (Brahms 1, Breitkopf 317803, PDF page 0).

    python3 benchmarks/omr-keysig-truth-2026-09/probe/handtruth_2_100.py REC.json AB_DIR

REC.json: a Brahms small-re-gather record covering PDF page 0. AB_DIR: where
`ab_2_100.py` wrote `ab_2_100.json` for it. For every glyph the arm refused
in the key slots, the hand-truth boxes that overlap it (page pixels, IoU>=0.3)
say what the ink really is: a key accidental (a correct refusal) or a
rest / notehead (an invented refusal -- must be 0). Then, as the baseline the
detector gives the key reader, our key-shaped header boxes against the truth's
`keyFlat/keySharp` boxes (found / invented / missed).
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

rec_path, ab_dir = sys.argv[1], Path(sys.argv[2])
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc
truth = json.load(open("data/hand-truth/pages/imslp317803/0.json"))["boxes"]
ab = json.load(open(ab_dir / "ab_2_100.json"))


def iou(a, b):
    iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = iw * ih
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


page_boxes = {}
for o in rec["observations"]:
    if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/0/"):
        bb = (o.get("detail") or {}).get("bbox_page_px")
        if bb:
            page_boxes[o["subject"]] = (o["value"][0], bb)

print("refused in key slots on PDF page 0:")
bad = 0
for r in ab["refused"]:
    s = r["subject"]
    if not s.startswith("glyph/0/"):
        continue
    cls, bb = page_boxes[s]
    hits = sorted(((iou(bb, t["rect"]), t["cls"]) for t in truth), reverse=True)[:2]
    kind = hits[0][1] if hits and hits[0][0] >= 0.3 else "NO TRUTH BOX"
    if kind.startswith(("rest", "notehead")):
        bad += 1
    print(f"  {s} {cls:<22} -> truth {kind}  {[(round(a, 2), b) for a, b in hits]}")
print("INVENTED refusals (truth says rest/notehead):", bad)

found = invented = 0
shaped = [(s, b) for s, (c, b) in page_boxes.items()
          if c in ("keyFlat", "keySharp", "keyNatural") and s.split("/")[4] == "0"]
tk = [t for t in truth if t["cls"] in ("keyFlat", "keySharp", "keyNatural")]
for s, b in shaped:
    if any(iou(b, t["rect"]) >= 0.3 for t in tk):
        found += 1
    else:
        invented += 1
missed = sum(1 for t in tk if not any(iou(b, t["rect"]) >= 0.3 for _, b in shaped))
print(f"key-class header boxes: {len(shaped)} (found {found}, invented {invented});"
      f" truth key boxes {len(tk)}, missed {missed}")
