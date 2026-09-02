"""Build the unified `data/user-labeled/catalog.yaml` from the versioned
labeling sessions admitted to the catalog membership.

The catalog is a single ultralytics-compatible YOLO data config that
unions the `vN-DATE-NAME/` subdirectories listed in
`<root>/catalog-versions.txt` — NOT every version directory on disk.
Membership is a recorded training decision: the committed catalog
deliberately excludes the clef-heavy v5/v6 batches because adding them
narrows the density prior, the mechanism that collapsed dense-page
noteheads 2506 → 114 in the clef fine-tune (PROJECT_STATUS.md open
decision #13). A run with no manifest and no --versions therefore
REFUSES rather than guessing, and a run with the manifest reproduces the
recorded membership exactly, listing any on-disk versions it leaves out.
Admitting a new version is an edit to the manifest — a visible,
committed diff — never a side effect of rebuilding.

Each version contributes its own train/val split (held out *within* that
version) so that retraining sees a stable val set per version while
still benefiting from new data.

Why per-version val splits, not a global one?
  - Holding out a chunk of every session means the val set keeps growing
    in lockstep with train. A global random split would have to re-shuffle
    on every rebuild, which makes run-to-run val numbers non-comparable.
  - Per-version split is also deterministic: same `--val-fraction` and
    same `--seed` → identical split, every time.

Output:
  data/user-labeled/catalog.yaml      ← consumed by `train_yolo.py --data`
  data/user-labeled/_catalog_train.txt ← list of train image paths
  data/user-labeled/_catalog_val.txt   ← list of val image paths
  data/user-labeled/_nc208/           ← filtered label copies for cells with
                                        custom-class boxes (see below)

By default the catalog's class space is capped at the trained checkpoint's
208 classes: hand-labeled boxes at IDs >= 208 (barlines, textDynamic) are
dropped from the emitted lists via filtered label copies, because training
with a data.yaml `nc` that differs from the checkpoint's `nc` silently
re-initializes the classification head (Phase 3.4: F1 98.8% → 79.3%).
Use --emit-full-catalog to also write an uncapped catalog-<nc>.yaml, or
--keep-custom-classes to make the uncapped space the main catalog.

The `.txt` files are ultralytics' "list-of-paths" input format, which we
use because (a) we don't want to copy/move images across the train/val
boundary, and (b) the version directories are immutable.

CLI:
    python3 -m tools.omr.training.build_catalog_yaml \\
        --root data/user-labeled/ \\
        --val-fraction 0.15
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .verdicts_to_yolo_labels import (
    DEEPSCORES_208_JSON,
    load_base_class_names,
    load_class_names,
)


# ---------------------------------------------------------------------------
# Catalog scanning
# ---------------------------------------------------------------------------


@dataclass
class VersionSlice:
    name: str                       # e.g. "v1-2026-05-17-orchestral"
    dir: Path                       # absolute path
    train_images: list[Path] = field(default_factory=list)
    val_images: list[Path] = field(default_factory=list)
    metadata: dict | None = None


def _stable_hash_fraction(key: str) -> float:
    """Map a string deterministically to [0..1)."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    # Take 8 bytes → uint64 → /2^64
    return int.from_bytes(digest[:8], "big") / 2 ** 64


def _scan_version_dir(d: Path, val_fraction: float, seed: str) -> VersionSlice:
    images_dir = d / "images"
    labels_dir = d / "labels"
    if not images_dir.is_dir() or not labels_dir.is_dir():
        return VersionSlice(name=d.name, dir=d.resolve())
    slice_ = VersionSlice(name=d.name, dir=d.resolve())
    meta_p = d / "metadata.json"
    if meta_p.exists():
        try:
            slice_.metadata = json.loads(meta_p.read_text())
        except json.JSONDecodeError:
            slice_.metadata = None

    paired: list[Path] = []
    for img in sorted(images_dir.iterdir()):
        if img.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        lbl = labels_dir / f"{img.stem}.txt"
        if not lbl.exists():
            continue  # skip images with no label file
        # IMPORTANT: do NOT .resolve() here — ultralytics looks for label
        # files by replacing `/images/` with `/labels/` in the image path.
        # If we resolve the symlink to its original location (which is in
        # benchmarks/.../cells/ — no `/images/` substring), YOLO won't
        # find our labels.  Keep the symlinked path under the version's
        # `images/` directory so the label resolution works.
        paired.append(img.absolute())

    for img in paired:
        # Deterministic per-image split: hash of "<version>:<stem>" with
        # the seed mixed in. Same val_fraction + same seed → same split.
        h = _stable_hash_fraction(f"{seed}:{d.name}:{img.stem}")
        if h < val_fraction:
            slice_.val_images.append(img)
        else:
            slice_.train_images.append(img)
    return slice_


