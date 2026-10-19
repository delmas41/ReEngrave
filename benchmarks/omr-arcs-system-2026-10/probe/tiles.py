"""ROADMAP 2.166 -- blind tiles for Sean into out/print/2.166-review/ (at most 25), the key apart in out/2.166/tiles-key.json.

Two kinds, nothing else of ours drawn:
  ARC  -- the traced line drawn thin in blue along the stroke, its two ends as two blue dots.
          "Is the blue line one tie, one slur, or something else? Which two notes does it join?"
  HEAD -- one blue box around a notehead box the erase came near (within half a space of erased ink).
          "Is the mark in the blue box a note, or not a note?"
Picks (seed 2166): ARC tiles from arcs read differently from the per-bar reading (joined across a barline, or run past
their boxes through a head/beam box that holds only the stroke); HEAD tiles from head boxes that lost ink or sit
beside erased ink; 2 CONTROLS (one arc read whole inside one bar, anchored at one position; one head touched by an
arc and kept whole).
usage: tiles.py DOC:PAGE ...
"""
import json
import random
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-arcs-system-2026-10/probe")
import numpy as np  # noqa: E402

import arc_debug  # noqa: E402
from tools.omr.staged import arcs_system as AS  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402

OUT = "out/print/2.166-review"
KEY = "out/2.166/tiles-key.json"
BLUE = (235, 111, 31)          # #1F6FEB in BGR
SCALE = 3
N_ARC, N_HEAD = 12, 11

rng = random.Random(2166)
# glyphs Sean has already answered (the judged index, and 2.164's tiles, not yet on main) are never asked again
SEEN = set()
for _t in json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]:
    for _g in [_t.get("subject")] + list(_t.get("subjects") or []):
        if _g:
            SEEN.add(str(_g))
try:
    SEEN |= {_t.get("glyph") for _t in json.load(open("out/2.166/key164.json")).get("tiles", [])}
except (OSError, ValueError):
    pass
cands_arc, cands_head, ctl_arc, ctl_head = [], [], [], []
pages = {}
for dp in sys.argv[1:]:
    doc, pg = dp.split(":")
    pg = int(pg)
    pws, cells, local, dets, log, summary, traces = arc_debug.run(doc, pg)
    gray = pws.page.binary
    rgb = getattr(pws.page, "rgb", None)
    if rgb is not None:
        import cv2
        gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY) if rgb.ndim == 3 else rgb
    pages[(doc, pg)] = gray
    # erased ink, page px
    er = np.zeros(gray.shape, bool)
    for c in cells:
        o = getattr(c, "image_no_staff_with_arcs", None)
        if o is None:
            continue
        ys, xs = np.nonzero((o < 128) & ~(c.image_no_staff < 128))
        up = float(c.upscale_factor)
        px = np.clip((c.bbox_page_px[0] + xs / up).astype(int), 0, gray.shape[1] - 1)
        py = np.clip((c.bbox_page_px[1] + ys / up).astype(int), 0, gray.shape[0] - 1)
        er[py, px] = True
    # trace points per arc subject: re-merge the traces of each arc's pieces
    by_piece = {}
    for t in traces:
        by_piece.setdefault(tuple(int(v) for v in t["box"]), t)
    box_of = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        for gi, d in enumerate(dets.get(sub.to_key(), ())):
            box_of[R.glyph(c.page_index, key[0], key[1], c.measure_index, gi).to_key()] = (d.smufl_name,
                                                                                         AS._page_box(c, d))
    for a in summary["arcs_detail"]:
        pts = {}
        for p in a["pieces"]:
            t = by_piece.get(tuple(int(v) for v in box_of[p][1]))
            if t:
                for x, r in t["points"].items():
                    pts.setdefault(x, r)
        item = dict(doc=doc, page=pg, kind="arc", subject=a["subject"], shape=a["shape"], cells=a["cells"],
                    pieces=a["pieces"], anchors=[a["anchor_left"], a["anchor_right"]], sp=a["space_page_px"],
                    pts=pts, stroke_only=[t["glyph"] for t in a["through_boxes"] if t["stroke_only"]])
        if a["subject"] in SEEN or any(g in SEEN for g in item["stroke_only"]):
            continue
        if len(a["cells"]) > 1 or item["stroke_only"]:
            cands_arc.append(item)
        elif a["shape"] == "two_heads_one_position_adjacent" and not a["cut_at_barline"]:
            ctl_arc.append(item)
    # heads near erased ink
    for g, (name, b) in box_of.items():
        if not str(name).startswith("notehead"):
            continue
        sp = 15.0
        for a in summary["arcs_detail"]:
            sp = a["space_page_px"]
            break
        m = int(round(0.5 * sp))
        x0, y0, x1, y1 = (int(round(v)) for v in b)
        near = int(er[max(0, y0 - m):y1 + m, max(0, x0 - m):x1 + m].sum())
        inside = int(er[max(0, y0):y1, max(0, x0):x1].sum())
        if near == 0 or g in SEEN:
            continue
        item = dict(doc=doc, page=pg, kind="head", subject=g, cls=name, box=[x0, y0, x1, y1], sp=sp,
                    erased_inside=inside, erased_near=near, stroke_only=g in summary["stroke_only_heads"])
        if inside > 0 or item["stroke_only"]:
            cands_head.append(item)
        else:
            ctl_head.append(item)
    print(dp, "arcs", len(summary["arcs_detail"]), "cand arc", len(cands_arc), "cand head", len(cands_head), flush=True)


