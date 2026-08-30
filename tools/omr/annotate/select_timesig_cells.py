"""Select staff-header cells for TIME-SIGNATURE labeling.

Time signatures are printed at the start of a piece / movement / meter change —
the first measure of the first system. This selector takes movement-start pages
(where a meter IS printed) and grabs each staff's header cell from the first
system, so a human can box the time-sig glyphs (`timeSig0`-`9`, `timeSigCommon`,
`timeSigCutCommon`). Those verdicts train a time-sig specialist for the decoupled
staff-header reader (`transcribe._read_staff_header`), which today reads clefs
well but no time-sig digits (the DSv2 domain gap).

Two things this gets right that the older clef selector didn't:

  * **Inference-matched cells.** It runs the EXACT `transcribe` phase-1 (no
    orchestral padding patch, dpi 300) so the canonical cells are byte-for-byte
    what `_read_staff_header` sees at inference — a specialist trained on them
    transfers. (`select_cells_orchestral` patches the padding + renders at 600 →
    a different canonical scale that would NOT transfer.)
  * **A complete manifest.** Every entry has `cell_png_path`,
    `cell_canonical_w/h`, etc., so `verdicts_to_yolo_labels` works without a
    post-patch (the `select_clef_cells` footgun).

Writes `<out>/cells.json`, `<out>/cells/<id>.png` (+ `_nostaff.png`), and
`<out>/TIMESIG_HINTS.txt` (the meter to expect on each page — a labeling aid).

CLI:
    python3 -m tools.omr.annotate.select_timesig_cells \
        --out-dir benchmarks/omr-labeling-timesig-2026-07-13 \
        --plan "beet5=/abs/beethoven5.pdf:1:2/4,bolero=/abs/bolero.pdf:1:3/4"
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
from ..measure_extractor import (
    detect_barlines, extract_measures, resegment_fused_measures)
from ..staff_line_removal import remove_staff_lines
from ..types import MeasureCell


@dataclass
class Source:
    tag: str
    pdf: Path
    page: int          # 0-based
    meter: str         # human hint, e.g. "2/4" (or "?" if unknown)
    first_system: bool = False  # keyboard pages: only the first system prints
                                # the meter; later "systems" are continuation
                                # lines (no time sig). Orchestral movement-start
                                # pages split the ONE opening into bracket-group
                                # "systems" that all show it → keep all (default).


def _phase1(pdf: Path, page: int, dpi: int) -> list[MeasureCell]:
    """EXACTLY transcribe's phase-1 — same cells `_read_staff_header` infers on."""
    img = render_page(pdf, page, dpi=dpi)
    pws = detect_staves(img)
    pws = detect_barlines(pws)
    cells = extract_measures(pws)
    cells = resegment_fused_measures(pws, cells)
    remove_staff_lines(cells)
    return cells


def _save_png(cell: MeasureCell, path: Path, no_staff: bool) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = cell.image_no_staff if no_staff else cell.image
    if img is None:
        return False
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return bool(cv2.imwrite(str(path), img))


def _clef_guess(staff_index: int, n_staves: int) -> str:
    if n_staves <= 1:
        return "treble"
    return "bass" if staff_index / (n_staves - 1) > 0.75 else "treble"


