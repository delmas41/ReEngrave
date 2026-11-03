"""ROADMAP 2.254 cause probe: why does the STAGED CV wedge reader (`hairpin_detection.detect_hairpins`, called by
`gather.gather_wedge_boxes`) miss most Brahms hairpins?

Re-runs the reader's own steps on one page -- the master cell map's staves (no re-detection), the page binary, the
detector boxes of the 20261029-night slice blanked exactly as the gather blanks them -- and, for every band
component at least MIN_WIDTH_SPACES wide, records which test it fails first (open / outline / isolated / width), plus
the growth ratio. Writes a colour overlay per page so the lane can look at what each real hairpin hit.

    python3 benchmarks/hairpin-reach-2026-11/probe_misses.py brahms 19 OUTDIR
"""
from __future__ import annotations

import json
import pathlib
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "page-claim-order-2026-11"))

import count as C  # noqa: E402
from tools.omr import hairpin_detection as H  # noqa: E402
from tools.omr.staged import cell_map  # noqa: E402
from tools.omr.staged.gather import _spacing, _system_local  # noqa: E402

COL = {"KEPT": (0, 170, 0), "open": (255, 140, 0), "outline": (200, 0, 200), "isolated": (230, 0, 0),
       "letter": (120, 120, 120), "converge": (0, 0, 0), "trend": (90, 90, 0), "unmeasurable": (0, 160, 230)}


def staff_rows(pws):
    rows = []
    for st in pws.staves:
        sp = _spacing(st)
        ys = [float(y) for y in st.line_ys]
        if sp and len(ys) >= 2:
            rows.append({"index": st.staff_index, "top": min(ys), "bottom": max(ys), "spacing": float(sp)})
    return rows


def det_boxes(plate, page):
    out = []
    for o in C.rows(C.SLICES / plate):
        if o["quantity"] != "glyph_box":
            continue
        if int(o["subject"].split("/")[1]) != page:
            continue
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b:
            out.append((b[0], b[1], b[2] - b[0], b[3] - b[1], o["value"][0]))
    return out


def growth(full_lab, full_stats, x, y, w, h):
    label = 0
    for yy in range(y, min(y + h, full_lab.shape[0])):
        for xx in range(x, min(x + w, full_lab.shape[1]), 3):
            if full_lab[yy, xx]:
                label = int(full_lab[yy, xx])
                break
        if label:
            break
    if not label:
        return None
    _x, _y, cw, ch, _a = full_stats[label]
    return (cw * ch) / max(1.0, float(w * h))


def probe(plate, page, out: pathlib.Path, blank=True):
    pdf = C.EDITIONS[plate][0]
    (pws, _cells), = cell_map.load_prepared(pdf, [page])
    binary = pws.page.binary
    ink = (binary == 0).astype(np.uint8) * 255
    rows = staff_rows(pws)
    local = _system_local(pws.staves)
    sps = sorted(r["spacing"] for r in rows)
    med = sps[len(sps) // 2]
    search = H.blank_point_detections(ink, det_boxes(plate, page), med) if blank else ink
    iso = ink
    if VARIANT in ("vert", "line"):
        search, iso = H.reach_inks(ink, search, rows)
    if VARIANT == "line":       # what detect_hairpins(reach=True) runs
        search = H.straight_runs(search, med)
        iso = H.straight_runs(iso, med)
    _n, full_lab, full_stats, _c = cv2.connectedComponentsWithStats(iso, 8)
    order = sorted(rows, key=lambda r: r["bottom"])
    res = []
    for i, s in enumerate(order):
        sp = s["spacing"]
        top, bot = H._band_bounds(order, i)
        band = search[top:bot, :]
        n, lab, stats, _c2 = cv2.connectedComponentsWithStats(band, 8)
        for k in range(1, n):
            x, y, w, h, area = stats[k]
            if w < H.MIN_WIDTH_SPACES * sp or w > H.MAX_WIDTH_SPACES * sp:
                continue
            m = H.measure_component(((lab[y:y + h, x:x + w] == k).astype(np.uint8)) * 255, sp)
            g = growth(full_lab, full_stats, x, top + y, w, h)
            if m is None:
                why = "unmeasurable"
            elif m["open_spaces"] < H.MIN_OPEN_SPACES:
                why = "open"
            elif m["outline_rms_spaces"] > H.MAX_OUTLINE_RMS_SPACES and (VARIANT not in ("vert", "line") or (H.robust_outline_rms(
                    ((lab[y:y + h, x:x + w] == k).astype(np.uint8)) * 255, sp) or 9) > H.MAX_OUTLINE_RMS_SPACES):
                why = "outline"
            elif g is None or g >= H.MAX_COMPONENT_GROWTH:
                why = "isolated"
            elif VARIANT in ("vert", "line") and not H.converges(m):
                why = "converge"
            elif VARIANT in ("vert", "line") and H.extent_trend(((lab[y:y + h, x:x + w] == k).astype(np.uint8)) * 255) < H.REACH_MIN_EXTENT_TREND:
                why = "trend"
            elif w / sp < 1.6:
                why = "letter"
            else:
                why = "KEPT"
            res.append({"staff": int(s["index"]), "system": int(local.get(s["index"], (-1, -1))[0]), "bbox": [int(x), int(top + y), int(x + w), int(top + y + h)],
                        "w_sp": round(w / sp, 2), "h_sp": round(h / sp, 2), "why": why,
                        "open": None if m is None else round(m["open_spaces"], 2),
                        "rms": None if m is None else round(m["outline_rms_spaces"], 3),
                        "closed": None if m is None else round(m["closed_spaces"], 2),
                        "trend": round(H.extent_trend(((lab[y:y + h, x:x + w] == k).astype(np.uint8)) * 255), 2),
                        "growth": None if g is None else round(g, 1)})
    out.mkdir(parents=True, exist_ok=True)
    vis = cv2.cvtColor(255 - ink, cv2.COLOR_GRAY2BGR)
    for i, s in enumerate(order):
        top, bot = H._band_bounds(order, i)
        cv2.rectangle(vis, (0, top), (vis.shape[1] - 1, bot), (220, 220, 255), 2)
    for r in res:
        if r["why"] != "KEPT" and (KEPT_ONLY or r["why"] == "open" or r["w_sp"] < 1.6):
            continue          # strokes: too many to draw
        b = r["bbox"]
        c = COL[r["why"]]
        cv2.rectangle(vis, (b[0] - 3, b[1] - 3), (b[2] + 3, b[3] + 3), c[::-1], 4)
    cv2.imwrite(str(out / ("%s_p%02d_%s_overlay.png" % (plate, page, VARIANT))), cv2.resize(vis, None, fx=0.35, fy=0.35, interpolation=cv2.INTER_AREA))
    (out / ("%s_p%02d_%s.json" % (plate, page, VARIANT))).write_text(json.dumps({"spacing_med": med, "rows": res}, indent=0))
    import collections
    print(plate, page, "spacing", round(med, 1), collections.Counter(r["why"] for r in res if r["w_sp"] >= 1.6))
    return pws, ink, res


VARIANT = "base"
KEPT_ONLY = bool(__import__("os").environ.get("KEPT_ONLY"))

if __name__ == "__main__":
    if len(sys.argv) > 4:
        VARIANT = sys.argv[4]
    probe(sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3]), blank=True)
