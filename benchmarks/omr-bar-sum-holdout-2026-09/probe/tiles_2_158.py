"""ROADMAP 2.158 blind tiles for Sean: notes `OMR_LONE_EVENT_FILLS_BAR` guesses from the bar (a lone event in a known meter).

    python3 .../tiles_2_158.py N_CHANGED     (reads out/2.158/replay_litolff.json + rr_litolff.on.record.json; ONE run: tiles AND key)

Roles (NEVER drawn; the KEY only, out/2.158/tiles-key.json, kept uncommitted):
  lone_event     -- flag OFF: the note is NARROWED (EXPORT marks it unread); ON: GUESSED to the candidate that fills the bar.
                    Sean's value says whether the guess is right. One tile per BAR (a chord's heads share a value).
  plain_control  -- a note the reader decided (head_and_marks) that the flag does not touch (can fail: our reading may be wrong).
Excluded: every glyph Sean has already judged (judged index + 2.153 key). Each tile: the note's neighbourhood, ONE blue box
(#1F6FEB) on the note asked about, "Tile N". Nothing else of ours."""
import collections
import json
import random
import sys
from pathlib import Path

import ijson
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
N_CHANGED = int(sys.argv[1]) if len(sys.argv) > 1 else 20
OUT, KEY = Path("out/print/2.158-review"), Path("out/2.158/tiles-key.json")
rnd = random.Random(2158)
JUDGED = {s for r in json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
          for s in (r["subjects"] or [r["subject"]] if r["subject_kind"] == "glyph" else []) if s}
K153 = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a033e6dfd0d2cc37a/out/2.153/tiles-key.json")
if K153.exists():
    JUDGED |= {r["glyph"] for r in json.load(open(K153))}

SRCS = {"litolff": ("out/2.158/replay_litolff.json", "out/2.158/rr_litolff.on.record.json"),
        "brahms": ("out/2.158/replay_brahms_p0_12.json", "out/2.158/rr_brahms_p0_12.on.record.json")}
bx, plain, pool, changed = {}, [], [], {}
for doc, (rp, recp) in SRCS.items():
    R = json.load(open(rp))
    with open(recp, "rb") as f:
        for o in ijson.items(f, "record.observations.item", use_float=True):
            d = o.get("detail") or {}
            if o["quantity"] == "glyph_box" and d.get("bbox_page_px") and d.get("category") == "notehead":
                bx[(doc, o["subject"])] = d["bbox_page_px"]
    by_bar = collections.defaultdict(list)
    for g, d in R["changed"].items():
        changed[(doc, g)] = d
        if (d["on"] or {}).get("reason") == "lone_event_fills_bar" and g not in JUDGED and (doc, g) in bx:
            by_bar["/".join(g.split("/")[1:5])].append(g)
    pool += [(doc, sorted(gs, key=lambda g: int(g.split("/")[-1]))[0]) for gs in by_bar.values()]
    if doc != "litolff":
        continue
    with open(recp, "rb") as f:
        chains = collections.defaultdict(list)
        for v in ijson.items(f, "record.verdicts.item", use_float=True):
            if v["quantity"] == "duration" and v["subject"].startswith("glyph/"):
                chains[v["subject"]].append(v)
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        L = ([x for x in ch if x["id"] not in sup] or ch)[-1]
        if (L["outcome"] == "decided" and L.get("reason") == "head_and_marks" and g not in R["changed"]
                and g not in JUDGED and (doc, g) in bx and isinstance(L["value"], dict) and not L["value"].get("is_rest")):
            plain.append(dict(doc=doc, glyph=g, off=None, on=dict(outcome="decided", written=L["value"].get("written"),
                                                                  dots=L["value"].get("dots"), reason="head_and_marks")))
pool.sort()
rnd.shuffle(pool)
picks = [dict(role="lone_event", doc=doc, glyph=g, **changed[(doc, g)]) for doc, g in pool[:N_CHANGED]]
plain.sort(key=lambda p: p["glyph"])
rnd.shuffle(plain)
halves = [p for p in plain if p["on"]["written"] == 2.0][:1]
others = [p for p in plain if p["on"]["written"] != 2.0][:1]
picks += [dict(role="plain_control", **p) for p in halves + others]
rnd.shuffle(picks)
print("pool: lone-event bars", len(pool), "(judged excluded); picked", len(picks))

OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("tile_*.png"):
    old.unlink()
KEY.parent.mkdir(parents=True, exist_ok=True)
SP = 33.0
BLUE = (31, 111, 235)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
except OSError:
    font = ImageFont.load_default()
pages, key = {}, []
for n, p in enumerate(picks, 1):
    pg = int(p["glyph"].split("/")[1])
    if (p["doc"], pg) not in pages:
        pages[(p["doc"], pg)] = np.asarray(Image.fromarray(render_page(PDFS[p["doc"]], pg, dpi=600).rgb).convert("RGB"))
    a = pages[(p["doc"], pg)]
    x0b, y0b, x1b, y1b = bx[(p["doc"], p["glyph"])]
    x0, y0 = int(max(x0b - 7 * SP, 0)), int(max(y0b - 5 * SP, 0))
    x1, y1 = int(min(x1b + 7 * SP, a.shape[1])), int(min(y1b + 5 * SP, a.shape[0]))
    crop = Image.fromarray(a[y0:y1, x0:x1].copy())
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    pad = 4
    ImageDraw.Draw(crop).rectangle([(x0b - x0) * 2 - pad, (y0b - y0) * 2 - pad, (x1b - x0) * 2 + pad,
                                    (y1b - y0) * 2 + pad], outline=BLUE, width=4)
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, bbox=bx[(p["doc"], p["glyph"])], **p))
json.dump(dict(question="What is the written value of the note in the blue box (2, 4, dotted 2 ...)?", tiles=len(picks),
               blue="the note asked about", nothing_else_drawn=True), open(OUT / "manifest.json", "w"), indent=1)
json.dump({}, open(OUT / "answers.json", "w"))
json.dump(key, open(KEY, "w"), indent=1)
# the check: one key row per PNG, same numbering, every key row's box is the box drawn for that glyph
pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks), (len(pngs), len(rows), len(picks))
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
assert all(r["glyph"] == p["glyph"] and r["bbox"] == bx[(p["doc"], p["glyph"])] for r, p in zip(rows, picks))
assert not any(r["glyph"] in JUDGED for r in rows)
print(len(pngs), "tiles, key rows", len(rows), "| roles", dict(collections.Counter((r["doc"], r["role"]) for r in rows)))
