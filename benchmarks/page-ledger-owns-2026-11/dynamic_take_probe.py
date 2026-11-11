"""2.284 r9 (read only): does a dynamic's page claim OWN ink that is not the dynamic's?

STAGED, ADJUDICATE over saved GATHER rows (flag `OMR_PAGE_LEDGER_OWNS=1`, the GATHER half already in the rows). For EVERY in-staff READ claim of owner
`word` (dynamic letters, spelled dynamics, in-staff READ words) the page ledger's own verdict says which cell strokes the claim owns (`stroke_owner`
verdict `strokes[ord]` = [state, family, owners, ...], the claim's row id in `owners`, after the page settle). The owned strokes are measured on the
PAGE RASTER (600 dpi, 0 = ink, staff-line runs erased: a staff line is not a stroke):

  inside   ink pixels of the claim's drawn box
  owned    ink pixels of the strokes the ledger gives the claim, taken whole as the strokes' ink inside their page boxes, one pixel counted once
  own      owned pixels on a component the claim's own evidence holds (the detector's `dynamicX` letter boxes, or -- a word -- its box), and not of a
           foreign SHAPE
  taken    owned pixels that are not the dynamic's, by the ink's SHAPE and never by a detector box existing:
             ring    a closed hollow head-sized hole body (0.9-2.0 sp wide, 0.6-1.5 sp tall)
             stem    a thin vertical run (>= 2.0 sp tall, <= 0.45 sp wide)
             beam    a thick horizontal run (>= 1.5 sp wide, aspect >= 3)
             ledger  a thin horizontal run (>= 1.0 sp wide, <= 0.35 sp tall, aspect >= 4)
             other   a component with no overlap with the claim's own letter evidence (dynamic claims only)
           each taken component also says `boxed` (a note-family detector box stands on >= 50% of it) or `unboxed`.

    usage: dynamic_take_probe.py plate slice_dir pages... [--json OUT] [--plant]

`--plant` is the control that can fail: on the first page the largest in-staff claim's box is enlarged over a hollow head whose detector boxes are
DELETED from the rows (a head with no box), the same measure is re-run, and it must report taken > 0 of kind ring, unboxed.
"""
import argparse
import collections
import copy
import json
import os
import pathlib
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
from tools.omr.staged import claim_readout as CR  # noqa: E402
from tools.omr.staged import lane_report as LR  # noqa: E402
from tools.omr.staged.record import STROKE_GLYPH_BASE  # noqa: E402

NOTE_FAMILIES = ("notehead", "stem", "flag", "beam", "rest", "accidental", "augmentationDot", "ledgerLine", "tuplet", "articulation", "fermata")
ENV = {"OMR_PAGE_LEDGER_OWNS": "1"}
FRINGE_PX = 8


def page_binary(plate, pg):
    from tools.omr.preprocessing import render_page
    return render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), pg, dpi=600).binary


def inter(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def area(a):
    return max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])


def ink_without_staff(binary, sp):
    ink = (binary == 0).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (int(round(3.0 * sp)), 1))
    lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, k)
    lines = cv2.dilate(lines, np.ones((3, 1), np.uint8))
    return (ink > 0) & ~(lines > 0)


def shape_of(mask, sp):
    h, w = mask.shape
    ws, hs = w / sp, h / sp
    if hs >= 2.0 and ws <= 0.45:
        return "stem"
    if ws >= 1.0 and hs <= 0.35 and ws / max(hs, 1e-6) >= 4:
        return "ledger"
    if ws >= 1.5 and hs >= 0.3 and ws / max(hs, 1e-6) >= 3:
        return "beam"
    pad = np.pad(mask, 1)
    inv = (~pad).astype(np.uint8)
    n, lab, st, _c = cv2.connectedComponentsWithStats(inv, 4)
    holes = sum(1 for k in range(1, n) if st[k][0] > 0 and st[k][1] > 0 and st[k][0] + st[k][2] < pad.shape[1] and st[k][1] + st[k][3] < pad.shape[0]
                and st[k][4] >= 0.08 * sp * sp)
    if holes and 0.9 <= ws <= 2.0 and 0.6 <= hs <= 1.5:
        return "ring"
    return "other"


