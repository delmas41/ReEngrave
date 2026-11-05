"""2.266b: 12 blind tiles, every one an accidental whose blue flag goes away with OMR_ACCIDENTAL_READ_ONCE (lane_report OFF blue, ON plain, same note by place).
Both plates, 4 naturals + 1 flat + 1 sharp where they exist, no two on one page+system, places Sean already judged left out. One thin orange box on the
accidental's own detector box, nothing of ours drawn. Question: "what is the marked sign?" The key (family kind, margin, what is written) is OUTSIDE the tile folder.
usage (repo root): python3 benchmarks/omr-one-ink-one-mark-2026-10/extract_2_266b.py WORK PLATE RECORD   (both plates), then
                   python3 benchmarks/omr-one-ink-one-mark-2026-10/tiles_2_266b.py WORK JUDGED.json OUT_DIR"""
import json, pathlib, random, sys

sys.path.insert(0, ".")
W = pathlib.Path(sys.argv[1])
judged = json.load(open(sys.argv[2]))
OUT = pathlib.Path(sys.argv[3])
QUOTA = {"litolff": {"natural": 5, "flat": 1, "sharp": 1},"brahms": {"natural": 5, "flat": 1, "sharp": 1}}
seen_judged = {r["sub"] for r in judged if r.get("n_matches") == 1} | {x["sub"] for r in judged for x in r.get("rows", [])}
items, used = [], set()
for plate in ("litolff", "brahms"):
    c = json.load(open(W / (plate + ".c266b.json")))
    pool = {}
    for head, o in c.items():
        if head in seen_judged or o["acc"] in seen_judged:
            continue
        pool.setdefault((o["family"] or {}).get("type"), []).append((head, o))
    rng = random.Random(2266)
    for kind, n in QUOTA[plate].items():
        rs = sorted(pool.get(kind, []))
        rng.shuffle(rs)
        got = 0
        for head, o in rs:
            pg, sy = head.split("/")[1], head.split("/")[2]
            if (plate, pg, sy) in used:
                continue
            used.add((plate, pg, sy))
            items.append(dict(plate=plate, page=int(pg), box=o["box"], role="case", kind="accidental", subject=o["acc"], head=head,
                              family_kind=kind, family_margin=(o["family"] or {}).get("margin"), detector_class=o.get("detector_class"),
                              one_ink_class=((o.get("one_ink") or {}).get("winner") or {}).get("class"), written=o.get("written")))
            got += 1
            if got == n:
                break
    print(plate, {k: len(v) for k, v in pool.items()}, "tiles", sum(1 for i in items if i["plate"] == plate))
random.Random(2662).shuffle(items)
from tools.omr.staged import lane_report as LR
OUT.mkdir(parents=True, exist_ok=True)
print(LR.cut_tiles(items, OUT, readme_extra="\n**Question (2.266b):** what is the sign inside the orange box: a sharp, a flat, a natural, or none?\n"))
for n, it in enumerate(items, 1):
    print(n, it["plate"], "p%d" % it["page"], it["family_kind"], "fam", it["family_margin"], "written", it["written"], "oi", it["one_ink_class"], it["subject"])
