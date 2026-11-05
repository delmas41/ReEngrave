"""2.266: 12 blind tiles, every one a place where the family (strokes) reading and the one-ink detector winner NAME DIFFERENT KINDS for one accidental.
Spread over the kind pairs that exist (family kind / one-ink kind) and both plates; places Sean already judged are left out; no two on one page+system.
One thin orange box on the accidental's own detector box, nothing of ours drawn. Question: "what is the marked sign?" The key (kinds, margins) is written
OUTSIDE the tile folder (OUT_DIR/key.json).
usage (repo root): python3 benchmarks/omr-one-ink-one-mark-2026-10/tiles_2_266.py SCRATCH_DIR JUDGED.json OUT_DIR"""
import json, pathlib, random, sys
from collections import defaultdict

sys.path.insert(0, ".")
S = sys.argv[1].rstrip("/") + "/"
judged = json.load(open(sys.argv[2]))
OUT = pathlib.Path(sys.argv[3])
T = {"accidentalflat": "flat", "accidentaldoubleflat": "flat", "accidentalnatural": "natural", "accidentalsharp": "sharp",
     "accidentaldoublesharp": "sharp"}
QUOTA = {"litolff": [("natural", "flat", 4), ("natural", "sharp", 1), ("flat", "natural", 1), ("sharp", "flat", 1)],
         "brahms": [("natural", "flat", 3), ("natural", "sharp", 2), ("flat", "sharp", 1), ("sharp", "flat", 1)]}
seen_judged = {r["sub"] for r in judged if r.get("n_matches") == 1} | {x["sub"] for r in judged for x in r.get("rows", [])}
items, used = [], set()
for plate in ("litolff", "brahms"):
    boxes = json.load(open(S + plate + ".jsonl.boxes.json"))
    pool = defaultdict(list)
    for l in open(S + plate + ".c266.jsonl"):
        r = json.loads(l)
        f, oi = r["family"] or {}, r["one_ink"]
        ft = f.get("type") if f.get("type") in ("flat", "natural", "sharp") else None
        ow = T.get(str((((oi or {}).get("winner")) or {}).get("class") or "").lower())
        if not (ft and ow and ft != ow) or r["written"] is None or r["subject"] in seen_judged or r["subject"] not in boxes:
            continue
        pool[(ft, ow)].append(r)
    rng = random.Random(2266)
    for ft, ow, n in QUOTA[plate]:
        rs = pool[(ft, ow)]
        rng.shuffle(rs)
        got = 0
        for r in rs:
            pg, sy = r["subject"].split("/")[1], r["subject"].split("/")[2]
            if (plate, pg, sy) in used:
                continue
            used.add((plate, pg, sy))
            items.append(dict(plate=plate, page=int(pg), box=[float(v) for v in boxes[r["subject"]]], role="case", kind="accidental", subject=r["subject"],
                              head=r["head"], family_kind=ft, family_margin=r["family"].get("margin"), oneink_kind=ow,
                              oneink_margin=r["one_ink"].get("margin"), oneink_rivals=[x.get("class") for x in r["one_ink"].get("rivals") or ()],
                              written=r["written"], family_kind_pair="%s/%s" % (ft, ow)))
            got += 1
            if got == n:
                break
        print(plate, ft, ow, "pool", len(rs), "took", got)
random.Random(266).shuffle(items)
from tools.omr.staged import lane_report as LR
OUT.mkdir(parents=True, exist_ok=True)
print(LR.cut_tiles(items, OUT, readme_extra="\n**Question (2.266):** what is the sign inside the orange box: a sharp, a flat, a natural, or none?\n"))
for n, it in enumerate(items, 1):
    print(n, it["plate"], "p%d" % it["page"], it["family_kind_pair"], "fam %.2f" % (it["family_margin"] or -1), "oi", it["oneink_margin"], it["subject"])
