"""GATHER only, dumped as a record-shaped JSON.

⚠️ WHY THIS EXISTS, AND WHAT IT IS NOT. Every quantity this lane reads --
`Q.INK`, `Q.GLYPH_BOX`, `Q.NOTEHEAD_STAFF_POSITION`, `Q.CELL_STAFF_SPACE` --
is a GATHER observation. The full CLI writes its record only after ADJUDICATE,
GROUPS and EVALUATE have run, and on a 27-staff Breitkopf page
`adjudicate_glyph_owner` alone is the O(n^2) step this repo already records
taking >40 min on this document. So this stops at the stage the question lives
in.

⚠️ IT IS NOT A SUBSTITUTE FOR THE FULL RECORD and must not be described as
one: it carries NO verdicts, so nothing downstream of GATHER can be asked of
it. It is the same `gather.gather` call the pipeline makes, with the same
arguments, and the observations it writes are byte-comparable with the full
run's -- which the full run, when it lands, is the control for.

READ-ONLY with respect to `tools/`: nothing here is imported by the pipeline.
"""
from __future__ import annotations

import argparse
import json
import sys

from tools.omr.staged import gather
from tools.omr.staged.pipeline import prepare_pages


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", required=True,
                    help="comma list of 0-based page indices")
    ap.add_argument("--weights", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    pages = [int(p) for p in a.pages.split(",")]
    from tools.omr.yolo_detector import YoloDetector
    det = YoloDetector(a.weights)

    print(f"GATHER ONLY: pages {pages} dpi {a.dpi} conf {a.conf}", flush=True)
    prepared = prepare_pages(a.pdf, pages, dpi=a.dpi)
    # ⚠️ Surya and Tesseract are OFF, deliberately and identically to the
    # full run this lane launched. Neither margin labels nor direction words
    # are read by anything here, and on a scan the direction reader alone is
    # measured at ~267 s/page for six words.
    log = gather.gather(prepared, detector=det, conf_threshold=a.conf,
                        imgsz=a.imgsz, dossier=None, roster=None,
                        pdf_path=a.pdf, surya_fallback=False,
                        ocr_fallback=False, progress=True)
    doc = log.to_json()
    with open(a.out, "w") as f:
        json.dump(doc, f)
    n_obs = len(doc.get("observations") or ())
    print(f"wrote {a.out}: {n_obs} observations", flush=True)
    if not n_obs:
        print("DEAD: zero observations", flush=True)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
