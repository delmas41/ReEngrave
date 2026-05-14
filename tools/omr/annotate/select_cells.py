"""Select ~30 Phase-1 measure cells across several PDFs and persist them.

Output:
    benchmarks/omr-phase2.5/cells.json   — manifest, one row per cell
    benchmarks/omr-phase2.5/cells/<cell_id>.png         — canonical cell
    benchmarks/omr-phase2.5/cells/<cell_id>_nostaff.png — staff lines removed

The manifest row matches the shape downstream tools (build_template, score)
expect:

    {
      "cell_id":              "wtc-p5-sys0-s0-m1",
      "pdf":                  "<absolute path>",
      "page":                 5,
      "system_index":         0,
      "staff_index":          0,
      "measure_index":        1,
      "cell_png_path":        "benchmarks/omr-phase2.5/cells/<cell_id>.png",
      "nostaff_png_path":     "benchmarks/omr-phase2.5/cells/<cell_id>_nostaff.png",
      "staff_line_ys_canonical": [194, 243, 291, 339, 389],
      "clef":                 "treble",
      "source_tag":           "wtc-p5"
    }

CLI:
    python3 -m tools.omr.annotate.select_cells \
        --out-dir benchmarks/omr-phase2.5

Selection plan (default, ~30 cells):
    - WTC Book 1 p5            → first 15 cells in reading order
    - Beethoven 5 p10          → first 10 cells in reading order
    - WTC Book 1 p10           → first 5 cells in reading order

Override any source with --sources spec like:
    --sources wtc=/path/to/wtc.pdf:5:15,wtc10=/path/wtc.pdf:10:5

(format: tag=pdf:page:n_cells, joined by commas)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2

from ..preprocessing import render_page
from ..staff_detector import detect_staves
from ..measure_extractor import detect_barlines, extract_measures
from ..staff_line_removal import remove_staff_lines
from ..types import MeasureCell


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


# Canonical default PDFs. If a path doesn't exist, we skip that source with a
# warning rather than failing.
_DEFAULT_PDFS = {
    "wtc": "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/PDF Scores/IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf",
    "beethoven5": "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf",
}


@dataclass(frozen=True)
class Source:
    tag: str
    pdf: Path
    page: int          # 0-based
    n_cells: int       # number of cells to take from reading order

    @property
    def label(self) -> str:
        return f"{self.tag}-p{self.page}"


def _default_sources() -> list[Source]:
    return [
        Source("wtc",        Path(_DEFAULT_PDFS["wtc"]),        page=5,  n_cells=15),
        Source("beet5",      Path(_DEFAULT_PDFS["beethoven5"]), page=10, n_cells=10),
        Source("wtc",        Path(_DEFAULT_PDFS["wtc"]),        page=10, n_cells=5),
    ]


# ---------------------------------------------------------------------------
# Cell extraction
# ---------------------------------------------------------------------------


def _run_phase1_on_page(pdf: Path, page: int, dpi: int = 600) -> list[MeasureCell]:
    img = render_page(pdf, page, dpi=dpi)
    pws = detect_staves(img)
    pws = detect_barlines(pws)
    cells = extract_measures(pws)
    remove_staff_lines(cells)
    return cells


def _cell_id(tag: str, page: int, cell: MeasureCell) -> str:
    return f"{tag}-p{page}-sys{cell.system_index}-s{cell.staff_index}-m{cell.measure_index}"


def _save_cell_png(cell: MeasureCell, png_path: Path, no_staff: bool) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    img = cell.image_no_staff if no_staff else cell.image
    if img is None:
        return
    if img.ndim == 3:
        # cells are stored RGB; cv2.imwrite wants BGR
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(png_path), img)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_sources(spec: str) -> list[Source]:
    """Parse --sources tag=pdf:page:n_cells[,tag=pdf:page:n_cells…]."""
    out: list[Source] = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            tag, rest = item.split("=", 1)
            pdf_str, page_str, n_str = rest.rsplit(":", 2)
        except ValueError:
            raise SystemExit(f"bad --sources entry: {item!r} (expected tag=pdf:page:n)")
        out.append(Source(tag=tag.strip(),
                          pdf=Path(pdf_str.strip()),
                          page=int(page_str),
                          n_cells=int(n_str)))
    return out


def select_cells(
    sources: list[Source],
    out_dir: Path,
    dpi: int = 600,
    default_clef: str = "treble",
) -> list[dict]:
    cells_dir = out_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []

    for src in sources:
        if not src.pdf.exists():
            print(f"  WARN: skipping {src.label} — PDF not found at {src.pdf}",
                  file=sys.stderr)
            continue
        print(f"  processing {src.label} ({src.n_cells} cells from {src.pdf.name})…")
        try:
            cells = _run_phase1_on_page(src.pdf, src.page, dpi=dpi)
        except Exception as exc:  # noqa: BLE001 — surface and skip
            print(f"  WARN: Phase 1 failed on {src.label}: {exc!r}", file=sys.stderr)
            continue
        if not cells:
            print(f"  WARN: no cells from {src.label}", file=sys.stderr)
            continue

        # Reading order: system, then staff, then measure. extract_measures
        # already returns in roughly that order, but sort to be safe.
        cells = sorted(cells, key=lambda c: (c.system_index, c.staff_index, c.measure_index))

        for c in cells[: src.n_cells]:
            cid = _cell_id(src.tag, src.page, c)
            cell_png = cells_dir / f"{cid}.png"
            nostaff_png = cells_dir / f"{cid}_nostaff.png"
            _save_cell_png(c, cell_png, no_staff=False)
            if c.image_no_staff is not None:
                _save_cell_png(c, nostaff_png, no_staff=True)

            # Paths in manifest are repo-relative if possible
            try:
                cell_rel = cell_png.relative_to(Path.cwd())
                nost_rel = nostaff_png.relative_to(Path.cwd())
            except ValueError:
                cell_rel = cell_png
                nost_rel = nostaff_png

            manifest.append({
                "cell_id":      cid,
                "pdf":          str(src.pdf),
                "page":         src.page,
                "system_index": c.system_index,
                "staff_index":  c.staff_index,
                "measure_index": c.measure_index,
                "cell_png_path":   str(cell_rel),
                "nostaff_png_path": str(nost_rel) if c.image_no_staff is not None else None,
                "staff_line_ys_canonical": list(c.staff_line_ys_canonical),
                "clef": default_clef,
                "source_tag": src.label,
                # Persist canonical cell dims so build_template can know the
                # overlay canvas size without loading the PNG.
                "cell_canonical_w": c.width,
                "cell_canonical_h": c.height,
            })

    # Write the manifest
    manifest_path = out_dir / "cells.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nwrote {len(manifest)} cells → {manifest_path}")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="Select cells for Phase 2.5 annotation.")
    ap.add_argument("--out-dir", default="benchmarks/omr-phase2.5",
                    help="Where to write cells/ and cells.json (default: benchmarks/omr-phase2.5)")
    ap.add_argument("--sources", default="",
                    help="Optional override: tag=pdf:page:n[,tag=pdf:page:n…]. "
                         "If empty, uses built-in WTC + Beethoven defaults.")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--clef", default="treble",
                    help="Assumed clef for cells (Phase 2.5 has no clef detection).")
    args = ap.parse_args()

    sources = parse_sources(args.sources) if args.sources else _default_sources()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    select_cells(sources, out_dir, dpi=args.dpi, default_clef=args.clef)


if __name__ == "__main__":
    main()
