"""Fine-tune YOLOv8m on the prepared DeepScoresV2 dataset.

Wraps `ultralytics.YOLO.train()`. Designed to fail fast (and clearly) if
the data.yaml or weights file is missing — long GPU sessions are
expensive and there's no point spending an hour training only to
discover a path typo on epoch 0.

Hardware tier expectations (full 50-epoch run at imgsz=1280):

    - Apple Silicon M-series GPU (MPS)  ~12-24 hours; not recommended
      for anything beyond smoke testing — ultralytics MPS support is
      functional but slower than CUDA per-watt
    - RTX 3070 / 3080 (8-10 GB)         ~14-20 hours
    - RTX 3090 / 4090 (24 GB)           ~10-16 hours
    - A100 / H100 (40-80 GB)            ~4-8 hours

Smoke mode (`--smoke`): 1 epoch on a synthesized 10-image dataset.
Should take <2 min on MPS or <30 s on an RTX 3090.

CLI:
    python3 -m tools.omr.training.train_yolo \
        --data data/deepscoresv2-yolo/data.yaml \
        --weights yolov8m.pt \
        --epochs 50 --imgsz 1280 --batch 16 \
        --device 0 \
        --project data/deepscoresv2-yolo/runs --name fine-tune-v1

    python3 -m tools.omr.training.train_yolo --smoke
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _fail(msg: str, code: int = 2) -> "int":
    print(f"ERROR: {msg}", file=sys.stderr)
    return code


def _validate_inputs(data_yaml: Path, weights: str) -> int | None:
    if not data_yaml.exists():
        return _fail(
            f"data.yaml not found at {data_yaml}. "
            "Run `python3 -m tools.omr.training.prepare_yolo_data` first."
        )

    # Weights: either a path that exists, or an ultralytics auto-download
    # alias like "yolov8m.pt". We treat any non-existent path that ends
    # in `.pt` and contains no slash as an alias and let ultralytics
    # handle the download.
    weights_path = Path(weights)
    looks_like_alias = (
        weights.endswith(".pt")
        and "/" not in weights
        and not weights_path.exists()
    )
    if not weights_path.exists() and not looks_like_alias:
        return _fail(f"weights not found and not a known alias: {weights}")
    return None


# ---------------------------------------------------------------------------
# Smoke mode — runs a 1-epoch training on a tiny synthesized dataset
# ---------------------------------------------------------------------------


def _build_smoke_dataset(workdir: Path) -> Path:
    """Synthesize a 10-image, 1-class dataset for smoke testing.

    Returns the path to data.yaml. Real images are drawn with PIL so the
    YOLO loader can actually read them; one synthetic bounding box per
    image.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise SystemExit(f"smoke mode requires Pillow: {exc}")
    import yaml

    images = workdir / "images" / "train"
    labels = workdir / "labels" / "train"
    val_images = workdir / "images" / "val"
    val_labels = workdir / "labels" / "val"
    for d in (images, labels, val_images, val_labels):
        d.mkdir(parents=True, exist_ok=True)

    def _draw(path: Path, label_path: Path, *, offset: int) -> None:
        im = Image.new("RGB", (320, 320), "white")
        draw = ImageDraw.Draw(im)
        x0, y0 = 50 + offset, 50 + offset
        x1, y1 = x0 + 100, y0 + 80
        draw.rectangle([x0, y0, x1, y1], outline="black", width=3)
        im.save(path)
        cx = (x0 + x1) / 2.0 / 320
        cy = (y0 + y1) / 2.0 / 320
        w = (x1 - x0) / 320
        h = (y1 - y0) / 320
        label_path.write_text(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

    for i in range(8):
        _draw(images / f"smoke_{i}.png", labels / f"smoke_{i}.txt", offset=i * 5)
    for i in range(2):
        _draw(val_images / f"smoke_val_{i}.png",
              val_labels / f"smoke_val_{i}.txt", offset=i * 5)

    data_yaml = workdir / "data.yaml"
    data_yaml.write_text(yaml.safe_dump({
        "path": str(workdir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "nc": 1,
        "names": ["smoke_box"],
    }, sort_keys=False))
    return data_yaml


# ---------------------------------------------------------------------------
# Training entrypoint
# ---------------------------------------------------------------------------


def train(
    *,
    data_yaml: Path,
    weights: str,
    epochs: int,
    imgsz: int,
    batch: int,
    device: str,
    patience: int,
    project: Path,
    name: str,
    workers: int,
    extra_kwargs: dict | None = None,
) -> dict:
    """Fire up ultralytics.YOLO.train(). Returns a summary dict.

    Imports ultralytics lazily so `--help` works without it installed.
    """
    from ultralytics import YOLO  # type: ignore

    model = YOLO(weights)
    project.mkdir(parents=True, exist_ok=True)
    kwargs = dict(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device if device != "auto" else None,
        patience=patience,
        project=str(project),
        name=name,
        workers=workers,
    )
    if extra_kwargs:
        kwargs.update(extra_kwargs)
    results = model.train(**kwargs)

    # `results` is an ultralytics Results object (the metrics). Return
    # what's serializable.
    save_dir = getattr(getattr(model, "trainer", None), "save_dir", None) or (project / name)
    return {
        "weights_path": str(Path(save_dir) / "weights" / "best.pt"),
        "save_dir": str(save_dir),
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": batch,
        "device": device,
        "metrics": getattr(results, "results_dict", None) or {},
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", default="data/deepscoresv2-yolo/data.yaml",
                    help="Path to data.yaml from prepare_yolo_data.py")
    ap.add_argument("--weights", default="yolov8m.pt",
                    help="Starting weights (path or ultralytics alias)")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--imgsz", type=int, default=1280,
                    help="Training image size (music symbols are small; "
                         "1280 is a good default)")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default="0",
                    help='"0" for cuda:0, "cpu", "mps", or "auto"')
    ap.add_argument("--patience", type=int, default=10,
                    help="Early-stop patience in epochs")
    ap.add_argument("--project", default="data/deepscoresv2-yolo/runs",
                    help="ultralytics 'project' directory (runs root)")
    ap.add_argument("--name", default="ds2-yolov8m",
                    help="ultralytics 'name' for this run")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--smoke", action="store_true",
                    help="Run a 1-epoch synthetic-data smoke test")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.smoke:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="yolo_smoke_") as td:
            workdir = Path(td)
            data_yaml = _build_smoke_dataset(workdir)
            print(f"smoke dataset built at {workdir}", file=sys.stderr)
            try:
                report = train(
                    data_yaml=data_yaml,
                    weights=args.weights,
                    epochs=1,
                    imgsz=320,
                    batch=2,
                    device=args.device,
                    patience=1,
                    project=workdir / "runs",
                    name="smoke",
                    workers=0,
                )
            except Exception as exc:  # noqa: BLE001
                return _fail(f"smoke train failed: {exc}", code=3)
        print(json.dumps(report, indent=2))
        return 0

    data_yaml = Path(args.data)
    bad = _validate_inputs(data_yaml, args.weights)
    if bad is not None:
        return bad

    report = train(
        data_yaml=data_yaml,
        weights=args.weights,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        patience=args.patience,
        project=Path(args.project),
        name=args.name,
        workers=args.workers,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
