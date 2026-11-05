"""2.263: (1) how many family-blue heads would STAY blue anyway (a one-ink guess follows in export.one_ink_guess_of), per candidate bar;
(2) 12 blind tiles: 6 Brahms naturals just ABOVE the proposed bar and 6 just BELOW it, one accidental per tile, thin orange box on the accidental's own
detector box, nothing of ours drawn (tools/omr/staged/lane_report.cut_tiles). The key (which side each is on, margin) is written OUTSIDE tiles/.
usage: python3 benchmarks/omr-accidental-family-2026-10/margin_crops.py SCRATCH_DIR OUT_DIR [BAR=0.25]   (run from the repo root; renders PDF pages, no OCR)"""
import json, pathlib, random, sys
from collections import defaultdict
sys.path.insert(0, ".")

S = sys.argv[1].rstrip("/") + "/"
OUT = pathlib.Path(sys.argv[2])
BAR = float(sys.argv[3]) if len(sys.argv) > 3 else 0.25


def heads(plate):
    rows = [json.loads(l) for l in open(S + plate + ".owners.jsonl")]
    by = defaultdict(list)
    for r in rows:
        if r["blue_by_family"] and r["written"] is not None:
            by[r["head"]].append(r)
    one = {}
    for h, rs in by.items():
        r = min(rs, key=lambda r: (r["family"].get("margin") if r["family"].get("margin") is not None else 9e9))
        one[h] = r
    return one


for plate in ("litolff", "brahms"):
    one = heads(plate)
    print("==", plate, "family-blue heads with a written accidental:", len(one))
    for t in (0.0, 0.2, 0.25, 0.3, 0.4):
        clr = [r for r in one.values() if r["family"]["type"] == "natural" and r["family"]["margin"] >= t]
        also = sum(1 for r in clr if r["one_ink"] and (r["one_ink_margin"] is None or r["one_ink_margin"] < 9e9))
        print("   natural >= %.2f: %d; of these a one-ink (2.186) guess is also on the owner verdict for %d (they would stay blue by that rule)" % (t, len(clr), also))

if len(sys.argv) > 4 and sys.argv[4] == "census-only":
    sys.exit(0)

from tools.omr.staged import lane_report as LR
boxes = json.load(open(S + "brahms.jsonl.boxes.json"))
one = heads("brahms")
cand = [r for r in one.values() if r["family"]["type"] == "natural" and r["family"]["why"] == "right_stem_lower" and r["subject"] in boxes]
above = sorted((r for r in cand if r["family"]["margin"] >= BAR), key=lambda r: r["family"]["margin"])
below = sorted((r for r in cand if r["family"]["margin"] < BAR), key=lambda r: -r["family"]["margin"])
print("natural candidates: above %d, below %d (bar %.2f)" % (len(above), len(below), BAR))


def spread(rows, n, seed):
    """the n rows closest to the line, no two on one page+system (so no two on one staff's ink and the pages differ as far as they can)."""
    pool = rows[:60]
    random.Random(seed).shuffle(pool)
    pool.sort(key=lambda r: abs(r["family"]["margin"] - BAR) // 0.02)      # near-line first, ties in random order
    got, seen = [], set()
    for r in pool:
        pg = r["subject"].split("/")[1]
        k = (pg, r["subject"].split("/")[2])
        if k in seen:
            continue
        seen.add(k)
        got.append(r)
        if len(got) == n:
            break
    return got


pa, pb = spread(above, 6, 2263), spread(below, 6, 2264)
items = []
for side, rs in (("above", pa), ("below", pb)):
    for r in rs:
        b = boxes[r["subject"]]
        items.append(dict(plate="brahms", page=int(r["subject"].split("/")[1]), box=[float(v) for v in b], role=side, subject=r["subject"],
                          head=r["head"], margin=r["family"]["margin"], stagger_top=r["family"]["features"].get("stagger_top_sp"),
                          stagger_bottom=r["family"]["features"].get("stagger_bottom_sp"), detector_class=r["family"].get("detector_class"),
                          written=r["written"], kind="accidental"))
random.Random(7).shuffle(items)
OUT.mkdir(parents=True, exist_ok=True)
info = LR.cut_tiles(items, OUT)
print(info)
for n, it in enumerate(items, 1):
    print(n, it["role"], it["subject"], "margin", it["margin"], "top/bottom stagger", it["stagger_top"], it["stagger_bottom"], "class", it["detector_class"])
