"""Open a printed page for whole-ink labeling (ROADMAP 1.7, plan C1–C2). Runs where the PDFs are.

    python3 -m tools.omr.hand_truth.session new --pdf <score> --page 0 [--dpi 600]
        [--weights omr-weights/<production>.pt] [--no-old-labels]
    python3 -m tools.omr.annotate.server --bench-dir <bench> --page-store <page.json>
    python3 -m tools.omr.hand_truth.session status <page.json> --pdf <score>
    python3 -m tools.omr.hand_truth.session raise <page.json> --cell <id> --kind missed_symbol --message "..."
    python3 -m tools.omr.hand_truth.session flag <page.json> f3 accepted|rejected
    python3 -m tools.omr.hand_truth.session resync <page.json> --bench <bench>
    python3 -m tools.omr.hand_truth.session advance <page.json> --to checked --pdf <score>

THE CELLS are the pipeline's own: ``detect_staves`` -> ``detect_barlines`` ->
``extract_measures`` at the product pads (no monkey-patch), each cell's page
rectangle taken from its own ``bbox_page_px``. Measure cells never reach the
margins, the title, the page number or a one-line percussion staff, so every
bit of ink OUTSIDE them becomes a REGION cell (``margin`` / ``top`` /
``bottom``) at the measure cells' scale — the instrument names, braces and
first-page headings Sean asked to capture live there.

THE PRE-FILLS (Sean 2026-10-08: "I am ok with prefills. The work we have done
so far could really speed up the process"), in order of trust, all into the
queue and never truth:

1. Sean's OLD labels on this page (``data/user-labeled/v*``), re-projected
   into page pixels through ``recut_cells``' exact frame check — a cell whose
   frame does not reproduce is refused, never approximated;
2. the detector, per cell, where a ``--weights`` file is given.

A detector box on the same mark as an old human box (same family, IoU >= 0.5)
is dropped; so is the second of two detector boxes on one mark seen from two
overlapping cells.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from tools.omr.hand_truth import bench as bench_mod
from tools.omr.hand_truth import checks, completeness, store
from tools.omr.hand_truth.store import REPO, Cell, PageTruth, Rect, StaffCheck, StoreError, edition_key

SESSIONS_DIR = REPO / "benchmarks" / "hand-truth-sessions"


def _commit() -> Dict:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=REPO,
                                    capture_output=True, text=True, check=True).stdout.strip())
        return {"commit": sha, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def _rgb_to_bgr(img: np.ndarray) -> np.ndarray:
    return img[..., ::-1].copy() if img.ndim == 3 else img


# ------------------------------------------------------------------ cutting
def measure_cells(page_img) -> Tuple[object, list]:
    """The product path's own cells for one rendered page."""
    from tools.omr import measure_extractor as me
    from tools.omr.staff_detector import detect_staves

    pws = detect_staves(page_img)
    pws = me.detect_barlines(pws)
    return pws, me.extract_measures(pws)


