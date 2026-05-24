#!/usr/bin/env python3
"""Phase H — render the 523 catalog PDF pages to PNG, aligned with the
Phase G YOLO labels.

For every {key}/labels/p{NNN}.txt in phase-e-labels/, render the matching
PDF page using the same pipeline (render_page + binarize + deskew at 300
DPI) used during label generation, then save as PNG. Optionally downscale
to a target max dimension (1280 by default) to save upload bandwidth and
training I/O — labels are normalized so this is safe.

The output layout is YOLO-friendly: paths contain `/images/` so the
ultralytics loader can find labels by string-swap. Label files are
hard-copied so the produced directory tree is self-contained and ready
for tar+ship to a remote GPU box.

  {OUT_ROOT}/images/{key}/p{NNN}.png
  {OUT_ROOT}/labels/{key}/p{NNN}.txt

CLI:
  python3 -m benchmarks.omr-imslp-pipeline.phase_h_render_pages \
      --max-dim 1280  --workers 6  --out phase-h-data
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr.preprocessing import render_page  # noqa: E402


# Match the constants used by phase_e_emit_labels.py so deskew + dims
# stay consistent.
PDF_DPI = 300

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "tools/omr/training/data/imslp"
LABELS_ROOT = REPO_ROOT / "benchmarks/omr-imslp-pipeline/phase-e-labels"
DEFAULT_OUT = REPO_ROOT / "benchmarks/omr-imslp-pipeline/phase-h-data"


# ─────────────────────────────────────────────────────────────────────────────
# Job description
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RenderJob:
    key: str               # e.g. "beethoven-symphony-1-imslp-52848-mvt1"
    work: str              # "beethoven-symphony-1"
    edition: str           # "imslp-52848"
    mvt: int
    pdf_path: Path
    page_1indexed: int     # 1-based PDF page (matches the p###.txt filename)
    image_out: Path
    label_src: Path
    label_dst: Path
    max_dim: int           # 0 = native size; otherwise longest side


def _parse_key(key: str) -> tuple[str, str, int]:
    """'beethoven-symphony-1-imslp-52848-mvt1' →
        ('beethoven-symphony-1', 'imslp-52848', 1)"""
    parts = key.rsplit("-mvt", 1)
    if len(parts) != 2:
        raise ValueError(f"unrecognized key format: {key!r}")
    head, mvt = parts
    # head = '{work}-imslp-{stem}'; split at "-imslp-"
    if "-imslp-" not in head:
        raise ValueError(f"unrecognized key format (no -imslp- in head): {key!r}")
    work, ed_stem = head.rsplit("-imslp-", 1)
    return work, f"imslp-{ed_stem}", int(mvt)


def discover_jobs(labels_root: Path, out_root: Path, *, max_dim: int) -> list[RenderJob]:
    """Walk phase-e-labels/{key}/labels/*.txt and build a render job per page."""
    jobs: list[RenderJob] = []
    if not labels_root.exists():
        raise FileNotFoundError(f"labels root not found: {labels_root}")
    for key_dir in sorted(labels_root.iterdir()):
        if not key_dir.is_dir():
            continue
        labels_dir = key_dir / "labels"
        if not labels_dir.exists():
            continue
        try:
            work, edition, mvt = _parse_key(key_dir.name)
        except ValueError:
            continue
        pdf_path = DATA_ROOT / work / "pdfs" / edition / "score.pdf"
        if not pdf_path.exists():
            print(f"  skip {key_dir.name}: PDF missing at {pdf_path}", file=sys.stderr)
            continue
        for label_file in sorted(labels_dir.glob("p*.txt")):
            try:
                page_1idx = int(label_file.stem.lstrip("p"))
            except ValueError:
                continue
            image_out = out_root / "images" / key_dir.name / f"p{page_1idx:03d}.png"
            label_dst = out_root / "labels" / key_dir.name / f"p{page_1idx:03d}.txt"
            jobs.append(RenderJob(
                key=key_dir.name,
                work=work,
                edition=edition,
                mvt=mvt,
                pdf_path=pdf_path,
                page_1indexed=page_1idx,
                image_out=image_out,
                label_src=label_file,
                label_dst=label_dst,
                max_dim=max_dim,
            ))
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Worker
# ─────────────────────────────────────────────────────────────────────────────


def _render_one(job: RenderJob) -> tuple[str, int, str]:
    """Render one page; copy its label. Returns (key, page, status)."""
    try:
        if job.image_out.exists() and job.label_dst.exists():
            return (job.key, job.page_1indexed, "skip-cached")
        job.image_out.parent.mkdir(parents=True, exist_ok=True)
        job.label_dst.parent.mkdir(parents=True, exist_ok=True)
        # The phase_e_emit_labels.py pipeline uses 0-based page_index.
        pi = render_page(job.pdf_path, job.page_1indexed - 1, dpi=PDF_DPI)
        rgb = pi.rgb  # H×W×3, uint8, deskewed
        h, w = rgb.shape[:2]
        if job.max_dim and max(w, h) > job.max_dim:
            scale = job.max_dim / max(w, h)
            new_w = int(round(w * scale))
            new_h = int(round(h * scale))
            rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        # cv2 expects BGR
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        ok = cv2.imwrite(str(job.image_out), bgr,
                         [cv2.IMWRITE_PNG_COMPRESSION, 6])
        if not ok:
            return (job.key, job.page_1indexed, "fail-imwrite")
        # Copy label (always — keeps the tree self-contained)
        shutil.copyfile(job.label_src, job.label_dst)
        return (job.key, job.page_1indexed, "ok")
    except Exception as exc:  # noqa: BLE001
        return (job.key, job.page_1indexed, f"error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels-root", default=str(LABELS_ROOT),
                    help="Where the phase-e-labels/ dir lives")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="Output root (will contain images/ and labels/)")
    ap.add_argument("--max-dim", type=int, default=1280,
                    help="Downscale rendered image so the longest dimension "
                         "equals this. 0 = native 300-DPI size.")
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 1))
    ap.add_argument("--limit", type=int, default=0,
                    help="Process only this many jobs (smoke test)")
    args = ap.parse_args(argv)

    labels_root = Path(args.labels_root).resolve()
    out_root = Path(args.out).resolve()
    jobs = discover_jobs(labels_root, out_root, max_dim=args.max_dim)
    if args.limit:
        jobs = jobs[:args.limit]
    print(f"Discovered {len(jobs)} render jobs across "
          f"{len({j.key for j in jobs})} (work, edition, mvt) tuples")
    print(f"Out: {out_root}")
    print(f"Max dim: {args.max_dim} px  Workers: {args.workers}")

    if not jobs:
        return 0

    t0 = time.time()
    if args.workers <= 1:
        results = [_render_one(j) for j in jobs]
    else:
        with mp.Pool(processes=args.workers) as pool:
            results = pool.map(_render_one, jobs, chunksize=4)
    dt = time.time() - t0

    ok_count = sum(1 for r in results if r[2] == "ok")
    skip_count = sum(1 for r in results if r[2] == "skip-cached")
    fail = [r for r in results if r[2] not in ("ok", "skip-cached")]
    print(f"\nrendered: {ok_count} ok, {skip_count} cached, {len(fail)} failed "
          f"in {dt:.1f} s")
    if fail:
        print("First 5 failures:")
        for r in fail[:5]:
            print(f"  {r[0]} p{r[1]:03d}: {r[2]}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
