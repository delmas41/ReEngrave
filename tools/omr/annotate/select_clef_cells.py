"""Clef-targeted cell selector for the clef-diversity labeling pass.

Extracts the m0 cell (first measure of each staff — the clef-bearing one) from
each requested page, across multiple pages/scores, into ONE clean labeling
batch. Unlike select_cells_orchestral (uniform sampling → mostly interior
measures with no clefs), this takes *only* the m0 cells, so every cell has a
clef. Fixes the junk-cell problem from the first batch.

Optional `--legato`: for each page, run LEGATO and record its top-to-bottom
clef sequence into CLEF_HINTS.txt, so you can steer toward the rare types
(alto / tenor / perc / change) rather than labeling treble repeats.

CLI:
    python3 -m tools.omr.annotate.select_clef_cells \
        --out-dir benchmarks/omr-labeling-clef-diverse \
        --plan "mahler=/abs/Mahler_5_.pdf:0, beet5=/abs/Beethoven5.pdf:44, lamer=/abs/LaMer.pdf:10" \
        [--legato]

Plan entries are `tag=PDF:page` (page 0-based). No cell count — it takes every
staff's m0 cell on that page.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from .select_cells_orchestral import (
    _cell_id,
    _patch_padding_globals,
    _run_phase1_on_page,
    _save_cell_png,
)

SCRATCH = os.environ.get("SCRATCH_LEGATO", "")
DEFAULT_LEGATO_DIR = os.environ.get("LEGATO_DIR", SCRATCH and str(Path(SCRATCH) / "legato") or "")
DEFAULT_LEGATO_PY = os.environ.get("LEGATO_PY", SCRATCH and str(Path(SCRATCH) / "legato-venv/bin/python") or "")


def _parse_plan(spec: str) -> list[tuple[str, Path, int]]:
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        tag, rest = part.split("=", 1)
        pdf, page = rest.rsplit(":", 1)
        out.append((tag.strip(), Path(pdf.strip()), int(page)))
    return out


def legato_clef_sequence(pdf: Path, page: int, out_dir: Path) -> list[str] | None:
    """Run LEGATO on a page, return its top-to-bottom clef sequence (or None)."""
    if not DEFAULT_LEGATO_DIR or not Path(DEFAULT_LEGATO_DIR).exists():
        return None
    try:
        import fitz
        from PIL import Image
        png = out_dir / f"_legato_{pdf.stem}_p{page}.png"
        pm = fitz.open(str(pdf))[page].get_pixmap(dpi=200)
        Image.frombytes("RGB", (pm.width, pm.height), pm.samples).save(str(png))
        env = {**os.environ, "PYTHONPATH": DEFAULT_LEGATO_DIR,
               "LEGATO_ENCODER_REF": os.environ.get("LEGATO_ENCODER_REF", "unsloth/Llama-3.2-11B-Vision"),
               "LEGATO_MAX_LENGTH": "1024", "PYTORCH_ENABLE_MPS_FALLBACK": "1"}
        subprocess.run(
            [DEFAULT_LEGATO_PY, "scripts/inference.py", "--model_path", "guangyangmusic/legato",
             "--image_path", str(png), "--output_path", str(out_dir), "--device", "cpu", "--beam_size", "1"],
            cwd=DEFAULT_LEGATO_DIR, env=env, capture_output=True, text=True, timeout=1800)
        js = sorted(out_dir.glob(f"{png.stem}*_abc.json"))
        if not js:
            return None
        abc = json.loads(js[-1].read_text())["abc_transcription"][0]
        return [m.group(2) for ln in abc.splitlines()
                for m in [re.match(r"V:\s*\d+\s+([a-z]+)", ln)] if m]
    except Exception as e:  # noqa: BLE001
        print(f"  [legato] skipped for {pdf.name} p{page}: {e}", file=sys.stderr)
        return None


def select(plan: list[tuple[str, Path, int]], out_dir: Path, dpi: int,
           use_legato: bool) -> None:
    _patch_padding_globals()
    cells_dir = out_dir / "cells"
    det_dir = out_dir / "detections"
    cells_dir.mkdir(parents=True, exist_ok=True)
    det_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    hints: list[str] = []
    for tag, pdf, page in plan:
        if not pdf.exists():
            print(f"  WARN: {tag} p{page} — PDF not found: {pdf}", file=sys.stderr)
            continue
        print(f"  {tag} p{page}: extracting m0 clef cells from {pdf.name}…")
        try:
            cells = _run_phase1_on_page(pdf, page, dpi=dpi)
        except Exception as e:  # noqa: BLE001
            print(f"  WARN: phase-1 failed on {tag} p{page}: {e!r}", file=sys.stderr)
            continue
        m0 = [c for c in cells if c.measure_index == 0]
        m0.sort(key=lambda c: (c.system_index, c.staff_index))
        n = 0
        for c in m0:
            cid = _cell_id(tag, page, c)
            if not _save_cell_png(c, cells_dir / f"{cid}.png", no_staff=False):
                continue
            _save_cell_png(c, cells_dir / f"{cid}_nostaff.png", no_staff=True)
            (det_dir / f"{cid}.json").write_text(json.dumps({"cell_id": cid, "detections": []}))
            manifest.append({"cell_id": cid, "png": f"cells/{cid}.png",
                             "system_index": c.system_index, "staff_index": c.staff_index})
            n += 1
        seq = legato_clef_sequence(pdf, page, out_dir) if use_legato else None
        hints.append(f"{tag} p{page}: {n} clef cells"
                     + (f"  | LEGATO clefs top→bottom: {', '.join(seq)}" if seq else ""))
        print(f"    → {n} clef cells" + (f"  (LEGATO: {seq})" if seq else ""))

    (out_dir / "cells.json").write_text(json.dumps(manifest, indent=2))
    (out_dir / "CLEF_HINTS.txt").write_text(
        "Clef-diversity labeling batch — one m0 (clef-bearing) cell per staff.\n"
        "Label EVERY symbol in each cell (clef + key-sig accidentals + time-sig\n"
        "digits + rests/notes). Prioritize the RARE clefs: cClefAlto (viola),\n"
        "cClefTenor (cello/bassoon high), unpitchedPercussionClef1 (perc), and\n"
        "the *Change classes (mid-bar). Skip redundant treble/bass repeats.\n"
        "keySharp/keyFlat/keyNatural for key-sig accidentals; accidental* for\n"
        "note accidentals.\n\nPer-page LEGATO clef reads (hints only — trust your eyes):\n  "
        + "\n  ".join(hints) + "\n")
    print(f"\n  batch → {out_dir}  ({len(manifest)} clef cells)")
    print(f"  serve: python3 -m tools.omr.annotate.server --bench-dir {out_dir}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--plan", required=True, help="tag=PDF:page, tag=PDF:page, … (page 0-based)")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--legato", action="store_true",
                    help="Tag each page with LEGATO's clef sequence (needs LEGATO_DIR/LEGATO_PY).")
    args = ap.parse_args(argv)
    select(_parse_plan(args.plan), args.out_dir, args.dpi, args.legato)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
