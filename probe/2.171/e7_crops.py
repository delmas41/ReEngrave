"""2.171 probe 7: the crops for Sean. Each crop = ONE symbol shown to the detector under 3 conditions, side by side, as the detector's own input pixels
(the letterboxed array handed to the model, cut to a window around the symbol, enlarged x4 with no smoothing), with the detector's top box and its confidence.
Picks the symbols from the e2 run files by rule (listed in index.json), re-runs ONLY those conditions (one detector process), and checks each printed conf
against the e2 run's number (must agree to 0.001; a crop whose conf is not the experiment's is not drawn).
usage: e7_crops.py"""
import json
import math
import sys
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
OUT = ROOT / "out/print/2.171"
OUT.mkdir(parents=True, exist_ok=True)
D = ROOT / "probe/2.171/data/"
STRIDE = 32
ZOOM = 4
HALF = 56          # net px each side of the symbol: a 112 x 112 net-pixel window shown at x4


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
    return "other"


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def conf(sc, cond):
    v = sc.get(cond)
    return v["want"][1] if v and v.get("want") else 0.0


RUN = {p: json.load(open(D / ("%s_run.json" % p))) for p in ("lit", "bra")}
SUB = {p: json.load(open(D / "subjects.json"))[p]["subjects"] for p in ("lit", "bra")}


def all_subj(plate):
    for key, r in RUN[plate].items():
        for i, sc in r.get("subj", {}).items():
            yield key, int(i), SUB[plate][int(i)], sc


def pick(plate, role, want, test, order, skip=(), ok=None):
    best = None
    for key, i, S, sc in all_subj(plate):
        if (plate, key, i) in skip:
            continue
        if S["role"] == role and (want is None or S["want"] == want) and test(sc) and (ok is None or ok(key, S)):
            v = order(sc)
            if best is None or v > best[0]:
                best = (v, key, i)
    return best


# (title, plate, subject picker, conditions drawn)
used = set()
CHOICES = []


def choose(title, plate, role, want, test, order, conds, ok=None):
    b = pick(plate, role, want, test, order, used, ok)
    if b is None:
        print("no symbol for", title)
        return
    used.add((plate, b[1], b[2]))
    CHOICES.append(dict(title=title, plate=plate, key=b[1], idx=b[2], conds=conds))


choose("A Brahms dot lost under the floor, found in a wider crop", "bra", "lost", "dot", lambda sc: conf(sc, "prod") < 0.2 and conf(sc, "wide") >= 0.4,
       lambda sc: conf(sc, "wide") - conf(sc, "prod"), ["prod", "wide", "sc0.70"])
choose("B Brahms flag lost under the floor, found when SMALLER", "bra", "lost", "flag", lambda sc: conf(sc, "prod") < 0.2 and conf(sc, "sc0.5") >= 0.5,
       lambda sc: conf(sc, "sc0.5") - conf(sc, "prod"), ["prod", "sc0.50", "wide"])
choose("C Brahms dot READ WELL, then made smaller / wider", "bra", "kept", "dot", lambda sc: conf(sc, "prod") >= 0.6,
       lambda sc: conf(sc, "prod") - conf(sc, "sc0.5"), ["prod", "sc0.50", "wide"],
       ok=lambda key, S: RUN["bra"][key]["meta"]["lines"][0] <= (S["bbox"][1] + S["bbox"][3]) / 2 <= RUN["bra"][key]["meta"]["lines"][1])
choose("D Litolff black head lost (welded to the line), found when LARGER", "lit", "lost", "blackhead", lambda sc: conf(sc, "prod") < 0.2 and conf(sc, "sc1.4") >= 0.4,
       lambda sc: conf(sc, "sc1.4") - conf(sc, "prod"), ["prod", "sc1.40", "wide"])
choose("E Litolff rest lost, found when SMALLER, not in a wider crop", "lit", "lost", "rest", lambda sc: conf(sc, "prod") < 0.2 and conf(sc, "sc0.7") >= 0.3 and conf(sc, "wide") < 0.25,
       lambda sc: conf(sc, "sc0.7") - conf(sc, "wide"), ["prod", "sc0.70", "wide"])
