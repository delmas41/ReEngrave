"""2.171 probe 2 (GATHER-only, writes NOTHING to a record): run the PRODUCTION detector on the subject bars under controlled one-variable changes.

The production feed, read from the code (not assumed):
  _build_measure_cell: page crop [staff.top - 4 sp .. staff.bottom + 4 sp (6 sp where the neighbour allows)] x [barline .. barline],
      upscaled so the staff span is 400 px (canonical staff space ~100 px; cubic), a MeasureCell.
  YoloDetector.detect: imgsz = imgsz_for_cell = round32(16 * long_side / canonical_space) (so the model is shown a ~16 px staff space),
      ultralytics predict: LetterBox(auto, centred, fill 114, bilinear resize by imgsz/long_side), conf floor, iou 0.7, agnostic NMS off.
This probe re-implements ONLY the letterbox (so scale, canvas, fill, interpolation and placement can be set one at a time) and feeds
the shipped model a ready-made array whose sides are multiples of 32 (ratio 1.0 inside ultralytics, no second resize).

Conditions (bar level; r_prod = the bar's own production ratio imgsz/long_side):
  prod        bar cell, r_prod, bilinear, centred, fill 114                      (control: must reproduce the record's conf)
  sc0.5 .. sc2.0   SCALE only: ratio r_prod * f, same crop
  wide        CONTEXT: half a bar added each side, SAME r_prod (so the symbol is the same size in pixels)
  wide_rule   the wide crop under the production rule (imgsz_for_cell on the wide cell) = what 2.167d ran
  triple      one bar added each side, r_prod;   system  the whole staff strip, r_prod (imgsz uncapped here)
  L1gray      LETTERBOX/ASPECT: the bar crop alone on a canvas of the wide crop's shape, fill 114 (letterbox grey)
  L2white     the same canvas, fill 255 (white page)
  L3whitepad  the bar crop with the stride padding white instead of grey (fill only, same shape as prod)
  area        INTERPOLATION only: prod but cv2.INTER_AREA downscale;  wide_area: wide with INTER_AREA
  phx1..6 / phy2,4,6   SAMPLING PHASE only: the bar crop's left/top edge moved 1..6 canonical px (0.16 .. 1 net px), nothing else
Subject level (the symbol is at the stated place in a white canvas twice the bar's width, bar crop unchanged otherwise):
  pos_c (centre), pos_l (1.5 sp from the left edge), pos_r (1.5 sp from the right edge), pos_c8 / pos_c16 / pos_c24 (centre + 8/16/24 net px)
usage: e2_run.py lit|bra OUT.json [first_n_bars]"""
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.preprocessing import render_page            # noqa: E402
from tools.omr.staff_detector import detect_staves          # noqa: E402
from tools.omr.measure_extractor import extract_measures, _build_measure_cell   # noqa: E402
from tools.omr.staged.gather import _system_local          # noqa: E402
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell   # noqa: E402

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
              "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
WEIGHTS = str(ROOT / "tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")
FLOOR = 0.05
STRIDE = 32

plate, out = sys.argv[1], sys.argv[2]
nmax = int(sys.argv[3]) if len(sys.argv) > 3 else None
SUB = json.load(open(str(ROOT) + "/probe/2.171/data/subjects.json"))[plate]["subjects"]
sample = [tuple(s) for s in json.load(open(str(ROOT) + "/probe/2.167d/data/%s_sample.json" % plate))]
by_key = {}
for i, s in enumerate(SUB):
    by_key.setdefault(s["key"], []).append(i)
keys = [("%d/%d/%d/%d" % s) for s in sample if ("%d/%d/%d/%d" % s) in by_key]
if nmax:
    keys = keys[:nmax]
det = YoloDetector(WEIGHTS)
det._ensure_loaded()
model = det._model
names = det._class_names
dev = det.device if det.device != "auto" else None


def ceil32(v):
    return int(math.ceil(v / STRIDE) * STRIDE)


