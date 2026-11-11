"""2.284b r2: 12 blind tiles on the claims r2 CHANGED (Litolff p2/p4/p6/p10 ON, GATHER records of the r2 lane report).

  5 cases  a dynamic word the claim now holds as ONE mark (`ff`, `sf`: letters joined by row, twins by centre) -- the box is the whole word
  2 cases  a word boxed as one wide `f` or sloppy overlapping pieces, now claimed whole but UNSPELLED (`wide_letter_box`)
  1 case   a `ledgerLine` box lying on the arc's own ink (>= BOX_ON_LINE_MIN), now the arc's, no longer a crossing
  2 ctrl   a lone detector letter in the staff the claim still holds as one `f`/`p` (right or wrong, we do not know: Sean's tiles 7 and 12 were)
  2 ctrl   a ledger box on an arc below the cut (0.5-0.85), still a crossing: the near-miss tiles (CLAUDE §4)
One thin orange box, nothing else drawn. Key beside (out/print/2.284b-r2/key.json), outside tiles/.

    usage: tiles_2284b_r2.py ON_RECORD (litolff)
"""
import collections
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import claim_readout as CR  # noqa: E402
from tools.omr.staged import lane_report as LR  # noqa: E402

PAGES = (2, 4, 6, 10)
src = CR.cut_record(pathlib.Path(sys.argv[1]))
words, wide, lone, dropped, near = [], [], [], [], []
areas = collections.defaultdict(list)
cls, box = {}, {}
rows_by_page = {}
for pg in PAGES:
    rows = CR.read_rows(src, [pg])
    rows_by_page[pg] = rows
    for o in rows["observations"]:
        if o["quantity"] == "glyph_box":
            cls[o["subject"]] = o["value"][0] if isinstance(o["value"], list) else o["value"]
            box[o["subject"]] = (o.get("detail") or {}).get("bbox_page_px")
for pg, rows in rows_by_page.items():
    claims = collections.defaultdict(list)
    for o in rows["observations"]:
        d = o.get("detail") or {}
        if o["quantity"] != "claimed_area":
            continue
        if d.get("owner") == "word" and d.get("source") == "dynamic_letters" and d.get("inside_staff"):
            claims[d.get("owner_row")].append((o["value"], d))
        if d.get("owner") == "arc":
            for lb in d.get("line_boxes") or []:
                if lb[1] in box and cls.get(lb[1]) == "ledgerLine":
                    dropped.append(dict(page=pg, box=box[lb[1]], what="ledger box on the arc's own ink (now the arc's)", mark_box=lb[1], share=lb[2]))
            for c in d.get("crossings") or []:
                if c[3] in box and cls.get(c[3]) == "ledgerLine":
                    near.append(dict(page=pg, box=box[c[3]], what="ledger box still a crossing (below the cut)", mark_box=c[3], share=c[5] if len(c) > 5 else None))
    for rid, lst in claims.items():
        d = lst[0][1]
        bx = d.get("word_box") or [min(a[0][0] for a in lst), min(a[0][1] for a in lst), max(a[0][2] for a in lst), max(a[0][3] for a in lst)]
        item = dict(page=pg, box=bx, row=rid)
        if d.get("text") in ("ff", "sf", "fff", "sff", "pp", "mf", "fp", "sfz"):
            words.append(dict(item, what="dynamic word held as one mark", text=d.get("text")))
        elif d.get("lone") and d.get("text") is None and d.get("detector_letter") is None:
            wide.append(dict(item, what="wide letter box held whole, unspelled"))
        elif d.get("lone"):
            lone.append(dict(item, what="lone detector letter, still one letter", text=d.get("detector_letter")))
rng = random.Random(2188)
pick, seen = [], set()
for pool, n, role in ((words, 5, "case"), (wide, 2, "case"), (dropped, 1, "case"), (lone, 2, "control"), (near, 2, "control")):
    pool = sorted(pool, key=lambda it: (it["page"], it["box"]))
    rng.shuffle(pool)
    k = 0
    for it in pool:
        key = (it["page"], round(it["box"][0] / 20), round(it["box"][1] / 20))
        if key in seen or k >= n:
            continue
        seen.add(key)
        pick.append(dict(it, role=role))
        k += 1
rng.shuffle(pick)
items = [dict(it, plate="litolff", box=[float(v) for v in it["box"]]) for it in pick]
print("pools: words %d wide %d dropped %d lone %d near %d -> %d tiles" % (len(words), len(wide), len(dropped), len(lone), len(near), len(items)))
out = ROOT / "out" / "print" / "2.284b-r2"
print(LR.cut_tiles(items, out))
