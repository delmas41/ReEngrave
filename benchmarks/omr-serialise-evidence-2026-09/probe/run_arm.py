#!/usr/bin/env python3
"""Transcribe + export one scanned page and one engraved page into an arm dir.

Produces `<name>.json` + `<name>.musicxml` per page, the layout
`benchmarks/omr-pipeline-audit-2026-09/probe/compare_arms.py` expects.

Two pages on purpose, and they are the two the `Barline` docstring's
connectivity table was measured on:

* **scan** — Beethoven 5 / Litolff, `pdf_page_index` 1, the scan-gate row
  `beethoven-sym5-mvt1-984073-p1`. A conductor's page: barlines cross the
  inter-staff gaps, so connectivity gates.
* **engraved** — the LilyPond `brahms-sym1-mvt1` fixture, page 0. An OPEN
  SCORE: LilyPond bars per staff, `barlines_cross_gaps` False, the votes
  stand alone.

⚠️ Run with `--no-direction-text --no-contextual` equivalents (they are the
defaults here) — those two rungs are nondeterministic enough to swamp a
byte-identity check, which is why `compare_arms.py`'s own control was taken
that way.

    python3 run_arm.py <out-dir>

⚠️ Inputs are resolved from `__file__` / `OMR_FIXTURE_ROOT`, never the CWD,
and a missing input is a non-zero exit rather than an arm with one page in it.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))

# Gitignored build products: the score library and the e2e fixtures. Both live
# in the MAIN checkout, not in a worktree — see CLAUDE.md's symlink note.
FIXTURE_ROOT = Path(os.environ.get("OMR_FIXTURE_ROOT", "/Users/seanjohnson/Desktop/ReEngrave"))

PAGES = {
    "beet5-984073-p1": (
        FIXTURE_ROOT / "library/editions/beethoven/symphony-5-op67"
        / "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        1,
    ),
    "brahms-sym1-mvt1-engraved-p0": (
        FIXTURE_ROOT / "benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.pdf",
        0,
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    missing = [str(p) for p, _ in PAGES.values() if not p.is_file()]
    if missing:
        print("REFUSING: input PDF(s) not found:\n  " + "\n  ".join(missing)
              + "\n  Set OMR_FIXTURE_ROOT to a checkout that has them.",
              file=sys.stderr)
        return 3

    from tools.omr.transcribe import transcribe
    from tools.omr.export import to_musicxml

    wanted = {k: v for k, v in PAGES.items() if args.only in (None, k)}
    if not wanted:
        print(f"REFUSING: --only {args.only!r} matched no page", file=sys.stderr)
        return 3

    for name, (pdf, page_index) in wanted.items():
        print(f"--- {name}: {pdf.name} page {page_index}", flush=True)
        result = transcribe(
            pdf_path=pdf,
            pages=[page_index],
            dpi=600,
            contextual=False,
            read_direction_text=False,
            progress=False,
        )
        (out / f"{name}.json").write_text(json.dumps(result, indent=1, default=str))
        (out / f"{name}.musicxml").write_text(to_musicxml(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
