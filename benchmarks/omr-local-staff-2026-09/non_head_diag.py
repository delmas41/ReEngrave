#!/usr/bin/env python3
"""lane-ledger-template-fix round 5 (2026-10-04): Sean says two Brahms control
tiles are "not noteheads" (part of another symbol). Cut a WIDE crop of each at
the gather's DPI, with the detector's class + confidence for the subject box and
every other detector box overlapping it, so the symbol they belong to can be
named from the print. Writes crops under out/print/ledgers/nonhead/.

    python3 benchmarks/omr-local-staff-2026-09/non_head_diag.py glyph/1/1/12/4/0 glyph/1/0/2/6/3
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import cv2  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

OUT = REPO / "out" / "print" / "ledgers" / "nonhead"


def boxes_with_scores(rec, page):
    out = []
    for o in rec.observations:
        if o["quantity"] != Q.GLYPH_BOX:
            continue
        sub = o["subject"]
        if int(sub.split("/")[1]) != page:
            continue
        b = (o.get("detail") or {}).get("bbox_page_px")
        if not b:
            continue
        out.append(dict(subject=sub, cls=(o.get("value") or [None])[0], score=o.get("score"),
                        reader=o.get("reader"), box=[float(v) for v in b]))
    return out


def main(subjects) -> int:
    doc = "brahms1-breitkopf"
    loaded = ts.load_doc(doc)
    rec = loaded["rec"]
    pages = score.PageCache(loaded["cfg"])
    OUT.mkdir(parents=True, exist_ok=True)
    print("gather dpi", loaded["cfg"]["dpi"])
    for sub in subjects:
        page = int(sub.split("/")[1])
        allb = boxes_with_scores(rec, page)
        me = [b for b in allb if b["subject"] == sub][0]
        x0, y0, x1, y1 = me["box"]
        gray = pages.get(page)
        staff_key = "staff/" + "/".join(sub.split("/")[1:4])
        lines = [float(y) for y in rec.obs(Q.STAFF_LINES, staff_key)[-1]["value"]]
        sp = (max(lines) - min(lines)) / 4.0
        print(f"\n== {sub}  class={me['cls']} score={me['score']} reader={me['reader']} box={[round(v) for v in me['box']]} "
              f"(w {x1 - x0:.0f}, h {y1 - y0:.0f}px = {(x1 - x0) / sp:.2f} x {(y1 - y0) / sp:.2f} sp), spacing {sp:.1f}px")
        print("  other detector boxes overlapping it (any overlap):")
        for b in allb:
            if b["subject"] == sub:
                continue
            bx0, by0, bx1, by1 = b["box"]
            ox, oy = min(x1, bx1) - max(x0, bx0), min(y1, by1) - max(y0, by0)
            if ox > 0 and oy > 0:
                print(f"    {b['subject']:<22} {str(b['cls']):<28} score {b['score']}  box {[round(v) for v in b['box']]}  overlap {ox:.0f}x{oy:.0f}px")
        # wide crop: the whole bar neighbourhood, all staves near it
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hw, hh = int(16 * sp), int(11 * sp)
        cx0, cy0 = max(0, int(cx - hw)), max(0, int(cy - hh))
        cx1, cy1 = min(gray.shape[1], int(cx + hw)), min(gray.shape[0], int(cy + hh))
        crop = cv2.cvtColor(gray[cy0:cy1, cx0:cx1], cv2.COLOR_GRAY2BGR)
        z = 2
        crop = cv2.resize(crop, None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
        for b in allb:
            bx0, by0, bx1, by1 = b["box"]
            if bx1 < cx0 or bx0 > cx1 or by1 < cy0 or by0 > cy1:
                continue
            if b["subject"] == sub:
                col, th = (0, 0, 255), 3
            elif min(x1, bx1) - max(x0, bx0) > 0 and min(y1, by1) - max(y0, by0) > 0:
                col, th = (255, 120, 0), 2
            elif "notehead" in str(b["cls"]).lower():
                col, th = (0, 170, 0), 1
            else:
                continue
            p0 = (int((bx0 - cx0) * z), int((by0 - cy0) * z)); p1 = (int((bx1 - cx0) * z), int((by1 - cy0) * z))
            cv2.rectangle(crop, p0, p1, col, th)
            if col != (0, 170, 0):
                cv2.putText(crop, str(b["cls"])[:22], (p0[0], max(10, p0[1] - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        name = OUT / (sub.replace("/", "_") + "_wide.jpg")
        cv2.imwrite(str(name), crop, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        print("  wrote", name, crop.shape)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