def discover_versions(root: Path) -> list[Path]:
    """Find all `vN-*/` subdirectories at the top level of `root`.

    This is an INVENTORY of what is on disk, not the catalog membership —
    membership comes from `select_versions` (the catalog-versions.txt
    manifest or an explicit --versions list).
    """
    if not root.exists():
        return []
    out: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        # Allow lowercase or uppercase v, digits, then a dash, then anything
        if not name.lower().startswith("v"):
            continue
        # Must look like "vN-..." — i.e. a digit right after "v"
        if len(name) < 2 or not name[1].isdigit():
            continue
        out.append(child)
    return out


# ---------------------------------------------------------------------------
# Version membership (catalog-versions.txt)
# ---------------------------------------------------------------------------
#
# Which versions the catalog unions is a training decision with a decision
# record behind it, not a property of the filesystem. Until 2026-09-02 the
# committed catalog's v1–v4 membership survived only as long as nobody
# re-ran this tool (benchmarks/omr-labeling-hollow-2026-08/AUDIT.md) — the
# same silent-footgun shape as the nc=214 head reset closed in July.


CATALOG_VERSIONS_MANIFEST = "catalog-versions.txt"

_DECISION_RECORD = (
    "PROJECT_STATUS.md open decision #13 and "
    "benchmarks/omr-labeling-hollow-2026-08/AUDIT.md"
)


def manifest_path(root: Path) -> Path:
    return root / CATALOG_VERSIONS_MANIFEST


def read_versions_manifest(root: Path) -> list[str] | None:
    """Parse `<root>/catalog-versions.txt`: one version directory name per
    line, `#` comments and blank lines ignored. None if the file is absent
    (which `select_versions` treats as an error, not as "take everything").
    """
    p = manifest_path(root)
    if not p.exists():
        return None
    names: list[str] = []
    for raw in p.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            names.append(line)
    return names


def select_versions(
    root: Path,
    requested: list[str] | None,
) -> tuple[list[Path], list[str], str]:
    """Resolve the catalog's version membership.

    The members are exactly `requested` (the --versions flag) or, when that
    is None, the manifest `<root>/catalog-versions.txt`. A root with
    neither is an error — never a silent union of everything on disk,
    because the committed membership excludes versions on purpose (v5/v6
    narrow the density prior; see the decision record).

    Returns (member dirs in membership order, on-disk version names left
    out, membership source for the summary). Exits when a named version is
    missing from disk or listed twice — either would build a catalog that
    does not reproduce the recorded membership.
    """
    discovered = discover_versions(root)
    by_name = {d.name: d for d in discovered}
    if requested is not None:
        source = "--versions"
    else:
        requested = read_versions_manifest(root)
        source = str(manifest_path(root))
        if requested is None:
            on_disk = "\n".join(f"    {d.name}" for d in discovered) \
                or "    (none)"
            raise SystemExit(
                f"{manifest_path(root)} not found.\n\n"
                "Catalog membership is a recorded training decision, not an\n"
                "inventory of what is on disk: the committed catalog.yaml\n"
                "deliberately excludes the clef-heavy v5/v6 batches, which\n"
                "narrow the density prior — the mechanism that collapsed\n"
                f"dense-page noteheads 2506 -> 114. See {_DECISION_RECORD}.\n"
                "Unioning every version directory would silently reverse\n"
                "that decision, so this tool refuses to guess.\n\n"
                "Write the manifest with one version directory name per\n"
                f"line ('#' comments allowed). Versions on disk under\n"
                f"{root}:\n{on_disk}\n\n"
                "Or pass --versions NAME [NAME ...] for a one-off build."
            )
    dupes = sorted(n for n, c in Counter(requested).items() if c > 1)
    if dupes:
        raise SystemExit(
            f"version(s) listed more than once in {source}: "
            + ", ".join(dupes)
        )
    missing = [n for n in requested if n not in by_name]
    if missing:
        raise SystemExit(
            f"version(s) named in {source} but not on disk under {root}: "
            + ", ".join(missing) + "\n"
            "Refusing to build a catalog that does not reproduce the "
            "recorded membership."
        )
    members = [by_name[n] for n in requested]
    excluded = [d.name for d in discovered if d.name not in set(requested)]
    return members, excluded, source


