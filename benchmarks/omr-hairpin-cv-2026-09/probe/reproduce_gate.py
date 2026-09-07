"""Does `hairpin_detection`'s docstring gate REPRODUCE? — run before wiring.

The module reports "59 of 99 hairpins against the detector's 1, and zero false
positives on five of the six pages that carry none" for code with no call site.
A claim measured once, by a harness driving the module directly, is exactly the
kind this repo has been bitten by. So: re-run it, on the eleven-row scan era,
before adding the call site.

⚠️ TWO INK RECIPES, MEASURED APART, because the wiring changes which one the
reader gets:

  probe     `gray < 180` on a fresh 600 dpi render — what
            `probe_band_ink.py` used, i.e. what the docstring's number was
            measured on. Re-rendered here, NOT deskewed.
  pipeline  `page.binary` from `preprocessing.render_page` — Sauvola, deskewed,
            and the frame every `bbox_page_px` in the transcription is already
            in. This is what a call site inside `transcribe` can hand it for
            free.

If those disagree the wiring is not the same experiment as the measurement, and
that has to be said out loud rather than discovered later.

    python3 benchmarks/omr-hairpin-cv-2026-09/probe/reproduce_gate.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "benchmarks" / "omr-pipeline-audit-2026-09" / "probe"))

import _fixtures  # noqa: E402
import numpy as np  # noqa: E402
import cv2  # noqa: E402

from tools.omr import hairpin_detection as hp  # noqa: E402

#: The eleven rows the docstring's gate was measured over. The scan gate is 20
#: rows now; the claim under test is the eleven-row one, so it is named rather
#: than derived from whatever `works.json` currently holds.
ELEVEN = [
    "bach-brandenburg3-mvt1-468678-p1",
    "beethoven-sym5-mvt1-575951-p1", "beethoven-sym5-mvt1-575951-p2",
    "beethoven-sym5-mvt1-984073-p1", "beethoven-sym5-mvt1-984073-p2",
    "brahms-sym1-mvt1-317803-p1", "brahms-sym1-mvt1-317803-p2",
    "dvorak-sym9-mvt1-405834-p5", "dvorak-sym9-mvt1-405834-p6",
    "mahler-sym5-mvt1-local-p2", "mahler-sym5-mvt1-local-p3",
]

HAIRPIN_CLASSES = ("dynamicCrescendoHairpin", "dynamicDiminuendoHairpin")


def _rows(root: Path) -> dict[str, dict]:
    works = json.loads(
        (root / "benchmarks/omr-scan-e2e-2026-09/works.json").read_text())
    return {r["row_id"]: r for r in works["rows"]}


def _truth_hairpins(path: Path) -> int | None:
    """`<wedge>` pairs in the truth encoding — two tags per hairpin."""
    if not path.is_file():
        return None
    return path.read_text().count("<wedge ") // 2


def _yolo_hairpins(result: dict) -> int:
    n = 0
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                for meas in staff.get("measures", []):
                    for det in meas.get("detections", []):
                        if det.get("class") in HAIRPIN_CLASSES:
                            n += 1
    return n


def _probe_ink(pdf: Path, page_index: int, dpi: int) -> np.ndarray:
    import fitz  # type: ignore
    doc = fitz.open(pdf)
    try:
        pm = doc[page_index].get_pixmap(dpi=dpi)
        img = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
            pm.height, pm.width, pm.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pm.n >= 3 else img[:, :, 0]
    finally:
        doc.close()
    return (gray < 180).astype(np.uint8) * 255


def _pipeline_ink(pdf: Path, page_index: int, dpi: int) -> np.ndarray:
    from tools.omr.preprocessing import render_page
    page = render_page(pdf, page_index, dpi=dpi)
    return (page.binary == 0).astype(np.uint8) * 255


def _detection_boxes(result: dict) -> list[tuple]:
    out = []
    for system in result["pages"][0].get("systems", []):
        for staff in system.get("staves", []):
            for meas in staff.get("measures", []):
                box = meas.get("bbox_page_px") or [0, 0, 0, 0]
                up = float(meas.get("upscale_factor") or 1.0) or 1.0
                for det in meas.get("detections", []):
                    b = det.get("bbox")
                    if not b or len(b) != 4:
                        continue
                    out.append((float(box[0]) + b[0] / up,
                                float(box[1]) + b[1] / up,
                                b[2] / up, b[3] / up, det.get("class") or ""))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--ink", choices=["probe", "pipeline", "both"], default="both")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    root = Path(_fixtures.root())
    rows = _rows(root)
    paths = _fixtures.fixtures(_fixtures.SCAN, expect_at_least=11)
    by_row = {Path(p).name.split("..graft09")[0]: Path(p) for p in paths}

    missing = [r for r in ELEVEN if r not in by_row]
    if missing:
        sys.stderr.write(f"FATAL: no fixture for {missing}\n")
        return 2

    modes = ["probe", "pipeline"] if args.ink == "both" else [args.ink]
    table: dict[str, dict] = {}
    for row_id in ELEVEN:
        res = json.loads(by_row[row_id].read_text())
        row = rows[row_id]
        pdf = root / "library" / row["edition"]["catalog_path"]
        page_index = row["page"]["pdf_page_index"]
        truth = _truth_hairpins(by_row[row_id].parent / f"{row_id}.truth.musicxml")
        staves = hp.staves_from_result(res, 0)
        spacings = sorted(s["spacing"] for s in staves)
        sp_med = spacings[len(spacings) // 2] if spacings else 1.0
        boxes = _detection_boxes(res)

        rec = {"truth_hairpins": truth, "yolo": _yolo_hairpins(res),
               "n_staves": len(staves)}
        for mode in modes:
            ink = (_probe_ink(pdf, page_index, args.dpi) if mode == "probe"
                   else _pipeline_ink(pdf, page_index, args.dpi))
            blanked = hp.blank_point_detections(ink, boxes, sp_med)
            found = hp.detect_hairpins(ink, staves, blanked)
            rec[mode] = len(found)
            rec[f"{mode}_kinds"] = {
                "crescendo": sum(1 for f in found if f.kind == "crescendo"),
                "diminuendo": sum(1 for f in found if f.kind == "diminuendo")}
        table[row_id] = rec
        print(f"{row_id:36s} truth {str(truth):>4s}  yolo {rec['yolo']:>3d}  "
              + "  ".join(f"{m} {rec[m]:>3d}" for m in modes), flush=True)

    print()
    tot_truth = sum(v["truth_hairpins"] or 0 for v in table.values())
    print(f"TOTAL truth hairpins {tot_truth}   yolo "
          f"{sum(v['yolo'] for v in table.values())}")
    for mode in modes:
        blank_pages = [k for k, v in table.items() if not v["truth_hairpins"]]
        fp = sum(table[k][mode] for k in blank_pages)
        silent = sum(1 for k in blank_pages if table[k][mode] == 0)
        print(f"  {mode:9s} found {sum(v[mode] for v in table.values()):4d}   "
              f"false positives on the {len(blank_pages)} hairpin-free pages: "
              f"{fp}  (silent on {silent} of {len(blank_pages)})")
    if args.json_out:
        args.json_out.write_text(json.dumps(table, indent=1))
        print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