def owner_verdicts_with_log(rows, env):
    """`CR.owner_verdicts` that also returns the rebuilt log: it re-ids the rows, and the verdict's `owners` carry the REBUILT ids."""
    from tools.omr.staged import adjudicate as A
    from tools.omr.staged.record import Q
    from tools.omr.staged.review import rerun as RR
    saved = {k: os.environ.get(k) for k in env}
    try:
        os.environ.update(env)
        log, idmap = RR.rebuild_gather({"observations": rows["observations"], "abstentions": rows["abstentions"], "verdicts": []})
        A._ensure_decisions()
        spec = A.REGISTRY[Q.STROKE_OWNER]
        log.freeze()
        out = {}
        for sub in A.subjects_for(log, spec):
            v = A.adjudicate_one(log, spec, sub)
            if isinstance(v.detail, dict):
                out[(sub.page, sub.system, sub.staff, sub.cell)] = v.detail
        return idmap, out
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def load(rows, plate_pg):
    """Claims, stroke page boxes, detector boxes, letter boxes of one page's rows."""
    claims, strokes, dets, letters = [], {}, [], {}
    cls = {}
    for o in rows["observations"]:
        q = o["quantity"]
        d = o.get("detail") or {}
        if q == "glyph_box" and isinstance(o["value"], list):
            cls[o["subject"]] = str(o["value"][0])
            if d.get("bbox_page_px"):
                dets.append((o["subject"], str(o["value"][0]), [float(t) for t in d["bbox_page_px"]], o))
        elif q == "stroke":
            parts = o["subject"].split("/")
            g = int(parts[-1]) if parts[-1].isdigit() else -1
            if STROKE_GLYPH_BASE <= g < 400_000 and d.get("bbox_page_px"):
                strokes[(int(parts[2]), int(parts[3]), int(parts[4]), g - STROKE_GLYPH_BASE)] = [float(t) for t in d["bbox_page_px"]]
        elif q == "dynamic_letter" and d.get("bbox_page_px"):
            letters[o["id"]] = [float(t) for t in d["bbox_page_px"]]
        elif q == "claimed_area" and d.get("owner") == "word" and d.get("standing", "READ") == "READ" and d.get("unit") == "area" and d.get("inside_staff"):
            claims.append(dict(id=o["id"], box=[float(v) for v in o["value"]], source=d.get("source"), text=d.get("text"),
                               letter=d.get("detector_letter"), category=d.get("category"), word_box=d.get("word_box"),
                               letter_rows=d.get("letter_rows") or [], sp=float(d.get("space_page_px") or 15.75), left_out=d.get("marks_left_out")))
    return claims, strokes, dets, letters


def measure(claims, strokes, dets, letters, verdicts, ink_all, idmap):
    H, W = ink_all.shape
    out = []
    for c in claims:
        sp = c["sp"]
        x0, y0, x1, y1 = (int(round(v)) for v in c["box"])
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        inside = int(ink_all[y0:y1, x0:x1].sum())
        # owned cell strokes (decided / merged) and contested ones
        owned_boxes, contested = [], 0
        for (page, system, staff, cell), det in verdicts.items():
            for ordi, srow in (det.get("strokes") or {}).items():
                if idmap.get(c["id"], c["id"]) not in srow[2]:
                    continue
                if srow[0] in ("decided", "merged") and srow[1] == "word":
                    b = strokes.get((system, staff, cell, int(ordi)))
                    if b:
                        owned_boxes.append(b)
                elif srow[0] == "contested":
                    contested += 1
        own_ev = [letters[i] for i in c["letter_rows"] if i in letters]
        is_word = not own_ev and not c["letter"]
        mask = np.zeros(ink_all.shape, bool)
        for b in owned_boxes:
            bx0, by0, bx1, by1 = max(0, int(b[0]) - 1), max(0, int(b[1]) - 1), min(W, int(b[2]) + 2), min(H, int(b[3]) + 2)
            mask[by0:by1, bx0:bx1] |= ink_all[by0:by1, bx0:bx1]
        owned_px = int(mask.sum())
        # components of the owned pixels
        n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        comps = []
        by_kind = collections.Counter()
        for k in range(1, n):
            cx, cy, cw, ch, a = (int(v) for v in st[k])
            if a < 4:
                continue
            m = lab[cy:cy + ch, cx:cx + cw] == k
            shp = shape_of(m, sp)
            cb = [float(cx), float(cy), float(cx + cw), float(cy + ch)]
            in_letter = any(inter(cb, e) >= 0.5 * area(cb) for e in own_ev)
            boxed_by = [cl for _s, cl, bb, _o in dets if cl.startswith(NOTE_FAMILIES) and inter(cb, bb) >= 0.5 * area(cb)]
            if a < FRINGE_PX:
                kind = "fringe"               # under 8 px: a pixel-wide fringe of a staff line or a stem edge names no mark, not counted as taken
            elif in_letter:
                kind = "own"                  # the f's crossbar / the ff ligature bar / the p's bowl lie in the detector's letter box: the letter's
            elif shp in ("ring", "stem", "beam", "ledger"):
                kind = shp
            elif not is_word:
                kind = "other"
            else:
                kind = "own"
            by_kind[kind] += a
            comps.append(dict(box=cb, px=a, shape=shp, kind=kind, in_letter=in_letter, boxed=bool(boxed_by), boxed_by=boxed_by[:2]))
        taken = sum(v for k, v in by_kind.items() if k not in ("own", "fringe"))
        out.append(dict(id=c["id"], box=c["box"], source=c["source"], text=c["text"], letter=c["letter"], category=c["category"], sp=sp,
                        box_w_sp=round((c["box"][2] - c["box"][0]) / sp, 2), box_h_sp=round((c["box"][3] - c["box"][1]) / sp, 2),
                        inside_px=inside, owned_px=owned_px, owned_boxes=owned_boxes, owned_strokes=len(owned_boxes), contested_strokes=contested,
                        own_px=by_kind.get("own", 0), taken_px=taken, taken_by_kind={k: v for k, v in by_kind.items() if k not in ("own", "fringe")}, fringe_px=by_kind.get("fringe", 0),
                        taken_boxed=sum(c2["px"] for c2 in comps if c2["kind"] not in ("own", "fringe") and c2["boxed"]),
                        taken_unboxed=sum(c2["px"] for c2 in comps if c2["kind"] not in ("own", "fringe") and not c2["boxed"]),
                        comps=[c2 for c2 in comps if c2["kind"] != "own"], rings_in_letter=[c2 for c2 in comps if c2["in_letter"] and c2["shape"] == "ring"], left_out=c["left_out"]))
    return out


