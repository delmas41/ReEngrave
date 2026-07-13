"""Dense-orchestral notehead-RECALL eval on the hand-labeled cell sets.

The domain-augmentation question — "does ScoreAug degradation make the detector
find more real-scan noteheads?" — is answered by measuring notehead RECALL on
real orchestral cells that are NOT in DSv2: the hand-labeled Beethoven-5,
Mahler-5, and La Mer cells (data/user-labeled/v1..v4).

Why recall, not F1: the human ground truth is *incomplete* on these dense cells
(a labeler boxes the clearly-real noteheads, not every faint one), so PRECISION
is confounded — many "false positives" are real noteheads the human never boxed.
RECALL against the boxed GT is the honest, model-agnostic "did it detect the
symbol" signal. Precision/F1 are printed too but only as loose context.

Ground truth: YOLO .txt labels (class cx cy w h, normalized to the cell PNG).
A box is a notehead iff its class index maps to a notehead name in the label
catalog (default data/user-labeled/catalog-214.yaml — the catalog the v1..v4
labels were emitted against). Model detections are noteheads iff model.names[cls]
contains "notehead". GT↔pred are matched by CENTER proximity (tolerance scaled
to the GT box size), exactly like wtc_forgetting_eval — fair to box-size drift
between checkpoints, which is what we want for a "did it fire here" recall.

Runs any number of checkpoints in one pass and prints a per-source / per-model
table, so Baseline vs Arm-A vs Arm-B come out side by side.

CLI (one row per source, one column-block per weights file):
    python3 -m tools.omr.training.eval_dense_recall \
        --weights omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
                  runs/armA/weights/best.pt runs/armB/weights/best.pt \
        --labels  production armA armB \
        --repo-root . --imgsz 1280 --conf 0.25 --device 0 \
        --json-out benchmarks/scoreaug-fair-test/dense_recall.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict
from pathlib import Path

import yaml

# Reuse the vetted category mapper so the model-side notehead filter matches
# exactly how wtc_forgetting_eval buckets classes.
from tools.omr.training.wtc_forgetting_eval import category_of


# ── which hand-labeled sets to score, and where their PNGs live ──────────────
# Each entry: (source tag, label glob relative to repo root). The cell PNG for a
# label <stem>.txt is found by searching CELLS_SUBDIRS for <stem>.png.
DEFAULT_SOURCES: list[tuple[str, str]] = [
    ("beet5",   "data/user-labeled/v1-2026-05-18-orchestral/labels/beet5-*.txt"),
    ("beet5",   "data/user-labeled/v2-2026-06-08-beet5/labels/beet5-*.txt"),
    ("mahler5", "data/user-labeled/v3-2026-06-09-mahler5/labels/mahler5-*.txt"),
    ("lamer",   "data/user-labeled/v4-2026-06-10-la-mer/labels/debussy-la-mer-*.txt"),
]

# Cell PNGs are gitignored; they live under these benchmark dirs (searched in
# order). On the GPU box, scp the cells into the same relative paths.
DEFAULT_CELLS_SUBDIRS: list[str] = [
    "benchmarks/omr-phase-realft/cells",
    "benchmarks/omr-labeling-2026-05-24/cells",
    "benchmarks/omr-labeling-2026-06-08/cells",
    "benchmarks/omr-labeling-2026-06-09/cells",
    "benchmarks/omr-labeling-2026-06-10/cells",
]


def notehead_catalog_indices(catalog_path: Path) -> set[int]:
    """Class indices in the label catalog whose name contains 'notehead'."""
    cat = yaml.safe_load(catalog_path.read_text())
    names = cat["names"]
    idx = {i for i, n in enumerate(names) if "notehead" in str(n).lower()}
    if not idx:
        raise SystemExit(f"no notehead classes found in {catalog_path}")
    return idx


def find_cell_png(stem: str, cells_dirs: list[Path]) -> Path | None:
    for d in cells_dirs:
        p = d / f"{stem}.png"
        if p.exists():
            return p
    return None


def load_gt_noteheads(
    label_path: Path, img_w: int, img_h: int, nh_idx: set[int]
) -> list[tuple[float, float, float, float]]:
    """Return notehead GT boxes as pixel (cx, cy, w, h) for this cell."""
    out = []
    for line in label_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        cls = int(parts[0])
        if cls not in nh_idx:
            continue
        cx, cy, w, h = (float(v) for v in parts[1:5])
        out.append((cx * img_w, cy * img_h, w * img_w, h * img_h))
    return out


def model_notehead_centers(
    model, png: Path, imgsz: int, conf: float, device: str
) -> list[tuple[float, float, float, float]]:
    """Run the model on a cell; return notehead detections as (cx, cy, w, h)."""
    names = {int(i): n for i, n in model.names.items()}
    r = model.predict(str(png), imgsz=imgsz, conf=conf, device=device,
                      verbose=False)[0]
    out = []
    for b in r.boxes:
        if category_of(names[int(b.cls)]) != "notehead":
            continue
        x0, y0, x1, y1 = (float(v) for v in b.xyxy[0])
        out.append(((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0))
    return out


def match_recall(
    gt: list[tuple], pred: list[tuple], tol_frac: float, tol_min: float
) -> int:
    """Greedy center-match (each pred claims its nearest unused GT within a
    size-scaled tolerance). Returns #GT matched (= TP for recall)."""
    gt_used = [False] * len(gt)
    tp = 0
    # match higher-anything-first is irrelevant here (preds unweighted); iterate
    # preds and let each claim the closest free GT within that GT's tolerance.
    for pcx, pcy, _pw, _ph in pred:
        best_j, best_d = -1, None
        for j, (gcx, gcy, gw, gh) in enumerate(gt):
            if gt_used[j]:
                continue
            thr = tol_frac * max(gw, gh, tol_min)
            d = ((gcx - pcx) ** 2 + (gcy - pcy) ** 2) ** 0.5
            if d <= thr and (best_d is None or d < best_d):
                best_d, best_j = d, j
        if best_j >= 0:
            gt_used[best_j] = True
            tp += 1
    return tp


