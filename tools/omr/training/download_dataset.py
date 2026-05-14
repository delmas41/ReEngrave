"""Download DeepScoresV2 to disk.

The DeepScoresV2 dataset is the canonical training set for music-symbol
detectors. It contains ~300k synthetically-rendered music score pages
with oriented-bounding-box annotations for ~135 SMuFL symbol classes.

Canonical sources (search "DeepScoresV2 dataset" + "Tuggener"):

    - Zenodo release (data archive, ~80 GB compressed for the full set;
      a "dense" subset is ~5-7 GB):
        https://zenodo.org/records/4012193
      (the record ID may bump as the authors publish revisions; see
      https://zenodo.org/search?q=DeepScoresV2 to find the latest)

    - GitHub annotation toolkit (parses the OBB JSON):
        https://github.com/yvan674/obb_anns

    - Project landing page (paper, examples, license):
        https://tuggeluk.github.io/

We download the "dense" subset by default — it's smaller (~5-7 GB) and
plenty for an initial fine-tune. The full set is available via --full but
is overkill for a first pass and takes far longer to download.

License: DeepScoresV2 is published under CC BY-SA 4.0 (with the caveat
that the underlying engravings are derived from public-domain or
permissively-licensed scores). Cite Tuggener et al. 2020 in any derived
work.

DO NOT run this script casually — it pulls multiple GB. Use --dry-run
during development to verify URLs and target paths without actually
fetching anything.

CLI:
    python3 -m tools.omr.training.download_dataset --out data/deepscoresv2/
    python3 -m tools.omr.training.download_dataset --dry-run
    python3 -m tools.omr.training.download_dataset --full --out data/deepscoresv2/
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Download manifest
# ---------------------------------------------------------------------------
#
# These URLs point at the Zenodo record's file endpoints. Zenodo URLs are
# stable across record-version bumps as long as the record DOI stays the
# same, but the filenames inside the record may change over time. If a URL
# 404s, visit the Zenodo record page and update the manifest by hand.
#
# expected_size_bytes is approximate; the script tolerates +/- 5%.


@dataclass(frozen=True)
class DatasetFile:
    name: str
    url: str
    expected_size_bytes: int
    sha256: str | None = None  # set to None when unknown; size check still runs


# Canonical DeepScoresV2 archive (dense subset). The dataset publishes
# multiple tarballs; the "dense" variant is the one most papers fine-tune
# on. The full set ("complete") is the union of dense + a much larger
# synthetic spread.
DENSE_FILES: list[DatasetFile] = [
    DatasetFile(
        name="ds2_dense.tar.gz",
        url="https://zenodo.org/records/4012193/files/ds2_dense.tar.gz",
        expected_size_bytes=6_500_000_000,  # ~6.5 GB compressed
        sha256=None,  # known-unknown; populate after first successful download
    ),
]

FULL_FILES: list[DatasetFile] = [
    DatasetFile(
        name="ds2_complete.tar.gz",
        url="https://zenodo.org/records/4012193/files/ds2_complete.tar.gz",
        expected_size_bytes=80_000_000_000,  # ~80 GB compressed
        sha256=None,
    ),
]


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def _human(n: int | float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if abs(f) < 1024.0:
            return f"{f:.1f} {u}"
        f /= 1024.0
    return f"{f:.1f} PB"


def _verify_size(path: Path, expected: int, tolerance: float = 0.05) -> bool:
    if not path.exists():
        return False
    actual = path.stat().st_size
    lo = int(expected * (1 - tolerance))
    hi = int(expected * (1 + tolerance))
    return lo <= actual <= hi


def _verify_sha256(path: Path, expected: str) -> bool:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == expected


def _download(url: str, dst: Path, *, chunk: int = 1 << 20) -> None:
    """Stream-download `url` to `dst`. Progress to stderr."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    with urllib.request.urlopen(url) as resp:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        downloaded = 0
        with tmp.open("wb") as out:
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                out.write(buf)
                downloaded += len(buf)
                if total:
                    pct = 100.0 * downloaded / total
                    print(
                        f"\r  {_human(downloaded)}/{_human(total)} ({pct:5.1f}%)",
                        end="",
                        file=sys.stderr,
                    )
        print(file=sys.stderr)
    tmp.replace(dst)


def download_dataset(
    out_dir: Path,
    *,
    files: list[DatasetFile],
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    """Download all files in the manifest into `out_dir`.

    Idempotent: skips any file already present at the expected size.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"out_dir": str(out_dir), "files": []}

    total_expected = sum(f.expected_size_bytes for f in files)
    print(f"DeepScoresV2 download plan:", file=sys.stderr)
    print(f"  target dir:    {out_dir}", file=sys.stderr)
    print(f"  files:         {len(files)}", file=sys.stderr)
    print(f"  total size:    ~{_human(total_expected)}", file=sys.stderr)
    print(file=sys.stderr)

    for f in files:
        dst = out_dir / f.name
        entry: dict = {
            "name": f.name,
            "url": f.url,
            "dst": str(dst),
            "expected_size_bytes": f.expected_size_bytes,
        }
        print(f"  {f.name}", file=sys.stderr)
        print(f"    URL:  {f.url}", file=sys.stderr)
        print(f"    dst:  {dst}", file=sys.stderr)
        print(f"    size: ~{_human(f.expected_size_bytes)}", file=sys.stderr)

        if dry_run:
            entry["status"] = "dry-run"
            report["files"].append(entry)
            continue

        if dst.exists() and not force and _verify_size(dst, f.expected_size_bytes):
            print(f"    -> already present, skipping", file=sys.stderr)
            entry["status"] = "skipped"
            report["files"].append(entry)
            continue

        try:
            _download(f.url, dst)
        except Exception as exc:  # noqa: BLE001
            print(f"    -> FAILED: {exc}", file=sys.stderr)
            entry["status"] = "failed"
            entry["error"] = str(exc)
            report["files"].append(entry)
            continue

        if not _verify_size(dst, f.expected_size_bytes):
            print(
                f"    -> WARNING: size mismatch (got {_human(dst.stat().st_size)})",
                file=sys.stderr,
            )
            entry["status"] = "size_mismatch"
        elif f.sha256 and not _verify_sha256(dst, f.sha256):
            print(f"    -> WARNING: sha256 mismatch", file=sys.stderr)
            entry["status"] = "sha256_mismatch"
        else:
            print(f"    -> OK", file=sys.stderr)
            entry["status"] = "ok"
        report["files"].append(entry)

    print(file=sys.stderr)
    print(
        "Next: extract the archive(s) (`tar -xzf ds2_dense.tar.gz -C <out_dir>`) "
        "then run `prepare_yolo_data.py`.",
        file=sys.stderr,
    )
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--out",
        default="data/deepscoresv2",
        help="Output directory (default: data/deepscoresv2)",
    )
    ap.add_argument(
        "--full",
        action="store_true",
        help="Download the full ~80 GB dataset instead of the ~6.5 GB dense subset",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned URLs and target paths, do not download",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the target file already exists at expected size",
    )
    args = ap.parse_args(argv)

    files = FULL_FILES if args.full else DENSE_FILES
    out_dir = Path(args.out)
    report = download_dataset(
        out_dir=out_dir, files=files, dry_run=args.dry_run, force=args.force,
    )
    # Print a final JSON summary on stdout for callers / tests that want
    # to inspect the result programmatically.
    import json
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