choose("F Brahms symbol lost, found by the neighbours' ink (own ink mirrored does it too, white canvas does not)", "bra", "lost", None,
       lambda sc: conf(sc, "prod") < 0.25 and conf(sc, "wide") >= 0.3 and conf(sc, "mirror") >= 0.3 and conf(sc, "L2white") < 0.25,
       lambda sc: conf(sc, "wide") + conf(sc, "mirror") - conf(sc, "L2white"), ["prod", "L2white", "wide"])
print([(c["title"][:30], c["key"], c["idx"]) for c in CHOICES])

det = YoloDetector(WEIGHTS)
det._ensure_loaded()
model, names = det._model, det._class_names
dev = det.device if det.device != "auto" else None


def build(cond, c, cell_of, pws, staff, s, ci, x0, x1, w, r0):
    """-> (img, r, interp, canvas_hw, fill, anchor, shift) for a condition, identical to e2_run's."""
    img = c.image
    h_can, w_can = img.shape[:2]
    k0 = c.upscale_factor * r0
    if cond == "prod":
        return img, r0, cv2.INTER_LINEAR, None, 114, None, c
    if cond.startswith("sc"):
        return img, r0 * float(cond[2:]), cv2.INTER_LINEAR, None, 114, None, c
    if cond in ("wide", "L2white"):
        cw = _build_measure_cell(pws, staff, s, int(x0 - w / 2), int(x1 + w / 2), ci, max_cell_width=100000)
        rw = k0 / cw.upscale_factor
        if cond == "wide":
            return cw.image, rw, cv2.INTER_LINEAR, None, 114, None, cw
        Hc = ceil32(int(round(cw.image.shape[0] * rw)))
        Wc = ceil32(int(round(cw.image.shape[1] * rw)))
        nw_bar = int(round(w_can * r0))
        ax = int(round((Wc - nw_bar) / 2))
        return img, r0, cv2.INTER_LINEAR, (Hc, Wc), 255, (ax, int(round((Hc - int(round(h_can * r0))) / 2))), c
    if cond == "wide_rule":
        cw = _build_measure_cell(pws, staff, s, int(x0 - w / 2), int(x1 + w / 2), ci, max_cell_width=100000)
        return cw.image, imgsz_for_cell(cw) / max(cw.image.shape[:2]), cv2.INTER_LINEAR, None, 114, None, cw
    raise ValueError(cond)


def render(img, r, interp, canvas_hw, fill, anchor):
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    h, w = img.shape[:2]
    nw, nh = int(round(w * r)), int(round(h * r))
    small = cv2.resize(img, (nw, nh), interpolation=interp) if (nw, nh) != (w, h) else img
    Hc, Wc = (ceil32(nh), ceil32(nw)) if canvas_hw is None else canvas_hw
    if anchor is None:
        left = int(round((Wc - nw) / 2 - 0.1))
        top = int(round((Hc - nh) / 2 - 0.1))
    else:
        left, top = anchor
    canvas = np.full((Hc, Wc, 3), fill, np.uint8)
    sx0, sy0 = max(0, -left), max(0, -top)
    dx0, dy0 = max(0, left), max(0, top)
    cw_ = min(nw - sx0, Wc - dx0)
    ch_ = min(nh - sy0, Hc - dy0)
    if cw_ > 0 and ch_ > 0:
        canvas[dy0:dy0 + ch_, dx0:dx0 + cw_] = small[sy0:sy0 + ch_, sx0:sx0 + cw_]
    return canvas, dict(rx=nw / w, ry=nh / h, left=left, top=top)


def label(img, text, org, color=(0, 0, 0), scale=0.5, thick=1):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


DESC = {"prod": "production bar crop", "wide": "wider crop, same pixel size", "sc0.70": "bar crop, 0.7 x smaller",
        "sc0.50": "bar crop, 0.5 x smaller", "sc1.40": "bar crop, 1.4 x larger", "L2white": "bar on wide WHITE canvas"}