def fam(cls):
    if cls == "augmentationDot":
        return "dot"
    if cls.startswith("flag"):
        return "flag"
    if cls.startswith("rest"):
        return "rest"
    if cls in ("noteheadBlackOnLine", "noteheadBlackInSpace"):
        return "blackhead"
    if cls.startswith("notehead"):
        return "otherhead"
    return "other"


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def net_run(img, r, interp=cv2.INTER_LINEAR, canvas_hw=None, fill=114, anchor=None, off=(0, 0)):
    """Resize `img` (canonical cell image) by ratio r, place it on a canvas (default: production-like centred stride-padded), run the model.
    Returns boxes (cls, conf, x0, y0, x1, y1) in the canonical image's own pixel frame (+off), plus the geometry used."""
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    h, w = img.shape[:2]
    nw, nh = int(round(w * r)), int(round(h * r))
    small = cv2.resize(img, (nw, nh), interpolation=interp) if (nw, nh) != (w, h) else img
    if canvas_hw is None:
        Hc, Wc = ceil32(nh), ceil32(nw)
    else:
        Hc, Wc = canvas_hw
    if anchor is None:
        left = int(round((Wc - nw) / 2 - 0.1))
        top = int(round((Hc - nh) / 2 - 0.1))
    else:
        left, top = anchor
    canvas = np.full((Hc, Wc, 3), fill, np.uint8)
    sx0, sy0 = max(0, -left), max(0, -top)
    dx0, dy0 = max(0, left), max(0, top)
    cw = min(nw - sx0, Wc - dx0)
    ch = min(nh - sy0, Hc - dy0)
    if cw > 0 and ch > 0:
        canvas[dy0:dy0 + ch, dx0:dx0 + cw] = small[sy0:sy0 + ch, sx0:sx0 + cw]
    res = model.predict(source=canvas, conf=FLOOR, iou=0.7, imgsz=max(Hc, Wc), device=dev, verbose=False)
    rows = []
    if res and getattr(res[0], "boxes", None) is not None and len(res[0].boxes):
        b = res[0].boxes
        xyxy = b.xyxy.cpu().numpy()
        cf = b.conf.cpu().numpy()
        cl = b.cls.cpu().numpy()
        rx, ry = nw / w, nh / h
        for (x0, y0, x1, y1), c, k in zip(xyxy, cf, cl):
            rows.append((names.get(int(k), str(int(k))), float(c), (x0 - left) / rx + off[0], (y0 - top) / ry + off[1],
                         (x1 - left) / rx + off[0], (y1 - top) / ry + off[1]))
    return rows, dict(canvas=(Hc, Wc), small=(nh, nw), left=left, top=top, r=r)


def to_page(cell, rows):
    x0, y0 = cell.bbox_page_px[0], cell.bbox_page_px[1]
    up = cell.upscale_factor
    return [[c, round(cf, 4), round(x0 + a / up, 1), round(y0 + b / up, 1), round(x0 + d / up, 1), round(y0 + e / up, 1)] for c, cf, a, b, d, e in rows]


def space_shown(cell, r, staff_sp_page):
    return round(staff_sp_page * cell.upscale_factor * r, 2)


def score(boxes, S, sp, top, bot):
    """The detector's top box over subject S: best any-class (IoU > 0.3) and best wanted-family box. [cls, conf, iou] or None."""
    bb = S["bbox"]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    anyb = wantb = None
    for b in boxes:
        box = b[2:6]
        if S["region"]:
            bx, by = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            ok = abs(bx - cx) < 0.9 * sp and top - 1.5 * sp <= by <= bot + 1.5 * sp
            ov = 1.0 if ok else 0.0
        else:
            ov = iou(bb, box)
            ok = ov > 0.3
        if not ok:
            continue
        if anyb is None or b[1] > anyb[1]:
            anyb = [b[0], b[1], round(ov, 2)]
        if fam(b[0]) == S["want"] and (wantb is None or b[1] > wantb[1]):
            wantb = [b[0], b[1], round(ov, 2)]
    return dict(any=anyb, want=wantb)


