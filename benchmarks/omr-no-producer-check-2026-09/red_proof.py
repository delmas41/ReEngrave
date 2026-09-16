#!/usr/bin/env python3
"""RED PROOF — inject a THIRD no-producer parameter into the real tree.

⚠️ `A check that cannot fail is worse than no check.` The unit tests prove the
mechanism on synthetic trees; this proves it on the ACTUAL `tools/` tree, on
files the check has already reported as clean, so a walk that silently stopped
examining `tools/` would still pass the synthetic tests and fail here.

It copies `tools/` to a scratch directory, adds one parameter threaded through
two real functions with nobody supplying it, and asserts the check names it.
**Nothing under the repo is written.**

    python3 benchmarks/omr-no-producer-check-2026-09/red_proof.py

Exits non-zero if the injected parameter is NOT caught, or if the control arm
(the same copy, unmutated) does not reproduce the tree's own findings.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr import no_producer as NP  # noqa: E402


# The injection. `rank_pages` is threaded from `transcribe` into an existing
# helper; no call site anywhere starts it, and the consumer abstains without
# it — the `pdf_path` shape exactly.
INJECTIONS = [
    (
        "omr/export_coverage.py",
        "def load_run(work: str, fixtures: Path | None = None) -> Run | None:",
        "def load_run(work: str, fixtures: Path | None = None,\n"
        "             rank_pages=None) -> Run | None:\n"
        "    if rank_pages is None:\n"
        "        print('no rank_pages supplied')\n"
        "        return None",
    ),
    (
        "omr/export_coverage.py",
        "def compare(",
        "def _inject_caller(work, rank_pages=None):\n"
        "    return load_run(work, rank_pages=rank_pages)\n\n\n"
        "def compare(",
    ),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="no-producer-red-"))
    dst = tmp / "tools"
    shutil.copytree(REPO / "tools", dst,
                    ignore=shutil.ignore_patterns("data", "__pycache__", "node_modules"))

    control = NP.scan([dst])
    base = {f.param for f in control.findings}
    print(f"CONTROL (unmutated copy of tools/): {sorted(base)}")
    if base != {"roster", "dossier"}:
        print("FAIL: the control arm does not reproduce the tree's own findings; "
              "the copy or the check is wrong, and the mutation arm below would "
              "be measuring that instead.", file=sys.stderr)
        return 2

    for rel, needle, replacement in INJECTIONS:
        p = dst / rel
        src = p.read_text()
        if needle not in src:
            print(f"FAIL: anchor not found in {rel}: {needle!r}", file=sys.stderr)
            return 2
        if src.count(needle) != 1:
            print(f"FAIL: anchor occurs {src.count(needle)} times in {rel} — a "
                  f"battery that mutates the wrong occurrence tests a different "
                  f"function.", file=sys.stderr)
            return 2
        p.write_text(src.replace(needle, replacement))

    mutated = NP.scan([dst])
    found = {f.param for f in mutated.findings}
    print(f"MUTATED (one injected chain):      {sorted(found)}")
    shutil.rmtree(tmp, ignore_errors=True)

    if "rank_pages" not in found:
        print("FAIL: the injected no-producer parameter was NOT caught. The "
              "check is not red-capable on the real tree.", file=sys.stderr)
        return 1
    print("\nOK — the check goes RED on a third instance it was never told about.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
