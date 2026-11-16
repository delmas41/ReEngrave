"""ROADMAP 2.311 -- TRY TO FALSIFY: "bars go red because the notes stand far from the staff" (Sean, 2026-11-16, after the red-bar tiles).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/farhead.py \
        --lit LIT.facts.json --lit-record LIT.record.json --bra BRA.facts.json --bra-record BRA.record.json \
        --crops out/print/2.311-clipped --json benchmarks/note-loss-funnel-2026-11/farhead-results.json

Reads only (the saved lit-a / bra-a records and their facts files); decides nothing.

1. Every bar = every cell/<page>/<system>/<staff>/<cell> the record holds on the count pages (the same pages as the 309 / 276 red-bar count).
   Red = `redbars.red_bars` (does not add up, unread/empty, held, partial red gap) -- the same list.
   FARTHEST HEAD: over the bar's notehead glyph boxes (`head` true, every fate -- written, refused, duplicate -- EXCEPT those the record itself
   gives to another staff: fate `owned_by_another_staff` / `not_a_notehead:belongs_to_a_nearer_staff`), the box CENTRE's distance beyond the
   nearer outer staff line of THIS staff, in staff spaces, from the record's own `staff_lines` row (page, system, staff). The attribution is the
   record's: a glyph key is (page, system, staff, cell) and the owner verdict has already moved heads that belong elsewhere.
   Ledger lines needed n = ceil(d - 0.75)  (d = 0.5 space beside the staff: none; 1.0 line or 1.5 space: one; 2.0: two; ...).
   Bins: 0 (within the staff and the space either side) / 1-2 ledger lines / 3+ ledger lines. A bar with no head: its own row.
   CONTROL: red share by number of heads in the bar as well (far heads come with busy bars; busy bars are red anyway).
2. Every `not_a_notehead:clipped_fragment` and `not_a_notehead:too_narrow` refusal: how many touch the top/bottom edge of their cell
   rectangle (within 1 staff space of `cell_box` y0/y1: the cell picture cut the mark) and how many red bars have one as the FIRST cause.
3. The cell crop's pad: read off the record's `cell_box` against `staff_lines`; the function is named in the output of the run.
4. Six `clipped_fragment` refusals at random (seed 2311003; 3 per plate), cut from the page at the cell rectangle (what the detector saw).
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

from checksheet import page_image
from redbars import run as red_run
from tools.omr.staged.record_io import load_record

SAMPLE = json.load(open("benchmarks/lane-report/sample.json"))
OTHER = ("owned_by_another_staff", "not_a_notehead:belongs_to_a_nearer_staff")
FRAG = ("not_a_notehead:clipped_fragment", "not_a_notehead:too_narrow")


def geometry(rec_path: str, pages: set) -> tuple:
    r = load_record(rec_path)
    obs = r.get("record", r)["observations"]
    lines = {}
    for o in obs:
        if o.get("quantity") == "staff_lines":
            s = o["subject"]
            if s.startswith("staff/") and int(s.split("/")[1]) in pages:
                lines[s] = json.loads(o["value"]) if isinstance(o["value"], str) else o["value"]
    return lines


def dist_sp(box, lines):
    cy = (box[1] + box[3]) / 2.0
    sp = (lines[4] - lines[0]) / 4.0
    return max(0.0, (lines[0] - cy) / sp, (cy - lines[4]) / sp), sp


def bin_of(n):
    return "0 within staff" if n <= 0 else ("1-2 ledger lines" if n <= 2 else "3+ ledger lines")


def analyse(plate, f, rec_path, rng_pick, crops):
    pages = set(SAMPLE["plates"][plate]["pages"])
    lines = geometry(rec_path, pages)
    red = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in red_run(f, pages)}
    bars = {}
    for k in f["cells"]:
        p = k.split("/")
        key = tuple(int(x) for x in p[1:5])
        if key[0] in pages:
            bars[key] = dict(heads=[], frag=[], pad=None)
    for k, g in f["glyphs"].items():
        p = k.split("/")
        if len(p) != 6 or not g["head"]:
            continue
        key = tuple(int(x) for x in p[1:5])
        if key not in bars:
            continue
        if (g["fate"] or "") in OTHER:
            continue
        bars[key]["heads"].append((k, g))
    res = collections.defaultdict(lambda: collections.Counter())
    far = {}
    pads_a, pads_b = collections.Counter(), collections.Counter()
    for key, b in bars.items():
        sl = lines.get("staff/%d/%d/%d" % key[:3])
        cell = f["cells"].get("cell/%d/%d/%d/%d" % key)
        if sl is None or cell is None:
            res["no staff line / cell row"]["bars"] += 1
            continue
        sp = (sl[4] - sl[0]) / 4.0
        pads_a[round((sl[0] - cell[1]) / sp)] += 1
        pads_b[round((cell[3] - sl[4]) / sp)] += 1
        dmax, n = 0.0, 0
        dreal = 0.0
        for k, g in b["heads"]:
            d, _ = dist_sp(g["box"], sl)
            dmax = max(dmax, d)
            if not (g["fate"] or "").startswith("not_a_notehead") and g["fate"] != "mark_group_duplicate":
                dreal = max(dreal, d)
        nreal = math.ceil(dreal - 0.75)
        isred0 = key in red
        nrh = sum(1 for k, g in b["heads"] if not (g["fate"] or "").startswith("not_a_notehead") and g["fate"] != "mark_group_duplicate")
        if nrh:
            nm = "REAL-HEADS-ONLY (no refused fragments/duplicates) | " + bin_of(nreal)
            res[nm]["bars"] += 1
            res[nm]["red"] += int(isred0)
            hb2 = "1-2 heads" if nrh <= 2 else ("3-5 heads" if nrh <= 5 else "6+ heads")
            nm = nm + " | " + hb2
            res[nm]["bars"] += 1
            res[nm]["red"] += int(isred0)
        n = math.ceil(dmax - 0.75) if b["heads"] else None
        bn = "no head" if n is None else bin_of(n)
        nh = len(b["heads"])
        hb = "0 heads" if nh == 0 else ("1-2 heads" if nh <= 2 else ("3-5 heads" if nh <= 5 else "6+ heads"))
        isred = key in red
        far[key] = (dmax, n)
        for name in (bn, "%s | %s" % (bn, hb) if bn != "no head" else None):
            if name is None:
                continue
            res[name]["bars"] += 1
            res[name]["red"] += int(isred)
        res["ALL"]["bars"] += 1
        res["ALL"]["red"] += int(isred)
        res["by heads | " + hb]["bars"] += 1
        res["by heads | " + hb]["red"] += int(isred)
    # 2. clipped / too_narrow refusals
    frags, edge = [], collections.Counter()
    kinds = collections.Counter()
    for key, b in bars.items():
        sl = lines.get("staff/%d/%d/%d" % key[:3])
        cell = f["cells"].get("cell/%d/%d/%d/%d" % key)
        for k, g in f["glyphs"].items():
            pass
        break
    for k, g in f["glyphs"].items():
        if g["fate"] not in FRAG:
            continue
        p = k.split("/")
        if len(p) != 6:
            continue
        key = tuple(int(x) for x in p[1:5])
        if key not in bars:
            continue
        sl = lines.get("staff/%d/%d/%d" % key[:3])
        cell = f["cells"].get("cell/%d/%d/%d/%d" % key)
        sp = (sl[4] - sl[0]) / 4.0
        top = g["box"][1] <= cell[1] + sp
        bot = g["box"][3] >= cell[3] - sp
        d, _ = dist_sp(g["box"], sl)
        frags.append(dict(glyph=k, fate=g["fate"], page=key[0], edge_top=top, edge_bottom=bot, dist_sp=round(d, 2), box=g["box"],
                          cell=cell, red=key in red))
    for fr in frags:
        kinds[fr["fate"]] += 1
        edge[(fr["fate"], "cut by cell top/bottom edge" if (fr["edge_top"] or fr["edge_bottom"]) else "not at an edge")] += 1
    red_first = collections.Counter()
    red_has = collections.Counter()
    for key, b in red.items():
        if b["why"].split(" (")[0] in ("not_a_notehead:clipped_fragment", "not_a_notehead:too_narrow") and b["cause"].startswith("2"):
            red_first[b["why"]] += 1
        fr_in = [fr for fr in frags if tuple(int(x) for x in fr["glyph"].split("/")[1:5]) == key]
        if fr_in:
            red_has["red bars holding one"] += 1
    # fragments far from the staff?
    fb = collections.Counter(bin_of(math.ceil(fr["dist_sp"] - 0.75)) for fr in frags)
    # 3. heads of ANOTHER staff poking into this cell, placed by the nearest other staff of the same system: beyond that staff's pad?
    poke = collections.Counter()
    for k, g in f["glyphs"].items():
        if g["head"] and (g["fate"] or "") in OTHER:
            p = k.split("/")
            if len(p) != 6 or int(p[1]) not in pages:
                continue
            page, sysi = int(p[1]), int(p[2])
            cands = [(s, v) for s, v in lines.items() if s.startswith("staff/%d/%d/" % (page, sysi)) and s != "staff/%s/%s/%s" % tuple(p[1:4])]
            if not cands:
                continue
            cy = (g["box"][1] + g["box"][3]) / 2
            s, v = min(cands, key=lambda sv: min(abs(cy - sv[1][0]), abs(cy - sv[1][4])))
            d, sp = dist_sp(g["box"], v)
            poke["twin heads attributed to the nearest other staff"] += 1
            if d > 4.0:
                poke["... of those, farther than the nominal 4-space pad of that staff"] += 1
            if d > 6.0:
                poke["... farther than the 6-space ceiling"] += 1
    # 4. random clipped_fragment crops
    pick = [fr for fr in frags if fr["fate"].endswith("clipped_fragment")]
    pick.sort(key=lambda fr: fr["glyph"])
    chosen = rng_pick(pick)
    outs = []
    for fr in chosen:
        im = page_image(plate, fr["page"])
        c = fr["cell"]
        crop = im.crop((int(c[0]), int(c[1]), int(c[2]), int(c[3]))).convert("RGB")
        s = max(1.0, 420.0 / crop.height)
        crop = crop.resize((int(crop.width * s), int(crop.height * s)), Image.LANCZOS)
        b = fr["box"]
        ImageDraw.Draw(crop).rectangle([(b[0] - c[0]) * s - 3, (b[1] - c[1]) * s - 3, (b[2] - c[0]) * s + 3, (b[3] - c[1]) * s + 3],
                                       outline=(255, 140, 0), width=2)
        name = "%s_%s.png" % (plate, fr["glyph"].replace("glyph/", "").replace("/", "-"))
        Path(crops).mkdir(parents=True, exist_ok=True)
        crop.save(Path(crops) / name)
        outs.append(dict(file=name, glyph=fr["glyph"], dist_sp=fr["dist_sp"], at_edge=(fr["edge_top"] or fr["edge_bottom"])))
    return dict(plate=plate, pages=sorted(pages), bins={k: dict(v) for k, v in sorted(res.items())}, n_bars=len(bars), n_red_bars=len(red),
                n_red_in_bars=sum(1 for k in red if k in bars), refusals=dict(kinds), refusal_edge={"%s | %s" % k: v for k, v in edge.items()},
                refusal_by_distance=dict(fb), red_first_cause_is_frag=dict(red_first), red_bars_holding_a_frag=dict(red_has),
                pad_above_spaces_counts=dict(pads_a), pad_below_spaces_counts=dict(pads_b), twin_heads=dict(poke), crops=outs)


def main() -> None:
    ap = argparse.ArgumentParser()
    for n in ("lit", "lit-record", "bra", "bra-record", "crops", "json"):
        ap.add_argument("--" + n, required=True)
    a = ap.parse_args()
    rng = random.Random(2311003)
    out = []
    for plate, fp, rp in (("litolff", a.lit, a.lit_record), ("brahms", a.bra, a.bra_record)):
        f = json.load(open(fp))
        r = analyse(plate, f, rp, lambda pop: rng.sample(pop, 3), a.crops)
        out.append(r)
        print("==", plate, "bars", r["n_bars"], "red (in those bars)", r["n_red_in_bars"], "of", r["n_red_bars"])
        for k, v in r["bins"].items():
            print("  %-34s bars %5d  red %4d  share %5.1f%%" % (k, v["bars"], v.get("red", 0), 100.0 * v.get("red", 0) / max(1, v["bars"])))
        for k in ("refusals", "refusal_edge", "refusal_by_distance", "red_first_cause_is_frag", "red_bars_holding_a_frag", "pad_above_spaces_counts",
                  "pad_below_spaces_counts", "twin_heads"):
            print(" ", k, r[k])
        print("  crops", [c["file"] for c in r["crops"]])
    Path(a.json).write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
