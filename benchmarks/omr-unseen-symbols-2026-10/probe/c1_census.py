"""ROADMAP 2.179 step 2 -- for every red bar of an export, what the detector and the gates did in that bar, and a crop to look at.

usage: python3 benchmarks/omr-unseen-symbols-2026-10/probe/c1_census.py DOC PDF RECORD RED_ROWS OUTDIR
DOC is litolff|brahms. Re-renders each page (pipeline.prepare_pages, the shipped cutter), matches each red bar's cell to the record by
its page box, re-runs the SAME routed production detector on that cell at 0.03 (production view; no new reading reaches any record), and
writes OUTDIR/DOC.census.json (per bar: rows written, record boxes with reader/class/conf and their standing refusals, and the sub-floor
boxes no record box of the same family stands on) and OUTDIR/sheets/DOC_NNN.png (per bar: the plain print above, the same print with
boxes drawn below: green = a record box of a note/rest/flag/dot family that no gate refused, red = refused by a gate, orange = under the
0.25 floor and not in the record, with class and score). The crops are for MY look (ours, not evidence) -- never sent to Sean.
"""
import collections
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, ".")
from tools.omr.staged import pipeline as P  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.yolo_detector import YoloDetector  # noqa: E402

doc, pdf, rec_path, red_path, outdir = sys.argv[1:6]
WEIGHTS = "omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
FLOOR, PROD = 0.03, 0.25
os.makedirs(os.path.join(outdir, "sheets"), exist_ok=True)

red = json.load(open(red_path))
result = load_record(rec_path)
rec = result["record"]


def fam(name):
    n = str(name)
    if n.startswith("notehead"):
        return "head"
    if n.startswith("rest"):
        return "rest"
    if n.startswith("flag"):
        return "flag"
    if n == "augmentationDot":
        return "dot"
    return None


cell_box = {}
glyphs = collections.defaultdict(dict)  # cell key -> glyph subject -> info
for o in rec["observations"]:
    q, s = o.get("quantity"), o.get("subject") or ""
    if q == "cell_box" and s.startswith("cell/"):
        cell_box[s[5:]] = o["value"]
    elif q == "glyph_box" and s.startswith("glyph/"):
        d = o.get("detail") or {}
        if not isinstance(d.get("bbox_page_px"), list):
            continue
        ck = "/".join(s.split("/")[1:5])
        if s in glyphs[ck]:
            continue
        glyphs[ck][s] = dict(cls=o["value"][0], conf=o.get("score"), reader=o.get("reader"), box=d["bbox_page_px"], refused=[])
REFUSING = {"notehead_is_not_a_notehead", "rest_is_not_a_rest", "flag_is_not_a_flag"}
dur = {}
for v in rec["verdicts"]:
    s = v.get("subject") or ""
    if not s.startswith("glyph/"):
        continue
    ck = "/".join(s.split("/")[1:5])
    q = v.get("quantity")
    if q in REFUSING and v.get("value") is True and s in glyphs[ck]:
        glyphs[ck][s]["refused"].append(v.get("reason") or q)
    if q == "duration":
        dur[s] = (v.get("status"), v.get("value"), v.get("reason"))
    if q == "dot_role" and s in glyphs[ck]:
        glyphs[ck][s]["dot_role"] = (v.get("status"), v.get("value"), v.get("reason"))
for ck in glyphs:
    for s, g in glyphs[ck].items():
        if s in dur:
            g["duration"] = dur[s]


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def same_ink(a, b):
    if iou(a, b) > 0.3:
        return True
    for p, q in ((a, b), (b, a)):
        cx, cy = (p[0] + p[2]) / 2, (p[1] + p[3]) / 2
        if q[0] <= cx <= q[2] and q[1] <= cy <= q[3]:
            return True
    return False


