"""Re-derive a label version's metadata class fields from its own label files.

**Why this exists rather than "just re-run the converter".** A version's
`metadata.json` records which classes it teaches, in two places:
`classes_used_in_this_version` (the aggregate) and each
`per_cell.classes_written`. Both are computed at conversion time from the
verdicts. Correcting a mislabeled cell by hand-editing the exported
`labels/<cell>.txt` line — which is what a class-only correction properly
does, since the box coordinates do not move — leaves both fields stating the
OLD class while the label states the new one.

The recorded resolution used to be "one converter re-run per affected version
with its original arguments". ⚠️ **That is DESTRUCTIVE for older versions and
silently so.** The converter copies each cell's PNG from the batch's
`cells/` directory, which is gitignored and, for the 2026-09 hollow batches,
largely deleted since (see `feedback_cells_not_reproducible`: labeled cell
PNGs are NOT regenerable — phase-1 has drifted). Measured 2026-09-03: of v8's
122 cells, **11 source PNGs still exist and 111 do not**, so a re-run writes
an 11-cell version over a 122-cell one, exits 0, and reports only
`cells written: 11`. v11's 11 cells all survive, so v11 alone is
reproducible.

So this heals the two fields FROM THE LABELS, which are what training reads
and therefore the thing metadata must agree with. Labels and images are never
touched. Every change is printed, and the write is refused unless the caller
names the cells expected to change — a metadata heal must be a
correction-sized diff, never a silent rewrite.

    python3 -m tools.omr.training.heal_version_metadata \\
        --version data/user-labeled/v11-2026-09-03-hollow3-lamer \\
        --expect-cells lamer-p5-sys0-s2-m0            # then --write

Validated against the converter itself: for v11 (the reproducible one) the
fields this computes are identical to those a full re-run produces.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .verdicts_to_yolo_labels import load_class_names


def _class_names_for(meta: dict, repo_root: Path) -> list[str]:
    """Resolve the id→name vocabulary the version was written with."""
    src = meta.get("source") or {}
    raw = src.get("weights_for_class_names")
    if not raw:
        raise SystemExit("metadata.source.weights_for_class_names is missing")
    weights = Path(raw)
    if not weights.is_absolute():
        weights = repo_root / weights
    if not weights.exists():
        raise SystemExit(f"weights not found, cannot name classes: {weights}")
    return load_class_names(weights, None)


def recompute(version_dir: Path, repo_root: Path) -> tuple[dict, dict, list[str]]:
    """Return (metadata, healed_metadata, change_log)."""
    meta = json.loads((version_dir / "metadata.json").read_text())
    names = _class_names_for(meta, repo_root)

    per_cell_labels: dict[str, list[str]] = {}
    for lf in sorted((version_dir / "labels").glob("*.txt")):
        seen: set[str] = set()
        for line in lf.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            cid = int(line.split()[0])
            if cid >= len(names):
                raise SystemExit(
                    f"{lf.name}: class id {cid} is outside the {len(names)}-name "
                    "vocabulary — wrong weights for this version"
                )
            seen.add(names[cid])
        per_cell_labels[lf.stem] = sorted(seen)

    healed = json.loads(json.dumps(meta))  # deep copy
    changes: list[str] = []

    for rec in healed.get("per_cell", []):
        cell_id = rec.get("cell_id")
        if cell_id not in per_cell_labels:
            continue  # cell has no label file (inspected-empty); leave as recorded
        was, now = rec.get("classes_written"), per_cell_labels[cell_id]
        if was != now:
            changes.append(f"per_cell {cell_id}: {was} -> {now}")
            rec["classes_written"] = now

    used_now = sorted({c for cs in per_cell_labels.values() for c in cs})
    if healed.get("classes_used_in_this_version") != used_now:
        changes.append(
            f"classes_used_in_this_version: {healed.get('classes_used_in_this_version')}"
            f" -> {used_now}"
        )
        healed["classes_used_in_this_version"] = used_now

    return meta, healed, changes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", type=Path, required=True,
                    help="data/user-labeled/<version> directory")
    ap.add_argument("--expect-cells", nargs="*", default=None,
                    help="cell ids whose per_cell entry is expected to change; "
                         "any other change refuses the write")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    version_dir = args.version if args.version.is_absolute() else repo_root / args.version
    _meta, healed, changes = recompute(version_dir, repo_root)

    print(f"{version_dir.name}: {len(changes)} change(s)")
    for c in changes:
        print("  " + c)
    if not changes:
        print("  metadata already agrees with the labels — nothing to do")
        return

    if args.expect_cells is not None:
        touched = {c.split()[1].rstrip(":") for c in changes if c.startswith("per_cell ")}
        unexpected = touched - set(args.expect_cells)
        if unexpected:
            raise SystemExit(
                f"REFUSING: unexpected per_cell changes {sorted(unexpected)} — "
                "a metadata heal must be correction-sized. Investigate before writing."
            )

    if not args.write:
        print("\n(dry run — pass --write to apply)")
        return

    out = version_dir / "metadata.json"
    out.write_text(json.dumps(healed, indent=2) + "\n")
    print(f"\nwrote {out}")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
