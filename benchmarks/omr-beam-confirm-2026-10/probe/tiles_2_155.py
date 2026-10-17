"""ROADMAP 2.155 blind tiles for Sean: notes whose stem `OMR_STEM_AT_BAR_EDGE` rescues at the bar's edge, plus controls that can fail.

    python3 .../tiles_2_155.py      (reads out/2.155/{diff_p1_2_10.json, litolff_p1_2_10_{base,edge}.record.json, reach_*.json};
                                     writes ONE set, tiles AND key, in this run)

Roles (NEVER drawn; the KEY only, out/2.155/tiles-key.json, kept uncommitted):
  changed        -- Litolff p1/p2/p10 re-gathered through ADJUDICATE with the 2.153 rule ON: the arm's value differs from the base's
  rescued_joined -- whole movement: the arm adds this head's stem and the join reader reads it JOINED to a beam stroke
  rescued_unjoined -- whole movement: the arm adds the stem, the join reader reads it NOT joined (or has no stroke to join)
  joined_control -- p1/p2/p10: an interior beamed note both arms decide the same (can fail: our reading may be wrong)
Each tile: the note's neighbourhood, ONE blue box (#1F6FEB) on the note asked about, a tile number. Nothing else of ours.
Cutting the tiles and writing the key happen in this ONE run, in ONE loop; the run ends by asserting one key row per PNG."""
import collections
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec as RC  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
OUT, KEY = Path("out/print/2.155-review"), Path("out/2.155/tiles-key.json")
rnd = random.Random(2155)
ANSWERED = {"glyph/2/1/7/12/2", "glyph/1/0/8/2/0", "glyph/10/1/6/3/2"}   # 2.153 tiles 4/14/16, Sean answered 8 8 8


def load(p):
    r = json.load(open(p))
    return r.get("record", r)


def verdicts(r):
    out = {}
    for v in r["verdicts"]:
        if v["quantity"] == "duration" and v.get("decider") == "adjudicate_duration" and v["subject"] not in out:
            val = v["value"] if isinstance(v["value"], dict) else {}
            out[v["subject"]] = dict(outcome=v["outcome"], reason=v.get("reason"), written=val.get("written"),
                                     cands=[c.get("written") for c in (v.get("candidates") or []) if isinstance(c, dict)],
                                     beams_by_stem=(v.get("detail") or {}).get("beams_by_stem"))
    return out


base, edge = load("out/2.155/litolff_p1_2_10_base.record.json"), load("out/2.155/litolff_p1_2_10_edge.record.json")
vb, ve = verdicts(base), verdicts(edge)
bbox3 = {o["subject"]: o["detail"]["bbox_page_px"] for o in edge["observations"]
         if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead"}
picks = []

# changed: one of each kind first, then the dominant kind
diff = [d for d in json.load(open("out/2.155/diff_p1_2_10.json")) if d["glyph"] not in ANSWERED and d["glyph"] in bbox3]
groups = collections.defaultdict(list)
for d in diff:
    groups[(d["base"][0], d["base"][2], d["arm"][0], d["arm"][2])].append(d)
for g in groups.values():
    rnd.shuffle(g)
ch = []
for k in sorted(groups, key=str):
    ch.append(groups[k].pop())
big = max(groups.values(), key=len)
ch += big[:6 - len(ch)]
for d in ch[:6]:
    picks.append(dict(doc="litolff", role="changed", glyph=d["glyph"], bbox=bbox3[d["glyph"]], base=vb.get(d["glyph"]),
                      arm=ve.get(d["glyph"])))

# controls: interior beamed eighths, same in both arms, beam read on the stem, not in a rescued cell
resc_cells = {"/".join(d["glyph"].split("/")[:5]) for d in diff}
ctl = [g for g, v in vb.items() if v["outcome"] == "decided" and v["written"] == 0.5 and (v["beams_by_stem"] or 0) >= 1
       and ve.get(g) == v and "/".join(g.split("/")[:5]) not in resc_cells and g in bbox3 and g not in ANSWERED]
rnd.shuffle(ctl)
for g in ctl[:2]:
    picks.append(dict(doc="litolff", role="joined_control", glyph=g, bbox=bbox3[g], base=vb[g], arm=ve[g]))

# whole movement rescues (not on the re-gathered pages)
want = {}
for doc, nj, nu in (("litolff", 3, 3), ("brahms", 2, 4)):
    R = json.load(open("out/2.155/reach_%s.json" % doc))["rescued"]
    R = [r for r in R if len(r["heads"]) == 1 and r["heads"][0] not in ANSWERED
         and not (doc == "litolff" and int(r["cell"].split("/")[1]) in (1, 2, 10))]
    rnd.shuffle(R)
    jo = [r for r in R if r["join"] == "joined"][:nj]
    un = [r for r in R if r["join"] in ("not_joined", "no_stroke")][:nu]
    for role, rows in (("rescued_joined", jo), ("rescued_unjoined", un)):
        for r in rows:
            want[r["heads"][0]] = (doc, role, r)
night_bbox, night_v = {}, {}
for doc in ("litolff", "brahms"):
    gs = {g for g, (d, _r, _x) in want.items() if d == doc}
    with RC.lock():
        for o in RC.items(RC.RECORDS[doc], "observations"):
            if o["quantity"] == "glyph_box" and o["subject"] in gs:
                night_bbox[o["subject"]] = o["detail"]["bbox_page_px"]
        for v in RC.items(RC.RECORDS[doc], "verdicts"):
            if v["quantity"] == "duration" and v["subject"] in gs and v.get("decider") == "adjudicate_duration":
                val = v["value"] if isinstance(v["value"], dict) else {}
                night_v.setdefault(v["subject"], dict(outcome=v["outcome"], reason=v.get("reason"), written=val.get("written")))
for g, (doc, role, r) in want.items():
    picks.append(dict(doc=doc, role=role, glyph=g, bbox=night_bbox[g], base=night_v.get(g),
                      arm=dict(stem_rescued=r["stem"], side=r["side"], join=r["join"], join_rows=r["join_rows"],
                               head_stem_before=r["head_stem"])))
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
    ImageDraw.Draw(crop).rectangle([(x0b - x0) * 2 - pad, (y0b - y0) * 2 - pad, (x1b - x0) * 2 + pad, (y1b - y0) * 2 + pad],
                                   outline=BLUE, width=4)
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, **p))
json.dump(dict(question="What is the written value of the note in the blue box (4, dotted 4, 8 ...)?", tiles=len(picks),
               blue="the note asked about", nothing_else_drawn=True), open(OUT / "manifest.json", "w"), indent=1)
json.dump(dict(answered=None, verbatim=None, tiles=[dict(n=k["n"], sean=None) for k in key]),
          open(OUT / "answers.json", "w"), indent=1)
json.dump(key, open(KEY, "w"), indent=1)
pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks), (len(pngs), len(rows), len(picks))
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
print(len(pngs), "tiles, key rows", len(rows), "| roles", dict(collections.Counter(r["role"] for r in rows)),
      "| docs", dict(collections.Counter(r["doc"] for r in rows)))