pages = sorted({r["page"] for r in red})
det = YoloDetector(WEIGHTS)
out = []
for p in pages:
    [(pws, cells)] = P.prepare_pages(pdf, [p])
    page_img = cv2.cvtColor(pws.page.rgb, cv2.COLOR_RGB2BGR)
    by_box = {}
    for c in cells:
        b = getattr(c, "bbox_page_px", None)
        if b:
            by_box[tuple(round(float(v), 1) for v in b)] = c
    rows_p = [r for r in red if r["page"] == p]
    for r in rows_p:
        ck = "%d/%d/%d/%d" % (r["page"], r["system"], r["staff"], r["cell"])
        cb = cell_box.get(ck)
        c = by_box.get(tuple(round(float(v), 1) for v in cb)) if cb else None
        entry = dict(bar=ck, words=r["words"], want=r["want_quarters"], counted=r["counted_quarters"], two_voice=r["two_voice"],
                     rows=[(x["kind"], x.get("type") or ("rest%s" % x.get("beats")), x.get("beats"), x["status"], x.get("glyph"), x.get("pitch"))
                           for x in r["rows"]], cell_box=cb)
        recg = glyphs.get(ck, {})
        entry["record"] = {s: g for s, g in recg.items() if fam(g["cls"])}
        sub = []
        if c is not None:
            for d in det.detect(c, conf_threshold=FLOOR):
                f = fam(d.smufl_name)
                if f is None or d.confidence >= PROD:
                    continue
                pb = G._page_box(c, d)
                if pb is None:
                    continue
                if any(fam(g["cls"]) == f and same_ink(pb, g["box"]) for g in recg.values()):
                    continue
                sub.append(dict(cls=d.smufl_name, conf=round(float(d.confidence), 3), box=[round(v, 1) for v in pb]))
        else:
            entry["note"] = "cell not matched"
        entry["subfloor"] = sub
        out.append(entry)
        # crop
        if cb is None or page_img is None:
            continue
        x0, y0, x1, y1 = cb
        sp = (y1 - y0) / 8.0
        X0, Y0 = int(max(0, x0 - 1.5 * sp)), int(max(0, y0 - 2.5 * sp))
        X1, Y1 = int(min(page_img.shape[1], x1 + 1.5 * sp)), int(min(page_img.shape[0], y1 + 2.5 * sp))
        crop = page_img[Y0:Y1, X0:X1].copy()
        ann = crop.copy()

        def rect(b, col, lab):
            a = (int(b[0] - X0), int(b[1] - Y0))
            z = (int(b[2] - X0), int(b[3] - Y0))
            cv2.rectangle(ann, a, z, col, 2)
            cv2.putText(ann, lab, (a[0], max(12, a[1] - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)
        for s, g in entry["record"].items():
            col = (0, 0, 220) if g["refused"] else (0, 160, 0)
            short = g["cls"].replace("notehead", "h").replace("InSpace", "S").replace("OnLine", "L").replace("rest", "r").replace("flag", "f")
            rect(g["box"], col, "%s %s" % (s.split("/")[-1], short[:9]))
        for sb in sub:
            short = sb["cls"].replace("notehead", "h").replace("InSpace", "S").replace("OnLine", "L").replace("rest", "r").replace("flag", "f")
            rect(sb["box"], (0, 140, 255), "%s .%02d" % (short[:9], int(sb["conf"] * 100)))
        both = np.vstack([crop, np.full((8, crop.shape[1], 3), 128, np.uint8), ann])
        sc = 1100.0 / both.shape[1]
        both = cv2.resize(both, (1100, int(both.shape[0] * sc)), interpolation=cv2.INTER_AREA)
        hdr = np.full((70, 1100, 3), 255, np.uint8)
        cv2.putText(hdr, "%d %s %s" % (len(out) - 1, ck, r["words"][15:]), (5, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(hdr, " ".join("%s%s" % (("" if k == "note" else "R"), (t or "")[:3]) + ("*" if st != "READ" else "")
                                  for k, t, _b, st, _g, _p in entry["rows"])[:110], (5, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        cv2.imwrite(os.path.join(outdir, "sheets", "%s_%03d.png" % (doc, len(out) - 1)), np.vstack([hdr, both]))
    print("page", p, len(rows_p), "bars", flush=True)
json.dump(out, open(os.path.join(outdir, "%s.census.json" % doc), "w"), indent=0, default=str)
print("wrote", len(out))
