"""Convert human-reviewed verdict JSON files into YOLO-format training labels.

This is the bridge from the labeling UI (which writes
`<cell_id>.verdict.json` files containing per-detection TP/FP verdicts and
human-added FN detections) into a YOLO training set that lives under
`data/user-labeled/<version>/`. The output is a fresh "session" directory
whose contents never get modified again — each future labeling pass writes
a new versioned directory and `build_catalog_yaml.py` unions them.

For each cell with a verdict JSON, we emit:

  data/user-labeled/<version>/
    images/<cell_id>.png        ← copied / symlinked from the cell PNG
    labels/<cell_id>.txt        ← YOLO format: cls_id cx cy w h (normalized)

Two verdict schemas are supported (the labeling UI writes v2; older runs
shipped v1).

Schema v2 conversion rules (the canonical / current schema)
-----------------------------------------------------------

  TP                  → keep model_bbox, class = model_predicted_class
  WRONG_CATEGORY      → keep model_bbox, class = human_corrected_class
  WRONG_BBOX          → use human_bbox, class = model_predicted_class
                         (or human_corrected_class if also set — the UI
                         allows both)
  FP                  → drop (model hallucinated)
  unsure              → drop (no signal)
  added_detections[]  → use bbox, class = human_class
                         (these are FNs the human drew on the image)

Schema v1 (backward-compat path)
--------------------------------

  TP                  → keep bbox, class = detection's smufl_name
  TP w/ wrong_pitch   → same as TP (pitch is not part of YOLO label space)
  FP w/o actual_label → drop
  FP w/  actual_label → keep bbox, class = actual_label (WRONG_CATEGORY)
  "" / "unsure"       → drop
  fn_noteheads[]      → synthesize bbox at (x, y) from median TP-notehead
                         size in the same cell; class defaults to
                         "noteheadBlackOnLine"

CLI:
    python3 -m tools.omr.training.verdicts_to_yolo_labels \\
        --verdicts-dir benchmarks/omr-phase-realft/verdicts \\
        --detections-dir benchmarks/omr-phase-realft/detections \\
        --manifest        benchmarks/omr-phase-realft/cells.json \\
        --version-name    v1-2026-05-17-orchestral \\
        --out-root        data/user-labeled \\
        --labeler         sean \\
        --description     "Beethoven 5 / Mahler 5 / La Mer / Bolero, 186 cells"
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .deepscores_classes import DEEPSCORES_V2_CLASSES


# Default bbox size for human-added FN noteheads, in canonical pixels.
# The labeling UI only captures a center point, so we have to estimate
# width/height. Numbers picked from inspection of typical notehead bboxes
# at 4 px / staff-line-spacing (the canonical scale).
_FN_DEFAULT_W = 28
_FN_DEFAULT_H = 32
# Default class for FN noteheads (the UI doesn't capture class today).
_FN_DEFAULT_CLASS = "noteheadBlackOnLine"


# ---------------------------------------------------------------------------
# Class mapping
# ---------------------------------------------------------------------------


def load_class_names(weights_path: Path | None, fallback_json: Path | None) -> list[str]:
    """Resolve the canonical class-name list.

    Preference order:
      1. weights_path     — read `model.names` from a .pt file. This is the
                            ground truth: it's what the trained model uses
                            and what fine-tuning will need to match.
      2. fallback_json    — a JSON list dumped from a prior load (so the
                            scripts work without torch installed).
      3. DEEPSCORES_V2_CLASSES — the in-repo snapshot. May be smaller than
                            the model's actual class list, so this is a
                            last resort.
    """
    if weights_path is not None and weights_path.exists():
        try:
            import torch  # local import — heavy
        except ImportError:
            torch = None
        if torch is not None:
            ckpt = torch.load(str(weights_path), map_location="cpu", weights_only=False)
            model = ckpt.get("model") if isinstance(ckpt, dict) else ckpt
            names = getattr(model, "names", None)
            if isinstance(names, dict):
                return [names[i] for i in sorted(int(k) for k in names.keys())]
            if isinstance(names, list):
                return list(names)
    if fallback_json is not None and fallback_json.exists():
        return json.loads(fallback_json.read_text())
    return list(DEEPSCORES_V2_CLASSES)


def name_to_first_index(class_names: list[str]) -> dict[str, int]:
    """Map class name → first occurrence index.

    DeepScoresV2's 208-class list contains duplicate names (two annotation
    sets overlap, e.g. `clefG` at both 5 and 141). The model emits the
    first occurrence so we mirror that.
    """
    out: dict[str, int] = {}
    for i, n in enumerate(class_names):
        out.setdefault(n, i)
    return out


# ---------------------------------------------------------------------------
# Per-cell conversion
# ---------------------------------------------------------------------------


@dataclass
class CellSummary:
    cell_id: str
    schema_version: int = 1
    n_tp: int = 0
    n_fp_dropped: int = 0
    n_wrong_cat: int = 0
    n_wrong_bbox: int = 0
    # n_fn_added counts human-added detections (v1: fn_noteheads,
    # v2: added_detections — same role, different name in the schema).
    n_fn_added: int = 0
    n_unsure_dropped: int = 0
    n_pending_dropped: int = 0
    n_dropped_unknown_class: int = 0
    classes_written: list[str] = field(default_factory=list)


@dataclass
class CellArtifacts:
    """Inputs for a single cell."""

    cell_id: str
    cell_png: Path
    canonical_w: int
    canonical_h: int
    detections: dict[str, dict]  # detection_id → detection dict


def _load_manifest(manifest_path: Path) -> dict[str, dict]:
    entries = json.loads(manifest_path.read_text())
    return {e["cell_id"]: e for e in entries}


def _load_detections(detections_dir: Path, cell_id: str) -> dict[str, dict]:
    p = detections_dir / f"{cell_id}.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {d["id"]: d for d in data.get("detections", [])}


def _median_notehead_size_v1(
    detections: dict[str, dict],
    verdicts: list[dict],
) -> tuple[int, int] | None:
    """Schema v1: median (w, h) over TP-verdicted noteheads in this cell.

    Returns None if no notehead TPs exist.
    """
    ws: list[int] = []
    hs: list[int] = []
    for v in verdicts:
        if v.get("verdict") != "TP":
            continue
        d = detections.get(v["detection_id"])
        if d is None:
            continue
        smufl = d.get("smufl_name", "")
        if "notehead" not in smufl.lower():
            continue
        ws.append(int(d.get("w") or 0))
        hs.append(int(d.get("h") or 0))
    if not ws or not hs:
        return None
    return int(statistics.median(ws)), int(statistics.median(hs))


def _emit_yolo_line(
    *,
    class_name: str,
    bbox: dict | None,
    img_w: int,
    img_h: int,
    class_index: dict[str, int],
) -> str | None:
    """Format one YOLO label line. Returns None if the class is unknown or
    the bbox degenerates after clamping."""
    cls_id = class_index.get(class_name)
    if cls_id is None or bbox is None:
        return None
    x = float(bbox.get("x", 0))
    y = float(bbox.get("y", 0))
    w = float(bbox.get("w", 0))
    h = float(bbox.get("h", 0))
    cx = max(0.0, min(1.0, (x + w / 2.0) / img_w))
    cy = max(0.0, min(1.0, (y + h / 2.0) / img_h))
    wn = max(0.0, min(1.0, w / img_w))
    hn = max(0.0, min(1.0, h / img_h))
    if wn <= 0 or hn <= 0:
        return None
    return f"{cls_id} {cx:.6f} {cy:.6f} {wn:.6f} {hn:.6f}"


def _convert_v2(
    *,
    cell_id: str,
    state: dict,
    img_w: int,
    img_h: int,
    class_index: dict[str, int],
) -> tuple[list[str], CellSummary]:
    """Schema v2 conversion (current canonical schema)."""
    summary = CellSummary(cell_id=cell_id, schema_version=2)
    lines: list[str] = []
    classes_seen: set[str] = set()

    for d in state.get("detections", []):
        verdict = (d.get("verdict") or "").strip()
        if not verdict:
            summary.n_pending_dropped += 1
            continue
        if verdict == "unsure":
            summary.n_unsure_dropped += 1
            continue
        if verdict == "FP":
            summary.n_fp_dropped += 1
            continue

        if verdict == "TP":
            class_name = (d.get("model_predicted_class") or "").strip()
            bbox = d.get("model_bbox")
            summary.n_tp += 1
        elif verdict == "WRONG_CATEGORY":
            class_name = (
                d.get("human_corrected_class") or d.get("model_predicted_class") or ""
            ).strip()
            bbox = d.get("model_bbox")
            summary.n_wrong_cat += 1
        elif verdict == "WRONG_BBOX":
            # Human re-drew the bbox; class may have stayed (model's) or
            # been corrected too (in which case prefer the correction).
            class_name = (
                d.get("human_corrected_class") or d.get("model_predicted_class") or ""
            ).strip()
            bbox = d.get("human_bbox") or d.get("model_bbox")
            summary.n_wrong_bbox += 1
        else:
            summary.n_pending_dropped += 1
            continue

        line = _emit_yolo_line(
            class_name=class_name,
            bbox=bbox,
            img_w=img_w,
            img_h=img_h,
            class_index=class_index,
        )
        if line is None:
            summary.n_dropped_unknown_class += 1
            continue
        lines.append(line)
        classes_seen.add(class_name)

    for h in state.get("added_detections", []):
        class_name = (h.get("human_class") or _FN_DEFAULT_CLASS).strip()
        line = _emit_yolo_line(
            class_name=class_name,
            bbox=h.get("bbox"),
            img_w=img_w,
            img_h=img_h,
            class_index=class_index,
        )
        if line is None:
            # Try the default class as a salvage path — but only if the
            # bbox itself was non-degenerate (so we don't fall back for
            # a zero-size bbox).
            fallback = _emit_yolo_line(
                class_name=_FN_DEFAULT_CLASS,
                bbox=h.get("bbox"),
                img_w=img_w,
                img_h=img_h,
                class_index=class_index,
            )
            if fallback is None:
                summary.n_dropped_unknown_class += 1
                continue
            lines.append(fallback)
            classes_seen.add(_FN_DEFAULT_CLASS)
            summary.n_fn_added += 1
            continue
        lines.append(line)
        classes_seen.add(class_name)
        summary.n_fn_added += 1

    summary.classes_written = sorted(classes_seen)
    return lines, summary


def _convert_v1(
    *,
    cell_id: str,
    state: dict,
    artifacts: CellArtifacts,
    img_w: int,
    img_h: int,
    class_index: dict[str, int],
) -> tuple[list[str], CellSummary]:
    """Schema v1 conversion (kept for backward compat with old verdicts)."""
    summary = CellSummary(cell_id=cell_id, schema_version=1)
    verdicts = state.get("verdicts", [])
    fn_noteheads = state.get("fn_noteheads", [])
    median_size = _median_notehead_size_v1(artifacts.detections, verdicts)
    fn_w, fn_h = median_size if median_size else (_FN_DEFAULT_W, _FN_DEFAULT_H)

    lines: list[str] = []
    classes_seen: set[str] = set()

    for v in verdicts:
        did = v.get("detection_id")
        det = artifacts.detections.get(did)
        verdict_label = (v.get("verdict") or "").strip()
        actual_label = (v.get("actual_label") or "").strip()

        if not verdict_label:
            summary.n_pending_dropped += 1
            continue
        if verdict_label == "unsure":
            summary.n_unsure_dropped += 1
            continue
        if verdict_label == "FP" and not actual_label:
            summary.n_fp_dropped += 1
            continue
        if det is None:
            summary.n_pending_dropped += 1
            continue

        if verdict_label == "FP" and actual_label:
            class_name = actual_label
            summary.n_wrong_cat += 1
        elif verdict_label == "TP":
            class_name = det.get("smufl_name", "")
            summary.n_tp += 1
        else:
            summary.n_pending_dropped += 1
            continue

        line = _emit_yolo_line(
            class_name=class_name,
            bbox={
                "x": det.get("x", 0),
                "y": det.get("y", 0),
                "w": det.get("w", 0),
                "h": det.get("h", 0),
            },
            img_w=img_w,
            img_h=img_h,
            class_index=class_index,
        )
        if line is None:
            summary.n_dropped_unknown_class += 1
            continue
        lines.append(line)
        classes_seen.add(class_name)

    for fn in fn_noteheads:
        try:
            x_center = int(fn["x_canonical"])
            y_center = int(fn["y_canonical"])
        except (KeyError, TypeError, ValueError):
            continue
        class_name = (fn.get("class_name") or _FN_DEFAULT_CLASS).strip()
        cls_id = class_index.get(class_name)
        if cls_id is None:
            cls_id = class_index.get(_FN_DEFAULT_CLASS)
            class_name = _FN_DEFAULT_CLASS
        if cls_id is None:
            summary.n_dropped_unknown_class += 1
            continue
        line = _emit_yolo_line(
            class_name=class_name,
            bbox={
                "x": max(0, x_center - fn_w // 2),
                "y": max(0, y_center - fn_h // 2),
                "w": fn_w,
                "h": fn_h,
            },
            img_w=img_w,
            img_h=img_h,
            class_index=class_index,
        )
        if line is None:
            continue
        lines.append(line)
        classes_seen.add(class_name)
        summary.n_fn_added += 1

    summary.classes_written = sorted(classes_seen)
    return lines, summary


def convert_cell(
    *,
    cell_id: str,
    verdict_state: dict,
    artifacts: CellArtifacts,
    class_index: dict[str, int],
) -> tuple[list[str], CellSummary]:
    """Return (yolo_label_lines, summary) for one cell.

    `yolo_label_lines` is a list of "cls cx cy w h" strings (one per kept
    symbol). Coordinates are normalized [0..1] against canonical_w/h.

    Dispatches on `verdict_state.schema_version`: v2 reads bboxes/classes
    directly from the verdict payload; v1 has to join against the
    artifacts.detections dict to recover the bbox.
    """
    img_w = artifacts.canonical_w
    img_h = artifacts.canonical_h
    if img_w <= 0 or img_h <= 0:
        raise ValueError(f"{cell_id}: bad canonical size {img_w}x{img_h}")

    schema = verdict_state.get("schema_version")
    if schema == 2:
        return _convert_v2(
            cell_id=cell_id,
            state=verdict_state,
            img_w=img_w,
            img_h=img_h,
            class_index=class_index,
        )
    # Fall through: anything without an explicit version-2 marker is v1.
    return _convert_v1(
        cell_id=cell_id,
        state=verdict_state,
        artifacts=artifacts,
        img_w=img_w,
        img_h=img_h,
        class_index=class_index,
    )


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


def _is_filled(verdict_state: dict) -> bool:
    """A verdict file counts as filled (i.e. usable as a training label) if
    any verdict has a non-empty label or any FN/added detection exists.
    Handles both schema v1 and v2.
    """
    if verdict_state.get("schema_version") == 2:
        for d in verdict_state.get("detections", []):
            if (d.get("verdict") or "").strip():
                return True
        if verdict_state.get("added_detections"):
            return True
        return False
    # v1
    verdicts = verdict_state.get("verdicts", [])
    if any((v.get("verdict") or "").strip() for v in verdicts):
        return True
    if verdict_state.get("fn_noteheads"):
        return True
    return False


def _copy_image(src: Path, dst: Path, *, symlink: bool) -> None:
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if symlink:
        try:
            dst.symlink_to(src.resolve())
            return
        except OSError:
            pass  # fall through to copy on filesystems that disallow symlinks
    shutil.copyfile(src, dst)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verdicts-dir", required=True, type=Path,
                    help="Directory of <cell_id>.verdict.json files.")
    ap.add_argument("--detections-dir", default=None, type=Path,
                    help="Directory of <cell_id>.json detection files. "
                         "Defaults to <verdicts-dir>/../detections.")
    ap.add_argument("--manifest", required=True, type=Path,
                    help="cells.json manifest (provides PNG paths + sizes).")
    ap.add_argument("--version-name", required=True,
                    help="Version directory name, e.g. "
                         "'v1-2026-05-17-orchestral'.")
    ap.add_argument("--out-root", default=Path("data/user-labeled"), type=Path,
                    help="Catalog root. Version dir created under this.")
    ap.add_argument("--weights", type=Path,
                    default=Path("tools/omr/training/data/weights/"
                                 "deepscoresv2-yolov8l-8shards-100ep.pt"),
                    help="Trained weights to extract class names from. "
                         "Falls back to fallback-json then snapshot.")
    ap.add_argument("--fallback-class-names",
                    default=Path("tools/omr/training/data/"
                                 "deepscoresv2_208_classes.json"),
                    type=Path,
                    help="JSON list of class names. Used if --weights "
                         "is missing or torch isn't installed.")
    ap.add_argument("--labeler", default="",
                    help="Free-text name of who did the labeling.")
    ap.add_argument("--description", default="",
                    help="Free-text description of the session.")
    ap.add_argument("--no-symlink", action="store_true",
                    help="Copy images instead of symlinking.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would happen, don't write anything.")
    args = ap.parse_args()

    verdicts_dir: Path = args.verdicts_dir
    detections_dir: Path = args.detections_dir or (verdicts_dir.parent / "detections")
    manifest_path: Path = args.manifest
    out_version_dir: Path = args.out_root / args.version_name
    images_dir = out_version_dir / "images"
    labels_dir = out_version_dir / "labels"

    if not verdicts_dir.exists():
        raise SystemExit(f"verdicts dir not found: {verdicts_dir}")
    if not manifest_path.exists():
        raise SystemExit(f"manifest not found: {manifest_path}")

    class_names = load_class_names(args.weights, args.fallback_class_names)
    class_index = name_to_first_index(class_names)
    print(f"loaded {len(class_names)} class names "
          f"({len(class_index)} unique after dedupe to first index)")

    manifest = _load_manifest(manifest_path)

    summaries: list[CellSummary] = []
    n_filled = 0
    n_empty = 0
    n_missing_manifest = 0
    n_missing_image = 0

    verdict_files = sorted(verdicts_dir.glob("*.verdict.json"))
    print(f"found {len(verdict_files)} verdict files")

    for vp in verdict_files:
        try:
            state = json.loads(vp.read_text())
        except json.JSONDecodeError as e:
            print(f"  SKIP {vp.name}: bad JSON ({e})")
            continue
        cell_id = state.get("cell_id") or vp.name.removesuffix(".verdict.json")
        if not _is_filled(state):
            n_empty += 1
            continue
        n_filled += 1
        manifest_entry = manifest.get(cell_id)
        if manifest_entry is None:
            n_missing_manifest += 1
            print(f"  SKIP {cell_id}: not in manifest")
            continue
        cell_png = Path(manifest_entry["cell_png_path"])
        if not cell_png.exists():
            n_missing_image += 1
            print(f"  SKIP {cell_id}: cell PNG not on disk: {cell_png}")
            continue
        artifacts = CellArtifacts(
            cell_id=cell_id,
            cell_png=cell_png,
            canonical_w=int(manifest_entry["cell_canonical_w"]),
            canonical_h=int(manifest_entry["cell_canonical_h"]),
            detections=_load_detections(detections_dir, cell_id),
        )
        lines, summary = convert_cell(
            cell_id=cell_id,
            verdict_state=state,
            artifacts=artifacts,
            class_index=class_index,
        )
        summaries.append(summary)
        if args.dry_run:
            print(
                f"  {cell_id} [v{summary.schema_version}]: "
                f"tp={summary.n_tp} fp_drop={summary.n_fp_dropped} "
                f"wrong_cat={summary.n_wrong_cat} wrong_bbox={summary.n_wrong_bbox} "
                f"fn_add={summary.n_fn_added} → {len(lines)} labels"
            )
            continue
        labels_dir.mkdir(parents=True, exist_ok=True)
        (labels_dir / f"{cell_id}.txt").write_text(
            "\n".join(lines) + ("\n" if lines else "")
        )
        _copy_image(
            cell_png,
            images_dir / f"{cell_id}.png",
            symlink=not args.no_symlink,
        )

    # Aggregate
    totals = {
        "n_cells_with_labels": len(summaries),
        "n_v1_cells": sum(1 for s in summaries if s.schema_version == 1),
        "n_v2_cells": sum(1 for s in summaries if s.schema_version == 2),
        "n_tp": sum(s.n_tp for s in summaries),
        "n_wrong_cat": sum(s.n_wrong_cat for s in summaries),
        "n_wrong_bbox": sum(s.n_wrong_bbox for s in summaries),
        "n_fn_added": sum(s.n_fn_added for s in summaries),
        "n_fp_dropped": sum(s.n_fp_dropped for s in summaries),
        "n_unsure_dropped": sum(s.n_unsure_dropped for s in summaries),
        "n_pending_dropped": sum(s.n_pending_dropped for s in summaries),
        "n_dropped_unknown_class": sum(
            s.n_dropped_unknown_class for s in summaries
        ),
    }

    classes_used: set[str] = set()
    for s in summaries:
        classes_used.update(s.classes_written)

    print()
    print(f"verdict files: {len(verdict_files)} total, "
          f"{n_filled} filled, {n_empty} empty/pending")
    if n_missing_manifest:
        print(f"  WARN: {n_missing_manifest} not in manifest")
    if n_missing_image:
        print(f"  WARN: {n_missing_image} missing cell PNG")
    print(f"cells written: {totals['n_cells_with_labels']} "
          f"(v1={totals['n_v1_cells']}, v2={totals['n_v2_cells']})")
    print(f"  TP labels:           {totals['n_tp']}")
    print(f"  WRONG_CATEGORY:      {totals['n_wrong_cat']}")
    print(f"  WRONG_BBOX:          {totals['n_wrong_bbox']}")
    print(f"  human-added (FN):    {totals['n_fn_added']}")
    print(f"  FP dropped:          {totals['n_fp_dropped']}")
    print(f"  unsure dropped:      {totals['n_unsure_dropped']}")
    print(f"  pending dropped:     {totals['n_pending_dropped']}")
    if totals["n_dropped_unknown_class"]:
        print(f"  unknown-class drop:  {totals['n_dropped_unknown_class']}")
    print(f"distinct classes used: {len(classes_used)}")

    if args.dry_run:
        print("\n(dry run — no files written)")
        return

    # Write metadata.json
    metadata = {
        "version_name": args.version_name,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "labeler": args.labeler,
        "description": args.description,
        "source": {
            "verdicts_dir": str(verdicts_dir),
            "detections_dir": str(detections_dir),
            "manifest": str(manifest_path),
            "weights_for_class_names": str(args.weights),
        },
        "totals": totals,
        "n_classes_in_vocab": len(class_names),
        "classes_used_in_this_version": sorted(classes_used),
        "per_cell": [
            {
                "cell_id": s.cell_id,
                "schema_version": s.schema_version,
                "n_tp": s.n_tp,
                "n_wrong_cat": s.n_wrong_cat,
                "n_wrong_bbox": s.n_wrong_bbox,
                "n_fn_added": s.n_fn_added,
                "n_fp_dropped": s.n_fp_dropped,
                "classes_written": s.classes_written,
            }
            for s in summaries
        ],
    }
    out_version_dir.mkdir(parents=True, exist_ok=True)
    (out_version_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2)
    )
    print(f"\nwrote {out_version_dir}/")
    print(f"  images/  ({len(summaries)} files)")
    print(f"  labels/  ({len(summaries)} files)")
    print(f"  metadata.json")
    print(f"\nNext: rebuild the catalog YAML:")
    print(f"  python3 -m tools.omr.training.build_catalog_yaml "
          f"--root {args.out_root}")


if __name__ == "__main__":
    main()
