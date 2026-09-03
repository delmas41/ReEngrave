"""Re-cut a labeling batch's cell PNGs, for exactly the ids it already has.

WHY THIS EXISTS. `benchmarks/*/cells/` is gitignored — the PNGs are large and
reproducible, so only the manifest, the detections and the verdicts are
committed. A fresh checkout of a batch therefore has every id and no image at
all: `/api/cell/{id}/image` answers 404 for all of them and the canvas draws
nothing, which reads as "the batch shows no music" while the sidebar, the
hotkeys and the hints all work. The server says so at startup —
`WARN: cells dir missing` — and that line is the confirmation.

WHY NOT JUST RE-RUN THE CUTTER. Because the cutter's job is to CHOOSE cells,
not to render known ones. `select_cells_orchestral` samples, and
`rank_and_trim.py` rewrites `cells.json` and deletes the PNGs it did not keep.
Pointing either at a batch that has been labeled can renumber the cell set and
orphan every verdict in it — a verdict file is keyed by `cell_id`, and a
verdict on a model detection is keyed by that detection's id. So this tool
never writes `cells.json`, never deletes anything, and never touches
`verdicts/`, `detections/` or `prefill/`. It reads the manifest and fills in
the images beside it.

⚠️ **THE FRAME MUST MATCH, AND IT IS CHECKED RATHER THAN ASSUMED.** Every
saved box — a human's drawn notehead as much as a model detection — is stored
in the cell's CANONICAL frame, so an image re-cut at a different padding is
not a slightly different picture: it is the same music at a different scale,
and every box in the batch lands somewhere else on it. Nothing downstream
would report that; the boxes would simply be wrong. The two cutters in this
repo disagree here on purpose — `select_cells_orchestral` monkey-patches
`PAD_*_STAFF_LINES` to 5.0, and `benchmarks/omr-labeling-hollow2-2026-09/
cut_candidate_cells.py` deliberately leaves the pipeline's own values — and
the manifest does not record which was used. It does record
`cell_canonical_w`, `cell_canonical_h` and `staff_line_ys_canonical`, which is
enough to tell: the padding mode is DERIVED by re-cutting and keeping the mode
whose frames match what the manifest already says, and a mode that matches
nothing is refused rather than written.

    python3 -m tools.omr.annotate.recut_cells --bench-dir BATCH --dry-run
    python3 -m tools.omr.annotate.recut_cells --bench-dir BATCH

Writing is all-or-nothing per batch by default: any id the re-cut does not
reproduce, or reproduces at a different frame, aborts the whole run with a
report. `--allow-partial` writes the cells that did verify and lists the rest.
Existing PNGs are never overwritten without `--overwrite`.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from .. import measure_extractor as _me


# The two framings a batch in this repo can have been cut with. "pipeline" is
# measure_extractor's own value, which `cut_candidate_cells.py` keeps;
# "orchestral" is the 5.0 that `select_cells_orchestral` patches in. Order
# matters only as the order they are tried in.
PADDING_MODES: tuple[str, ...] = ("pipeline", "orchestral")

ORCH_PAD_STAFF_LINES = 5.0


@contextlib.contextmanager
def padding_mode(mode: str) -> Iterator[None]:
    """Run with `measure_extractor`'s pad constants set for *mode*.

    Restores them afterwards — `select_cells_orchestral._patch_padding_globals`
    mutates the module globals and never puts them back, which is harmless in
    a one-shot cutter and would not be here, since this tool may try both
    modes in one process.
    """
    if mode not in PADDING_MODES:
        raise ValueError(f"unknown padding mode {mode!r}")
    before = (_me.PAD_ABOVE_STAFF_LINES, _me.PAD_BELOW_STAFF_LINES)
    try:
        if mode == "orchestral":
            _me.PAD_ABOVE_STAFF_LINES = ORCH_PAD_STAFF_LINES
            _me.PAD_BELOW_STAFF_LINES = ORCH_PAD_STAFF_LINES
        yield
    finally:
        _me.PAD_ABOVE_STAFF_LINES, _me.PAD_BELOW_STAFF_LINES = before


def cell_key(system_index: int, staff_index: int, measure_index: int) -> tuple[int, int, int]:
    return (int(system_index), int(staff_index), int(measure_index))


def entry_key(entry: dict) -> tuple[int, int, int]:
    """The (system, staff, measure) a manifest entry names.

    This is the join to a freshly cut page, and it is the same triple the cell
    id is built from — `_cell_id` renders it as `-sysN-sM-mK`. Joining on the
    triple rather than on the id string keeps this working for a batch whose
    tag differs from its file names.
    """
    return cell_key(
        entry["system_index"], entry["staff_index"], entry["measure_index"]
    )


def index_cells(cells: Iterable[Any]) -> dict[tuple[int, int, int], Any]:
    """Index freshly cut cells by their (system, staff, measure) triple."""
    return {
        cell_key(c.system_index, c.staff_index, c.measure_index): c
        for c in cells
    }


def frame_mismatch(entry: dict, cell: Any) -> str | None:
    """Say how a re-cut cell's frame differs from the manifest's, or None.

    Compared exactly, not within a tolerance. These are integer pixel sizes
    produced by the same deterministic code path from the same page: equal is
    the only reading that means "this is the frame the boxes were drawn on".
    A near miss is a different framing, and the boxes would be off by whatever
    the near miss is.
    """
    want_w = entry.get("cell_canonical_w")
    want_h = entry.get("cell_canonical_h")
    if want_w is not None and int(want_w) != int(cell.width):
        return f"width {cell.width} != manifest {want_w}"
    if want_h is not None and int(want_h) != int(cell.height):
        return f"height {cell.height} != manifest {want_h}"
    want_ys = entry.get("staff_line_ys_canonical")
    if want_ys:
        got_ys = [int(y) for y in cell.staff_line_ys_canonical]
        if got_ys != [int(y) for y in want_ys]:
            return f"staff lines {got_ys} != manifest {list(want_ys)}"
    return None


@dataclass
class SourceAssessment:
    """What one (pdf, page) of the manifest looks like against a re-cut page."""

    matched: list[tuple[dict, Any]] = field(default_factory=list)
    missing: list[dict] = field(default_factory=list)          # id absent from the cut
    mismatched: list[tuple[dict, str]] = field(default_factory=list)  # cut, wrong frame

    @property
    def ok(self) -> bool:
        return not self.missing and not self.mismatched


def assess(entries: Sequence[dict], index: dict[tuple[int, int, int], Any]) -> SourceAssessment:
    """Sort a page's manifest entries into matched / missing / mismatched."""
    out = SourceAssessment()
    for entry in entries:
        cell = index.get(entry_key(entry))
        if cell is None:
            out.missing.append(entry)
            continue
        why = frame_mismatch(entry, cell)
        if why is not None:
            out.mismatched.append((entry, why))
            continue
        out.matched.append((entry, cell))
    return out


