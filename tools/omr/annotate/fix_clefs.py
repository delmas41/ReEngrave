"""Patch cells.json + detection JSONs to assign the right clef per cell, then
re-resolve notehead pitches with the corrected clef.

Heuristic per source_tag:
  - WTC keyboard (grand staff, 2 staves/system):
      staff_index 0 → treble  (right hand)
      staff_index 1 → bass    (left hand)
  - Bach SATB chorales (4 staves/system):
      staff_index 0,1 → treble  (soprano, alto)
      staff_index 2 → tenor (or treble-with-clef-8vb in practice)
      staff_index 3 → bass
  - Beethoven 5 orchestral (18 staves/system, varied):
      Default to treble; the user must override bass/alto per affected cell
      via the web UI.

CLI:
    python3 -m tools.omr.annotate.fix_clefs \
        --manifest benchmarks/omr-phase2.5/cells.json \
        --detections-dir benchmarks/omr-phase2.5/detections
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..pitch_resolver import pitch_for_notehead
from ..template_matcher import SymbolDetection


def infer_clef(entry: dict) -> str:
    """Pick a reasonable default clef for one cell.

    Returns one of "treble" | "bass" | "alto" | "tenor". Caller is free to
    override via the UI on a per-cell basis.
    """
    source = (entry.get("source_tag") or "").lower()
    staff_index = int(entry.get("staff_index", 0))

    # WTC: Bach keyboard pieces use grand staff. staff_index is page-global
    # (staves 0,2,4,... are RH treble; 1,3,5,... are LH bass).
    if source.startswith("wtc"):
        return "treble" if (staff_index % 2 == 0) else "bass"

    # Bach SATB chorale (if/when added as a source) — typically 4 staves per
    # system. Use within-system position when possible (staff_index % 4).
    if source.startswith("bach-chorale") or "satb" in source:
        pos = staff_index % 4
        if pos <= 1:
            return "treble"
        if pos == 2:
            return "tenor"
        return "bass"

    # Beethoven 5 / general orchestral — instrument-specific. Without
    # instrument info we can't reliably auto-assign; user overrides.
    return "treble"


def _detection_from_dict(det_dict: dict, cell_canonical_w: int, cell_canonical_h: int, staff_lines):
    """Reconstruct a thin SymbolDetection stand-in for the pitch resolver."""
    # SymbolDetection's pitch_for_notehead reads .x_center, .y_center,
    # .staff_line_ys_canonical (on the cell). Build a minimal object.
    class _DetView:
        def __init__(self, d):
            self.smufl_name = d["smufl_name"]
            self.category = d["category"]
            self.x_center = d["x_center"]
            self.y_center = d["y_center"]
            self.confidence = d["confidence"]
            self.cell = _CellView(staff_lines)
            self.pitch = d.get("pitch")
    class _CellView:
        def __init__(self, lines):
            self.staff_line_ys_canonical = list(lines)
    return _DetView(det_dict)


def _reresolve(det_path: Path, clef: str, staff_lines: list[int],
                cell_canonical_w: int, cell_canonical_h: int) -> tuple[int, int]:
    if not det_path.exists():
        return (0, 0)
    data = json.loads(det_path.read_text())
    n_changed = 0
    n_total = 0
    for d in data.get("detections", []):
        if d.get("category") != "notehead":
            continue
        n_total += 1
        view = _detection_from_dict(d, cell_canonical_w, cell_canonical_h, staff_lines)
        new_pitch = pitch_for_notehead(view, clef=clef)
        if new_pitch != d.get("pitch"):
            d["pitch"] = new_pitch
            n_changed += 1
    det_path.write_text(json.dumps(data, indent=2))
    return n_changed, n_total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="benchmarks/omr-phase2.5/cells.json")
    ap.add_argument("--detections-dir", default="benchmarks/omr-phase2.5/detections")
    ap.add_argument("--dry-run", action="store_true",
                    help="Just print what would change, don't write")
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    dets_dir = Path(args.detections_dir)

    manifest = json.loads(manifest_path.read_text())
    total_changed_notes = 0
    total_notes = 0
    n_cells_clef_changed = 0

    for entry in manifest:
        cid = entry["cell_id"]
        current_clef = entry.get("clef", "treble")
        new_clef = infer_clef(entry)
        if new_clef != current_clef:
            n_cells_clef_changed += 1
            print(f"  {cid}: clef {current_clef} → {new_clef}")
            if not args.dry_run:
                entry["clef"] = new_clef

        clef_to_use = new_clef if not args.dry_run else new_clef
        det_path = dets_dir / f"{cid}.json"
        if det_path.exists():
            n_ch, n_tot = _reresolve(
                det_path, clef_to_use,
                entry.get("staff_line_ys_canonical", []),
                entry.get("cell_canonical_w", 2048),
                entry.get("cell_canonical_h", 600),
            )
            total_changed_notes += n_ch
            total_notes += n_tot

    if not args.dry_run:
        manifest_path.write_text(json.dumps(manifest, indent=2))

    print()
    print(f"summary: {n_cells_clef_changed} cells got a new default clef; "
          f"re-resolved {total_changed_notes}/{total_notes} notehead pitches"
          + (" (dry-run, no files written)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
