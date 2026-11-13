"""ROADMAP 2.307 T2 -- score the three ways of looking (measure only; no tuning, no guards).

    python3 benchmarks/page-and-zoom-2026-11/t2_score.py WORK_DIR OUT.json [--crops CROP_DIR]

WORK_DIR holds `t2_detect_page.py` outputs `<plate>.p<page>.json`. Per way, every box is in page pixels; the ONE merge rule is "same class at
the same place (IoU >= 0.5) is one mark" (the most confident box kept), applied within the way. Families: head_filled / head_hollow /
head_whole, rest, accidental, flag, dot, clef (the brief's list).

Scoring:
  * Brahms p0 against Sean's hand labels (`data/hand-truth/pages/imslp317803/0.json`), per family: FOUND (a box of that family on the label,
    IoU >= 0.3 or the label centre inside the box), MISSED, NOT HIS (a box of the family on no label of the family). Labels were prefilled
    from a cell detector run and then confirmed, fixed or drawn, so `cells` is favoured by construction (origin is reported).
  * Every page against `cells` by place (same family, IoU >= 0.3): IN BOTH / ONLY CELLS / ONLY THIS WAY. "Only this way" is the false-box
    risk (it is also where a mark the cells missed would be); it is counted, never called right or wrong.
  * Sean's judged answers where a judged mark exists: every tile of `judged` (benchmarks/*/answers via `tools.omr.staged.judged`) on these
    pages with a page box and a head/rest/accidental subject -- is a box of the way's family on it (same rule as labels).
"""
import collections
import glob
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from t1b_clipped import family  # noqa: E402

FAMS = ("head_filled", "head_hollow", "head_whole", "rest", "accidental", "flag", "dot", "clef")
WAYS = ("cells", "row", "band")


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def on(lab_rect, box):
    cx, cy = (lab_rect[0] + lab_rect[2]) / 2, (lab_rect[1] + lab_rect[3]) / 2
    return iou(lab_rect, box) >= 0.3 or (box[0] <= cx <= box[2] and box[1] <= cy <= box[3])


def merged(items):
    """[[cls, conf, x0, y0, x1, y1], ...] -> one mark per (class, place)."""
    by_cls = collections.defaultdict(list)
    for it in items:
        for b in it["boxes"]:
            by_cls[b[0]].append(b)
    out = []
    for cls, bs in by_cls.items():
        bs.sort(key=lambda b: -b[1])
        kept = []
        for b in bs:
            if all(iou(b[2:], k[2:]) < 0.5 for k in kept):
                kept.append(b)
        out.extend(kept)
    return out


def fam_boxes(marks):
    d = collections.defaultdict(list)
    for b in marks:
        f = family(b[0])
        if f in FAMS:
            d[f].append(b)
    return d


