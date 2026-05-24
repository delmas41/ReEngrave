#!/usr/bin/env python3
"""Move Beethoven symphony IMSLP PDFs from ~/Downloads/IMSLP/ into the per-work training layout.

Filename convention assumed (matches Sean's IMSLP downloads):
    Beethoven_Symphony_No{N}_IMSLP{ID}[-PMLP{PMLP_ID}]-{descriptor}.pdf

Target:
    {repo_root}/tools/omr/training/data/imslp/beethoven-symphony-{N}/pdfs/imslp-{ID}/
        ├── score.pdf
        └── metadata.yaml

Idempotent — files already at the target are skipped. Source files are MOVED (not copied)
to save disk; original ~/Downloads/IMSLP/ acts as a staging area.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

SOURCE = Path.home() / "Downloads/IMSLP"
TARGET_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp")

FILENAME_RE = re.compile(r"^Beethoven_Symphony_No(\d+)_IMSLP(\d+)-(.+)\.pdf$")

PUBLISHER_KEYWORDS = [
    ("breitkopf", "breitkopf", "Breitkopf & Härtel"),
    ("unger",     "eulenburg-unger", "Eulenburg, ed. Max Unger"),
    ("haslinger", "haslinger", "Tobias Haslinger, Vienna"),
    ("ricordi",   "ricordi", "Ricordi, Milan"),
    ("eulenburg", "eulenburg", "Eulenburg study score"),
    ("schott",    "schott", "Schott, Mainz"),
    ("sakamoto",  "sakamoto", "Modern Japanese (Sakamoto)"),
    ("japan",     "japan", "Modern Japanese"),
]


def guess_publisher(descriptor: str) -> tuple[str, str]:
    lower = descriptor.lower()
    for keyword, slug, label in PUBLISHER_KEYWORDS:
        if keyword in lower:
            return slug, label
    return "", ""


def main() -> int:
    if not SOURCE.exists():
        print(f"Source missing: {SOURCE}", file=sys.stderr)
        return 1

    moved = skipped = errors = 0
    for pdf in sorted(SOURCE.glob("*.pdf")):
        m = FILENAME_RE.match(pdf.name)
        if not m:
            print(f"  ! unparseable filename: {pdf.name}", file=sys.stderr)
            errors += 1
            continue

        sym_n, imslp_id, descriptor = m.groups()
        target_dir = TARGET_ROOT / f"beethoven-symphony-{sym_n}" / "pdfs" / f"imslp-{imslp_id}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_pdf = target_dir / "score.pdf"
        meta_file = target_dir / "metadata.yaml"

        if target_pdf.exists():
            skipped += 1
            continue

        shutil.move(str(pdf), str(target_pdf))

        publisher_slug, publisher_label = guess_publisher(descriptor)
        meta_file.write_text(
            f"imslp_id: {imslp_id}\n"
            f"imslp_url: https://imslp.org/wiki/Special:ReverseLookup/{imslp_id}\n"
            f"original_filename: {pdf.name}\n"
            f"work: Beethoven Symphony No. {sym_n}\n"
            f"publisher: \"{publisher_label}\"\n"
            f"publisher_slug: \"{publisher_slug}\"\n"
            f"year: \"\"\n"
            f"plate_number: \"\"\n"
            f"country: \"\"\n"
            f"confirmed: false\n"
            f"notes: \"\"\n"
        )
        moved += 1
        size_mb = target_pdf.stat().st_size // (1024 * 1024)
        tag = f"[{publisher_slug}]" if publisher_slug else "[?]"
        print(f"  {tag:>20s}  beethoven-symphony-{sym_n}/pdfs/imslp-{imslp_id}/  ({size_mb} MB)")

    print(f"\nMoved: {moved}, skipped: {skipped}, errors: {errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