cache = {}
index = []
for ch in CHOICES:
    plate, key, idx = ch["plate"], ch["key"], ch["idx"]
    S = SUB[plate][idx]
    p, s, st, ci = [int(v) for v in key.split("/")]
    if (plate, p) not in cache:
        pws = detect_staves(render_page(PDF[plate], p, dpi=600))
        cells = extract_measures(pws)
        local = _system_local(pws.staves)
        by_staff = {q.staff_index: q for q in pws.staves}
        cell_of = {}
        for c_ in cells:
            k = local.get(c_.staff_index)
            if k:
                cell_of[(k[0], k[1], c_.measure_index)] = c_
        cache = {(plate, p): (pws, by_staff, cell_of)}
    pws, by_staff, cell_of = cache[(plate, p)]
    c = cell_of[(s, st, ci)]
    staff = by_staff[c.staff_index]
    x0, y0, x1, y1 = c.bbox_page_px
    w = x1 - x0
    imgsz = imgsz_for_cell(c)
    r0 = imgsz / max(c.image.shape[:2])
    frames = []
    for cond in ch["conds"]:
        img, r, interp, hw, fill, anchor, cu = build(cond, c, cell_of, pws, staff, s, ci, x0, x1, w, r0)
        canvas, g = render(img, r, interp, hw, fill, anchor)
        res = model.predict(source=canvas, conf=0.05, iou=0.7, imgsz=max(canvas.shape[:2]), device=dev, verbose=False)
        boxes = []
        if res and res[0].boxes is not None and len(res[0].boxes):
            b = res[0].boxes
            for (a0, b0, a1, b1), cf, cl in zip(b.xyxy.cpu().numpy(), b.conf.cpu().numpy(), b.cls.cpu().numpy()):
                boxes.append((names.get(int(cl), "?"), float(cf), [a0, b0, a1, b1]))
        # symbol box (page px) -> canvas px
        bb = S["bbox"]

        def to_canvas(px, py):
            xc = (px - cu.bbox_page_px[0]) * cu.upscale_factor
            yc = (py - cu.bbox_page_px[1]) * cu.upscale_factor
            return xc * g["rx"] + g["left"], yc * g["ry"] + g["top"]
        sx0, sy0 = to_canvas(bb[0], bb[1])
        sx1, sy1 = to_canvas(bb[2], bb[3])
        symbox = [sx0, sy0, sx1, sy1]
        # the detector's top box over it: best conf among any class with IoU > 0.3 (A items: none)
        sp_c = staff.line_spacing_px * cu.upscale_factor * g["rx"]          # staff space in canvas px
        ytop = (staff.line_ys[0] - cu.bbox_page_px[1]) * cu.upscale_factor * g["ry"] + g["top"]
        ybot = (staff.line_ys[4] - cu.bbox_page_px[1]) * cu.upscale_factor * g["ry"] + g["top"]

        def over(bx):
            if S["region"]:        # a symbol with no box at all: the box centre within 0.9 sp of its x and inside the staff band (as in e2_run.score)
                return abs((bx[0] + bx[2]) / 2 - cx0) < 0.9 * sp_c and ytop - 1.5 * sp_c <= (bx[1] + bx[3]) / 2 <= ybot + 1.5 * sp_c
            return iou(symbox, bx) > 0.3
        cx0 = (sx0 + sx1) / 2
        top = None
        for cls, cf, bx in boxes:
            if over(bx) and (top is None or cf > top[1]):
                top = (cls, cf, bx)
        wantb = None
        for cls, cf, bx in boxes:
            if over(bx) and fam(cls) == S["want"] and (wantb is None or cf > wantb[1]):
                wantb = (cls, cf, bx)
        # agreement with the experiment's number
        e2 = conf(RUN[plate][key]["subj"][str(idx)], {"sc0.50": "sc0.5", "sc0.70": "sc0.7", "sc1.40": "sc1.4"}.get(cond, cond))
        got = wantb[1] if wantb else 0.0
        ok = abs(got - e2) < 0.01
        # draw
        cx, cy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
        x_a, y_a = int(round(cx - HALF)), int(round(cy - HALF))
        win = np.full((2 * HALF, 2 * HALF, 3), 160, np.uint8)
        ax0, ay0 = max(0, x_a), max(0, y_a)
        ax1, ay1 = min(canvas.shape[1], x_a + 2 * HALF), min(canvas.shape[0], y_a + 2 * HALF)
        if ax1 > ax0 and ay1 > ay0:
            win[ay0 - y_a:ay1 - y_a, ax0 - x_a:ax1 - x_a] = canvas[ay0:ay1, ax0:ax1]
        big = cv2.resize(win, None, fx=ZOOM, fy=ZOOM, interpolation=cv2.INTER_NEAREST)

        def bx_draw(bx, color, thick):
            p0 = (int((bx[0] - x_a) * ZOOM), int((bx[1] - y_a) * ZOOM))
            p1 = (int((bx[2] - x_a) * ZOOM), int((bx[3] - y_a) * ZOOM))
            cv2.rectangle(big, p0, p1, color, thick)
        bx_draw(symbox if not S["region"] else [cx0 - 0.6 * sp_c, ytop, cx0 + 0.6 * sp_c, ybot], (235, 111, 31), 1)           # BLUE (BGR) = where the symbol is (our look)
        if wantb:
            bx_draw(wantb[2], (0, 170, 0) if wantb[1] >= 0.25 else (0, 140, 255), 2)   # GREEN kept / ORANGE under the floor
        panel = np.full((big.shape[0] + 74, big.shape[1], 3), 255, np.uint8)
        panel[74:] = big
        label(panel, DESC.get(cond, cond), (6, 18), (0, 0, 0), 0.55, 1)
        shown_S = round(staff.line_spacing_px * cu.upscale_factor * r, 1)
        frames.append(dict(cond=cond, conf=round(got, 3), cls=(wantb[0] if wantb else None), any_top=(round(top[1], 3), top[0]) if top else None, e2_conf=round(e2, 3), matches_e2=ok,
                           S_px=shown_S, panel=panel, canvas=list(canvas.shape[:2])))
        if not ok:
            print("MISMATCH", key, idx, cond, got, e2)
    # titles and S on the panels
    for f in frames:
        pn = f["panel"]
        txt = "conf %.2f %s" % (f["conf"], (f["cls"] or "no box over it")) if f["conf"] > 0 else "no box >= 0.05 of the right family"
        label(pn, txt, (6, 40), (0, 120, 0) if f["conf"] >= 0.25 else (0, 90, 220), 0.5, 1)
        label(pn, "staff space shown: %.1f px  | input %dx%d" % (f["S_px"], f["canvas"][1], f["canvas"][0]), (6, 62), (60, 60, 60), 0.42, 1)
    row = np.concatenate([f["panel"] for f in frames], axis=1)
    head = np.full((70, row.shape[1], 3), 255, np.uint8)
    label(head, ch["title"], (6, 24), (0, 0, 0), 0.62, 2)
    label(head, "%s %s page/system/staff/cell %s | ours: %s | record conf %.2f (%s)" % ("Litolff" if plate == "lit" else "Brahms", S["role"] + (" " + S["cause"] if S["cause"] else ""), key,
                                                                                    (S["what"] or "")[:70], S["rec_conf"] or 0, S["cls"] or "no box"), (6, 52), (60, 60, 60), 0.45, 1)
    out = np.concatenate([head, row], axis=0)
    n = len(index) + 1
    cv2.imwrite(str(OUT / ("crop_%d.png" % n)), out)
    index.append(dict(crop=n, title=ch["title"], plate=plate, key=key, subject=idx, role=S["role"], cause=S["cause"], want=S["want"], symbol_box_page_px=S["bbox"],
                      frames=[{k: v for k, v in f.items() if k != "panel"} for f in frames]))
json.dump(index, open(OUT / "index.json", "w"), indent=1)
print("wrote", len(index), "crops; all conf agree with the experiment:", all(fr["matches_e2"] for it in index for fr in it["frames"]))
