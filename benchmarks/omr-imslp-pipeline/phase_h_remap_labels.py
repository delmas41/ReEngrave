#!/usr/bin/env python3
"""Phase H — remap catalog labels from the 146-class DEEPSCORES_V2_CLASSES
snapshot index space to the 208-class prod-weights index space.

The Phase G label emitter wrote class IDs based on
tools/omr/training/deepscores_classes.DEEPSCORES_V2_CLASSES (146 classes,
SMuFL-style names like "gClef"). The production weights at
deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt were trained with nc=208 and
DSv2-dense-style names (like "clefG"). Fine-tuning the prod weights with
a 146-class yaml causes ultralytics to print:

    Overriding model.yaml nc=208 with nc=146

…which RE-INITIALIZES the classification head → catastrophic forgetting
(exactly the Phase 3.4 v1 failure mode).

Fix: remap the catalog .txt files in-place from snapshot indices to prod
indices, then train with a yaml that declares nc=208 + prod names. The
head stays intact and we only fine-tune from a known-good starting point.

Mapping strategy: name match (with manual aliases for the small number
of renaming differences between the SMuFL snapshot and DSv2-dense form).
Snapshot classes that have NO equivalent in prod (e.g. ones the prod
training set didn't include) are dropped — their labels are removed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Manual aliases for snapshot-name → prod-name (where the symbol is
# identical but the convention differs).
NAME_ALIASES: dict[str, str] = {
    "gClef": "clefG",
    "cClefAlto": "clefCAlto",
    "cClefTenor": "clefCTenor",
    "fClef": "clefF",
    "unpitchedPercussionClef1": "clefUnpitchedPercussion",
    "gClefChange": "clefG",          # treat clef-change marks as the base clef
    "cClefAltoChange": "clefCAlto",
    "cClefTenorChange": "clefCTenor",
    "fClefChange": "clefF",
    # DSv2 names some symbols differently (verified by walking the prod
    # weights' names list). The rest are identical between snapshot and
    # prod.
}


def parse_prod_names(prod_tsv: Path) -> list[str]:
    """Read prod_names.tsv (id\tname per line) and return the names by id
    in ascending order. Verifies the file is dense [0, N)."""
    rows: list[tuple[int, str]] = []
    for line in prod_tsv.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        try:
            i = int(parts[0])
        except ValueError:
            continue
        rows.append((i, parts[1]))
    rows.sort()
    expected = list(range(len(rows)))
    if [i for i, _ in rows] != expected:
        raise SystemExit(f"prod names file is not dense [0, {len(rows)}); rows: {rows[:10]}")
    return [n for _, n in rows]


def build_snapshot_to_prod_map(
    snapshot_names: list[str], prod_names: list[str]
) -> dict[int, int | None]:
    """For each snapshot index, look up the equivalent prod index.
    Returns None for snapshot entries with no prod match (caller drops
    those labels)."""
    # Prefer FIRST occurrence — prod has duplicate names (208 slots, 168
    # unique). The 0–135 range corresponds to the primary 'deepscores'
    # annotation set; 136+ is the secondary 'muscima' (handwritten music)
    # set. Modern engraved orchestral scores are in the primary set, so
    # use those head neurons.
    prod_idx_by_name: dict[str, int] = {}
    for i, n in enumerate(prod_names):
        if n not in prod_idx_by_name:
            prod_idx_by_name[n] = i
    out: dict[int, int | None] = {}
    for s_idx, s_name in enumerate(snapshot_names):
        target = NAME_ALIASES.get(s_name, s_name)
        if target in prod_idx_by_name:
            out[s_idx] = prod_idx_by_name[target]
        else:
            out[s_idx] = None
    return out


def remap_label_file(
    src_path: Path,
    dst_path: Path,
    mapping: dict[int, int | None],
    counters: dict[str, int],
) -> None:
    out_lines: list[str] = []
    with src_path.open() as f:
        for line in f:
            parts = line.split()
            if len(parts) != 5:
                continue
            try:
                s_id = int(parts[0])
            except ValueError:
                continue
            p_id = mapping.get(s_id)
            if p_id is None:
                counters["dropped"] = counters.get("dropped", 0) + 1
                counters[f"dropped_id_{s_id}"] = counters.get(f"dropped_id_{s_id}", 0) + 1
                continue
            parts[0] = str(p_id)
            out_lines.append(" ".join(parts))
            counters["kept"] = counters.get("kept", 0) + 1
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text("\n".join(out_lines) + ("\n" if out_lines else ""))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels-root", required=True,
                    help="phase-h-data/labels/ (input — written in place by default)")
    ap.add_argument("--out-root", default=None,
                    help="If set, write remapped labels here instead of in place")
    ap.add_argument("--prod-names", required=True,
                    help="Path to prod_names.tsv (id\\tname per line)")
    args = ap.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.omr.training.deepscores_classes import DEEPSCORES_V2_CLASSES

    prod_names = parse_prod_names(Path(args.prod_names))
    snap_names = list(DEEPSCORES_V2_CLASSES)
    print(f"Snapshot classes: {len(snap_names)}")
    print(f"Prod classes:     {len(prod_names)}")

    mapping = build_snapshot_to_prod_map(snap_names, prod_names)
    print(f"\nSnapshot → prod mapping (first 30):")
    for i in range(min(30, len(snap_names))):
        tgt = mapping[i]
        s = snap_names[i]
        p = prod_names[tgt] if tgt is not None else "(DROPPED)"
        print(f"  {i:>3} {s:<35} → {tgt if tgt is not None else '--':>3} {p}")

    n_dropped_snapshot = sum(1 for v in mapping.values() if v is None)
    print(f"\nSnapshot classes with no prod equivalent: {n_dropped_snapshot}")

    labels_root = Path(args.labels_root).resolve()
    out_root = Path(args.out_root).resolve() if args.out_root else labels_root

    counters: dict[str, int] = {}
    n_files = 0
    for src in labels_root.rglob("*.txt"):
        rel = src.relative_to(labels_root)
        dst = out_root / rel
        remap_label_file(src, dst, mapping, counters)
        n_files += 1

    print(f"\nProcessed {n_files} label files")
    print(f"  kept:    {counters.get('kept', 0)} labels")
    print(f"  dropped: {counters.get('dropped', 0)} labels")
    if counters.get('dropped', 0) > 0:
        print("\n  drops per snapshot id:")
        for k, v in sorted(counters.items()):
            if k.startswith("dropped_id_"):
                s_id = int(k[len("dropped_id_"):])
                s = snap_names[s_id] if s_id < len(snap_names) else "??"
                print(f"    id={s_id:>3} {s:<35} {v} labels")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
