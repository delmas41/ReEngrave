"""Convert DeepScoresV2 annotations into YOLO format.

DeepScoresV2 ships its annotations in an extended-COCO JSON format. The
key extension is **oriented bounding boxes** (OBBs): each annotation has
both a standard axis-aligned `a_bbox` (xmin, ymin, xmax, ymax in absolute
pixel coords) and an oriented `o_bbox` (8-value polygon: x1, y1, ..., x4,
y4 in absolute pixel coords). YOLOv8 by default consumes axis-aligned
boxes (the OBB variant is YOLOv8-OBB; we use the simpler standard model
here and consume `a_bbox`).

DeepScoresV2 JSON schema (per `deepscores_train.json` /
`deepscores_test.json`, source: https://github.com/yvan674/obb_anns):

    {
        "info": {...},
        "annotation_sets": ["deepscores", "muscima"],
        "categories": {
            "1": {"name": "brace", "color": "#ff0000", ...},
            "2": {"name": "ledgerLine", ...},
            ...
        },
        "images": [
            {"id": 0, "filename": "lg-1...-foo.png", "width": 1960, "height": 2772},
            ...
        ],
        "annotations": {
            "0": {
                "a_bbox": [xmin, ymin, xmax, ymax],   # axis-aligned absolute
                "o_bbox": [x1, y1, x2, y2, x3, y3, x4, y4],  # oriented absolute
                "cat_id": ["12", "..."],  # list (one per annotation_set)
                "area": ...,
                "img_id": 0,
                "comments": ""
            },
            ...
        }
    }

Note the category id strings (not ints) and the per-image annotation list
keyed under `annotations` by string id (not image id). This script handles
both shapes (some DeepScoresV2 versions wrap annotations as a flat list
keyed by image_id; some as a single dict). When in doubt the script
inspects the JSON before assuming.

YOLO format output (one `.txt` per image, alongside the .png in a parallel
labels/ directory):

    <class_id> <cx_norm> <cy_norm> <w_norm> <h_norm>
    ...

where `class_id` is a 0-indexed integer into the `names` array of
`data.yaml`, and all coords are normalized to [0..1] using image
width/height.

CLI:
    python3 -m tools.omr.training.prepare_yolo_data \
        --src data/deepscoresv2 --dst data/deepscoresv2-yolo
    python3 -m tools.omr.training.prepare_yolo_data --dry-run \
        --dst data/deepscoresv2-yolo-mock

In --dry-run mode no real dataset is required; the script synthesizes a
tiny mock (2 images, 3 annotations) and exercises the full conversion
path. This is what the test suite uses.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from .deepscores_classes import DEEPSCORES_V2_CLASSES


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class ImageInfo:
    id: int
    filename: str
    width: int
    height: int


@dataclass
class Annotation:
    img_id: int
    cat_id: int  # 0-indexed into the YOLO class list
    xmin: float
    ymin: float
    xmax: float
    ymax: float


# ---------------------------------------------------------------------------
# Conversion math
# ---------------------------------------------------------------------------


def bbox_to_yolo(
    xmin: float, ymin: float, xmax: float, ymax: float, *, img_w: int, img_h: int,
) -> tuple[float, float, float, float]:
    """Convert (xmin, ymin, xmax, ymax) in absolute pixels to
    (cx_norm, cy_norm, w_norm, h_norm) in [0..1].

    Clamps to [0..1] in case an annotation extends slightly past the image
    edge (DeepScoresV2 has a few of those).
    """
    if img_w <= 0 or img_h <= 0:
        raise ValueError(f"non-positive image dims: {img_w} x {img_h}")
    cx = (xmin + xmax) / 2.0 / img_w
    cy = (ymin + ymax) / 2.0 / img_h
    w = (xmax - xmin) / img_w
    h = (ymax - ymin) / img_h
    cx = min(1.0, max(0.0, cx))
    cy = min(1.0, max(0.0, cy))
    w = min(1.0, max(0.0, w))
    h = min(1.0, max(0.0, h))
    return cx, cy, w, h


def yolo_to_bbox(
    cx: float, cy: float, w: float, h: float, *, img_w: int, img_h: int,
) -> tuple[float, float, float, float]:
    """Inverse of `bbox_to_yolo`. Used by tests for round-trip checks."""
    abs_cx = cx * img_w
    abs_cy = cy * img_h
    abs_w = w * img_w
    abs_h = h * img_h
    return (
        abs_cx - abs_w / 2.0,
        abs_cy - abs_h / 2.0,
        abs_cx + abs_w / 2.0,
        abs_cy + abs_h / 2.0,
    )


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------


def _parse_categories(raw_cats: dict | list) -> list[str]:
    """Return a class-name list ordered by category id ascending.

    DeepScoresV2 ships categories as a dict keyed by string id. We map
    each id -> name and emit in id order so the resulting YOLO class_id
    column matches `categories.id - 1` (DeepScoresV2 is 1-indexed; YOLO
    is 0-indexed).
    """
    if isinstance(raw_cats, dict):
        # keys may be strings or ints
        items = sorted(((int(k), v.get("name") if isinstance(v, dict) else str(v))
                        for k, v in raw_cats.items()), key=lambda kv: kv[0])
        return [name for _, name in items]
    if isinstance(raw_cats, list):
        # COCO-style list of {id, name}
        items = sorted(((int(c["id"]), c["name"]) for c in raw_cats),
                       key=lambda kv: kv[0])
        return [name for _, name in items]
    raise ValueError(f"unrecognized categories shape: {type(raw_cats)}")


def _parse_images(raw_imgs: list[dict]) -> dict[int, ImageInfo]:
    out: dict[int, ImageInfo] = {}
    for entry in raw_imgs:
        img = ImageInfo(
            id=int(entry["id"]),
            filename=str(entry["filename"]),
            width=int(entry["width"]),
            height=int(entry["height"]),
        )
        out[img.id] = img
    return out


def _annotation_cat_id(raw_cat: object) -> int:
    """Extract the DeepScoresV2 `cat_id` from an annotation.

    Some releases ship `cat_id` as a 2-element list (one id per
    annotation_set: ["deepscores_id", "muscima_id"]). We always want the
    first (DeepScoresV2 native) id. Some releases ship it as a single
    string or int.
    """
    if isinstance(raw_cat, list) and raw_cat:
        return int(raw_cat[0])
    return int(raw_cat)  # type: ignore[arg-type]


def _parse_annotations(
    raw_ann: dict | list, *, image_index: dict[int, ImageInfo],
) -> list[Annotation]:
    """Yield Annotation per record. Tolerant of both dict- and list-shaped
    annotation containers.
    """
    annotations: list[Annotation] = []
    iterable: Iterable[dict]
    if isinstance(raw_ann, dict):
        iterable = raw_ann.values()
    elif isinstance(raw_ann, list):
        iterable = raw_ann
    else:
        raise ValueError(f"unrecognized annotations shape: {type(raw_ann)}")

    for rec in iterable:
        img_id = int(rec["img_id"])
        if img_id not in image_index:
            continue  # orphan annotation
        a = rec.get("a_bbox") or rec.get("bbox")
        if not a:
            continue
        xmin, ymin, xmax, ymax = (float(a[0]), float(a[1]), float(a[2]), float(a[3]))
        cat_id_1based = _annotation_cat_id(rec["cat_id"])
        annotations.append(Annotation(
            img_id=img_id,
            cat_id=cat_id_1based - 1,  # 1-based -> 0-based for YOLO
            xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax,
        ))
    return annotations


def load_deepscores_json(path: Path) -> tuple[list[str], dict[int, ImageInfo], list[Annotation]]:
    """Read a single DeepScoresV2 annotation file and return
    (class_names, image_index, annotations).
    """
    data = json.loads(path.read_text())
    cats = _parse_categories(data.get("categories", {}))
    imgs = _parse_images(data.get("images", []))
    anns = _parse_annotations(data.get("annotations", []), image_index=imgs)
    return cats, imgs, anns


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def write_yolo_labels(
    annotations_by_image: dict[int, list[Annotation]],
    image_index: dict[int, ImageInfo],
    labels_dir: Path,
) -> int:
    """Write `<labels_dir>/<image_stem>.txt` files. Returns count written."""
    labels_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for img_id, anns in annotations_by_image.items():
        img = image_index[img_id]
        stem = Path(img.filename).stem
        lines: list[str] = []
        for a in anns:
            cx, cy, w, h = bbox_to_yolo(
                a.xmin, a.ymin, a.xmax, a.ymax,
                img_w=img.width, img_h=img.height,
            )
            lines.append(f"{a.cat_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        (labels_dir / f"{stem}.txt").write_text("\n".join(lines) + "\n")
        n += 1
    return n


def write_data_yaml(
    *,
    dst: Path,
    class_names: list[str],
    train_images_dir: Path,
    val_images_dir: Path,
    test_images_dir: Path | None = None,
) -> Path:
    """Write the ultralytics-style data.yaml that train_yolo.py consumes."""
    payload: dict = {
        "path": str(dst.resolve()),
        "train": str(train_images_dir.relative_to(dst) if train_images_dir.is_relative_to(dst) else train_images_dir),
        "val": str(val_images_dir.relative_to(dst) if val_images_dir.is_relative_to(dst) else val_images_dir),
        "nc": len(class_names),
        "names": class_names,
    }
    if test_images_dir is not None:
        payload["test"] = str(
            test_images_dir.relative_to(dst)
            if test_images_dir.is_relative_to(dst) else test_images_dir
        )
    dst.mkdir(parents=True, exist_ok=True)
    path = dst / "data.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False))
    return path


# ---------------------------------------------------------------------------
# Real-data conversion path
# ---------------------------------------------------------------------------


def convert_split(
    *,
    json_path: Path,
    src_images_dir: Path,
    dst_images_dir: Path,
    dst_labels_dir: Path,
    symlink_images: bool = True,
) -> tuple[list[str], int, int]:
    """Convert one annotation file (one split). Returns
    (class_names, n_images_linked, n_labels_written).
    """
    class_names, image_index, anns = load_deepscores_json(json_path)

    # Bucket annotations by image
    by_img: dict[int, list[Annotation]] = {}
    for a in anns:
        by_img.setdefault(a.img_id, []).append(a)
    # Ensure every image gets a label file even if empty
    for img_id in image_index:
        by_img.setdefault(img_id, [])

    n_labels = write_yolo_labels(by_img, image_index, dst_labels_dir)

    # Symlink (or copy) image files into dst_images_dir so the YOLO
    # loader can find them. Ultralytics expects images/labels in
    # parallel sibling directories.
    dst_images_dir.mkdir(parents=True, exist_ok=True)
    n_imgs = 0
    for img in image_index.values():
        src = src_images_dir / img.filename
        dst = dst_images_dir / Path(img.filename).name
        if dst.exists():
            n_imgs += 1
            continue
        if not src.exists():
            continue  # tolerate missing images; ultralytics will warn
        if symlink_images:
            try:
                dst.symlink_to(src.resolve())
            except OSError:
                shutil.copy2(src, dst)
        else:
            shutil.copy2(src, dst)
        n_imgs += 1
    return class_names, n_imgs, n_labels


def convert_dataset(
    *,
    src: Path,
    dst: Path,
    symlink_images: bool = True,
) -> dict:
    """Convert the full DeepScoresV2 source tree at `src` into a YOLO
    dataset rooted at `dst`. Expected layout under `src`:

        deepscoresv2/
          images/                       (all .png files)
          deepscores_train.json
          deepscores_test.json

    Output:

        deepscoresv2-yolo/
          images/train/
          images/val/
          labels/train/
          labels/val/
          data.yaml
    """
    src = src.resolve()
    dst = dst.resolve()

    images_src = src / "images"
    train_json = src / "deepscores_train.json"
    val_json = src / "deepscores_test.json"

    if not images_src.exists():
        raise FileNotFoundError(f"expected images directory at {images_src}")
    if not train_json.exists():
        raise FileNotFoundError(f"expected {train_json}")
    if not val_json.exists():
        raise FileNotFoundError(f"expected {val_json}")

    train_imgs_dst = dst / "images" / "train"
    val_imgs_dst = dst / "images" / "val"
    train_labels_dst = dst / "labels" / "train"
    val_labels_dst = dst / "labels" / "val"

    train_classes, n_tr_imgs, n_tr_lbls = convert_split(
        json_path=train_json,
        src_images_dir=images_src,
        dst_images_dir=train_imgs_dst,
        dst_labels_dir=train_labels_dst,
        symlink_images=symlink_images,
    )
    val_classes, n_va_imgs, n_va_lbls = convert_split(
        json_path=val_json,
        src_images_dir=images_src,
        dst_images_dir=val_imgs_dst,
        dst_labels_dir=val_labels_dst,
        symlink_images=symlink_images,
    )

    # The two splits should use the same class list. If they disagree,
    # the train set is authoritative (it's larger).
    if train_classes != val_classes:
        print(
            "  WARNING: train and val class lists differ; "
            "using train classes for data.yaml",
            file=sys.stderr,
        )

    yaml_path = write_data_yaml(
        dst=dst,
        class_names=train_classes,
        train_images_dir=train_imgs_dst,
        val_images_dir=val_imgs_dst,
    )

    return {
        "data_yaml": str(yaml_path),
        "n_classes": len(train_classes),
        "train": {"images_linked": n_tr_imgs, "labels_written": n_tr_lbls},
        "val": {"images_linked": n_va_imgs, "labels_written": n_va_lbls},
    }


# ---------------------------------------------------------------------------
# Mock data for --dry-run
# ---------------------------------------------------------------------------


def _build_mock_dataset_json(class_names: list[str]) -> dict:
    """Build a minimal DeepScoresV2-shaped JSON for testing.

    Two 100x100 images, three annotations spread across them.
    """
    # 1-based category ids (DeepScoresV2 convention)
    categories = {str(i + 1): {"name": n} for i, n in enumerate(class_names)}
    images = [
        {"id": 0, "filename": "mock_001.png", "width": 100, "height": 100},
        {"id": 1, "filename": "mock_002.png", "width": 200, "height": 100},
    ]
    annotations = {
        "0": {
            "img_id": 0,
            "cat_id": ["1", "1"],
            "a_bbox": [10, 20, 30, 40],
            "o_bbox": [10, 20, 30, 20, 30, 40, 10, 40],
            "area": 400, "comments": "",
        },
        "1": {
            "img_id": 0,
            "cat_id": ["2"],
            "a_bbox": [50, 50, 70, 80],
            "o_bbox": [50, 50, 70, 50, 70, 80, 50, 80],
            "area": 600, "comments": "",
        },
        "2": {
            "img_id": 1,
            "cat_id": ["6"],  # gClef per the snapshot
            "a_bbox": [100, 10, 180, 90],
            "o_bbox": [100, 10, 180, 10, 180, 90, 100, 90],
            "area": 6400, "comments": "",
        },
    }
    return {
        "info": {"version": "mock"},
        "annotation_sets": ["deepscores"],
        "categories": categories,
        "images": images,
        "annotations": annotations,
    }


def dry_run_conversion(dst: Path) -> dict:
    """Synthesize a tiny dataset in `dst` and run the conversion path on
    it. Touches no network.

    Returns a report dict suitable for tests to assert on.
    """
    class_names = DEEPSCORES_V2_CLASSES
    mock_root = dst / "_mock_src"
    mock_images_dir = mock_root / "images"
    mock_images_dir.mkdir(parents=True, exist_ok=True)
    # Create empty placeholder PNG files so symlinking works
    for img in _build_mock_dataset_json(class_names)["images"]:
        p = mock_images_dir / img["filename"]
        # Minimal valid PNG header + IEND so it's at least a real file
        # on disk (size won't match image dims, but YOLO only reads the
        # image at training time — the conversion script only needs the
        # JSON's image dims).
        p.write_bytes(_MINIMAL_PNG)

    train_json = mock_root / "deepscores_train.json"
    val_json = mock_root / "deepscores_test.json"
    payload = _build_mock_dataset_json(class_names)
    train_json.write_text(json.dumps(payload))
    val_json.write_text(json.dumps(payload))

    result = convert_dataset(src=mock_root, dst=dst, symlink_images=False)
    result["mode"] = "dry-run"
    return result


# A 1x1 transparent PNG (smallest possible valid PNG, ~67 bytes)
_MINIMAL_PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15"
    "C4890000000D49444154789C6360000000000200015A0D5D8B0000000049454E44"
    "AE426082"
)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", default="data/deepscoresv2",
                    help="Path to extracted DeepScoresV2 root")
    ap.add_argument("--dst", default="data/deepscoresv2-yolo",
                    help="Output directory for YOLO-format dataset")
    ap.add_argument("--dry-run", action="store_true",
                    help="Synthesize a tiny mock dataset and run conversion")
    ap.add_argument("--no-symlink", action="store_true",
                    help="Copy images into the dst dir instead of symlinking")
    args = ap.parse_args(argv)

    dst = Path(args.dst)
    if args.dry_run:
        report = dry_run_conversion(dst)
    else:
        report = convert_dataset(
            src=Path(args.src), dst=dst, symlink_images=not args.no_symlink,
        )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