def analyse(plate, pg, rows, binary=None):
    idmap, verdicts = owner_verdicts_with_log(rows, ENV)
    binary = binary if binary is not None else page_binary(plate, pg)
    claims, strokes, dets, letters = load(rows, pg)
    sps = [c["sp"] for c in claims] or [15.5]
    ink_all = ink_without_staff(binary, sorted(sps)[len(sps) // 2])
    return measure(claims, strokes, dets, letters, verdicts, ink_all, idmap), ink_all


def plant(plate, pg, rows, binary):
    """The control that can fail: a real hollow head with its detector boxes DELETED (no box), a claim's box enlarged over it."""
    claims, strokes, dets, letters = load(rows, pg)
    heads = [(s, cl, bb, o) for s, cl, bb, o in dets if cl.startswith("notehead")]
    sps = [c["sp"] for c in claims] or [15.5]
    ink_all = ink_without_staff(binary, sorted(sps)[len(sps) // 2])
    best = None
    for c in sorted(claims, key=lambda c: -(c["box"][2] - c["box"][0])):
        for s, cl, bb, o in heads:
            if "Half" not in cl and "Whole" not in cl:
                continue
            # a hollow head within 4 sp of the claim, not already inside its box
            cx, cy = (c["box"][0] + c["box"][2]) / 2, (c["box"][1] + c["box"][3]) / 2
            hx, hy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            if abs(hx - cx) < 4 * c["sp"] and abs(hy - cy) < 5 * c["sp"] and inter(bb, c["box"]) == 0:
                best = (c, s, bb)
                break
        if best:
            break
    if not best:
        return dict(error="no hollow head near a claim on this page")
    c, skey, bb = best
    gone = {s for s, cl, b2, o in dets if inter(b2, bb) > 0.3 * area(bb)}          # every detector box over that head (twins too)
    rows2 = copy.deepcopy(rows)
    drop_ids = set()
    keep = []
    for o in rows2["observations"]:
        if o["subject"] in gone and o["quantity"] in ("glyph_box", "glyph_conf", "glyph_strokes", "page_mark", "page_mark_owner", "notehead_class", "notehead_ink",
                                                       "notehead_staff_position", "head_ink", "glyph_ladder"):
            continue
        keep.append(o)
    rows2["observations"] = keep
    nb = [min(c["box"][0], bb[0] - 4), min(c["box"][1], bb[1] - 4), max(c["box"][2], bb[2] + 4), max(c["box"][3], bb[3] + 4)]
    for o in rows2["observations"]:
        if o["id"] == c["id"]:
            o["value"] = nb
    res, _ = analyse(plate, pg, rows2, binary)
    mine = [r for r in res if r["id"] == c["id"]]
    return dict(claim=c["id"], head_box=bb, deleted_boxes=sorted(gone), new_box=nb, result=mine[0] if mine else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plate")
    ap.add_argument("src")
    ap.add_argument("pages", nargs="+", type=int)
    ap.add_argument("--json")
    ap.add_argument("--plant", action="store_true")
    a = ap.parse_args()
    out = {"plate": a.plate, "src": a.src, "pages": {}}
    tot = collections.Counter()
    for pg in a.pages:
        rows = CR.read_rows(pathlib.Path(a.src), [pg])
        binary = page_binary(a.plate, pg)
        res, _ink = analyse(a.plate, pg, rows, binary)
        out["pages"][str(pg)] = dict(claims=res)
        if a.plant:
            out["pages"][str(pg)]["plant"] = plant(a.plate, pg, rows, binary)
        for r in res:
            tot["claims"] += 1
            tot["claims_taking"] += 1 if r["taken_px"] else 0
            tot["inside_px"] += r["inside_px"]
            tot["owned_px"] += r["owned_px"]
            tot["own_px"] += r["own_px"]
            tot["taken_px"] += r["taken_px"]
            tot["fringe_px"] += r["fringe_px"]
            tot["rings_in_letter"] += len(r["rings_in_letter"])
            for k, v in r["taken_by_kind"].items():
                tot["taken_" + k] += v
        print("page", pg, "claims", len(res), flush=True)
    out["totals"] = dict(tot)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out["totals"]))


if __name__ == "__main__":
    main()
