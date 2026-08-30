#!/usr/bin/env python3
"""Stage 1 of the margin-label pilot: render margin crops + the free ground truth.

Split from the API call because the OMR stack (cv2, scipy, skimage, fitz) and the
Anthropic SDK live in different environments here — the host has `anthropic`
0.28.0 while the repo pins 0.116.0, and structured outputs need the newer one.
Splitting also makes the crops reusable: stage 2 can be re-run against different
models or prompts without re-rendering a page.

Ground truth is free — `staff_labels.read_staff_labels` resolves instruments from
the PDF's OCR text layer, so pages that have one already know the answer.

Usage: python3 benchmarks/omr-margin-labels-2026-08/make_crops.py --limit 10
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.staff_labels import has_text_layer, read_staff_labels
from tools.omr.staff_labels_vision import build_margin_crop

CORPUS = "/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp"
PAGES = (40, 59)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10, help="max systems to crop")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default=str(Path(__file__).parent / "crops"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []

    pdfs = [p for w in sorted(os.listdir(CORPUS))
            for p in sorted(glob.glob(f"{CORPUS}/{w}/pdfs/*/score.pdf"))]

    for pdf in pdfs:
        if len(manifest) >= args.limit:
            break
        for page_index in PAGES:
            if len(manifest) >= args.limit:
                break
            if not has_text_layer(pdf, page_index):
                continue
            try:
                pws = detect_staves(render_page(pdf, page_index, dpi=args.dpi))
            except Exception as exc:                        # noqa: BLE001
                print(f"skip {pdf} p{page_index}: {exc}", file=sys.stderr)
                continue

            truth = {}
            for lab in read_staff_labels(pws):
                truth[lab.staff_index] = {
                    "text": lab.text,
                    "instrument": lab.instrument.name if lab.matched else None,
                    "confidence": lab.confidence,
                }

            by_system: dict[int, list] = {}
            for st in sorted(pws.staves, key=lambda s: s.top_y):
                by_system.setdefault(st.system_index, []).append(st)

            # {CORPUS}/{work}/pdfs/{edition}/score.pdf — parents[1] is "pdfs".
            work = f"{Path(pdf).parents[2].name}_{Path(pdf).parents[0].name}"
            for sys_index, staves in sorted(by_system.items()):
                if len(manifest) >= args.limit:
                    break
                crop = build_margin_crop(pws, staves)
                if crop is None:
                    continue
                name = f"{work}_p{page_index}_s{sys_index}.png"
                (out / name).write_bytes(crop.png)
                manifest.append({
                    "png": name,
                    "work": work,
                    "page_index": page_index,
                    "system_index": sys_index,
                    "staff_indices": crop.staff_indices,
                    "truth": {str(k): v for k, v in truth.items()
                              if k in crop.staff_indices},
                })
                print(f"  {name}  {len(crop.staff_indices)} staves, "
                      f"{sum(1 for k in crop.staff_indices if truth.get(k, {}).get('instrument'))} "
                      f"resolved by the text layer")

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(manifest)} crops -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