def select_timesig(sources: list[Source], out_dir: Path, dpi: int = 300) -> list[dict]:
    cells_dir = out_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    hints: list[str] = []

    for src in sources:
        if not src.pdf.exists():
            print(f"  WARN skip {src.tag}: PDF not found {src.pdf}", file=sys.stderr)
            continue
        print(f"  {src.tag} p{src.page + 1} (expect {src.meter}) — {src.pdf.name}")
        try:
            cells = _phase1(src.pdf, src.page, dpi)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN phase1 failed {src.tag}: {exc!r}", file=sys.stderr)
            continue
        if not cells:
            print(f"  WARN no cells {src.tag}", file=sys.stderr)
            continue

        n_staves = 1 + max(c.staff_index for c in cells)
        # Each staff-row's header cell (min measure_index) in EVERY system on the
        # page. On a movement-start page the opening is usually split into
        # bracket groups (system 0/1/2 …), all showing the meter; a genuine
        # continuation system lower on the page won't — its header cell has a
        # clef but no time sig and is kept as a useful hard negative (the human
        # simply boxes nothing there). Key by (system, staff).
        keep_sys = min(c.system_index for c in cells) if src.first_system else None
        header: dict[tuple[int, int], MeasureCell] = {}
        for c in cells:
            if keep_sys is not None and c.system_index != keep_sys:
                continue  # keyboard: only the first line carries the meter
            key = (c.system_index, c.staff_index)
            cur = header.get(key)
            if cur is None or c.measure_index < cur.measure_index:
                header[key] = c

        n_here = 0
        for key in sorted(header):
            c = header[key]
            cid = f"{src.tag}-p{src.page + 1}-sys{c.system_index}-s{c.staff_index}-m{c.measure_index}"
            cell_png = cells_dir / f"{cid}.png"
            if not _save_png(c, cell_png, no_staff=False):
                print(f"    skip {cid}: empty image", file=sys.stderr)
                continue
            nostaff_png = cells_dir / f"{cid}_nostaff.png"
            has_nostaff = c.image_no_staff is not None and _save_png(c, nostaff_png, no_staff=True)
            try:
                cell_rel = cell_png.relative_to(Path.cwd())
                nost_rel = nostaff_png.relative_to(Path.cwd()) if has_nostaff else None
            except ValueError:
                cell_rel, nost_rel = cell_png, (nostaff_png if has_nostaff else None)
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
                "clef": _clef_guess(c.staff_index, n_staves),
                "source_tag": f"{src.tag}-p{src.page + 1}",
                "cell_canonical_w": c.width,
                "cell_canonical_h": c.height,
                "n_staves_on_page": n_staves,
                "expected_time_sig": src.meter,
            })
            n_here += 1
        hints.append(f"{src.tag}-p{src.page + 1}: {n_here} staves — expect time signature "
                     f"{src.meter}  ({src.pdf.name})")

    (out_dir / "cells.json").write_text(json.dumps(manifest, indent=2))
    (out_dir / "TIMESIG_HINTS.txt").write_text(
        "Time-signature labeling hints — the meter printed on each page's first\n"
        "system. BOX the time-sig glyphs only (timeSig0-9, timeSigCommon,\n"
        "timeSigCutCommon); confirm the model's pre-labeled noteheads/clefs.\n"
        "Verify against the actual cell — these are aids, not ground truth.\n\n"
        + "\n".join(hints) + "\n")
    print(f"\nwrote {len(manifest)} header cells → {out_dir / 'cells.json'}")
    print(f"hints → {out_dir / 'TIMESIG_HINTS.txt'}")
    return manifest


def parse_plan(spec: str) -> list[Source]:
    """`tag=/abs/file.pdf:PAGE:METER,tag2=...` — PAGE is 1-based (human)."""
    out: list[Source] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        tag, rest = part.split("=", 1)
        # rsplit twice off the right so Windows-ish paths with ':' still work
        path_and_page, meter = rest.rsplit(":", 1)
        pdf_str, page_str = path_and_page.rsplit(":", 1)
        out.append(Source(tag=tag.strip(), pdf=Path(pdf_str.strip()),
                          page=int(page_str) - 1, meter=meter.strip()))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--plan", required=True,
                    help="tag=/abs/file.pdf:PAGE:METER,... (PAGE 1-based, METER like 2/4)")
    ap.add_argument("--dpi", type=int, default=300,
                    help="Render DPI — match transcribe (default 300)")
    ap.add_argument("--first-system-tags", default="",
                    help="Comma-separated tags whose pages are KEYBOARD/multi-line "
                         "(take only the first system — the one that prints the "
                         "meter). Orchestral tags keep all bracket-group systems.")
    args = ap.parse_args(argv)
    sources = parse_plan(args.plan)
    if not sources:
        print("ERROR: empty plan", file=sys.stderr)
        return 2
    fs_tags = {t.strip() for t in args.first_system_tags.split(",") if t.strip()}
    for s in sources:
        if s.tag in fs_tags:
            s.first_system = True
    select_timesig(sources, args.out_dir, dpi=args.dpi)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
