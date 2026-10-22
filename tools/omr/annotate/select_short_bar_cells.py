"""Select measure cells for HOLLOW-NOTEHEAD labeling, by what the bar is missing.

`benchmarks/omr-first-run-2026-08/DURATIONS.md` measured why durations fail on
scans and it is not the rhythm layer: on a 600 dpi bitonal print the half
notehead's counter closes to a thin sliver inside an otherwise solid head, the
detector never calls it hollow, and Beethoven 5 p.1 turns 68 half notes into 8.
The engraved control has duration recall equal to pitch recall, so the gap is
appearance, and the lever for appearance is labelled examples.

This picks the cells worth a human's time.

## The signal

A bar whose detected content does not fill its meter is missing something, and
since the meter is now read from the header
(`benchmarks/omr-timesig-2026-08/`), the shortfall is computable without any
reference. Ranking cells by it is worth about four times uniform sampling.
Measured on Beethoven 5 p.1, where the reference says which bars hold half
notes:

    top 20 by deficit   20 of 20 contain a half note   (100%)
    top 40 by deficit   37 of 40                        (92%)
    random 20            5 of 20                        (25%)
    random 40           13 of 40                        (32%)

Two candidate rankings were tried first and are recorded in DURATIONS.md as
failures: proposing the heads directly as enclosed white (662 candidates for 68
notes) and as unclaimed notehead-sized ink blobs (8 for 68 — a hollow head is
attached to its stem and its ties, so it is never its own component). Nothing
here proposes a box; the human draws them, and this only decides where to look.

## What it emits

The same manifest and cell PNGs as `select_cells_orchestral`, whose helpers it
reuses, so `run_yolo`, the labeling server and `verdicts_to_yolo_labels` all work
unchanged. It also writes `SHORT_BAR_HINTS.txt` — per cell, the meter and how
many beats are missing, which is what to look for in that bar.

⚠️ It does NOT call `_patch_padding_globals`, so cells carry the pipeline's own
`PAD_ABOVE/BELOW_STAFF_LINES` rather than the orchestral selector's 5.0. That is
deliberate and it is the argument `select_timesig_cells` makes: a cell a
specialist is trained on should be what the detector sees at inference, and
padding changes the canonical scale. It does mean these cells are framed slightly
tighter than the 2026-05/06 batches, so if ledger-line notes come out clipped,
raise the pad here rather than assuming the older framing.

    python3 -m tools.omr.annotate.select_short_bar_cells \\
        --out-dir benchmarks/omr-labeling-hollow-2026-08 \\
        --plan "beet5=/abs/beethoven5.pdf:2:12,mahler=/abs/mahler5.pdf:12:12"

`page` is 1-based on the CLI, as in the other selectors.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from ..transcribe import DEFAULT_WEIGHTS, transcribe
from .select_cells_orchestral import (
    _cell_id,
    _infer_clef_from_staff_index,
    _run_phase1_on_page,
    _save_cell_png,
)

#: A bar must be missing at least this share of its meter to be worth labelling.
#: Below it the shortfall is rounding in the duration parse rather than a note
#: nobody saw.
MIN_DEFICIT_FRACTION = 0.25

#: ...and a bar that resolved to nothing at all is skipped. An empty cell is
#: either a genuine whole-bar rest or a total detection failure, and neither is
#: a hollow-notehead example.
MIN_RESOLVED_BEATS = 0.01


@dataclass
class Source:
    tag: str
    pdf: Path
    page: int          # 0-based
    n_cells: int


def measure_deficits(
    pdf: Path, pages: list[int], weights: Path = DEFAULT_WEIGHTS, dpi: int = 600
) -> dict[int, dict[tuple[int, int], tuple[float, float, str]]]:
    """How many beats each (staff, measure) is short of its meter, per page.

    Returns `{page_index: {(staff, measure): (deficit, resolved, meter)}}`. Bars
    whose meter was never read are absent — without a meter there is no
    shortfall to compute, which is the honest answer rather than assuming 4/4.

    The pages are transcribed in ONE call, from the first requested through the
    last, because a meter is printed at the start of a movement and carried from
    there. Asking for page 30 alone gets no meter and therefore no ranking; asking
    for 1 through 30 carries the movement's meter onto all of them.
    """
    span = list(range(min(pages), max(pages) + 1))
    result = transcribe(pdf_path=pdf, pages=span, weights=str(weights),
                        dpi=dpi, progress=False)
    out: dict[int, dict[tuple[int, int], tuple[float, float, str]]] = {}
    for out_page in result.get("pages", []):
        page_index = out_page.get("page_index")
        per_page: dict[tuple[int, int], tuple[float, float, str]] = {}
        for system in out_page.get("systems", []):
            for staff in system.get("staves", []):
                staff_time = staff.get("time_signature")
                for measure in staff.get("measures", []):
                    time_sig = measure.get("time_signature") or staff_time
                    if not time_sig:
                        continue
                    numerator = time_sig.get("numerator")
                    denominator = time_sig.get("denominator")
                    if not numerator or not denominator:
                        continue
                    beats = numerator * 4.0 / denominator
                    resolved = 0.0
                    for det in measure.get("detections", []):
                        if det.get("category") in ("notehead", "rest"):
                            resolved += float(det.get("duration_beats") or 0.0)
                    per_page[(staff["staff_index"], measure["measure_index"])] = (
                        max(0.0, beats - resolved), resolved,
                        time_sig.get("raw") or f"{numerator}/{denominator}",
                    )
        out[page_index] = per_page
    return out


def select_short_bars(
    sources: list[Source], out_dir: Path, dpi: int = 600,
    weights: Path = DEFAULT_WEIGHTS,
) -> list[dict]:
    cells_dir = out_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    hints: list[str] = []

    # One transcribe per PDF, spanning every page asked for, so the meter read
    # at the start of the movement reaches the later pages.
    by_pdf: dict[Path, list[Source]] = {}
    for src in sources:
        by_pdf.setdefault(src.pdf, []).append(src)
    deficits_by_page: dict[Path, dict[int, dict]] = {}
    for pdf, group in by_pdf.items():
        if not pdf.exists():
            print(f"  WARN: no PDF at {pdf}", file=sys.stderr)
            continue
        wanted = sorted({s.page for s in group})
        print(f"  {pdf.name}: transcribing pages "
              f"{min(wanted) + 1}-{max(wanted) + 1} for the meter…")
        try:
            deficits_by_page[pdf] = measure_deficits(pdf, wanted, weights, dpi)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN: transcribe failed on {pdf.name}: {exc!r}", file=sys.stderr)

    for src in sources:
        if not src.pdf.exists():
            continue
        deficits = deficits_by_page.get(src.pdf, {}).get(src.page, {})
        if not deficits:
            print(f"  WARN: no meter read on {src.tag} p{src.page + 1} — "
                  f"nothing to rank by", file=sys.stderr)
            continue

        try:
            cells = _run_phase1_on_page(src.pdf, src.page, dpi=dpi)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN: phase 1 failed on {src.tag} p{src.page + 1}: {exc!r}",
                  file=sys.stderr)
            continue
        if not cells:
            continue
        n_staves = 1 + max(c.staff_index for c in cells)

        scored = []
        for cell in cells:
            entry = deficits.get((cell.staff_index, cell.measure_index))
            if entry is None:
                continue
            deficit, resolved, meter = entry
            beats = deficit + resolved
            if resolved < MIN_RESOLVED_BEATS:
                continue
            if beats <= 0 or deficit / beats < MIN_DEFICIT_FRACTION:
                continue
            scored.append((deficit, cell, resolved, meter))
        scored.sort(key=lambda row: -row[0])
        picked = scored[:src.n_cells]
        print(f"    {len(scored)} short bars, taking {len(picked)}")

        for deficit, cell, resolved, meter in picked:
            cid = _cell_id(src.tag, src.page, cell)
            cell_png = cells_dir / f"{cid}.png"
            nostaff_png = cells_dir / f"{cid}_nostaff.png"
            if not _save_cell_png(cell, cell_png, no_staff=False):
                continue
            has_nostaff = (
                cell.image_no_staff is not None
                and _save_cell_png(cell, nostaff_png, no_staff=True)
            )
            try:
                cell_rel = cell_png.relative_to(Path.cwd())
                nost_rel = nostaff_png.relative_to(Path.cwd()) if has_nostaff else None
            except ValueError:
                cell_rel, nost_rel = cell_png, (nostaff_png if has_nostaff else None)

            manifest.append({
                "cell_id": cid,
                "pdf": str(src.pdf),
                "page": src.page,
                "system_index": cell.system_index,
                "staff_index": cell.staff_index,
                "measure_index": cell.measure_index,
                "cell_png_path": str(cell_rel),
                "nostaff_png_path": str(nost_rel) if nost_rel is not None else None,
                "staff_line_ys_canonical": list(cell.staff_line_ys_canonical),
                "clef": _infer_clef_from_staff_index(cell.staff_index, n_staves),
                "source_tag": f"{src.tag}-p{src.page + 1}",
                "cell_canonical_w": cell.width,
                "cell_canonical_h": cell.height,
                "n_staves_on_page": n_staves,
                "meter": meter,
                "beats_resolved": round(resolved, 3),
                "beats_missing": round(deficit, 3),
            })
            hints.append(
                f"{cid}: {meter}, resolved {resolved:g} of "
                f"{resolved + deficit:g} beats — {deficit:g} missing"
            )

    manifest_path = out_dir / "cells.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    (out_dir / "SHORT_BAR_HINTS.txt").write_text(
        "How many beats each cell is short of its own meter. A bar missing about\n"
        "half its length is the signature of an undetected half note — which is\n"
        "what this batch exists to label. The hint is a place to look, not a\n"
        "claim: label what the cell shows.\n\n" + "\n".join(hints) + "\n"
    )
    print(f"\nwrote {len(manifest)} cells → {manifest_path}")
    return manifest


def parse_plan(spec: str) -> list[Source]:
    out: list[Source] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        tag, _, rest = chunk.partition("=")
        pdf_str, _, tail = rest.rpartition(":")
        pdf_path, _, page_str = pdf_str.rpartition(":")
        out.append(Source(tag=tag.strip(), pdf=Path(pdf_path),
                          page=int(page_str) - 1, n_cells=int(tail)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--plan", required=True,
                    help="tag=pdf:page:n,... (page is 1-based)")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    select_short_bars(parse_plan(args.plan), args.out_dir,
                      dpi=args.dpi, weights=args.weights)


if __name__ == "__main__":
    main()
