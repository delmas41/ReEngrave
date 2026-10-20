"""ROADMAP 2.175 -- the blind tiles for Sean: "how many notes does this head stand for, and what is each one's value?".

usage: tiles_2_175.py OUTDIR SPEC ...   SPEC = plate:ON.json:ON.record.json:CONTROLS.json:N_UNISON
Tiles and key come from ONE run of this script and are checked equal (same ids, same order, same subjects) before it
exits; every tile has ONE blue box on the shared head and nothing else of ours drawn. The key (ours; never shown to Sean)
holds what the arm reads. Two controls: a plain one-stem head ("one: 4" or its value) and a chord on one stem."""
import json
import os
import random
import sys

import fitz
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sample_2_175 import PDF, SP, BLUE, boxes_of, crop  # noqa: E402

HSP = {"lit": 16.0, "bra": 28.0}      # staff space in page pixels, for the head-size test only
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
specs = [a.split(":") for a in sys.argv[2:]]
rng = random.Random(2175)
items = []          # (kind, plate, subject, bb, ours)


def quarter_name(beats):
    return {4.0: "whole", 2.0: "half", 1.0: "quarter", 0.5: "eighth", 0.25: "sixteenth"}.get(beats, str(beats))


for plate, on_json, rec_json, ctl_json, n in specs:
    n = int(n)
    d = json.load(open(on_json))
    rows = d["unison"]["rows"]
    boxes = boxes_of(rec_json)
    dec = {s: r for s, r in rows.items() if r["outcome"] == "decided" and s in boxes}

    def pick(pred, k):
        pool = sorted(s for s, r in dec.items() if pred(r["value"]["voices"]))
        rng.shuffle(pool)
        return pool[:k]
    beams = pick(lambda v: v["up"]["source"] == "beam" and v["up"]["beats"] == v["down"]["beats"], 2)
    plain = pick(lambda v: v["up"]["source"] == "none_seen", 1)
    differ = pick(lambda v: v["up"]["beats"] != v["down"]["beats"], 1)
    flagged = pick(lambda v: v["up"]["source"] == "flag", 1)
    opened = pick(lambda v: v["up"]["source"] == "open_head", 1)
    chosen = (beams + plain + differ + flagged + opened)
    # fill up to n with refusals the arm made (a one-voice-unmarked shared head): the question is the same
    refused = sorted(s for s, r in rows.items() if r["reason"] == "one_voice_unmarked" and s in boxes)
    rng.shuffle(refused)
    chosen = chosen[:n]
    for s in refused[:max(0, n - len(chosen))]:
        chosen.append(s)
    for s in chosen:
        r = rows[s]
        ours = (r["value"]["voices"] if r["outcome"] == "decided" else {"refused": r["reason"], "readings": (r.get("detail") or {}).get("readings")})
        items.append(("unison", plate, s, boxes[s], ours))
    ctl = json.load(open(ctl_json))
    heads = ctl["heads"]
    # both controls come from the first plate (the cleaner engraving): a plain one-stem head, a chord on one stem
    if plate == specs[0][0]:
        for kind, pool in (("control_plain_one_stem", ctl["plain"]), ("control_chord_one_stem", ctl["chord"])):
            # a control must be an unmistakable head: one head's size, an unbeamed quarter
            def _ok(s):
                h = heads.get(s)
                if not h or (h.get("dur") or [None, None])[1] != 1.0:
                    return False
                w, ht = h["bb"][2] - h["bb"][0], h["bb"][3] - h["bb"][1]
                return 0.9 * HSP[plate] <= w <= 1.6 * HSP[plate] and 0.8 * HSP[plate] <= ht <= 1.3 * HSP[plate]
            pool = sorted(s for s in pool if _ok(s))
            if pool:
                s = rng.choice(pool)
                items.append((kind, plate, s, heads[s]["bb"], {"duration": heads[s].get("dur")}))

# order: shuffle so a control is not recognisable by position
rng.shuffle(items)
docs = {p: fitz.open(PDF[p]) for p in {i[1] for i in items}}
key = []
for k, (kind, plate, sub, bb, ours) in enumerate(items, 1):
    page = int(sub.split("/")[1])
    im = crop(docs[plate][page], plate, bb)
    im.thumbnail((900, 520))
    im.save(os.path.join(out, "tile_%02d.png" % k))
    key.append({"tile": k, "plate": plate, "subject": sub, "kind": kind, "ours": ours})
json.dump(key, open(os.path.join(out, "key.json"), "w"), indent=1)
# checked equal: the PNGs on disk are exactly the key's tiles, in order, and every key subject is distinct
png = sorted(f for f in os.listdir(out) if f.startswith("tile_") and f.endswith(".png"))
assert png == ["tile_%02d.png" % t["tile"] for t in key], (png, len(key))
assert len({t["subject"] for t in key}) == len(key)
open(os.path.join(out, "README.md"), "w").write(
    "# 2.175 review tiles (blind)\n\n"
    "%d tiles, STAGED, records 20261018-night. Page crops, nothing of ours drawn except ONE blue box on the head.\n\n"
    "**The question on every tile: how many notes does the blue-boxed head stand for, and what is each one's value?** "
    "(for example \"two: 8 and 4\", \"two: 8 and 8\", or \"one: 4\").\n\n"
    "Tiles and `key.json` (ours: what the OFF/ON arms read, plate, subject, which are the 2 controls) were written by one run of "
    "`benchmarks/omr-unison-two-voices-2026-10/probe/tiles_2_175.py` and checked equal (same ids, same order, distinct subjects): "
    "%d tiles = %d key rows.\n" % (len(key), len(png), len(key)))
print(len(key), "tiles;", sum(1 for t in key if t["kind"].startswith("control")), "controls; checked equal")
