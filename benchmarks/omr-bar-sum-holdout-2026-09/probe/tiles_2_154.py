"""ROADMAP 2.154 blind tiles for Sean: notes whose value the BAR SUM set, which `OMR_BAR_SUM_CONFIRM_ONLY` takes back.

    python3 .../tiles_2_154.py     (reads out/2.154/arms_{litolff,brahms}.json and the injected slices; ONE run: tiles AND key)

Roles (NEVER drawn; the KEY only, out/2.154/tiles-key.json, kept uncommitted):
  bar_pick       -- base: the bar chose this value from a NARROWING (reconcile_duration or an INFER *_by_bar rule); arm a/b:
                    the narrowing stands (or another non-bar rule decides). Sean's value says whether the bar's pick was right.
  bar_move       -- base: the bar MOVED a DECIDED value by one beam level (reconcile_duration); arm a keeps the move, arm b
                    keeps the reader's own value. Sean's value says which of the two was right.
  plain_control  -- a note the reader decided (head_and_marks) and no arm changes (can fail: our reading may be wrong).
Excluded: every glyph Sean has already judged (judged index + 2.153 tiles). Head-sized boxes only (a tile asks about a VALUE).
Each tile: the note's neighbourhood, ONE blue box (#1F6FEB) on the note asked about, a tile number. Nothing else of ours."""
import collections
import json
import random
import statistics
import sys
from pathlib import Path

import ijson
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
OUT, KEY = Path("out/print/2.154-review"), Path("out/2.154/tiles-key.json")
BAR = ("reconcile_duration", "infer:collapse_bare_stem_by_bar", "infer:collapse_narrowed_by_bar")
rnd = random.Random(2154)
JUDGED = {s for r in json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
          for s in (r["subjects"] or [r["subject"]] if r["subject_kind"] == "glyph" else []) if s}
JUDGED |= {r["glyph"] for r in json.load(open(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a033e6dfd0d2cc37a/out/2.153/tiles-key.json"))}


def boxes(doc):
    out = {}
    with open("out/2.154/iw_%s.json" % doc, "rb") as f:
        for o in ijson.items(f, "observations.item", use_float=True):
            d = o.get("detail") or {}
            if o["quantity"] == "glyph_box" and d.get("bbox_page_px") and d.get("category") == "notehead":
                out[o["subject"]] = d["bbox_page_px"]
    return out


def live(path):
    chains = collections.defaultdict(list)
    for v in json.load(open(path))["record"]["verdicts"]:
        if v["quantity"] == "duration" and v["subject"].startswith("glyph/"):
            chains[v["subject"]].append(v)
    out = {}
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        out[g] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
    return out


def brief(v):
    if v is None:
        return None
    val = v["value"] if isinstance(v["value"], dict) else {}
    return dict(outcome=v["outcome"], written=val.get("written"), dots=val.get("dots"), reason=v.get("reason"),
                decider=v.get("decider"), cands=sorted({(c.get("value") or {}).get("written")
                                                        for c in (v.get("candidates") or [])
                                                        if isinstance(c.get("value"), dict)} - {None}) or None)


def pick(pool, n, by):
    groups = {}
    for x in pool:
        groups.setdefault(by(x), []).append(x)
    for g in groups.values():
        rnd.shuffle(g)
    out = []
    while len(out) < n and any(groups.values()):
        for k in sorted(groups, key=str):
            if groups[k] and len(out) < n:
                out.append(groups[k].pop())
    return out


picks = []
for doc, npick, nmove, nctl in (("litolff", 7, 4, 1), ("brahms", 7, 4, 1)):
    bx = boxes(doc)
    mh = statistics.median(b[3] - b[1] for b in bx.values())
    mw = statistics.median(b[2] - b[0] for b in bx.values())
    ok = lambda g: g in bx and 0.75 <= (bx[g][3] - bx[g][1]) / mh <= 1.6 and 0.75 <= (bx[g][2] - bx[g][0]) / mw <= 1.6
    L = {arm: live("out/2.154/rr_%s.%s.record.json" % (doc, arm)) for arm in ("base", "a", "b")}
    pool_pick, pool_move, pool_ctl = [], [], []
    for g, vb in L["base"].items():
        if g in JUDGED or not ok(g):
            continue
        b, a, bb = brief(vb), brief(L["a"].get(g)), brief(L["b"].get(g))
        row = dict(doc=doc, glyph=g, bbox=bx[g], base=b, arm_a=a, arm_b=bb)
        if b["decider"] in BAR and b != a:
            pool_pick.append(row)
        elif b["decider"] in BAR and b == a and b != bb:
            pool_move.append(row)
        elif b["decider"] == "adjudicate_duration" and b["reason"] == "head_and_marks" and b == a == bb:
            pool_ctl.append(row)
    print(doc, "pools: bar_pick", len(pool_pick), "bar_move", len(pool_move), "control", len(pool_ctl))
    for role, pool, n, by in (
            ("bar_pick", pool_pick, npick, lambda r: (r["base"]["decider"], (r["arm_a"] or {}).get("reason"))),
            ("bar_move", pool_move, nmove, lambda r: (r["base"]["written"], (r["arm_b"] or {}).get("written"))),
            ("plain_control", pool_ctl, nctl, lambda r: r["base"]["written"])):
        for r in pick(pool, n, by):
            picks.append(dict(role=role, **r))
rnd.shuffle(picks)

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
    x0b, y0b, x1b, y1b = p["bbox"]
    x0, y0 = int(max(x0b - 6 * SP, 0)), int(max(y0b - 5 * SP, 0))
    x1, y1 = int(min(x1b + 6 * SP, a.shape[1])), int(min(y1b + 5 * SP, a.shape[0]))
    crop = Image.fromarray(a[y0:y1, x0:x1].copy())
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    pad = 4
    ImageDraw.Draw(crop).rectangle([(x0b - x0) * 2 - pad, (y0b - y0) * 2 - pad, (x1b - x0) * 2 + pad,
                                    (y1b - y0) * 2 + pad], outline=BLUE, width=4)
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, **p))
json.dump(dict(question="What is the written value of the note in the blue box (4, dotted 4, 8 ...)?", tiles=len(picks),
               blue="the note asked about", nothing_else_drawn=True), open(OUT / "manifest.json", "w"), indent=1)
json.dump({}, open(OUT / "answers.json", "w"))   # blank for Sean ({} adds no row to the judged index; per-tile "" would)
json.dump(key, open(KEY, "w"), indent=1)
# the check the report quotes: one key row per PNG, same numbering, every key glyph's box is the one drawn
pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks), (len(pngs), len(rows), len(picks))
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
assert all(r["glyph"] == p["glyph"] and r["bbox"] == p["bbox"] for r, p in zip(rows, picks))
print(len(pngs), "tiles, key rows", len(rows), "| roles", dict(collections.Counter((r["doc"], r["role"]) for r in rows)))