def region_rects(ink: np.ndarray, covered: Sequence[Rect], spacing: float,
                 page_w: int, page_h: int) -> List[Rect]:
    """Rectangles around every ink component that no measure cell contains.

    Ink outside the covered rectangles is grown by one staff space so the
    letters of one word, or a brace and its hooks, become one region; each
    region is padded by half a space and clipped to the page.
    """
    import cv2

    outside = ink.astype(bool).copy()
    for x0, y0, x1, y1 in covered:
        outside[int(y0):int(np.ceil(y1)), int(x0):int(np.ceil(x1))] = False
    if not outside.any():
        return []
    k = max(3, int(round(spacing)) | 1)
    grown = cv2.dilate(outside.astype(np.uint8), np.ones((k, k), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(grown, connectivity=8)
    pad = spacing / 2.0
    out = []
    for i in range(1, n):
        x, y, w, h, _ = (int(v) for v in stats[i])
        mask = (labels[y:y + h, x:x + w] == i) & outside[y:y + h, x:x + w]
        ys, xs = np.nonzero(mask)
        if not len(xs):
            continue
        out.append((max(0.0, x + xs.min() - pad), max(0.0, y + ys.min() - pad),
                    min(float(page_w), x + xs.max() + 1 + pad), min(float(page_h), y + ys.max() + 1 + pad)))
    return sorted(out, key=lambda r: (r[1], r[0]))


def _region_kind(r: Rect, staff_tops: List[float], staff_bottoms: List[float]) -> str:
    if staff_tops and r[3] <= min(staff_tops):
        return "top"
    if staff_bottoms and r[1] >= max(staff_bottoms):
        return "bottom"
    return "margin"


def build_page(page_img, *, edition: str, pdf: str = "", max_cell_width: Optional[int] = None
               ) -> Tuple[PageTruth, Dict[str, np.ndarray], list]:
    """Cut one rendered page (a ``PageImage``) into measure + region cells.

    Returns the empty page truth, every cell's canonical image (BGR, as the
    bench stores it) and the product path's ``MeasureCell`` list.
    """
    import cv2

    from tools.omr import measure_extractor as me

    pws, cells = measure_cells(page_img)
    h, w = page_img.binary.shape[:2]
    page = PageTruth(edition=edition, pdf_page_index=int(page_img.page_index), dpi=int(page_img.dpi),
                     width=int(w), height=int(h),
                     provenance={"cutter": "measure_extractor.extract_measures at the product pads",
                                 "pdf": pdf, **_commit()})
    images: Dict[str, np.ndarray] = {}
    scales = []
    for mc in sorted(cells, key=lambda c: (c.system_index, c.staff_index, c.measure_index)):
        cid = f"s{mc.system_index}-st{mc.staff_index}-m{mc.measure_index}"
        ch, cw = mc.image.shape[:2]
        page.add_cell(Cell(id=cid, kind="measure", rect=tuple(float(v) for v in mc.bbox_page_px),
                           canonical_w=int(cw), canonical_h=int(ch), system=int(mc.system_index),
                           staff=int(mc.staff_index), measure=int(mc.measure_index),
                           staff_line_ys=[float(y) for y in mc.staff_line_ys_canonical]))
        images[cid] = _rgb_to_bgr(mc.image)
        x0, _, x1, _ = mc.bbox_page_px
        scales.append(cw / max(1, x1 - x0))
    staves5 = [s for s in pws.staves if len(s.line_ys) >= 5]
    for s in staves5:
        page.staves.append(StaffCheck(system=int(s.system_index), staff=int(s.staff_index)))
    scale = float(np.median(scales)) if scales else 1.0
    spacing = float(np.median([s.line_spacing_px for s in staves5])) if staves5 else 20.0
    max_w = int(max_cell_width or me.MAX_CELL_WIDTH_PX)
    ink = page_img.binary < 128
    rects = region_rects(ink, [c.rect for c in page.cells], spacing, w, h)
    tops = [min(s.line_ys) for s in staves5]
    bottoms = [max(s.line_ys) for s in staves5]
    counter: Dict[str, int] = {}
    for r in rects:
        kind = _region_kind(r, tops, bottoms)
        # Split a region wider than the cell budget into overlapping chunks.
        span = max_w / scale
        x = r[0]
        while x < r[2]:
            x1 = min(r[2], x + span)
            chunk = (x, r[1], x1, r[3])
            n = counter.get(kind, 0)
            counter[kind] = n + 1
            cid = f"{kind}-{n}"
            cw = max(1, int(round((x1 - x) * scale)))
            chh = max(1, int(round((r[3] - r[1]) * scale)))
            crop = page_img.rgb[int(chunk[1]):int(np.ceil(chunk[3])), int(chunk[0]):int(np.ceil(chunk[2]))]
            img = cv2.resize(crop, (cw, chh), interpolation=cv2.INTER_CUBIC if scale >= 1 else cv2.INTER_AREA)
            page.add_cell(Cell(id=cid, kind=kind, rect=chunk, canonical_w=cw, canonical_h=chh))
            images[cid] = _rgb_to_bgr(img)
            if x1 >= r[2]:
                break
            x = x1 - spacing  # one space of overlap: a mark on the cut is whole in one chunk
    return page, images, cells


# ------------------------------------------------------------------ pre-fills
def _iou(a: Rect, b: Rect) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


# Classes never queued: a staff line is confirmed per staff on the bench's L*
# boxes (bench.STAFF_LINE_CLASS), never boxed (Sean, 2026-10-08).
NOT_PROPOSED = frozenset({bench_mod.STAFF_LINE_CLASS})


def _skip(report: Dict, cls: str) -> bool:
    if cls not in NOT_PROPOSED:
        return False
    skipped = report.setdefault("boxes_not_proposed", {})
    skipped[cls] = skipped.get(cls, 0) + 1
    return True


def propose_deduped(page: PageTruth, cls: str, rect: Rect, source: str,
                    score: Optional[float] = None, iou: float = 0.5) -> bool:
    """Queue a proposal unless the same mark (same family, IoU >= ``iou``) is
    already queued or already truth. A queued OLD-LABEL proposal always wins."""
    fam = completeness.family_of(cls)
    for b in page.boxes:
        if completeness.family_of(b.cls) == fam and _iou(b.rect, rect) >= iou:
            return False
    for q in page.queue:
        if completeness.family_of(q.cls) == fam and _iou(q.rect, rect) >= iou:
            if q.source.startswith("sean-") or (q.score or 0) >= (score or 0):
                return False
            page.queue.remove(q)
            break
    page.propose(cls, rect, source=source, score=score)
    return True


def old_label_entries(edition: str, pdf_page_index: int) -> List[Tuple[str, dict, Path]]:
    """(version, manifest entry, label file) for every old labeled cell on the page."""
    from tools.omr.hand_truth import inventory

    entries: Dict[str, dict] = {}
    for f in sorted((REPO / "benchmarks").glob("**/*cells*.json")):
        for r in inventory._manifest_rows(inventory._json(f)):
            if r.get("pdf") and r.get("page") is not None and r["cell_id"] not in entries:
                entries[r["cell_id"]] = r
    from tools.omr.hand_truth.inventory import _vkey

    out = []
    # NEWEST version first: v13-v21 complete the same cells v7-v12 started, so
    # the more complete labeling must be the one the dedupe keeps.
    for vdir in sorted((REPO / "data" / "user-labeled").glob("v*-*"), key=lambda d: -_vkey(d.name)):
        for lab in sorted((vdir / "labels").glob("*.txt")):
            e = entries.get(lab.stem)
            if e and edition_key(e["pdf"]) == edition and int(e["page"]) == pdf_page_index:
                out.append((vdir.name, e, lab))
    return out


def prefill_old_labels(page: PageTruth, pdf: Path, *, dpi: Optional[int] = None, log=print) -> Dict:
    """Sean's earlier boxes on this page, re-projected through the EXACT frame check."""
    from tools.omr.annotate.recut_cells import choose_mode_and_cut, entry_key
    from tools.omr.training.verdicts_to_yolo_labels import DEEPSCORES_208_JSON, load_class_names

    names = load_class_names(None, DEEPSCORES_208_JSON)
    found = old_label_entries(page.edition, page.pdf_page_index)
    report = {"cells_found": len(found), "cells_projected": 0, "cells_refused": [], "boxes_queued": 0,
              "boxes_dropped_as_duplicates": 0}
    if not found:
        return report
    _, assessed = choose_mode_and_cut(pdf, page.pdf_page_index, [e for _, e, _ in found],
                                      dpi=dpi or page.dpi, log=log)
    cut = {entry_key(e): c for e, c in assessed.matched}
    for e, why in assessed.mismatched:
        report["cells_refused"].append({"cell_id": e["cell_id"], "why": why})
    for e in assessed.missing:
        report["cells_refused"].append({"cell_id": e["cell_id"], "why": "not in the re-cut"})
    for version, e, lab in found:
        mc = cut.get(entry_key(e))
        if mc is None:
            continue
        x0, y0, x1, y1 = mc.bbox_page_px
        cw, ch = int(mc.width), int(mc.height)
        sx, sy = (x1 - x0) / cw, (y1 - y0) / ch
        report["cells_projected"] += 1
        for line in lab.read_text().splitlines():
            p = line.split()
            if len(p) != 5:
                continue
            k, cx, cy, bw, bh = int(p[0]), *(float(v) for v in p[1:])
            if k >= len(names):
                continue
            r = (x0 + (cx - bw / 2) * cw * sx, y0 + (cy - bh / 2) * ch * sy,
                 x0 + (cx + bw / 2) * cw * sx, y0 + (cy + bh / 2) * ch * sy)
            if _skip(report, names[k]):
                continue
            if propose_deduped(page, names[k], r, source=f"sean-{version.split('-')[0]}"):
                report["boxes_queued"] += 1
            else:
                report["boxes_dropped_as_duplicates"] += 1
    return report


def prefill_detector(page: PageTruth, measure_cells_list: list, region_images: Dict[str, np.ndarray],
                     weights: Path, *, conf: float = 0.25) -> Dict:
    """The detector's boxes per cell, into the queue in page pixels."""
    from tools.omr.types import MeasureCell
    from tools.omr.yolo_detector import YoloDetector

    det = YoloDetector(weights)
    report = {"boxes_queued": 0, "boxes_dropped_as_duplicates": 0}
    by_id = {f"s{m.system_index}-st{m.staff_index}-m{m.measure_index}": m for m in measure_cells_list}
    for c in page.cells:
        mc = by_id.get(c.id)
        if mc is None:
            img = region_images[c.id][..., ::-1]  # back to RGB, as the detector reads cells
            x0, y0, x1, y1 = (int(v) for v in c.rect)
            mc = MeasureCell(page_index=page.pdf_page_index, system_index=-1, staff_index=-1,
                             measure_index=-1, image=img, image_no_staff=None,
                             bbox_page_px=(x0, y0, x1, y1), staff_line_ys_canonical=[],
                             upscale_factor=c.canonical_h / max(1, y1 - y0))
        for d in det.detect(mc, conf_threshold=conf):
            if _skip(report, d.smufl_name):
                continue
            r = c.to_page((d.x_canonical, d.y_canonical, d.x_canonical + d.width_canonical,
                           d.y_canonical + d.height_canonical))
            if propose_deduped(page, d.smufl_name, r, source=f"detector:{Path(weights).name}",
                               score=float(d.confidence)):
                report["boxes_queued"] += 1
            else:
                report["boxes_dropped_as_duplicates"] += 1
    return report


# ------------------------------------------------------------------ CLI
def _render(pdf: Path, page: int, dpi: int):
    from tools.omr.preprocessing import render_page

    return render_page(pdf, page, dpi=dpi)


def cmd_new(a) -> int:
    pdf = Path(a.pdf)
    img = _render(pdf, a.page, a.dpi)
    edition = a.edition or edition_key(pdf.name)
    page, images, mcells = build_page(img, edition=edition, pdf=pdf.name)
    target = page.path()
    if target.exists() and not a.force:
        raise SystemExit(f"{target} exists — a page store is never overwritten (pass --force to start over)")
    region_images = {c.id: images[c.id] for c in page.cells if c.kind != "measure"}
    reports = {}
    if not a.no_old_labels:
        reports["old_labels"] = prefill_old_labels(page, pdf, dpi=a.dpi)
    if a.weights:
        reports["detector"] = prefill_detector(page, mcells, region_images, Path(a.weights))
    page.provenance["prefill"] = reports
    page.save()
    bench = Path(a.bench or (SESSIONS_DIR / f"{edition}-p{page.pdf_page_index}"))
    bench_mod.write_bench(page, images, bench, pdf=str(pdf))
    print(json.dumps({"page_store": str(target), "bench": str(bench),
                      "cells": {k: sum(1 for c in page.cells if c.kind == k) for k in store.CELL_KINDS},
                      "staves": len(page.staves), "queue": len(page.queue), "prefill": reports}, indent=1))
    print(f"\nlabel it:\n  python3 -m tools.omr.annotate.server --bench-dir {bench} --page-store {target}")
    return 0


def _ink_report(page: PageTruth, pdf: Optional[str]):
    if not pdf:
        return None
    img = _render(Path(pdf), page.pdf_page_index, page.dpi)
    staff_mask = np.zeros((page.height, page.width), bool)
    # Staff lines are confirmed per staff, not boxed: remove them before
    # counting components, at the staves' own rows.
    from tools.omr.staff_detector import detect_staves

    for s in detect_staves(img).staves:
        t = max(1, int(round(getattr(s, "median_line_thickness_px", None) or 2)))
        for y in s.line_ys:
            staff_mask[max(0, int(y) - t):int(y) + t + 1, max(0, int(s.x_start)):int(s.x_end) + 1] = True
    return completeness.ink_coverage(page, img.binary < 128, staff_mask)


def _write(page: PageTruth, path: Path) -> None:
    path.write_text(json.dumps(page.to_json(), indent=1, sort_keys=True) + "\n")


def cmd_status(a) -> int:
    page = store.load(Path(a.page))
    ink = _ink_report(page, a.pdf)
    flags = checks.run_all(page, ink)
    _write(page, Path(a.page))
    done = completeness.page_complete(page, ink)
    print(json.dumps({
        "page": f"{page.edition}:{page.pdf_page_index}", "state": page.state,
        "cells": len(page.cells), "boxes": len(page.boxes), "queue_left": len(page.queue),
        "cells_not_swept_for_all_ink": [c.id for c in page.cells
                                        if completeness.families_covered(c.inspected) is not None],
        "staves_unconfirmed": [f"{s.system}.{s.staff}" for s in page.staves if s.lines_right is not True],
        "ink": None if ink is None else {"components": ink.components, "uncovered": len(ink.uncovered),
                                          "specks": ink.specks_below_min_area},
        "new_flags": len(flags), "open_flags": [f"{f.id} {f.kind}: {f.message}" for f in page.open_flags()],
        "whole_ink": done,
    }, indent=1))
    return 0


def cmd_resync(a) -> int:
    """Fold EVERY saved cell verdict of a bench into the page store again — the
    recovery for a save whose sync failed (the server reported it, loudly)."""
    path = Path(a.page)
    page = store.load(path)
    touched = set()
    for c in page.cells:
        touched |= bench_mod.sync_cell(page, Path(a.bench), c.id)
    bench_mod.refresh_cells(page, Path(a.bench), touched)
    _write(page, path)
    print(f"resynced {len(page.cells)} cells; {len(page.boxes)} boxes, {len(page.queue)} pre-fills left")
    return 0


def cmd_raise(a) -> int:
    """File a flag by hand — how Claude's VISUAL pass (plan C5 step 2) reports what it
    sees in a cell. A flag is never an edit; Sean accepts or rejects it."""
    path = Path(a.page)
    page = store.load(path)
    page.cell(a.cell)
    rect = tuple(float(v) for v in a.rect.split(",")) if a.rect else None
    f = page.raise_flag(a.kind, a.message, by=a.by, cell_id=a.cell, rect=rect,
                        box_ids=[x for x in (a.boxes or "").split(",") if x])
    _write(page, path)
    print(f.id)
    return 0


def cmd_flag(a) -> int:
    path = Path(a.page)
    page = store.load(path)
    page.resolve_flag(a.flag_id, a.status)
    _write(page, path)
    return 0


def cmd_advance(a) -> int:
    path = Path(a.page)
    page = store.load(path)
    if a.to == "checked":
        ink = _ink_report(page, a.pdf)
        checks.run_all(page, ink)
        done = completeness.page_complete(page, ink)
        if not done["complete"] or page.open_flags() or page.queue:
            _write(page, path)
            raise SystemExit(f"not checked: whole-ink {done}, open flags {len(page.open_flags())}, "
                             f"pre-fills left {len(page.queue)}")
    if a.to == "verified":
        # `verified` means every printed bar was marked ok on the LilyPond side
        # by side (plan C6), on the labels as they are NOW.
        from tools.omr.hand_truth import review

        v = review.verdict(path, page)
        if not v["verified"]:
            raise SystemExit(f"not verified: {v}")
    page.advance(a.to)
    _write(page, path)
    print(f"{page.edition}:{page.pdf_page_index} -> {page.state}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("--pdf", required=True)
    n.add_argument("--page", type=int, required=True, help="0-based PDF page index")
    n.add_argument("--dpi", type=int, default=600)
    n.add_argument("--edition")
    n.add_argument("--weights")
    n.add_argument("--bench")
    n.add_argument("--no-old-labels", action="store_true")
    n.add_argument("--force", action="store_true")
    s = sub.add_parser("status")
    s.add_argument("page")
    s.add_argument("--pdf", help="re-render to run the ink-coverage control")
    r = sub.add_parser("resync")
    r.add_argument("page")
    r.add_argument("--bench", required=True)
    rz = sub.add_parser("raise")
    rz.add_argument("page")
    rz.add_argument("--cell", required=True)
    rz.add_argument("--kind", required=True, help="e.g. missed_symbol, wrong_class")
    rz.add_argument("--message", required=True)
    rz.add_argument("--rect", help="x0,y0,x1,y1 in PAGE pixels")
    rz.add_argument("--boxes", help="comma-separated box ids")
    rz.add_argument("--by", default="claude:visual")
    f = sub.add_parser("flag")
    f.add_argument("page")
    f.add_argument("flag_id")
    f.add_argument("status", choices=("accepted", "rejected"))
    v = sub.add_parser("advance")
    v.add_argument("page")
    v.add_argument("--to", required=True, choices=store.STATES[1:])
    v.add_argument("--pdf")
    a = ap.parse_args(list(argv) if argv is not None else None)
    return {"new": cmd_new, "status": cmd_status, "resync": cmd_resync, "raise": cmd_raise, "flag": cmd_flag,
            "advance": cmd_advance}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
