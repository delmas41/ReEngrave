"""2.284b: 12 blind tiles on the places the two new claims changed (no exported-file change came from them, so the lane report's own tiles cannot
show them): 8 lone dynamic letters INSIDE a staff that now claim their ink READ (the new claim most able to be wrong: a false letter box would take
ink), 4 arc CROSSINGS (a stroke the slur runs along that holds a mark's own ink, now marked, not taken -- the box is the crossed mark).
Drawn at random (seed 2188) from Litolff p2/p4/p6/p10 ON. Tiles + sheet in out/print/2.284b/tiles, key OUTSIDE in out/print/2.284b/key.json.

    usage: tiles_2284b.py ON_RECORD
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import claim_readout as CR  # noqa: E402
from tools.omr.staged import lane_report as LR  # noqa: E402

src = CR.cut_record(pathlib.Path(sys.argv[1]))
letters, crossings, boxes, cls = [], [], {}, {}
with open(src / "observations.jsonl") as fh:
    for line in fh:
        if '"glyph_box"' in line[:120]:
            o = json.loads(line)
            b = (o.get("detail") or {}).get("bbox_page_px")
            if b:
                boxes[o["subject"]] = b
                cls[o["subject"]] = o["value"][0]
with open(src / "observations.jsonl") as fh:
    for line in fh:
        if '"claimed_area"' not in line[:200]:
            continue
        o = json.loads(line)
        d = o.get("detail") or {}
        if d.get("owner") == "word" and d.get("source") == "dynamic_letters" and d.get("lone") and d.get("inside_staff"):
            letters.append(dict(page=int(o["subject"].split("/")[1]), box=d.get("word_box") or o["value"], what="lone dynamic letter claim (in staff)",
                                text=d.get("text"), row=o["id"]))
        if d.get("owner") == "arc" and d.get("crossings"):
            pg = int(o["subject"].split("/")[1])
            for cr in d["crossings"]:
                if cr[3] in boxes:
                    crossings.append(dict(page=pg, box=boxes[cr[3]], what="arc crossing (mark kept from the arc)", mark_box=cr[3],
                                          mark_class=cls.get(cr[3]), arc=d.get("owner_glyph"), row=o["id"]))
rng = random.Random(2188)
seen, pick = set(), []
for pool, n in ((letters, 8), (crossings, 4)):
    pool = sorted(pool, key=lambda it: (it["page"], it["box"]))
    rng.shuffle(pool)
    k = 0
    for it in pool:
        key = (it["page"], round(it["box"][0] / 20), round(it["box"][1] / 20))
        if key in seen or k >= n:
            continue
        seen.add(key)
        pick.append(it)
        k += 1
rng.shuffle(pick)
items = [dict(it, plate="litolff", role="case", box=[float(v) for v in it["box"]]) for it in pick]
print(len(letters), "letter claims,", len(crossings), "crossings ->", len(items), "tiles")
out = ROOT / "out" / "print" / "2.284b"
print(LR.cut_tiles(items, out))
