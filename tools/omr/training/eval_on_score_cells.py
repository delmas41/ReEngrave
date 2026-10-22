"""Evaluate a trained YOLO checkpoint against the user's actual cells.

Two evaluations in one script:

    1. mAP@0.5 on DeepScoresV2's val split (delegated to ultralytics
       `model.val()` against the data.yaml used for training). This is
       the published-benchmark number; it tells us how the weights would
       look on a paper.

    2. Raw detection counts on a sample of WTC cells from
       `benchmarks/omr-phase2.5/cells.json`. This tells us whether the
       newly-trained weights actually fire on this project's real input
       distribution — DeepScoresV2 is synthetic, the WTC scan is real,
       so the gap matters.

The script prints a JSON report to stdout. No verdicts are computed here
(that's `tools/omr/annotate/score.py`'s job). The intent is a quick
"does the new model see anything?" check before launching the longer
scorer pipeline.

CLI:
    python3 -m tools.omr.training.eval_on_score_cells \
        --weights data/deepscoresv2-yolo/runs/ds2-yolov8m/weights/best.pt \
        --data data/deepscoresv2-yolo/data.yaml \
        --cells benchmarks/omr-phase2.5/cells.json \
        --n-sample 5 --conf 0.25 --device 0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _fail(msg: str, code: int = 2) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return code


def evaluate_map(weights: Path, data_yaml: Path, *, device: str) -> dict:
    """Run ultralytics val() and return the metrics dict."""
    from ultralytics import YOLO  # type: ignore

    model = YOLO(str(weights))
    results = model.val(
        data=str(data_yaml),
        device=device if device != "auto" else None,
        verbose=False,
    )
    # results.box has the box-detection mAP fields
    box = getattr(results, "box", None)
    out: dict = {}
    if box is not None:
        for k in ("map", "map50", "map75", "mp", "mr"):
            v = getattr(box, k, None)
            if v is not None:
                try:
                    out[k] = float(v)
                except (TypeError, ValueError):
                    pass
    return {"deepscoresv2_val": out}


def evaluate_score_cells(
    weights: Path,
    cells_manifest: Path,
    *,
    n_sample: int,
    conf: float,
    device: str,
) -> dict:
    """Run YoloDetector on `n_sample` cells and report detection stats."""
    # Late imports so --help works without torch
    from ..yolo_detector import YoloDetector
    from ..annotate.build_template import _load_cell_from_manifest

    manifest = json.loads(cells_manifest.read_text())
    if not manifest:
        return {"error": "manifest is empty"}
    sample = manifest[:n_sample]

    detector = YoloDetector(str(weights), device=device)
    root = Path.cwd()

    per_cell: list[dict] = []
    cat_totals: dict[str, int] = {}
    for entry in sample:
        cid = entry["cell_id"]
        try:
            cell = _load_cell_from_manifest(entry, root)
        except FileNotFoundError as exc:
            per_cell.append({"cell_id": cid, "error": str(exc)})
            continue
        dets = detector.detect(cell, conf_threshold=conf)
        cat_breakdown: dict[str, int] = {}
        for d in dets:
            cat_breakdown[d.category] = cat_breakdown.get(d.category, 0) + 1
            cat_totals[d.category] = cat_totals.get(d.category, 0) + 1
        confs = [d.confidence for d in dets]
        per_cell.append({
            "cell_id": cid,
            "n_detections": len(dets),
            "category_breakdown": cat_breakdown,
            "confidence_min": float(min(confs)) if confs else None,
            "confidence_max": float(max(confs)) if confs else None,
            "sample_class_labels": [d.smufl_name for d in dets[:8]],
        })
    return {
        "score_cells": {
            "n_sampled": len(sample),
            "conf_threshold": conf,
            "per_cell": per_cell,
            "category_totals": cat_totals,
        }
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--weights", required=True,
                    help="Path to a trained .pt (e.g. .../runs/ds2-yolov8m/weights/best.pt)")
    ap.add_argument("--data", default="data/deepscoresv2-yolo/data.yaml",
                    help="Path to the data.yaml that was used for training "
                         "(needed for the DeepScoresV2 val-set mAP step)")
    ap.add_argument("--cells", default="benchmarks/omr-phase2.5/cells.json",
                    help="Cell manifest to sample WTC inference cells from")
    ap.add_argument("--n-sample", type=int, default=5)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--device", default="0")
    ap.add_argument("--skip-map", action="store_true",
                    help="Skip the DeepScoresV2 val-set mAP step (faster; "
                         "useful when iterating on the cell-sample step)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    weights = Path(args.weights)
    if not weights.exists():
        return _fail(f"weights not found: {weights}")

    cells = Path(args.cells)
    if not cells.exists():
        return _fail(f"cells manifest not found: {cells}")

    report: dict = {"weights": str(weights)}

    if not args.skip_map:
        data_yaml = Path(args.data)
        if not data_yaml.exists():
            return _fail(f"data.yaml not found: {data_yaml}")
        try:
            report.update(evaluate_map(weights, data_yaml, device=args.device))
        except Exception as exc:  # noqa: BLE001
            report["deepscoresv2_val_error"] = str(exc)

    report.update(evaluate_score_cells(
        weights, cells,
        n_sample=args.n_sample, conf=args.conf, device=args.device,
    ))

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
