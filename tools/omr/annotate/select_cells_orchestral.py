"""Select per-instrument measure-cells from orchestral pages.

The default `select_cells.py` uses PAD_ABOVE/BELOW_STAFF_LINES = 4 which is
fine for piano scores (lots of room around 2 staves) but produces overly
tall cells on orchestral pages — adjacent instrument staves are only ~2-3
spacings apart, so a single 'cell' spills into ~5 instruments.

This selector:
  * Monkey-patches PAD_*_STAFF_LINES = 5.0 so extreme ledger-line notes are
    fully captured in the crop (dynamics and articulations above/below still
    fit without spilling into a neighbouring instrument's staff).
  * For each requested page, samples cells uniformly across the (staff x
    measure) grid so we get a mix of instrument families, page positions,
    and within-page densities.

Output schema is identical to select_cells.py — produces
`<out>/cells.json` plus `<out>/cells/<id>.png` + `<id>_nostaff.png`.

CLI:
    python3 -m tools.omr.annotate.select_cells_orchestral \\
        --out-dir benchmarks/omr-phase-realft \\
        --plan beet5=PDF:1:12,beet5=PDF:5:12,...
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
from .. import measure_extractor as _me
from ..staff_line_removal import remove_staff_lines
from ..types import MeasureCell


# Padding for orchestral cells — 5.0 staff-spaces above/below captures
# extreme ledger-line notes and high/low dynamics without spilling into
# adjacent staves on typical orchestral page densities. (Default in
# measure_extractor is 4; prior value here was 2.5 which clipped ledger notes.)
ORCH_PAD_STAFF_LINES = 5.0


@dataclass(frozen=True)
class Source:
    tag: str           # piece slug, e.g. "beet5"
    pdf: Path
    page: int          # 0-based page index
    n_cells: int       # cells to take from this page


def _patch_padding_globals():
    """Reduce measure_extractor's pad constants for orchestral selection."""
    _me.PAD_ABOVE_STAFF_LINES = ORCH_PAD_STAFF_LINES
    _me.PAD_BELOW_STAFF_LINES = ORCH_PAD_STAFF_LINES


def _run_phase1_on_page(pdf: Path, page: int, dpi: int = 600) -> list[MeasureCell]:
    img = render_page(pdf, page, dpi=dpi)
    pws = detect_staves(img)
    pws = _me.detect_barlines(pws)
    cells = _me.extract_measures(pws)
    remove_staff_lines(cells)
    return cells


def _cell_id(tag: str, page: int, cell: MeasureCell) -> str:
    # 1-based page in the ID for human readability.
    return f"{tag}-p{page+1}-sys{cell.system_index}-s{cell.staff_index}-m{cell.measure_index}"


def _sample_uniform(items: list, n: int) -> list:
    """Pick *n* items spaced evenly across the list."""
    if n >= len(items):
        return list(items)
    if n <= 0:
        return []
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def _save_cell_png(cell: MeasureCell, png_path: Path, no_staff: bool) -> bool:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    img = cell.image_no_staff if no_staff else cell.image
    if img is None:
        return False
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return bool(cv2.imwrite(str(png_path), img))


def _infer_clef_from_staff_index(staff_index: int, n_staves: int) -> str:
    """Heuristic: assume top-of-page = treble winds, bottom = bass strings.

    Hand-labeling will correct as needed. The clef field is only used for
    optional Verovio-based pitch resolution downstream; for fine-tuning
    label generation it doesn't matter what we put here.
    """
    if n_staves == 0:
        return "treble"
    rel = staff_index / max(1, n_staves - 1)
    if rel < 0.3:
        return "treble"
    if rel > 0.75:
        return "bass"
    return "treble"


def select_orchestral(
    sources: list[Source],
    out_dir: Path,
    dpi: int = 600,
) -> list[dict]:
    _patch_padding_globals()

    cells_dir = out_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []

    for src in sources:
        if not src.pdf.exists():
            print(f"  WARN: skipping {src.tag} p{src.page+1} — PDF not found at {src.pdf}",
                  file=sys.stderr)
            continue
        print(f"  processing {src.tag} p{src.page+1} ({src.n_cells} cells from {src.pdf.name})…")
        try:
            cells = _run_phase1_on_page(src.pdf, src.page, dpi=dpi)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN: phase 1 failed on {src.tag} p{src.page+1}: {exc!r}",
                  file=sys.stderr)
            continue
        if not cells:
            print(f"  WARN: no cells from {src.tag} p{src.page+1}", file=sys.stderr)
            continue

        # Order in reading order (system, then staff, then measure)
        cells = sorted(
            cells,
            key=lambda c: (c.system_index, c.staff_index, c.measure_index),
        )
        # Distinct staves on this page (across all systems)
        n_staves = 1 + max(c.staff_index for c in cells)

        picked = _sample_uniform(cells, src.n_cells)

        for c in picked:
            cid = _cell_id(src.tag, src.page, c)
            cell_png = cells_dir / f"{cid}.png"
            nostaff_png = cells_dir / f"{cid}_nostaff.png"
            saved = _save_cell_png(c, cell_png, no_staff=False)
            if not saved:
                print(f"    skip {cid}: empty image", file=sys.stderr)
                continue
            has_nostaff = False
            if c.image_no_staff is not None:
                has_nostaff = _save_cell_png(c, nostaff_png, no_staff=True)

            try:
                cell_rel = cell_png.relative_to(Path.cwd())
                nost_rel = nostaff_png.relative_to(Path.cwd()) if has_nostaff else None
            except ValueError:
                cell_rel = cell_png
                nost_rel = nostaff_png if has_nostaff else None

            manifest.append({
                "cell_id": cid,
                "pdf": str(src.pdf),
                "page": src.page,
                "system_index": c.system_index,
                "staff_index": c.staff_index,
                "measure_index": c.measure_index,
                "cell_png_path": str(cell_rel),
                "nostaff_png_path": str(nost_rel) if nost_rel is not None else None,
                "staff_line_ys_canonical": list(c.staff_line_ys_canonical),
                "clef": _infer_clef_from_staff_index(c.staff_index, n_staves),
                "source_tag": f"{src.tag}-p{src.page+1}",
                "cell_canonical_w": c.width,
                "cell_canonical_h": c.height,
                "n_staves_on_page": n_staves,
            })

    manifest_path = out_dir / "cells.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nwrote {len(manifest)} cells → {manifest_path}")
    return manifest


def parse_plan(spec: str) -> list[Source]:
    """Parse --plan tag=pdf:page:n[,tag=pdf:page:n…].

    `page` is 1-based on the CLI for human ergonomics; we convert to 0-based
    internally to match the rest of the codebase.
    """
    out: list[Source] = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            tag, rest = item.split("=", 1)
            pdf_str, page_str, n_str = rest.rsplit(":", 2)
        except ValueError as exc:
            raise SystemExit(f"bad --plan entry: {item!r}: {exc}")
        out.append(Source(
            tag=tag.strip(),
            pdf=Path(pdf_str.strip()),
            page=int(page_str) - 1,
            n_cells=int(n_str),
        ))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Select orchestral measure cells.")
    ap.add_argument("--out-dir", default="benchmarks/omr-phase-realft",
                    help="Output benchmark directory.")
    ap.add_argument("--plan", required=True,
                    help="tag=pdf:page:n,... (page is 1-based)")
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    sources = parse_plan(args.plan)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    select_orchestral(sources, out_dir, dpi=args.dpi)


if __name__ == "__main__":
    main()