res = {}
t0 = time.time()
pages = sorted({int(k.split("/")[0]) for k in keys})
for p in pages:
    pws = detect_staves(render_page(PDF[plate], p, dpi=600))
    cells = extract_measures(pws)
    local = _system_local(pws.staves)
    by_staff = {s.staff_index: s for s in pws.staves}
    cell_of = {}
    for c in cells:
        k = local.get(c.staff_index)
        if k:
            cell_of[(k[0], k[1], c.measure_index)] = c
    for key in [k for k in keys if int(k.split("/")[0]) == p]:
        _, s, st, ci = [int(v) for v in key.split("/")]
        c = cell_of.get((s, st, ci))
        if c is None:
            res[key] = dict(error="no cell")
            continue
        staff = by_staff[c.staff_index]
        sp = staff.line_spacing_px
        x0, y0, x1, y1 = c.bbox_page_px
        w = x1 - x0
        top, bot = float(staff.line_ys[0]), float(staff.line_ys[4])
        img = c.image
        h_can, w_can = img.shape[:2]
        imgsz = imgsz_for_cell(c)
        r0 = imgsz / max(h_can, w_can)
        conds = {}
        meta = dict(cell=[x0, y0, x1, y1], spacing=sp, lines=[top, bot], imgsz=imgsz, r0=r0, up=c.upscale_factor,
                    space_shown=space_shown(c, r0, sp), shape=[h_can, w_can])

        def cell_x(a, b):
            return _build_measure_cell(pws, staff, s, int(a), int(b), ci, max_cell_width=100000)

        def keep(name, rows, cell, geo=None):
            conds[name] = dict(boxes=to_page(cell, rows), geo=geo)

        rows, geo = net_run(img, r0)
        keep("prod", rows, c, geo)
        k0 = c.upscale_factor * r0          # net px per PAGE px: the thing that fixes the symbol's size

        def rr(cell_x_):
            return k0 / cell_x_.upscale_factor     # same symbol pixel size in a cell that may have a different canonical upscale
        for f in (0.5, 0.7, 0.85, 1.2, 1.4, 2.0):
            rows, geo = net_run(img, r0 * f)
            geo["space"] = space_shown(c, r0 * f, sp)
            keep("sc%.2f" % f if f in (0.85, 1.2) else "sc%.1f" % f, rows, c, geo)
        cw = cell_x(x0 - w / 2, x1 + w / 2)
        c3 = cell_x(x0 - w, x1 + w)
        csys = cell_x(staff.x_start, staff.x_end)
        if cw is not None:
            rows, geo = net_run(cw.image, rr(cw))
            keep("wide", rows, cw, geo)
            rows, geo = net_run(cw.image, imgsz_for_cell(cw) / max(cw.image.shape[:2]))
            keep("wide_rule", rows, cw, geo)
            rows, geo = net_run(cw.image, rr(cw), interp=cv2.INTER_AREA)
            keep("wide_area", rows, cw, geo)
            # canvas of the wide crop's shape at ratio r0
            Hc = ceil32(int(round(cw.image.shape[0] * rr(cw))))
            Wc = ceil32(int(round(cw.image.shape[1] * rr(cw))))
            nw_bar = int(round(w_can * r0))
            ax = int(round((Wc - nw_bar) / 2))
            rows, geo = net_run(img, r0, canvas_hw=(Hc, Wc), fill=114, anchor=(ax, int(round((Hc - int(round(h_can * r0))) / 2))))
            keep("L1gray", rows, c, geo)
            rows, geo = net_run(img, r0, canvas_hw=(Hc, Wc), fill=255, anchor=(ax, int(round((Hc - int(round(h_can * r0))) / 2))))
            keep("L2white", rows, c, geo)
        if c3 is not None:
            rows, geo = net_run(c3.image, rr(c3))
            keep("triple", rows, c3, geo)
        if csys is not None:
            rows, geo = net_run(csys.image, rr(csys))
            keep("system", rows, csys, geo)
        # INK CONTEXT, what kind: (mirror) the bar's own ink reflected into the side areas; (foreign) the side areas filled with ink from other bars of the
        # same staff (3 bars away), so "music-like ink is around" is kept and "the true neighbours are around" is broken.
        pad = int(w_can // 2)
        if 0 < pad < w_can:
            im3 = cv2.copyMakeBorder(img if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR), 0, 0, pad, pad, cv2.BORDER_REFLECT_101)
            rows, geo = net_run(im3, r0, off=(-pad, 0))
            keep("mirror", rows, c, geo)
            fill_l = fill_r = None
            for dl in (3, 4, 2, 5):
                oc = cell_of.get((s, st, ci - dl))
                if oc is not None and abs(oc.upscale_factor - c.upscale_factor) < 1e-6 and oc.image.shape[1] >= pad:
                    fill_l = oc
                    break
            for dl in (3, 4, 2, 5):
                oc = cell_of.get((s, st, ci + dl))
                if oc is not None and abs(oc.upscale_factor - c.upscale_factor) < 1e-6 and oc.image.shape[1] >= pad:
                    fill_r = oc
                    break
            if fill_l is not None and fill_r is not None:
                def vfit(oc):
                    # align the filler's top staff line with this bar's, so the staff stays one straight staff across the seams
                    a = oc.image if oc.image.ndim == 3 else cv2.cvtColor(oc.image, cv2.COLOR_GRAY2BGR)
                    dy = int(round(c.staff_line_ys_canonical[0] - oc.staff_line_ys_canonical[0]))
                    z = np.full((h_can, a.shape[1], 3), 255, np.uint8)
                    ys0, yd0 = max(0, -dy), max(0, dy)
                    hh = min(a.shape[0] - ys0, h_can - yd0)
                    if hh > 0:
                        z[yd0:yd0 + hh] = a[ys0:ys0 + hh]
                    return z
                im4 = np.concatenate([vfit(fill_l)[:, -pad:], img if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR), vfit(fill_r)[:, :pad]], axis=1)
                rows, geo = net_run(im4, r0, off=(-pad, 0))
                keep("foreign", rows, c, geo)
        rows, geo = net_run(img, r0, fill=255)
        keep("L3whitepad", rows, c, geo)
        nh0, nw0 = int(round(h_can * r0)), int(round(w_can * r0))
        for tag, mx, my, fill in (("mw32", 32, 0, 255), ("mw64", 64, 0, 255), ("mw128", 128, 0, 255), ("mw256", 256, 0, 255),
                                  ("mg128", 128, 0, 114), ("mv64", 0, 64, 255), ("mwv128", 128, 128, 255)):
            Hc_, Wc_ = ceil32(nh0 + 2 * my), ceil32(nw0 + 2 * mx)
            rows, geo = net_run(img, r0, canvas_hw=(Hc_, Wc_), fill=fill, anchor=((Wc_ - nw0) // 2, (Hc_ - nh0) // 2))
            keep(tag, rows, c, geo)
        rows, geo = net_run(img, r0, interp=cv2.INTER_AREA)
        keep("area", rows, c, geo)
        for k in range(1, 7):
            rows, geo = net_run(img[:, k:], r0, off=(k, 0))
            keep("phx%d" % k, rows, c, geo)
        for k in (2, 4, 6):
            rows, geo = net_run(img[k:, :], r0, off=(0, k))
            keep("phy%d" % k, rows, c, geo)
        # ---- subject level
        subj = {}
        for i in by_key[key]:
            S = SUB[i]
            sc = {}
            for name, v in conds.items():
                sc[name] = score(v["boxes"], S, sp, top, bot)
            # position runs
            bb = S["bbox"]
            xs_can = ((bb[0] + bb[2]) / 2 - x0) * c.upscale_factor
            xs_net = xs_can * r0
            Sp = space_shown(c, r0, sp)
            nh = int(round(h_can * r0))
            Hc = ceil32(nh)
            Wc = ceil32(2 * int(round(w_can * r0)))
            top_a = int(round((Hc - nh) / 2 - 0.1))
            for tag, left in (("pos_c", Wc / 2 - xs_net), ("pos_l", 1.5 * Sp - xs_net), ("pos_r", Wc - 1.5 * Sp - xs_net),
                              ("pos_c8", Wc / 2 - xs_net + 8), ("pos_c16", Wc / 2 - xs_net + 16), ("pos_c24", Wc / 2 - xs_net + 24)):
                rows, geo = net_run(img, r0, canvas_hw=(Hc, Wc), fill=255, anchor=(int(round(left)), top_a))
                sc[tag] = score(to_page(c, rows), S, sp, top, bot)
                sc[tag]["x_net"] = round(left + xs_net, 1)
            subj[str(i)] = sc
        res[key] = dict(meta=meta, conds=conds, subj=subj)
    print("page", p, "done", round(time.time() - t0), "s", flush=True)
json.dump(res, open(out, "w"), default=float)
print("wrote", out, len(res), flush=True)
