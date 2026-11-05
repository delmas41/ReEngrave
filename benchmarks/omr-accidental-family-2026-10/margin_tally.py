"""2.263: tally Sean's judged accidentals against the reader's type and signed margin (input: margin_judged.py output, and the hand-box
margin run `eval_hand_boxes_margin.py` for the independent 142). One reading per tile: an A (head under the tile box) or B (box on the accidental) match,
the best margin if twins agree on the type. Right = the reader's CLEAR type is Sean's word; wrong = a clear type that is not; unclear = no decision.
usage: python3 benchmarks/omr-accidental-family-2026-10/margin_tally.py JUDGED.json [HAND_MARGIN.json]"""
import json, sys
from collections import Counter

res = json.load(open(sys.argv[1]))
hand = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else []
TYPES = ("flat", "natural", "sharp")
rows = []     # (source, label, plate, sean, reader_type, why, margin, owned)
amb = []
for t in res:
    if t["sean"] in (None, "rest"):
        continue
    ms = [m for m in t["matches"] if m["how"][0] in "AB"]
    if not ms:
        amb.append((t["set"], t["tile"], t["sean"], [(m["type"], m["margin"]) for m in t["matches"]]))
        continue
    types = {m["type"] for m in ms}
    m = ms[0]
    if len(types) > 1:
        amb.append((t["set"], t["tile"], t["sean"], "twins disagree", [(m["type"], m["margin"]) for m in ms]))
        continue
    rows.append(("tile", "%s#%s" % (t["set"], t["tile"]), t["plate"], t["sean"], m["type"], m["why"], m["margin"], m["owned"]))
for o in hand:
    rows.append(("hand", "p%s" % o["page"], "brahms", o["sean"], o["type"], o["why"], o.get("margin"), None))

print("tiles/boxes with a reading:", len(rows), " set aside (no A/B match or twins disagree):", len(amb))
for a in amb:
    print("   aside:", a)
for src in ("tile", "hand"):
    sub = [r for r in rows if r[0] == src]
    c = Counter((r[3], "right" if r[4] == r[3] else ("unclear" if r[4] not in TYPES else "WRONG")) for r in sub)
    print(src, len(sub), dict(c))
print("clear readings that are not Sean's word:")
for r in rows:
    if r[4] in TYPES and r[4] != r[3]:
        print("   ", r)
print()
THR = [None, 0.0, 0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]
print("natural/sharp readings by candidate READ_MARGIN (flat has no margin and can never clear one):")
for t in THR:
    for src in ("tile", "hand", "both"):
        sub = [r for r in rows if (src == "both" or r[0] == src) and r[4] in ("natural", "sharp") and r[6] is not None]
        above = [r for r in sub if t is None or r[6] >= t]
        below = [r for r in sub if not (t is None or r[6] >= t)]
        ar, aw = sum(r[4] == r[3] for r in above), sum(r[4] != r[3] for r in above)
        br, bw = sum(r[4] == r[3] for r in below), sum(r[4] != r[3] for r in below)
        print("  bar %-5s %-4s above: right %3d wrong %d | below: right %3d wrong %d" % ("all" if t is None else t, src, ar, aw, br, bw))
low = sorted((r[6], r[1], r[3], r[4]) for r in rows if r[4] in ("natural", "sharp") and r[6] is not None)
print("ten lowest margins read natural/sharp:", low[:10])
print("readings by (type, margin) on the tiles:", sorted((r[4], r[6]) for r in rows if r[0] == "tile" and r[4] in TYPES))
