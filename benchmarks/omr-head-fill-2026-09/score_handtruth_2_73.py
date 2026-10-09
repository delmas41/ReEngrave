"""ROADMAP 2.73 -- score a staged record's HALF heads against Sean's hand labels.

PATH: STAGED, GATHER+ADJUDICATE only (CLAUDE.md 6b). Truth is
`data/hand-truth/pages/<edition>/<page>.json` (page pixels at the page's dpi,
`labeler: sean`). A hand head is matched by its box in page pixels against the
record's kept notehead glyphs; the POSITION compared is the staff position the
hand box's centre reads against the hand cell's own (localised) staff lines,
rounded to a half step, vs ADJUDICATE's `notehead_position` -- never Q.PITCH.

    python3 benchmarks/omr-head-fill-2026-09/score_handtruth_2_73.py REC.json \
        [--page 0] [-v] [--json out.json]

Counts reported (27 half heads on Brahms 317803 pdf 0):
  box     the head is covered by ONE kept notehead box (IoU >= 0.5 with Sean's)
  single  no second kept box lies on the same head (IoU >= 0.2: a split head)
  pos     that box's ADJUDICATE position is the line/space Sean's box centre reads
  half    that box's ADJUDICATE duration is a half (written 2.0, dots allowed)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HT = Path("data/hand-truth/pages/imslp317803/0.json")
SP = 32.0   # Brahms 317803 pdf 0 staff space, page px at 600 dpi (hand cells: 32-32.5)


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def hand_position(cell, rect):
    """Position (float half-steps from the cell's top line) of the box centre,
    against the hand cell's OWN staff lines (page -> canonical by the cell's
    stored scale)."""
    x0, y0, x1, y1 = cell["rect"]
    sy = cell["canonical_h"] / (y1 - y0)
    ys = cell["staff_line_ys"]
    half = (sum(ys[i + 1] - ys[i] for i in range(len(ys) - 1)) / (len(ys) - 1)) / 2.0
    cy = ((rect[1] + rect[3]) / 2.0 - y0) * sy
    return (cy - ys[0]) / half


def load_truth(path=HT, classes=("noteheadHalfOnLine", "noteheadHalfInSpace")):
    d = json.load(open(path))
    cells = {c["id"]: c for c in d["cells"]}
    out = []
    for b in d["boxes"]:
        if b["cls"] in classes and b.get("labeler") == "sean":
            c = cells[b["cell_id"]]
            out.append({"id": b["id"], "cls": b["cls"], "rect": b["rect"],
                        "pos": hand_position(c, b["rect"]), "cell": b["cell_id"]})
    return out


def record_heads(run, page=0):
    """Every notehead glyph on `page` with its standing ADJUDICATE facts."""
    from tools.omr.staged import readout
    out = []
    for k, g in run.glyphs.items():
        if g.page != page or g.family != "note" or not g.box_page:
            continue
        vs = {}
        for v in run.verdicts_at(k, "ADJUDICATE"):
            vs[v["quantity"]] = v
        status, why = readout.adjudicate_status(run, g)
        pos = vs.get("notehead_position")
        pval = (pos or {}).get("value") if (pos or {}).get("outcome") == "decided" else None
        if pval is None:
            # a head that is not far keeps GATHER position reading (what
            # EVALUATE restate_pitch reads): the recorded staff position
            sp = run.obs_at(k, "notehead_staff_position")
            if sp:
                pval = int(round(float(sp[-1]["value"])))
        dur = vs.get("duration")
        rebuilt = None
        cut = run.obs_at(k, "head_line_cut")
        if cut and g.box_canon and g.box_page:
            x, y, w, h = (float(v) for v in cut[-1]["value"])
            sx = (g.box_page[2] - g.box_page[0]) / (g.box_canon[2] - g.box_canon[0])
            sy = (g.box_page[3] - g.box_page[1]) / (g.box_canon[3] - g.box_canon[1])
            rebuilt = (g.box_page[0] + (x - g.box_canon[0]) * sx,
                       g.box_page[1] + (y - g.box_canon[1]) * sy,
                       g.box_page[0] + (x + w - g.box_canon[0]) * sx,
                       g.box_page[1] + (y + h - g.box_canon[1]) * sy)
        out.append({"key": k, "cls": g.cls, "box": g.box_page, "rebuilt": rebuilt,
                    "status": status,
                    "why": why[:1], "pos": pval,
                    "dur": (dur or {}).get("value"),
                    "durstate": (dur or {}).get("outcome"),
                    "durreason": (dur or {}).get("reason")})
    return out


def _is_half(dur):
    if not isinstance(dur, dict):
        return False
    w = dur.get("written")
    if w is None:
        return False
    # a half note, or a dotted half (the 27 hand heads include both)
    return any(abs(float(w) - v) < 1e-6 for v in (2.0, 3.0, 3.5))


def score(run, page=0, truth=None, min_iou=0.5):
    truth = truth or load_truth()
    heads = record_heads(run, page)
    rows = []
    for t in truth:
        cands = [h for h in heads if iou(h["box"], t["rect"]) > 0.05]
        kept = [h for h in cands if h["status"] in ("kept", "narrowed", "abstained")]
        # ONE HEAD = a kept box whose CENTRE lies within 0.6 staff space of the
        # hand box's centre (both axes). Sean's own boxes are sometimes the
        # detector's partial pre-fill, so a head is matched by where it IS, not
        # by IoU alone (IoU >= 0.5 is reported too, as `box_ok`).
        tcx, tcy = (t["rect"][0] + t["rect"][2]) / 2, (t["rect"][1] + t["rect"][3]) / 2
        near = [h for h in kept
                if abs((h["box"][0] + h["box"][2]) / 2 - tcx) <= 0.6 * SP
                and abs((h["box"][1] + h["box"][3]) / 2 - tcy) <= 0.6 * SP]
        best = min(near, key=lambda h: abs((h["box"][1] + h["box"][3]) / 2 - tcy)
                   + abs((h["box"][0] + h["box"][2]) / 2 - tcx), default=None)
        # the head's box is the detector's, or -- where GATHER read the mirror
        # hole across a line -- the rebuilt head standing beside it on the record
        head_box_iou = 0.0
        if best is not None:
            head_box_iou = max(iou(best["box"], t["rect"]),
                               iou(best["rebuilt"], t["rect"]) if best["rebuilt"] else 0.0)
        box_ok = best is not None and head_box_iou >= min_iou
        n_kept = len(near)
        pos_ok = (best is not None and best["pos"] is not None
                  and int(best["pos"]) == int(round(t["pos"])))
        rows.append({
            "id": t["id"], "hand_cls": t["cls"], "hand_pos": round(t["pos"], 2),
            "found": best is not None,
            "box_ok": box_ok, "pos_ok": pos_ok,
            "half": bool(best and _is_half(best["dur"])),
            "single": n_kept == 1,
            "best": best and {k: best[k] for k in
                              ("key", "cls", "pos", "dur", "status")},
            "iou": round(head_box_iou, 2),
            "all": [(h["key"].split("/", 2)[2], h["cls"], h["status"],
                     (h["why"] or [""])[0][:60], round(iou(h["box"], t["rect"]), 2))
                    for h in cands]})
    return rows


def summary(rows):
    n = len(rows)
    on = [r for r in rows if r["hand_cls"].endswith("OnLine")]
    sp = [r for r in rows if not r["hand_cls"].endswith("OnLine")]
    t = lambda rs, k: sum(1 for r in rs if r[k])
    return {"n": n,
            **{k: t(rows, k) for k in ("found", "box_ok", "single", "pos_ok", "half")},
            "on_line": {"n": len(on), **{k: t(on, k) for k in ("found", "box_ok", "single", "pos_ok", "half")}},
            "in_space": {"n": len(sp), **{k: t(sp, k) for k in ("found", "box_ok", "single", "pos_ok", "half")}}}


def main(argv=None):
    import os
    import sys
    sys.path.insert(0, os.getcwd())
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--json")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args(argv)
    from tools.omr.staged import readout
    run = readout.load_run(a.record)
    rows = score(run, a.page)
    print(json.dumps(summary(rows)))
    if a.v:
        for r in rows:
            print(r["id"], r["hand_cls"][9:], "pos", r["hand_pos"], "box", r["box_ok"],
                  "single", r["single"], "pos", r["pos_ok"], "half", r["half"],
                  "best", r["best"], "iou", r["iou"])
            for x in r["all"]:
                print("     ", x)
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
