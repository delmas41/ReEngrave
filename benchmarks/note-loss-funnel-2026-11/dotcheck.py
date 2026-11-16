"""ROADMAP 2.311 -- TRY TO FALSIFY: "red bars come from an augmentation dot not read on a note that has an arc beside it"
(Sean, red-bar tiles 7, 9, 10, 11, 12 of out/print/2.311-redbars: two dotted quarters, tie/arc to the next bar).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/dotcheck.py \
        --lit LIT.facts.json --lit-record LIT.record.json --bra BRA.facts.json --bra-record BRA.record.json \
        --key out/print/2.311-redbars-key.json --crops out/print/2.311-dots --json benchmarks/note-loss-funnel-2026-11/dotcheck-results.json

Reads only (saved lit-a / bra-a records and facts); nothing is re-gathered or re-decided.
1. Red bars (the same 309 / 276) that "does not add up" SHORT by exactly 0.5 per missing dot, whose written notes are all plain/dotted
   quarters (a bar of rests and quarters is counted apart), by page.
2. The red-bar tiles' heads: the record's verdict on the head; every detector augmentationDot box right of it (window: from 0.3 space
   left of the head's right edge to 3.5 spaces right of it, within 1.2 spaces of its centre) with the record's own `dot_role` verdict;
   slur/tie boxes within 1 space of that dot.
3. Whole plate: every augmentationDot-class box by its `dot_role` verdict (value, reason); whether a head beside it carries a dot in
   the written file; how many of those with no dot written lie within 1 staff space of a slur/tie BOX (an upper bound: the box of
   an arc is mostly empty paper).
4. Six more crops (seed 2311004): written plain quarter notes of a SHORT 6/8 red bar, the page right of the head, one thin box on the head.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

from checksheet import page_image
from redbars import run as red_run
from tools.omr.staged.record_io import load_record

SAMPLE = json.load(open("benchmarks/lane-report/sample.json"))
OTHER = ("owned_by_another_staff", "not_a_notehead:belongs_to_a_nearer_staff")


def lines_and_roles(rec_path, pages):
    r = load_record(rec_path)
    rec = r.get("record", r)
    lines, roles = {}, {}
    for o in rec["observations"]:
        if o.get("quantity") == "staff_lines" and o["subject"].startswith("staff/") and int(o["subject"].split("/")[1]) in pages:
            lines[o["subject"]] = json.loads(o["value"]) if isinstance(o["value"], str) else o["value"]
    for v in rec["verdicts"]:
        if v.get("quantity") == "dot_role":
            roles[v["subject"]] = (v.get("outcome"), v.get("value"), v.get("reason"))
    return lines, roles


def boxes_near(a, b, grow):
    return not (a[2] + grow < b[0] or b[2] + grow < a[0] or a[3] + grow < b[1] or b[3] + grow < a[1])


def run_plate(plate, f, rec_path, key_rows, crops, rng):
    pages = set(SAMPLE["plates"][plate]["pages"])
    lines, roles = lines_and_roles(rec_path, pages)
    red = red_run(f, pages)
    written = collections.defaultdict(list)
    for h in f["written"]:
        written[h["rg"]].append(h)
    heads_by_page = collections.defaultdict(list)
    dots_by_page = collections.defaultdict(list)
    arcs_by_page = collections.defaultdict(list)
    for k, g in f["glyphs"].items():
        p = k.split("/")
        if len(p) != 6:
            continue
        pg = int(p[1])
        if g["head"]:
            heads_by_page[pg].append((k, g))
        elif g["cls"] == "augmentationDot":
            dots_by_page[pg].append((k, g))
        elif g["cls"] in ("slur", "tie"):
            arcs_by_page[pg].append((k, g))

    def sp_of(k):
        p = k.split("/")
        sl = lines.get("staff/%s/%s/%s" % tuple(p[1:4]))
        return (sl[4] - sl[0]) / 4.0 if sl else None

    def dots_beside(k, g):
        sp = sp_of(k)
        if sp is None:
            return []
        cy = (g["box"][1] + g["box"][3]) / 2
        out = []
        for dk, dg in dots_by_page[g["page"]]:
            d = dg["box"]
            dcx, dcy = (d[0] + d[2]) / 2, (d[1] + d[3]) / 2
            if g["box"][2] - 0.3 * sp <= dcx <= g["box"][2] + 3.5 * sp and abs(dcy - cy) <= 1.2 * sp:
                out.append((dk, dg))
        return out

    # ---- 1. short bars, quarters only
    res = dict(plate=plate)
    pat = collections.Counter()
    short_all = collections.Counter()
    pool = []
    for b in red:
        if b["kind"] != "does_not_add_up" or not b.get("counted_quarters") or b.get("want_quarters") is None:
            continue
        want, got = b["want_quarters"], b["counted_quarters"]
        if max(got) >= want:
            continue
        pre = "glyph/%d/%d/%d/%d/" % (b["page"], b["system"], b["staff"], b["cell"])
        ws = [h for rg, hs in written.items() if rg.startswith(pre) for h in hs]
        notes = [h for h in ws if h["kind"] == "note"]
        rests = [h for h in ws if h["kind"] != "note"]
        diff = want - max(got)
        short_all["short bars (all)"] += 1
        if not notes or any(h["type"] != "quarter" for h in notes):
            continue
        plain = [h for h in notes if not (h.get("sub") or {}).get("dot")]
        k = diff / 0.5
        if abs(k - round(k)) > 1e-6 or round(k) > len(plain):
            continue
        tag = "quarters only" if not rests else "quarters + rests"
        pat[tag] += 1
        pat["%s | page %d" % (tag, b["page"])] += 1
        # every head of the bar written? (no head refused/narrowed in the bar)
        heads = [(kk, g) for kk, g in f["glyphs"].items() if kk.startswith(pre) and g["head"] and (g["fate"] or "") not in OTHER]
        if all((g["fate"] in ("written", "written_relocated")) or (g["fate"] or "").startswith("not_a_notehead") or g["fate"] == "mark_group_duplicate"
               for kk, g in heads):
            pat[tag + " | and every real head written"] += 1
        if want == 3.0 and not rests:
            for h in plain:
                pool.append(h)
    res["short_exact_halves"] = dict(pat)
    res["short_red_bars_all"] = dict(short_all)
    res["red_bars_total"] = len(red)

    # ---- 3. whole plate dots
    role_c = collections.Counter()
    used = collections.Counter()
    arc_c = collections.Counter()
    for pg, dl in dots_by_page.items():
        for dk, dg in dl:
            o = roles.get(dk, (None, None, None))
            role = "%s:%s" % (o[1], o[2])
            sp = sp_of(dk)
            role_c[role] += 1
            if sp is None:
                continue
            dcx, dcy = (dg["box"][0] + dg["box"][2]) / 2, (dg["box"][1] + dg["box"][3]) / 2
            carried = False
            for hk, hg in heads_by_page[pg]:
                if hg["box"][2] - 0.3 * sp <= dcx <= hg["box"][2] + 3.5 * sp and abs(dcy - (hg["box"][1] + hg["box"][3]) / 2) <= 1.2 * sp:
                    if any((h.get("sub") or {}).get("dot") for h in written.get(hk, [])):
                        carried = True
                        break
            near_arc = any(boxes_near(dg["box"], ag["box"], 1.0 * sp) for ak, ag in arcs_by_page[pg])
            cat = ("dot written on a head beside it" if carried else "NO dot written beside it") + " | role " + str(o[1])
            used[cat] += 1
            if near_arc:
                arc_c[cat] += 1
    res["dots_by_role"] = dict(role_c.most_common())
    res["dots_by_use"] = dict(used)
    res["dots_within_1sp_of_an_arc_box"] = dict(arc_c)
    res["dots_total"] = sum(role_c.values())

    # ---- 2. tile heads
    tiles = []
    for t in key_rows:
        if t["plate"] != plate or plate != "brahms":
            continue
        rows = []
        for m in t["marks"]:
            if m["kind"] != "note head":
                continue
            g = f["glyphs"][m["glyph"]]
            if (g["fate"] or "") in OTHER or g["fate"] and g["fate"].startswith("not_a_notehead"):
                continue
            ds = dots_beside(m["glyph"], g)
            sp = sp_of(m["glyph"])
            rows.append(dict(glyph=m["glyph"], box=m["box"], fate=m["fate"], duration=m["duration"], written=m.get("written"),
                             dot_boxes=[dict(glyph=dk, box=[round(x, 1) for x in dg["box"]], role=roles.get(dk),
                                             arc_boxes_within_1sp=[ak for ak, ag in arcs_by_page[g["page"]] if boxes_near(dg["box"], ag["box"], sp)])
                                        for dk, dg in ds]))
        tiles.append(dict(tile=t["tile"], page=t["page"], system=t["system"], staff=t["staff"], cell=t["cell"], measure=t["measure"],
                          counted=t["counted_quarters"], want=t["want_quarters"], heads=rows))
    res["tile_heads"] = tiles
    tcrops = []
    for t in tiles:
        for h in t["heads"]:
            wd = (h["written"] or {}).get("dots")
            if wd:      # a head written dotted: nothing to look for
                continue
            im = page_image(plate, t["page"])
            sp = sp_of(h["glyph"])
            b = h["box"]
            cy = (b[1] + b[3]) / 2
            x0, x1, y0, y1 = int(b[0] - 1.5 * sp), int(b[2] + 5 * sp), int(cy - 3.5 * sp), int(cy + 3.5 * sp)
            crop = im.crop((x0, y0, x1, y1)).convert("RGB")
            sc = 360.0 / crop.height
            crop = crop.resize((int(crop.width * sc), int(crop.height * sc)), Image.LANCZOS)
            ImageDraw.Draw(crop).rectangle([(b[0] - x0) * sc - 2, (b[1] - y0) * sc - 2, (b[2] - x0) * sc + 2, (b[3] - y0) * sc + 2],
                                           outline=(255, 140, 0), width=2)
            name = "tile%02d_%s.png" % (t["tile"], h["glyph"].replace("glyph/", "").replace("/", "-"))
            Path(crops).mkdir(parents=True, exist_ok=True)
            crop.save(Path(crops) / name)
            tcrops.append(name)
    res["tile_head_crops"] = tcrops
    # ---- 4. crops
    out = []
    if plate == "brahms":
        pool.sort(key=lambda h: h["rg"])
        res["crop_pool"] = len(pool)
        for h in rng.sample(pool, 6):
            im = page_image(plate, h["page"])
            sp = sp_of(h["rg"])
            b = h["box"]
            cy = (b[1] + b[3]) / 2
            x0, x1, y0, y1 = int(b[0] - 1.5 * sp), int(b[2] + 5 * sp), int(cy - 3.5 * sp), int(cy + 3.5 * sp)
            crop = im.crop((x0, y0, x1, y1)).convert("RGB")
            s = 360.0 / crop.height
            crop = crop.resize((int(crop.width * s), int(crop.height * s)), Image.LANCZOS)
            ImageDraw.Draw(crop).rectangle([(b[0] - x0) * s - 2, (b[1] - y0) * s - 2, (b[2] - x0) * s + 2, (b[3] - y0) * s + 2],
                                           outline=(255, 140, 0), width=2)
            name = "plain_%s.png" % h["rg"].replace("glyph/", "").replace("/", "-")
            Path(crops).mkdir(parents=True, exist_ok=True)
            crop.save(Path(crops) / name)
            g = f["glyphs"][h["rg"]]
            ds = dots_beside(h["rg"], g)
            out.append(dict(file=name, glyph=h["rg"], measure=h["measure"], dot_boxes_beside=[(dk, roles.get(dk)) for dk, dg in ds]))
    res["random_plain_quarters"] = out
    # ---- 5. unclassified ink: a dot-sized, unboxed piece right of a plain written quarter (pool = short red bars; control = all other bars)
    pieces = collections.defaultdict(list)
    for k, g in f["glyphs"].items():
        if g["cls"] is None:
            pieces[g["page"]].append((k, g["box"]))

    def dotlike_beside(rg, h):
        sp = sp_of(rg)
        b = h["box"]
        cy = (b[1] + b[3]) / 2
        n = []
        for pk, pb in pieces[h["page"]]:
            w, hh = pb[2] - pb[0], pb[3] - pb[1]
            if 0.3 * sp <= w <= 0.8 * sp and 0.3 * sp <= hh <= 0.8 * sp:
                pcx, pcy = (pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2
                if b[2] + 0.2 * sp <= pcx <= b[2] + 3.0 * sp and abs(pcy - cy) <= 1.0 * sp:
                    n.append(pk)
        return n

    redkeys = {(b["page"], b["system"], b["staff"], b["cell"]) for b in red}
    poolkeys = {h["rg"] for h in pool}
    cnt = collections.Counter()
    for rg, hs in written.items():
        for h in hs:
            if h["kind"] != "note" or h["type"] != "quarter" or (h.get("sub") or {}).get("dot") or not rg.startswith("glyph/"):
                continue
            pp = rg.split("/")
            grp = "POOL: plain quarter in a short quarters-only 6/8 red bar" if rg in poolkeys else (
                "red bar, other" if tuple(int(x) for x in pp[1:5]) in redkeys else "bars not red")
            if sp_of(rg) is None or int(pp[1]) not in pages:
                continue
            cnt[grp + " | plain quarters"] += 1
            if dotlike_beside(rg, h):
                cnt[grp + " | with a dot-sized unclassified ink piece right of the head, no dot box"] += 1
    res["dotlike_ink_beside_plain_quarters"] = dict(cnt)
    for o in out:
        pk = [h for h in pool if h["rg"] == o["glyph"]][0]
        o["dotlike_ink_pieces"] = dotlike_beside(o["glyph"], pk)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    for n in ("lit", "lit-record", "bra", "bra-record", "key", "crops", "json"):
        ap.add_argument("--" + n, required=True)
    a = ap.parse_args()
    key = json.load(open(a.key))
    rng = random.Random(2311004)
    out = []
    for plate, fp, rp in (("litolff", a.lit, a.lit_record), ("brahms", a.bra, a.bra_record)):
        r = run_plate(plate, json.load(open(fp)), rp, key, a.crops, rng)
        out.append(r)
        print("==", plate)
        for k in ("red_bars_total", "short_red_bars_all", "short_exact_halves", "dots_total", "dots_by_role", "dots_by_use", "dots_within_1sp_of_an_arc_box", "dotlike_ink_beside_plain_quarters"):
            print(" ", k, r[k])
        for t in r["tile_heads"]:
            print("  tile", t["tile"], "p%d bar %s" % (t["page"], t["measure"]), "want", t["want"], "counted", t["counted"])
            for h in t["heads"]:
                print("    ", h["glyph"], h["fate"], h["duration"]["reason"], h["duration"]["value"] and h["duration"]["value"].get("dots"),
                      "| dot boxes:", [(d["glyph"], d["role"], len(d["arc_boxes_within_1sp"])) for d in h["dot_boxes"]])
        print("  crops", r["random_plain_quarters"])
    Path(a.json).write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
