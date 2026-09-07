#!/usr/bin/env python3
"""Cut two pages — one SCAN, one ENGRAVED — into an arm directory.

Feeds `benchmarks/omr-pipeline-audit-2026-09/probe/compare_arms.py`, which is
the comparator the barline-evidence change already used; this only produces
the arms it eats (`<name>.json` + `<name>.musicxml` per page).

Both pages are named here rather than passed in, so the two arms cannot
silently be different pages. Inputs resolve from `__file__` — never the CWD —
and a missing one is a non-zero exit, not an empty arm that compares clean.

    python3 .../probe/run_arms.py <arm-dir>

⚠️ `--no-direction-text --no-contextual`: the comparator's determinism control
was established under those flags, and they also keep this off the shared
Surya/llama-server entirely.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# `library/` and the e2e fixtures are machine-local and gitignored, and in a
# git worktree they live in the MAIN checkout. Resolve there when the worktree
# has no copy of its own — the alternative is a probe that prints clean zeros
# from the wrong tree, which has already caused one false retraction here.
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")

PAGES = [
    # (name, pdf relative to a root, page index, dpi)
    # The scan benchmark's own first row: Beethoven 5 / Litolff 1870, bitonal.
    ("scan-beethoven5-litolff-p1",
     "library/editions/beethoven/symphony-5-op67/"
     "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
     1, 600),
    # An engraved orchestral fixture — the other family entirely.
    ("engraved-brahms1", "benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.pdf",
     0, 600),
]


def resolve(rel: str) -> Path:
    for root in (REPO, MAIN):
        p = root / rel
        if p.is_file():
            return p
    sys.exit(f"FATAL: input not found in {REPO} or {MAIN}: {rel}")


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(f"usage: {Path(__file__).name} <arm-dir>")
    arm = Path(sys.argv[1]).resolve()
    arm.mkdir(parents=True, exist_ok=True)
    made = 0
    for name, rel, page, dpi in PAGES:
        pdf = resolve(rel)
        js, mx = arm / f"{name}.json", arm / f"{name}.musicxml"
        print(f"[{name}] {pdf}  page {page} @ {dpi}dpi", flush=True)
        subprocess.run(
            [sys.executable, "-u", "-m", "tools.omr.transcribe", str(pdf),
             "--pages", str(page), "--dpi", str(dpi), "--out", str(js),
             "--no-direction-text", "--no-contextual"],
            cwd=REPO, check=True,
        )
        subprocess.run(
            [sys.executable, "-u", "-m", "tools.omr.export", str(js),
             "--format", "musicxml", "--out", str(mx)],
            cwd=REPO, check=True,
        )
        if not js.is_file() or not mx.is_file() or mx.stat().st_size == 0:
            sys.exit(f"FATAL: {name} produced no usable output")
        made += 1
    if made != len(PAGES):
        sys.exit(f"FATAL: made {made} of {len(PAGES)} pages")
    print(f"OK: {made} pages -> {arm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