def resolve_pdf(raw: str, *, pdf_root: Path | None, repo_root: Path) -> Path | None:
    """Find the batch's source PDF on THIS machine.

    A manifest records the absolute path the batch was cut from — on the
    machine that cut it. That path is right there and nowhere else, so a
    checkout on another machine, or a git worktree, has to re-root it. The
    score library's layout is the thing both machines share, so the tail from
    `library/` onward is what carries across.
    """
    if not raw:
        return None
    direct = Path(raw)
    if direct.exists():
        return direct

    parts = direct.parts
    tail: Path | None = None
    if "library" in parts:
        tail = Path(*parts[parts.index("library"):])

    for base in (pdf_root, repo_root):
        if base is None:
            continue
        if tail is not None:
            candidate = base / tail
            if candidate.exists():
                return candidate
        candidate = base / direct.name
        if candidate.exists():
            return candidate
    return None


def group_sources(manifest: Sequence[dict]) -> dict[tuple[str, int], list[dict]]:
    """Group manifest entries by the (pdf, page) they came from.

    Phase 1 is the expensive part — a 600 dpi orchestral page — so it is run
    once per source page and every cell wanted from that page is taken from
    the one cut.
    """
    out: dict[tuple[str, int], list[dict]] = {}
    for entry in manifest:
        out.setdefault((entry.get("pdf", ""), int(entry.get("page", 0))), []).append(entry)
    return out