def collect_cells(
    repo_root: Path, sources: list[tuple[str, str]], cells_dirs: list[Path],
    nh_idx: set[int],
) -> list[dict]:
    """Resolve every (label, cell PNG) pair and load its notehead GT once.

    Uses Pillow to read image size (cheap, no torch needed)."""
    from PIL import Image

    cells = []
    missing = []
    for tag, rel_glob in sources:
        for lbl in sorted(glob.glob(str(repo_root / rel_glob))):
            lbl = Path(lbl)
            stem = lbl.stem
            png = find_cell_png(stem, cells_dirs)
            if png is None:
                missing.append(stem)
                continue
            with Image.open(png) as im:
                w, h = im.size
            gt = load_gt_noteheads(lbl, w, h, nh_idx)
            cells.append({"tag": tag, "stem": stem, "png": png,
                          "gt": gt, "n_gt": len(gt)})
    if missing:
        print(f"WARNING: {len(missing)} labels had no cell PNG "
              f"(first few: {missing[:5]})")
    return cells


def evaluate(
    weights: str, label: str, cells: list[dict], imgsz: int, conf: float,
    device: str, tol_frac: float, tol_min: float,
) -> dict:
    from ultralytics import YOLO
    import warnings
    warnings.filterwarnings("ignore")
    model = YOLO(weights)

    by_src: dict[str, dict] = defaultdict(lambda: {"tp": 0, "n_gt": 0, "n_pred": 0})
    per_cell = []
    for c in cells:
        if c["n_gt"] == 0:
            continue
        pred = model_notehead_centers(model, c["png"], imgsz, conf, device)
        tp = match_recall(c["gt"], pred, tol_frac, tol_min)
        s = by_src[c["tag"]]
        s["tp"] += tp
        s["n_gt"] += c["n_gt"]
        s["n_pred"] += len(pred)
        per_cell.append({"stem": c["stem"], "tag": c["tag"], "n_gt": c["n_gt"],
                         "n_pred": len(pred), "tp": tp})

    def _finalize(d: dict) -> dict:
        rec = d["tp"] / d["n_gt"] if d["n_gt"] else 0.0
        prec = d["tp"] / d["n_pred"] if d["n_pred"] else 0.0
        return {**d, "recall": rec, "precision": prec}

    per_src = {tag: _finalize(dict(v)) for tag, v in by_src.items()}
    tot = {"tp": sum(v["tp"] for v in by_src.values()),
           "n_gt": sum(v["n_gt"] for v in by_src.values()),
           "n_pred": sum(v["n_pred"] for v in by_src.values())}
    return {"label": label, "weights": Path(weights).name,
            "overall": _finalize(tot), "per_source": per_src,
            "per_cell": per_cell}


