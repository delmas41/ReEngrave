"""Write the page-normalised truth for a scan-gate row, reusing the
staves-map-completion session's own candidate maps and its probe-time
`page_normalise` patches.

Nothing here is a new truth: `candidate_maps` transcribes what `works.json`
already holds for the Mahler rows, and `normalise_patched` is that session's
labelled *not the fix* monkeypatch for two latent `page_normalise` faults.

This exists because the one-line percussion question has TWO eras and they give
opposite answers. In the shipped era Mahler's truth carries 38 encoded parts
against our 17 printed staves, so a part added in the middle only re-shuffles
which parts musicdiff's monotonic alignment sheds. In the normalised era the
truth is 21 parts against 21 printed staves — and the 4 one-line percussion
entries are 4 of that 21, so they are exactly the parts a five-line-only
prediction cannot supply.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
COMPLETION = ROOT / "benchmarks" / "omr-staves-map-completion-2026-09"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))
sys.path.insert(0, str(COMPLETION))

import page_normalise                      # noqa: E402
import candidate_maps                      # noqa: E402
import normalise_patched                   # noqa: E402

REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")
OUT = HERE / "derived-truth"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="*", default=None)
    args = ap.parse_args(argv)
    normalise_patched.apply()
    OUT.mkdir(exist_ok=True)
    rows = args.rows or [r for r in candidate_maps.CANDIDATES
                         if r.startswith("mahler")]
    for rid in rows:
        truth = REC / f"{rid}.truth.musicxml"
        dst = OUT / f"{rid}.normalised.musicxml"
        rep = page_normalise.write(truth, candidate_maps.flat(rid), dst)
        print(f"{rid}: {rep['n_source_parts']} -> {rep['n_output_parts']} parts"
              f"  -> {dst.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