# ---------------------------------------------------------------------------
# nc capping (drop custom-class boxes so fine-tuning matches the checkpoint)
# ---------------------------------------------------------------------------
#
# The version dirs' label files keep EVERY human-drawn box, including custom
# classes at IDs >= 208 (barlines, textDynamic — see verdicts_to_yolo_labels).
# But fine-tuning against a data.yaml whose `nc` differs from the
# checkpoint's `nc` makes ultralytics silently re-initialize the whole
# classification head — that's the Phase 3.4 catastrophic-forgetting
# failure (F1 98.8% → 79.3%, benchmarks/omr-phase3.4b/).
#
# So by default the catalog is capped at the base vocabulary (nc=208):
# label files containing out-of-range boxes get a filtered copy under
# `<root>/_nc<N>/<version>/labels/`, with an image symlink alongside so
# ultralytics' `/images/` → `/labels/` path substitution finds the copy.
# The original version dirs stay untouched (they're immutable), and the
# custom boxes stay available via --emit-full-catalog.


def _cap_labels_to_nc(
    root: Path,
    image_paths: list[Path],
    nc: int,
) -> tuple[list[Path], Counter]:
    """Redirect images whose label file has boxes with class id >= nc.

    Returns (possibly-redirected image paths, Counter of dropped class ids).
    Filtered label copies + relative image symlinks are written under
    `<root>/_nc<nc>/<version>/{labels,images}/`.
    """
    capped_root = root / f"_nc{nc}"
    out_paths: list[Path] = []
    dropped: Counter = Counter()
    for img in image_paths:
        version_dir = img.parent.parent          # <root>/<version>
        label = version_dir / "labels" / f"{img.stem}.txt"
        lines = label.read_text().splitlines()
        keep, drop = [], []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            (drop if int(ln.split()[0]) >= nc else keep).append(ln)
        if not drop:
            out_paths.append(img)
            continue
        for ln in drop:
            dropped[int(ln.split()[0])] += 1
        cap_labels = capped_root / version_dir.name / "labels"
        cap_images = capped_root / version_dir.name / "images"
        cap_labels.mkdir(parents=True, exist_ok=True)
        cap_images.mkdir(parents=True, exist_ok=True)
        (cap_labels / f"{img.stem}.txt").write_text(
            "\n".join(keep) + ("\n" if keep else "")
        )
        link = cap_images / img.name
        if not link.is_symlink():
            # Relative target so the link survives moving/cloning the repo.
            link.symlink_to(os.path.relpath(img, cap_images))
        out_paths.append(link)
    return out_paths, dropped


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=Path("data/user-labeled"), type=Path,
                    help="Catalog root containing vN-*/ version dirs.")
    ap.add_argument("--versions", nargs="+", default=None, metavar="NAME",
                    help="Explicit version membership for this build "
                         "(overrides <root>/catalog-versions.txt). Without "
                         "it, the manifest is REQUIRED and the build "
                         "reproduces exactly what it lists — membership is "
                         "a recorded training decision (see "
                         "PROJECT_STATUS.md open decision #13), so a "
                         "rebuild never silently widens the catalog.")
    ap.add_argument("--val-fraction", type=float, default=0.15,
                    help="Per-version fraction held out for val "
                         "(default 0.15).")
    ap.add_argument("--seed", default="reengrave",
                    help="Seed string mixed into the val-split hash. "
                         "Change to reshuffle.")
    ap.add_argument("--weights", type=Path,
                    default=Path("tools/omr/training/data/weights/"
                                 "deepscoresv2-yolov8l-8shards-100ep.pt"),
                    help="Trained .pt file to read class names from.")
    ap.add_argument("--fallback-class-names",
                    default=DEEPSCORES_208_JSON,
                    type=Path,
                    help="JSON list of class names. Used if --weights is "
                         "missing or torch isn't installed. Defaults to "
                         "the committed 208-name snapshot.")
    ap.add_argument("--output-yaml", default=None, type=Path,
                    help="Override output path. Defaults to "
                         "<root>/catalog.yaml.")
    ap.add_argument("--max-classes", type=int, default=None,
                    help="Cap the catalog's class space at N: boxes with "
                         "class id >= N are dropped (filtered label copies "
                         "go under <root>/_nc<N>/). Default: the base "
                         "vocabulary size (208) so `nc` matches the "
                         "DSv2-trained checkpoints — training with a "
                         "mismatched nc silently re-initializes the whole "
                         "classification head (the Phase 3.4 collapse).")
    ap.add_argument("--keep-custom-classes", action="store_true",
                    help="Do NOT cap: emit the full vocabulary including "
                         "custom classes (barlines, textDynamic) as the "
                         "main catalog. Only sane together with "
                         "train_yolo --allow-nc-expansion.")
    ap.add_argument("--emit-full-catalog", action="store_true",
                    help="Additionally write catalog-<nc_full>.yaml (+ its "
                         "train/val lists) with the uncapped class space, "
                         "for a future nc-expansion run.")
    args = ap.parse_args()

    root: Path = args.root.resolve()
    val_fraction = float(args.val_fraction)
    if not (0.0 <= val_fraction <= 0.5):
        raise SystemExit(
            "val-fraction must be in [0.0, 0.5]; "
            f"got {val_fraction!r}"
        )

    requested: list[str] | None = None
    if args.versions is not None:
        # Accept both space- and comma-separated names.
        requested = [n for tok in args.versions for n in tok.split(",") if n]
    version_dirs, excluded_versions, membership_source = select_versions(
        root, requested,
    )
    if not version_dirs:
        print(f"no versions in the catalog membership "
              f"({membership_source}) — nothing to catalog yet.")
        # Still emit a catalog stub so the path exists. Downstream training
        # will fail-fast with an empty list.
        print("(writing empty catalog stub anyway)")

    slices = [
        _scan_version_dir(d, val_fraction, args.seed)
        for d in version_dirs
    ]

    train_paths: list[Path] = []
    val_paths: list[Path] = []
    for s in slices:
        train_paths.extend(s.train_images)
        val_paths.extend(s.val_images)

    base_names = load_base_class_names(args.weights, args.fallback_class_names)
    full_names = load_class_names(args.weights, args.fallback_class_names)

    root.mkdir(parents=True, exist_ok=True)

    # Cap the main catalog's class space (default: base vocabulary = 208)
    # unless explicitly told to keep the custom classes.
    dropped: Counter = Counter()
    if args.keep_custom_classes:
        nc_main = len(full_names)
        main_names = full_names
        main_train, main_val = train_paths, val_paths
    else:
        nc_main = args.max_classes or len(base_names)
        main_names = full_names[:nc_main]
        # Regenerate the capped tree from scratch so stale copies from a
        # previous build can't linger.
        capped_root = root / f"_nc{nc_main}"
        if capped_root.exists():
            shutil.rmtree(capped_root)
        main_train, d1 = _cap_labels_to_nc(root, train_paths, nc_main)
        main_val, d2 = _cap_labels_to_nc(root, val_paths, nc_main)
        dropped = d1 + d2

    # Write list-of-paths files
    train_txt = root / "_catalog_train.txt"
    val_txt = root / "_catalog_val.txt"
    train_txt.write_text("\n".join(str(p) for p in main_train) +
                         ("\n" if main_train else ""))
    val_txt.write_text("\n".join(str(p) for p in main_val) +
                       ("\n" if main_val else ""))

    # Write data.yaml
    output_yaml = args.output_yaml or (root / "catalog.yaml")
    payload = {
        "path": str(root),
        "train": str(train_txt),
        "val": str(val_txt),
        "nc": nc_main,
        "names": main_names,
    }
    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    output_yaml.write_text(yaml.safe_dump(payload, sort_keys=False))

    # Optional: the uncapped catalog, for a deliberate nc-expansion run.
    full_yaml: Path | None = None
    if args.emit_full_catalog:
        full_train_txt = root / "_catalog_full_train.txt"
        full_val_txt = root / "_catalog_full_val.txt"
        full_train_txt.write_text("\n".join(str(p) for p in train_paths) +
                                  ("\n" if train_paths else ""))
        full_val_txt.write_text("\n".join(str(p) for p in val_paths) +
                                ("\n" if val_paths else ""))
        full_yaml = root / f"catalog-{len(full_names)}.yaml"
        full_yaml.write_text(yaml.safe_dump({
            "path": str(root),
            "train": str(full_train_txt),
            "val": str(full_val_txt),
            "nc": len(full_names),
            "names": full_names,
        }, sort_keys=False))

    # Write a sidecar summary for humans
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root": str(root),
        "val_fraction": val_fraction,
        "seed": args.seed,
        "membership_source": membership_source,
        "n_versions": len(slices),
        "versions_excluded_on_disk": excluded_versions,
        "n_train_images": len(train_paths),
        "n_val_images": len(val_paths),
        "n_classes": nc_main,
        "n_classes_full_vocab": len(full_names),
        "n_boxes_dropped_over_nc": sum(dropped.values()),
        "boxes_dropped_by_class": {
            (full_names[i] if i < len(full_names) else f"class{i}"): n
            for i, n in sorted(dropped.items())
        },
        "full_catalog": str(full_yaml) if full_yaml else None,
        "weights_source": str(args.weights),
        "versions": [
            {
                "name": s.name,
                "dir": str(s.dir),
                "n_train_images": len(s.train_images),
                "n_val_images": len(s.val_images),
                "metadata_present": s.metadata is not None,
                "labeler": (s.metadata or {}).get("labeler"),
                "description": (s.metadata or {}).get("description"),
                "created_utc": (s.metadata or {}).get("created_utc"),
            }
            for s in slices
        ],
    }
    (root / "_catalog_summary.json").write_text(json.dumps(summary, indent=2))

    # Pretty stdout
    print(f"catalog root:    {root}")
    print(f"membership:      {membership_source}")
    print(f"versions in catalog: {len(slices)}")
    for s in slices:
        labeler = (s.metadata or {}).get("labeler") or "?"
        print(f"  {s.name}  train={len(s.train_images):>4}  "
              f"val={len(s.val_images):>3}  labeler={labeler}")
    if excluded_versions:
        print(f"\nexcluded ({len(excluded_versions)} on disk, not in the "
              f"membership — deliberate; see {_DECISION_RECORD}):")
        for name in excluded_versions:
            print(f"  {name}")
        print(f"  (to admit one: edit {manifest_path(root)} and rebuild, "
              f"or pass --versions for a one-off build)")
    print(f"\ntotals:")
    print(f"  train images: {len(train_paths)}")
    print(f"  val images:   {len(val_paths)}")
    print(f"  classes (nc): {nc_main}  (full vocab: {len(full_names)})")
    if dropped:
        print(f"\ncustom-class boxes dropped from the nc={nc_main} catalog "
              f"({sum(dropped.values())} total; kept in the version dirs"
              + (" and the full catalog" if full_yaml else
                 "; --emit-full-catalog to use them") + "):")
        for i, n in sorted(dropped.items()):
            name = full_names[i] if i < len(full_names) else f"class{i}"
            print(f"  {name} (id {i}): {n}")
    print(f"\nwrote:")
    print(f"  {output_yaml}")
    print(f"  {train_txt}")
    print(f"  {val_txt}")
    if full_yaml:
        print(f"  {full_yaml}  (+ full train/val lists)")
    print(f"  {root / '_catalog_summary.json'}")
    print(f"\nPoint training at: --data {output_yaml}")


if __name__ == "__main__":
    main()
