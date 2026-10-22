"""Generate verdict templates for each cell in the manifest.

For each cell:
    1. Reload its no-staff PNG + canonical staff lines from cells.json
    2. Wrap them in a MeasureCell and run detect_symbols()
    3. Persist the raw detections JSON (so the scorer can re-read them
       without re-running the matcher)
    4. Render an overlay PNG with numbered detection rectangles
    5. Emit a markdown verdict template the human can fill in

Outputs (relative to --out-dir, default benchmarks/omr-phase2.5):

    detections/<cell_id>.json   — list of {id, smufl_name, category, x, y, w, h, conf, pitch}
    overlays/<cell_id>.png      — annotated PNG (4× scaled if cell is small)
    verdicts/<cell_id>.md       — verdict template

CLI:
    python3 -m tools.omr.annotate.build_template \
        --manifest benchmarks/omr-phase2.5/cells.json \
        --out-dir  benchmarks/omr-phase2.5
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from ..pitch_resolver import pitch_for_notehead
from ..symbol_library.loader import SymbolLibrary
from ..template_matcher import SymbolDetection, detect_symbols
from ..types import MeasureCell


# ---------------------------------------------------------------------------
# Reconstruct a MeasureCell from a manifest entry + saved PNG
# ---------------------------------------------------------------------------


def _load_cell_from_manifest(entry: dict, root: Path) -> MeasureCell:
    """Load the saved cell + no-staff PNGs into a MeasureCell.

    `root` is the directory paths in the manifest are relative to (usually
    the repo root, the directory the user ran build_template from).
    """
    def _resolve(p: str | None) -> Path | None:
        if not p:
            return None
        pp = Path(p)
        return pp if pp.is_absolute() else (root / pp)

    cell_png = _resolve(entry["cell_png_path"])
    nostaff_png = _resolve(entry.get("nostaff_png_path"))

    image = cv2.imread(str(cell_png), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"cell png not loadable: {cell_png}")
    image_no_staff = (cv2.imread(str(nostaff_png), cv2.IMREAD_GRAYSCALE)
                      if nostaff_png and nostaff_png.exists() else None)

    h, w = image.shape
    return MeasureCell(
        page_index=entry["page"],
        system_index=entry["system_index"],
        staff_index=entry["staff_index"],
        measure_index=entry["measure_index"],
        image=image,
        image_no_staff=image_no_staff,
        bbox_page_px=(0, 0, w, h),
        staff_line_ys_canonical=list(entry["staff_line_ys_canonical"]),
        upscale_factor=1.0,
    )


# ---------------------------------------------------------------------------
# Overlay rendering
# ---------------------------------------------------------------------------


# Distinct hues for the first dozen detections, then a generic recycle.
_PALETTE_BGR = [
    (0, 0, 255),     # red
    (0, 200, 0),     # green
    (255, 0, 0),     # blue
    (0, 200, 200),   # yellow
    (255, 0, 255),   # magenta
    (200, 100, 0),   # teal
    (0, 100, 255),   # orange
    (200, 0, 200),   # purple
    (100, 200, 0),   # lime
    (50, 50, 200),   # brick
    (180, 105, 255), # pink
    (50, 180, 180),  # mustard
]


def _color_for(i: int) -> tuple[int, int, int]:
    return _PALETTE_BGR[i % len(_PALETTE_BGR)]


def render_overlay(
    cell: MeasureCell,
    detections: list[SymbolDetection],
    upscale: int = 2,
) -> np.ndarray:
    """Render a BGR image with each detection drawn as a numbered rect.

    The result is upscaled by `upscale` so labels remain legible. Detections
    are sorted by x_center for stable numbering across runs.
    """
    img = cell.image
    if img is None:
        raise ValueError("cell has no image")
    if img.ndim == 2:
        canvas = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        canvas = img.copy()
        if canvas.shape[2] == 3:
            # the saved PNG was read by cv2 as BGR already; nothing to do.
            pass

    # Lighten the background a little so colored rectangles pop.
    canvas = cv2.addWeighted(canvas, 0.7, np.full_like(canvas, 255), 0.3, 0)

    # Draw staff lines as a faint reference.
    for y in cell.staff_line_ys_canonical:
        cv2.line(canvas, (0, y), (canvas.shape[1] - 1, y), (200, 200, 200), 1)

    ordered = sorted(detections, key=lambda d: d.x_center)

    # Draw detection boxes + labels.
    for i, d in enumerate(ordered):
        color = _color_for(i)
        x0, y0 = d.x_canonical, d.y_canonical
        x1, y1 = x0 + d.width_canonical, y0 + d.height_canonical
        cv2.rectangle(canvas, (x0, y0), (x1, y1), color, 2)
        # Label "D<i>" inside a small filled chip so text is always readable.
        label = f"D{i}"
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        tx = max(0, x0)
        ty = max(text_size[1] + 4, y0 - 4)
        cv2.rectangle(canvas, (tx, ty - text_size[1] - 4),
                      (tx + text_size[0] + 6, ty + 2), color, -1)
        cv2.putText(canvas, label, (tx + 3, ty - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
                    cv2.LINE_AA)

    # Upscale for legibility (overlays may be opened by a human).
    if upscale > 1:
        new_w = canvas.shape[1] * upscale
        new_h = canvas.shape[0] * upscale
        canvas = cv2.resize(canvas, (new_w, new_h),
                            interpolation=cv2.INTER_LINEAR)
    return canvas


# ---------------------------------------------------------------------------
# Verdict markdown template
# ---------------------------------------------------------------------------


def build_verdict_markdown(
    entry: dict,
    detections: list[SymbolDetection],
    overlay_rel: str,
) -> str:
    """Build the markdown verdict template for one cell.

    `overlay_rel` is a path expressed relative to the verdicts/ directory
    (so the embedded image link works when the user opens the markdown).
    """
    ordered = sorted(detections, key=lambda d: d.x_center)
    cid = entry["cell_id"]
    clef = entry.get("clef", "treble")
    staff_ys = ", ".join(str(y) for y in entry["staff_line_ys_canonical"])

    lines: list[str] = []
    lines.append(f"# Cell {cid} — verdicts\n")
    lines.append(f"**Image:** ![overlay]({overlay_rel})\n")
    lines.append(f"**Clef assumed:** {clef}\n")
    lines.append(f"**Staff lines (canonical y):** {staff_ys}\n")
    lines.append(f"**Source:** {entry.get('source_tag', '?')}  ·  "
                 f"page {entry['page']}  ·  sys {entry['system_index']}  "
                 f"staff {entry['staff_index']}  measure {entry['measure_index']}\n")
    lines.append("")
    lines.append("## Detections")
    lines.append("")
    lines.append("For each detection below, replace `verdict: __` with one of:")
    lines.append("- `TP` — true positive (right symbol, right location)")
    lines.append("- `FP` — false positive (wrong symbol or hallucinated)")
    lines.append("- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong")
    lines.append("- `unsure` — leave for human review")
    lines.append("")
    lines.append("Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.")
    lines.append("")

    if not ordered:
        lines.append("_(matcher returned zero detections — this is itself a data point; "
                     "fill out the FN section below.)_")
        lines.append("")
    else:
        for i, d in enumerate(ordered):
            pitch_str = f" → {d.pitch}" if d.pitch else ""
            lines.append(
                f"- [ ] D{i}  {d.smufl_name} ({d.category}) at "
                f"(x={d.x_center}, y={d.y_center}){pitch_str}  conf={d.confidence:.2f}\n"
                f"       verdict: __________"
            )
        lines.append("")

    lines.append("## Missed noteheads (FN)")
    lines.append("")
    lines.append("For each notehead in the cell image that the matcher did NOT find, add a row:")
    lines.append("")
    lines.append("```")
    lines.append("FN1 at (x=___, y=___) → pitch=___")
    lines.append("FN2 at (x=___, y=___) → pitch=___")
    lines.append("```")
    lines.append("")

    lines.append("## Wrong-pitch corrections")
    lines.append("")
    lines.append("Only fill in for detections marked `WRONG_PITCH` above. Format:")
    lines.append("")
    lines.append("```")
    lines.append("D0 → correct pitch is C4")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Detection serialization
# ---------------------------------------------------------------------------


def _detections_to_dict(cell_id: str, detections: list[SymbolDetection]) -> dict:
    ordered = sorted(detections, key=lambda d: d.x_center)
    return {
        "cell_id": cell_id,
        "detections": [
            {
                "id": f"D{i}",
                "smufl_name": d.smufl_name,
                "category": d.category,
                "x": d.x_canonical,
                "y": d.y_canonical,
                "w": d.width_canonical,
                "h": d.height_canonical,
                "x_center": d.x_center,
                "y_center": d.y_center,
                "confidence": float(d.confidence),
                "pitch": d.pitch,
            }
            for i, d in enumerate(ordered)
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_templates(
    manifest_path: Path,
    out_dir: Path,
    library: SymbolLibrary | None = None,
    overlay_upscale: int = 2,
) -> tuple[int, int]:
    """For each cell in the manifest, run the matcher and write artifacts.

    Returns (n_cells_processed, n_detections_total).
    """
    if library is None:
        library = SymbolLibrary.load()

    overlays_dir = out_dir / "overlays"
    verdicts_dir = out_dir / "verdicts"
    detections_dir = out_dir / "detections"
    overlays_dir.mkdir(parents=True, exist_ok=True)
    verdicts_dir.mkdir(parents=True, exist_ok=True)
    detections_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text())
    root = Path.cwd()

    n_dets_total = 0
    n_cells = 0

    for entry in manifest:
        cid = entry["cell_id"]
        try:
            cell = _load_cell_from_manifest(entry, root)
        except FileNotFoundError as exc:
            print(f"  WARN: skipping {cid} — {exc}")
            continue

        clef = entry.get("clef", "treble")
        detections = detect_symbols(cell, library)
        # Resolve pitches for noteheads.
        for d in detections:
            if d.category == "notehead":
                d.pitch = pitch_for_notehead(d, clef=clef)

        n_dets_total += len(detections)
        n_cells += 1

        # Persist detections JSON.
        det_path = detections_dir / f"{cid}.json"
        det_path.write_text(json.dumps(
            _detections_to_dict(cid, detections), indent=2))

        # Render overlay.
        overlay_path = overlays_dir / f"{cid}.png"
        canvas = render_overlay(cell, detections, upscale=overlay_upscale)
        cv2.imwrite(str(overlay_path), canvas)

        # Verdict markdown — image link is relative to verdicts/ directory.
        overlay_rel = f"../overlays/{cid}.png"
        md = build_verdict_markdown(entry, detections, overlay_rel)
        (verdicts_dir / f"{cid}.md").write_text(md)

        print(f"  {cid}: {len(detections)} detections "
              f"({sum(1 for d in detections if d.category == 'notehead')} noteheads)")

    print(f"\nwrote {n_cells} cells / {n_dets_total} detections "
          f"→ {overlays_dir}, {verdicts_dir}, {detections_dir}")
    return n_cells, n_dets_total


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Render overlays + verdict templates for Phase 2.5.")
    ap.add_argument("--manifest", default="benchmarks/omr-phase2.5/cells.json",
                    help="Path to cells.json from select_cells")
    ap.add_argument("--out-dir", default="benchmarks/omr-phase2.5")
    ap.add_argument("--upscale", type=int, default=2,
                    help="Overlay upscale factor for legibility (default 2)")
    args = ap.parse_args()
    build_templates(Path(args.manifest), Path(args.out_dir),
                    overlay_upscale=args.upscale)


if __name__ == "__main__":
    main()
