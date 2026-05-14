"""Run YoloDetector on cells from a manifest, write detections JSON and
auto-port verdicts so the existing scorer can grade them.

Mirrors `port_verdicts.py` but with the YOLO detector as the engine.
Detections-side output is identical in schema to the template-matcher
detections so `tools/omr/annotate/score.py` works unchanged.

CLI:
    python3 -m tools.omr.annotate.run_yolo \
        --manifest benchmarks/omr-phase2.5/cells.json \
        --cells wtc-p5-sys0-s0-m0 wtc-p5-sys0-s0-m1 wtc-p5-sys0-s0-m2 wtc-p5-sys0-s0-m3 \
        --weights yolov8m.pt \
        --baseline-verdicts benchmarks/omr-phase2.5/verdicts \
        --out-dir benchmarks/omr-phase3/verdicts-yolo \
        --detections-out benchmarks/omr-phase3/detections-yolo \
        --conf 0.10
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from ..yolo_detector import YoloDetector
from ..template_matcher import SymbolDetection
from .build_template import _load_cell_from_manifest, _detections_to_dict
from .port_verdicts import parse_baseline, find_match, render_verdict_md


def run(
    manifest_path: Path,
    cell_ids: list[str],
    weights: str,
    out_dir: Path,
    detections_out: Path,
    baseline_dir: Path | None,
    conf_threshold: float,
    device: str,
    time_n_runs: int,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    detections_out.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text())
    root = Path.cwd()
    by_id = {e["cell_id"]: e for e in manifest}

    detector = YoloDetector(weights, device=device)

    summary: dict = {
        "weights": weights,
        "conf_threshold": conf_threshold,
        "device": device,
        "per_cell": {},
    }

    for cid in cell_ids:
        entry = by_id.get(cid)
        if entry is None:
            print(f"  WARN: cell {cid} not in manifest")
            continue
        cell = _load_cell_from_manifest(entry, root)

        # Time multiple runs to get a stable median.
        if time_n_runs >= 2:
            timing = detector.time_detect(
                cell, conf_threshold=conf_threshold, n_runs=time_n_runs,
            )
            detections = detector.detect(cell, conf_threshold=conf_threshold)
        else:
            t0 = time.perf_counter()
            detections = detector.detect(cell, conf_threshold=conf_threshold)
            t1 = time.perf_counter()
            timing = {
                "n_runs": 1,
                "n_detections": len(detections),
                "all_times_s": [t1 - t0],
                "median_s_excluding_warmup": t1 - t0,
                "mean_s_excluding_warmup": t1 - t0,
            }

        # Persist detections JSON.
        det_path = detections_out / f"{cid}.json"
        det_path.write_text(json.dumps(_detections_to_dict(cid, detections), indent=2))

        # Try to port baseline verdicts if a baseline_dir is given AND a
        # markdown for this cell exists. Because YOLO will produce
        # detections at totally different locations than the template
        # matcher (different category names too), the port will mostly
        # produce "pending" markers — that's the point.
        ordered = sorted(detections, key=lambda d: d.x_center)
        ported: list[tuple[SymbolDetection, dict | None]]
        if baseline_dir is not None:
            md_path = baseline_dir / f"{cid}.md"
            if md_path.exists():
                baseline = parse_baseline(md_path.read_text())
                ported = [(d, find_match(d, baseline)) for d in ordered]
            else:
                ported = [(d, None) for d in ordered]
        else:
            ported = [(d, None) for d in ordered]

        overlay_rel = f"../overlays/{cid}.png"  # may not exist for YOLO
        md = render_verdict_md(cid, entry, ordered, overlay_rel, ported)
        (out_dir / f"{cid}.md").write_text(md)

        n_total = len(ordered)
        n_ported = sum(1 for (_, b) in ported if b is not None)

        # Confidence distribution + sample class labels.
        confs = [d.confidence for d in ordered]
        sample_classes = [d.smufl_name for d in ordered[:10]]
        cat_breakdown: dict[str, int] = {}
        for d in ordered:
            cat_breakdown[d.category] = cat_breakdown.get(d.category, 0) + 1

        summary["per_cell"][cid] = {
            "n_detections": n_total,
            "n_ported_from_baseline": n_ported,
            "confidence_min": float(min(confs)) if confs else None,
            "confidence_max": float(max(confs)) if confs else None,
            "confidence_mean": float(np.mean(confs)) if confs else None,
            "confidence_median": float(np.median(confs)) if confs else None,
            "category_breakdown": cat_breakdown,
            "sample_class_labels": sample_classes,
            "timing": timing,
        }
        print(
            f"  {cid}: dets={n_total}  ported={n_ported}  "
            f"conf_range=[{min(confs):.2f}..{max(confs):.2f}]" if confs else
            f"  {cid}: dets=0"
        )

    summary_path = out_dir / "_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {summary_path}")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="benchmarks/omr-phase2.5/cells.json")
    ap.add_argument("--cells", nargs="+", required=True)
    ap.add_argument("--weights", default="yolov8m.pt")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--detections-out", required=True)
    ap.add_argument("--baseline-verdicts", default="benchmarks/omr-phase2.5/verdicts")
    ap.add_argument("--conf", type=float, default=0.10)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--time-n-runs", type=int, default=5)
    args = ap.parse_args()
    run(
        manifest_path=Path(args.manifest),
        cell_ids=args.cells,
        weights=args.weights,
        out_dir=Path(args.out_dir),
        detections_out=Path(args.detections_out),
        baseline_dir=Path(args.baseline_verdicts) if args.baseline_verdicts else None,
        conf_threshold=args.conf,
        device=args.device,
        time_n_runs=args.time_n_runs,
    )


if __name__ == "__main__":
    main()