def render(results: list[dict]) -> str:
    srcs = sorted({s for r in results for s in r["per_source"]})
    L = ["=" * 78,
         "  Dense-orchestral notehead RECALL (hand-labeled real cells, not in DSv2)",
         "=" * 78,
         "recall = matched GT noteheads / total GT noteheads (center-match).",
         "precision is confounded by incomplete human GT — context only.", ""]
    # recall table
    hdr = f"{'source':<10}{'GT':>6}  " + "".join(f"{r['label']:>16}" for r in results)
    L.append("RECALL  (higher = finds more real noteheads)")
    L.append(hdr)
    for s in srcs:
        n_gt = next((r["per_source"][s]["n_gt"] for r in results if s in r["per_source"]), 0)
        row = f"{s:<10}{n_gt:>6}  "
        for r in results:
            v = r["per_source"].get(s)
            row += f"{(v['recall'] if v else 0):>15.3f} "
        L.append(row)
    # overall
    n_gt_all = results[0]["overall"]["n_gt"] if results else 0
    row = f"{'OVERALL':<10}{n_gt_all:>6}  "
    for r in results:
        row += f"{r['overall']['recall']:>15.3f} "
    L.append(row)
    L.append("")
    # tp/pred detail
    L.append("detail (TP / n_pred noteheads):")
    L.append(f"{'source':<10}          " + "".join(f"{r['label']:>16}" for r in results))
    for s in srcs:
        row = f"{s:<10}          "
        for r in results:
            v = r["per_source"].get(s)
            cell = f"{v['tp']}/{v['n_pred']}" if v else "-"
            row += f"{cell:>16}"
        L.append(row)
    L.append("=" * 78)
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", nargs="+", required=True,
                    help="One or more checkpoint .pt files (Baseline A B ...).")
    ap.add_argument("--labels", nargs="*", default=None,
                    help="Display label per weights file (default: filename).")
    ap.add_argument("--repo-root", type=Path, default=Path("."),
                    help="Repo root that --labels globs + cells dirs resolve under.")
    ap.add_argument("--catalog", type=Path,
                    default=Path("data/user-labeled/catalog-214.yaml"),
                    help="Label catalog the GT .txt files were emitted against.")
    ap.add_argument("--cells-subdirs", nargs="*", default=DEFAULT_CELLS_SUBDIRS,
                    help="Cell-PNG dirs (relative to --repo-root), searched in order.")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--device", default="0")
    ap.add_argument("--tol-frac", type=float, default=0.6,
                    help="Center-match tolerance as a fraction of GT box size.")
    ap.add_argument("--tol-min", type=float, default=40.0,
                    help="Floor (px) for the size used in the tolerance.")
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args(argv)

    repo = args.repo_root.resolve()
    catalog = args.catalog if args.catalog.is_absolute() else repo / args.catalog
    nh_idx = notehead_catalog_indices(catalog)
    cells_dirs = [repo / d for d in args.cells_subdirs]

    cells = collect_cells(repo, DEFAULT_SOURCES, cells_dirs, nh_idx)
    n_by_src: dict[str, int] = defaultdict(int)
    gt_by_src: dict[str, int] = defaultdict(int)
    for c in cells:
        n_by_src[c["tag"]] += 1
        gt_by_src[c["tag"]] += c["n_gt"]
    print(f"notehead catalog indices: {sorted(nh_idx)}")
    print("cells resolved: " + ", ".join(
        f"{t}={n_by_src[t]} ({gt_by_src[t]} GT noteheads)" for t in sorted(n_by_src)))
    print(f"total: {len(cells)} cells, {sum(gt_by_src.values())} GT noteheads\n")

    labels = args.labels or [Path(w).stem for w in args.weights]
    if len(labels) != len(args.weights):
        return _err("--labels count must match --weights count")

    results = []
    for w, lab in zip(args.weights, labels):
        print(f"scoring {lab}  ({w}) ...")
        results.append(evaluate(w, lab, cells, args.imgsz, args.conf,
                                args.device, args.tol_frac, args.tol_min))

    report = render(results)
    print("\n" + report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps({
            "config": {"imgsz": args.imgsz, "conf": args.conf,
                       "tol_frac": args.tol_frac, "tol_min": args.tol_min,
                       "catalog": str(catalog), "nh_idx": sorted(nh_idx)},
            "results": results,
        }, indent=2))
        (args.json_out.with_suffix(".txt")).write_text(report + "\n")
        print(f"\nwrote {args.json_out}")
    return 0


def _err(msg: str) -> int:
    print(f"ERROR: {msg}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