def pick(items, n):
    by_doc = {}
    for it in items:
        by_doc.setdefault(it["doc"], []).append(it)
    out = []
    docs = sorted(by_doc)
    for d in docs:
        rng.shuffle(by_doc[d])
    i = 0
    while len(out) < n and any(by_doc.values()):
        d = docs[i % len(docs)]
        if by_doc[d]:
            out.append(by_doc[d].pop())
        i += 1
    return out


chosen = [dict(it, role="arc") for it in pick(cands_arc, N_ARC)]
chosen += [dict(it, role="head") for it in pick(cands_head, N_HEAD)]
if ctl_arc:
    chosen.append(dict(rng.choice(ctl_arc), role="control_arc"))
if ctl_head:
    chosen.append(dict(rng.choice(ctl_head), role="control_head"))
rng.shuffle(chosen)

import cv2  # noqa: E402
import os  # noqa: E402
os.makedirs(OUT, exist_ok=True)
key, manifest = [], []
for n, it in enumerate(chosen, 1):
    gray = pages[(it["doc"], it["page"])]
    sp = it["sp"]
    if it["kind"] == "arc":
        xs = sorted(it["pts"])
        ys = [v for r in it["pts"].values() for v in r]
        bx0, bx1, by0, by1 = xs[0], xs[-1], min(ys), max(ys)
    else:
        bx0, by0, bx1, by1 = it["box"]
    X0 = int(max(0, bx0 - 4 * sp))
    X1 = int(min(gray.shape[1], bx1 + 4 * sp))
    Y0 = int(max(0, by0 - 5 * sp))
    Y1 = int(min(gray.shape[0], by1 + 5 * sp))
    crop = cv2.cvtColor(gray[Y0:Y1, X0:X1], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_NEAREST)
    if it["kind"] == "arc":
        line = [((x - X0) * SCALE + SCALE // 2, int(((r[0] + r[1]) / 2.0 - Y0) * SCALE)) for x, r in sorted(it["pts"].items())]
        for (xa, ya), (xb, yb) in zip(line, line[1:]):
            if xb - xa <= 3 * SCALE:
                cv2.line(crop, (xa, ya), (xb, yb), BLUE, 1)
        for p in (line[0], line[-1]):
            cv2.circle(crop, p, 5, BLUE, -1)
        q = "Is the blue line one tie, one slur, or something else? Which two notes does it join?"
    else:
        x0, y0, x1, y1 = it["box"]
        cv2.rectangle(crop, ((x0 - X0) * SCALE - 2, (y0 - Y0) * SCALE - 2), ((x1 - X0) * SCALE + 2, (y1 - Y0) * SCALE + 2),
                      BLUE, 2)
        q = "Is the mark in the blue box a note, or not a note?"
    cv2.putText(crop, "Tile %d" % n, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    f = "tile_%02d.png" % n
    cv2.imwrite(os.path.join(OUT, f), crop)
    manifest.append(dict(n=n, file=f, question=q))
    k = {kk: vv for kk, vv in it.items() if kk != "pts"}
    k.update(n=n, file=f, page_crop=[X0, Y0, X1, Y1])
    key.append(k)
json.dump(dict(colours="blue line + two blue dots = the curve we read and its two ends; blue box = the mark we ask "
                       "about. Nothing else on the tile is ours.", tiles=manifest),
          open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
if not os.path.exists(os.path.join(OUT, "answers.json")):
    json.dump({}, open(os.path.join(OUT, "answers.json"), "w"))
json.dump(dict(seed=2166, tiles=key), open(KEY, "w"), indent=1, default=str)
print("tiles", len(chosen), "arc", sum(1 for c in chosen if c["kind"] == "arc"),
      "head", sum(1 for c in chosen if c["kind"] == "head"))