def load_manifest(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError(f"{path} is not a list of cells")
    return data


def _needs_write(png: Path, overwrite: bool) -> bool:
    return overwrite or not png.exists()


def _save(cell: Any, png: Path, *, no_staff: bool) -> bool:
    # Imported here so the module's pure helpers stay importable (and
    # testable) on a machine with no OpenCV.
    from .select_cells_orchestral import _save_cell_png

    return _save_cell_png(cell, png, no_staff=no_staff)


def cut_page(pdf: Path, page: int, *, dpi: int, mode: str) -> list[Any]:
    from .select_cells_orchestral import _run_phase1_on_page

    with padding_mode(mode):
        return _run_phase1_on_page(pdf, page, dpi=dpi)


def choose_mode_and_cut(
    pdf: Path,
    page: int,
    entries: Sequence[dict],
    *,
    dpi: int,
    modes: Sequence[str] = PADDING_MODES,
    log=print,
) -> tuple[str, SourceAssessment]:
    """Cut the page under each padding mode; keep the one the manifest agrees with.

    Returns the first mode that reproduces every wanted cell at the recorded
    frame. Where none does, returns the best attempt — most matched, fewest
    mismatched — so the report names a real discrepancy rather than the last
    mode tried.
    """
    best: tuple[str, SourceAssessment] | None = None
    for mode in modes:
        cells = cut_page(pdf, page, dpi=dpi, mode=mode)
        found = assess(entries, index_cells(cells))
        log(
            f"    padding={mode}: {len(found.matched)} matched, "
            f"{len(found.missing)} missing, {len(found.mismatched)} wrong frame"
        )
        if found.ok:
            return mode, found
        if best is None or (
            len(found.matched), -len(found.mismatched)
        ) > (len(best[1].matched), -len(best[1].mismatched)):
            best = (mode, found)
    assert best is not None
    return best


@dataclass
class Report:
    written: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    mismatched: list[tuple[str, str]] = field(default_factory=list)
    unresolved_pdfs: list[str] = field(default_factory=list)
    unreachable: int = 0          # cells whose source PDF was never found
    modes: dict[str, str] = field(default_factory=dict)

    @property
    def clean(self) -> bool:
        return not (self.missing or self.mismatched or self.unresolved_pdfs)


def recut(
    bench_dir: Path,
    *,
    repo_root: Path,
    pdf_root: Path | None = None,
    dpi: int = 600,
    dry_run: bool = False,
    overwrite: bool = False,
    allow_partial: bool = False,
    log=print,
) -> Report:
    manifest = load_manifest(bench_dir / "cells.json")
    cells_dir = bench_dir / "cells"
    report = Report()

    sources = group_sources(manifest)
    log(f"{len(manifest)} cells from {len(sources)} source page(s)")

    verified: list[tuple[dict, Any]] = []
    for (raw_pdf, page), entries in sorted(sources.items(), key=lambda kv: kv[0]):
        pdf = resolve_pdf(raw_pdf, pdf_root=pdf_root, repo_root=repo_root)
        if pdf is None:
            log(f"  page {page}: PDF NOT FOUND — {raw_pdf}")
            # Recorded once per file, not once per page: one missing PDF is
            # one problem however many of the batch's pages came from it. Its
            # cells are NOT also listed as "the cut did not produce", which
            # would report a single unfound file as 56 separate failures and
            # bury the one line that says what to do about it.
            if raw_pdf not in report.unresolved_pdfs:
                report.unresolved_pdfs.append(raw_pdf)
            report.unreachable += len(entries)
            continue
        log(f"  page {page}: {len(entries)} cells from {pdf}")
        mode, found = choose_mode_and_cut(pdf, page, entries, dpi=dpi, log=log)
        report.modes[f"{pdf.name}:p{page}"] = mode
        report.missing.extend(e["cell_id"] for e in found.missing)
        report.mismatched.extend((e["cell_id"], why) for e, why in found.mismatched)
        verified.extend(found.matched)

    if not report.clean and not allow_partial:
        log("")
        log("REFUSING TO WRITE — the re-cut does not reproduce this batch.")
        _log_problems(report, log)
        log("")
        log("Nothing was written. cells.json, verdicts/ and detections/ are untouched.")
        log("Re-run with --allow-partial to write only the cells that did verify.")
        return report

    for entry, cell in verified:
        cid = entry["cell_id"]
        png = cells_dir / f"{cid}.png"
        if not _needs_write(png, overwrite):
            report.skipped_existing.append(cid)
            continue
        if dry_run:
            report.written.append(cid)
            continue
        if _save(cell, png, no_staff=False):
            report.written.append(cid)
            if getattr(cell, "image_no_staff", None) is not None:
                _save(cell, cells_dir / f"{cid}_nostaff.png", no_staff=True)
        else:
            report.missing.append(cid)

    verb = "would write" if dry_run else "wrote"
    log("")
    log(
        f"{verb} {len(report.written)} PNG(s); "
        f"{len(report.skipped_existing)} already present"
    )
    if not report.clean:
        _log_problems(report, log)
    return report


def _log_problems(report: Report, log) -> None:
    if report.unresolved_pdfs:
        log(
            f"  {len(report.unresolved_pdfs)} source PDF(s) not found on this "
            f"machine, accounting for {report.unreachable} cell(s):"
        )
        for raw in report.unresolved_pdfs:
            log(f"    {raw}")
        log("    The manifest records the path of the machine that CUT the batch.")
        log("    Pass --pdf-root DIR pointing at the checkout that holds library/.")
    if report.missing:
        log(f"  {len(report.missing)} cell id(s) the re-cut did not produce:")
        for cid in report.missing[:10]:
            log(f"    {cid}")
        if len(report.missing) > 10:
            log(f"    … and {len(report.missing) - 10} more")
    if report.mismatched:
        log(f"  {len(report.mismatched)} cell(s) cut at a DIFFERENT FRAME:")
        for cid, why in report.mismatched[:10]:
            log(f"    {cid}: {why}")
        if len(report.mismatched) > 10:
            log(f"    … and {len(report.mismatched) - 10} more")
        log("    Every saved box is in the canonical frame, so writing these")
        log("    would put the batch's existing boxes in the wrong places.")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Re-cut a labeling batch's cell PNGs from the source PDF."
    )
    ap.add_argument("--bench-dir", required=True, help="Batch directory holding cells.json.")
    ap.add_argument("--pdf-root", default=None,
                    help="Checkout holding library/, when the manifest's absolute "
                         "PDF path is from another machine.")
    ap.add_argument("--dpi", type=int, default=600,
                    help="Rasterization DPI (default 600, what the cutters use).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Verify and report; write nothing.")
    ap.add_argument("--overwrite", action="store_true",
                    help="Re-render PNGs that already exist (default: leave them).")
    ap.add_argument("--allow-partial", action="store_true",
                    help="Write the cells that verified even if others did not.")
    args = ap.parse_args(argv)

    bench_dir = Path(args.bench_dir).resolve()
    if not (bench_dir / "cells.json").exists():
        print(f"no cells.json in {bench_dir}", file=sys.stderr)
        return 2

    report = recut(
        bench_dir,
        repo_root=Path(__file__).resolve().parents[3],
        pdf_root=Path(args.pdf_root).resolve() if args.pdf_root else None,
        dpi=args.dpi,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        allow_partial=args.allow_partial,
    )
    return 0 if report.clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