def main():
    work, outp = sys.argv[1], sys.argv[2]
    crops = sys.argv[sys.argv.index("--crops") + 1] if "--crops" in sys.argv else None
    res = {"pages": {}, "timing": {}, "labels_p0": {}, "vs_cells": collections.defaultdict(lambda: collections.defaultdict(collections.Counter)),
           "judged": {}}
    pages = {}
    for f in sorted(glob.glob(os.path.join(work, "*.p*.json"))):
        d = json.load(open(f))
        key = "%s/%d" % (d["plate"], d["page"])
        pages[key] = {w: fam_boxes(merged(d["ways"][w]["items"])) for w in WAYS}
        res["timing"][key] = {w: round(d["ways"][w]["t_detect"], 1) for w in WAYS}
        res["timing"][key]["prepare"] = round(d["t_prepare"], 1)
        res["timing"][key]["most_boxes_in_a_call"] = {w: d["ways"][w]["most_boxes_in_a_call"] for w in WAYS}
    only_way = {w: [] for w in ("row", "band")}
    for key, ways in pages.items():
        plate = key.split("/")[0]
        for fam in FAMS:
            cb = ways["cells"].get(fam, [])
            for w in ("row", "band"):
                wb = ways[w].get(fam, [])
                both = sum(1 for b in wb if any(iou(b[2:], c[2:]) >= 0.3 for c in cb))
                only_c = sum(1 for c in cb if not any(iou(b[2:], c[2:]) >= 0.3 for b in wb))
                ow = [b for b in wb if not any(iou(b[2:], c[2:]) >= 0.3 for c in cb)]
                t = res["vs_cells"][plate][w]
                t[fam + ":both"] += both
                t[fam + ":only_cells"] += only_c
                t[fam + ":only_this_way"] += len(ow)
                only_way[w].extend((key, fam, b) for b in ow)
        res["pages"][key] = {w: {f: len(v) for f, v in ways[w].items()} for w in WAYS}
    # Sean's p0 labels
    if "brahms/0" in pages:
        lab = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
        labs = collections.defaultdict(list)
        for b in lab["boxes"]:
            f = family(b["cls"])
            if f in FAMS:
                labs[f].append(b)
        for w in WAYS:
            row = {}
            for fam in FAMS:
                L = labs.get(fam, [])
                B = pages["brahms/0"][w].get(fam, [])
                found = [l for l in L if any(on(l["rect"], b[2:]) for b in B)]
                missed = [l for l in L if l not in found]
                notyours = [b for b in B if not any(on(l["rect"], b[2:]) for l in L)]
                row[fam] = dict(labels=len(L), found=len(found), missed=len(missed), not_his=len(notyours),
                                missed_drawn=sum(1 for l in missed if l["origin"] == "drawn"))
            res["labels_p0"][w] = row
    # judged answers
    try:
        from tools.omr.staged import judged as J
        jt = judged_tiles(J, set(pages))
    except Exception as exc:                     # noqa: BLE001
        jt = []
        res["judged_error"] = repr(exc)
    for w in WAYS:
        c = collections.Counter()
        for t in jt:
            key = "%s/%d" % (t["plate"], t["page"])
            fam = t["family"]
            if fam in ("head", "not_a_head"):
                B = [b for f in ("head_filled", "head_hollow", "head_whole") for b in pages[key][w].get(f, [])]
            else:
                B = pages[key][w].get(fam, [])
            c[fam + (":boxed" if any(on(t["box"], b[2:]) for b in B) else ":not_boxed")] += 1
        res["judged"][w] = dict(c)
    res["judged_n"] = len(jt)
    # 20 seeded leads per way
    if crops:
        os.makedirs(crops, exist_ok=True)
        rng = random.Random(2307)
        leads = {}
        for w, lst in only_way.items():
            pick = rng.sample(lst, min(20, len(lst)))
            leads[w] = [dict(page=k, family=f, cls=b[0], conf=b[1], box=b[2:]) for k, f, b in pick]
        json.dump(leads, open(os.path.join(crops, "leads.json"), "w"), indent=1)
    res["vs_cells"] = {p: {w: dict(t) for w, t in ws.items()} for p, ws in res["vs_cells"].items()}
    json.dump(res, open(outp, "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("timing", "labels_p0", "vs_cells", "judged", "judged_n")}, indent=1))


def judged_tiles(J, pages):
    """Sean's judged tiles on these pages that name a head / rest / accidental and carry a page box."""
    """The judged index (`benchmarks/acceptance/judged-tiles.json`): a tile with a glyph subject, a mark-sized page box (<= 120 px a side, the
    index's own `with_derived_positions` limit) and an answer that says what the ink IS: a duration answer = a notehead (any head family), a
    rest answer = a rest, `not_a_note` = NOT a head (a head box there is a false box). Other answers are skipped."""
    out = []
    rows = json.load(open(J.INDEX_PATH))["tiles"]
    for r in rows:
        box, sub, plate = r.get("page_box"), r.get("subject"), r.get("doc")
        if not box or not sub or not plate or not str(sub).startswith("glyph/"):
            continue
        if box[2] - box[0] > 120 or box[3] - box[1] > 120:
            continue
        page = int(str(sub).split("/")[1])
        if "%s/%d" % (plate, page) not in pages:
            continue
        ak = r.get("answer_kind")
        f = {"duration": "head", "duration_multi": "head", "rest": "rest", "not_a_note": "not_a_head"}.get(ak)
        if f:
            out.append(dict(plate=plate, page=page, box=box, family=f))
    return out


if __name__ == "__main__":
    main()
